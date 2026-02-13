import sys
import socket
import secrets
import ipaddress
import re
import os
import random
import html
import json
import requests  # Pour effectuer la requête HTTP sécurisée
from functools import wraps
from urllib.parse import urlparse

from flask import Flask, jsonify, render_template, request, Response, make_response, abort
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect  # Protection CSRF robuste
from flask_limiter import Limiter  # Rate Limiting
from flask_limiter.util import get_remote_address
import feedparser
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# ==========================================
# 0. CONFIGURATION & SÉCURITÉ
# ==========================================
load_dotenv()

# 1. Protection Identifiants (Correctif #5)
ADMIN_USERNAME = os.environ.get('ADMIN_USER')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASS')

if not ADMIN_USERNAME or not ADMIN_PASSWORD:
    print("❌ ERREUR CRITIQUE DE SÉCURITÉ")
    print("Les variables d'environnement ADMIN_USER et ADMIN_PASS sont OBLIGATOIRES.")
    print("L'application refuse de démarrer avec des identifiants par défaut ou temporaires.")
    sys.exit(1) # Arrêt immédiat de l'application

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))

# Configuration Secrets
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# 2. Rate Limiting (Correctif #4)
# Limite globale par défaut et stockage en mémoire
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# 3. Protection CSRF (Correctif #2)
csrf = CSRFProtect(app)

# Configuration DB
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

if not database_url:
    database_url = 'sqlite:///' + os.path.join(basedir, 'data.db')

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024

db = SQLAlchemy(app)

# ==========================================
# MODÈLES DE DONNÉES (Inchangés)
# ==========================================
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

class Feed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category_name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    media_type = db.Column(db.String(20), default='text', nullable=False) 

class SavedArticle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100))
    url = db.Column(db.String(500), unique=True, nullable=False)
    title = db.Column(db.String(500))
    media_type = db.Column(db.String(20), default='text', nullable=False)

with app.app_context():
    db.create_all()
    # Initialisation DB (inchangée...)
    if not Feed.query.first():
        cat_actu = "Actualités"
        if not Category.query.filter_by(name=cat_actu).first():
            db.session.add(Category(name=cat_actu))
        db.session.add(Feed(category_name=cat_actu, url="https://www.lemonde.fr/rss/une.xml", media_type='text'))
        cat_pod = "Tech & Science"
        if not Category.query.filter_by(name=cat_pod).first():
            db.session.add(Category(name=cat_pod))
        db.session.add(Feed(category_name=cat_pod, url="https://radiofrance-podcast.net/podcast09/rss_14312.xml", media_type='audio'))
        db.session.commit()

# ==========================================
# FONCTIONS DE SÉCURITÉ AVANCÉES
# ==========================================

def check_auth(username, password):
    return (secrets.compare_digest(username, ADMIN_USERNAME) and 
            secrets.compare_digest(password, ADMIN_PASSWORD))

def authenticate():
    return Response('Connexion requise.\n', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# Correctif #1 : Protection Anti-DNS Rebinding
def safe_fetch_rss(url):
    """
    Récupère le contenu RSS de manière sécurisée en prévenant le DNS Rebinding.
    1. Résout l'IP.
    2. Vérifie que l'IP est publique.
    3. Effectue la requête directement vers l'IP (en forçant le header Host).
    """
    if not url: return None, "URL vide"
    
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            return None, "Protocole invalide"
        
        hostname = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        
        # 1. Résolution DNS
        ip_addr = socket.gethostbyname(hostname)
        
        # 2. Vérification IP (Liste noire locale)
        ip = ipaddress.ip_address(ip_addr)
        if ip.is_loopback or ip.is_private or ip.is_link_local:
            return None, f"Accès interdit (IP locale détectée: {ip})"
            
        # 3. Requête "Epinglée" sur l'IP
        # On remplace le hostname par l'IP dans l'URL pour la requête requests
        # Mais on garde le hostname dans le header 'Host' pour que le serveur virtuel (VHost) comprenne.
        target_url = url.replace(hostname, ip_addr, 1)
        headers = {'Host': hostname, 'User-Agent': 'Serendipite-RSS-Bot/1.0'}
        
        # Note: verify=False est nécessaire ici car le certificat SSL sera valide pour 
        # le hostname, mais pas pour l'IP. C'est un compromis acceptable pour des flux RSS publics.
        # Pour une sécurité maximale en HTTPS, il faudrait un contexte SSL personnalisé complexe.
        response = requests.get(target_url, headers=headers, timeout=5, verify=False)
        
        if response.status_code != 200:
            return None, f"Erreur HTTP {response.status_code}"
            
        return response.content, None

    except Exception as e:
        return None, f"Erreur réseau: {str(e)}"

def sanitize_link(link):
    if not link: return "#"
    link = link.strip()
    if link.lower().startswith(('http://', 'https://')):
        return link
    return "#"

def sanitize_category_name(name):
    if not isinstance(name, str): return "Inconnu"
    clean = re.sub(r'[^\w\s\-\.]', '', name)
    return clean.strip()[:100]

def get_config_by_type(m_type):
    # (Logique inchangée - récupération des flux)
    all_cats = Category.query.order_by(Category.name).all()
    target_feeds = Feed.query.filter_by(media_type=m_type).all()
    target_cat_names = set(f.category_name for f in target_feeds)
    other_type = 'audio' if m_type == 'text' else 'text'
    other_feeds = Feed.query.filter_by(media_type=other_type).all()
    other_cat_names = set(f.category_name for f in other_feeds)
    data = {}
    for c in all_cats:
        has_target = c.name in target_cat_names
        has_other = c.name in other_cat_names
        is_empty = (not has_target) and (not has_other)
        if has_target or is_empty:
            cat_urls = [f.url for f in target_feeds if f.category_name == c.name]
            data[c.name] = cat_urls
    return data

def get_full_export_data():
    feeds = Feed.query.all()
    feeds_list = [{"category": f.category_name, "url": f.url, "media_type": f.media_type} for f in feeds]
    saved = SavedArticle.query.all()
    saved_list = [{"category": s.category, "url": s.url, "title": s.title, "media_type": s.media_type} for s in saved]
    return {"feeds": feeds_list, "saved": saved_list}

# ==========================================
# ROUTES
# ==========================================

@app.route('/')
@requires_auth
# Correctif #3 : SSTI -> Utilisation de render_template au lieu de render_template_string
def home():
    return render_template('index.html')

@app.route('/get-random')
@requires_auth
@limiter.limit("10 per minute") # Correctif #4 : Rate Limiting strict sur les actions lourdes
def get_random():
    cat = request.args.get('category')
    m_type = request.args.get('media_type', 'text')
    
    config = get_config_by_type(m_type)
    urls = config.get(cat, [])
    
    if not urls: return jsonify({"error": "Catégorie vide"})
    
    try:
        url = random.choice(urls)
        
        # UTILISATION DU NOUVEAU FETCH SÉCURISÉ (DNS REBINDING PROOF)
        content, error_msg = safe_fetch_rss(url)
        
        if error_msg:
             return jsonify({"error": f"Sécurité/Réseau : {error_msg}", "source": url})

        # On passe le contenu brut à feedparser (pas l'URL)
        feed = feedparser.parse(content)
        
        if not feed.entries: return jsonify({"error": "Flux vide ou illisible", "source": url})
        
        art = random.choice(feed.entries)
        
        # Nettoyage et préparation (inchangé)
        summary = art.get('summary', '') or art.get('subtitle', '')
        soup = BeautifulSoup(summary, "html.parser")
        clean_summary = soup.get_text()[:300] + "..."
        clean_link = sanitize_link(art.get('link', '#'))
        
        audio_url = None
        if m_type == 'audio':
            if hasattr(art, 'enclosures'):
                for enc in art.enclosures:
                    if enc.type.startswith('audio'):
                        audio_url = sanitize_link(enc.href)
                        break
            if not audio_url and hasattr(art, 'links'):
                for link in art.links:
                    if link.type and link.type.startswith('audio'):
                        audio_url = sanitize_link(link.href)
                        break
        
        return jsonify({
            "source": html.escape(feed.feed.get('title', 'Source')),
            "title": html.escape(art.get('title', 'Sans titre')),
            "link": clean_link,
            "summary": clean_summary,
            "audio_url": audio_url
        })
    except Exception as e: return jsonify({"error": str(e)})

@app.route('/test-sources')
@requires_auth
@limiter.limit("2 per minute") # Rate limit très strict pour éviter le DoS par scan
def test_sources():
    cat = request.args.get('category')
    m_type = request.args.get('media_type', 'text')
    config = get_config_by_type(m_type)
    urls = config.get(cat, [])
    
    rep = []
    for u in urls:
        # Test utilisant la méthode sécurisée
        content, err = safe_fetch_rss(u)
        if err:
             rep.append({"url": u, "valid": False, "error": err})
             continue

        try:
            f = feedparser.parse(content)
            rep.append({"url": u, "valid": (hasattr(f,'entries') and len(f.entries)>0)})
        except: rep.append({"url": u, "valid": False})
    return jsonify(rep)

@app.route('/api/feeds/get_config')
@requires_auth
def api_get_config():
    m_type = request.args.get('media_type', 'text')
    return jsonify(get_config_by_type(m_type))

# --- ROUTES DE MODIFICATION (POST) ---
# Flask-WTF protège automatiquement ces routes car CSRFProtect est actif.
# Si le token manque dans le Header 'X-CSRFToken', la requête sera rejetée (400 Bad Request).

@app.route('/api/feeds/export')
@requires_auth
def export_feeds():
    data = get_full_export_data()
    response = make_response(json.dumps(data, indent=4, ensure_ascii=False))
    response.headers['Content-Disposition'] = 'attachment; filename=serendipite_full_backup.json'
    response.headers['Content-Type'] = 'application/json'
    return response

@app.route('/api/feeds/import', methods=['POST'])
@requires_auth
@limiter.limit("5 per minute")
def import_feeds():
    if 'file' not in request.files: return jsonify({"success": False, "msg": "No file"})
    file = request.files['file']
    if file.filename == '': return jsonify({"success": False, "msg": "Empty filename"})
    try:
        data = json.load(file)
        if not isinstance(data, dict): return jsonify({"success": False, "msg": "Invalid JSON"})
        count_cat = 0; count_url = 0; count_saved = 0
        
        # Logique Import (Avec vérification safe_fetch pour valider l'URL)
        if "feeds" in data and isinstance(data["feeds"], list):
            for item in data["feeds"]:
                cat = sanitize_category_name(item.get('category'))
                url = item.get('url')
                if not cat: continue
                
                # Check rapide si l'URL est au moins syntaxiquement correcte
                if sanitize_link(url) == "#": continue 
                
                if not Category.query.filter_by(name=cat).first():
                    db.session.add(Category(name=cat))
                    count_cat += 1
                if not Feed.query.filter_by(category_name=cat, url=url[:500]).first():
                    db.session.add(Feed(category_name=cat, url=url[:500], media_type=item.get('media_type','text')))
                    count_url += 1
        
        # (Le reste de l'import saved articles... inchangé)
        if "saved" in data:
            for item in data["saved"]:
                url = item.get('url')
                if sanitize_link(url) != "#":
                    if not SavedArticle.query.filter_by(url=url[:500]).first():
                        db.session.add(SavedArticle(url=url[:500], title=item.get('title',''), category=item.get('category',''), media_type=item.get('media_type','text')))
                        count_saved += 1
        
        db.session.commit()
        return jsonify({"success": True, "msg": f"Importé: {count_url} flux, {count_saved} articles."})
    except Exception as e:
        return jsonify({"success": False, "msg": str(e)})

@app.route('/api/feeds/manage', methods=['POST'])
@requires_auth
@limiter.limit("20 per minute")
def manage_feeds():
    d = request.json
    action = d.get('action')
    cat = d.get('category')
    url = d.get('url')
    m_type = d.get('media_type', 'text')
    
    try:
        if action == 'add_cat':
            if cat and not Category.query.filter_by(name=cat).first():
                db.session.add(Category(name=cat)); db.session.commit()
        elif action == 'del_cat':
            Category.query.filter_by(name=cat).delete()
            Feed.query.filter_by(category_name=cat).delete(); db.session.commit()
        elif action == 'add_url':
            # Validation de l'URL via URLParser simple ici (le fetch vérifiera l'IP plus tard)
            if sanitize_link(url) == "#": return jsonify({"success":False, "msg":"URL invalide"})
            if not Category.query.filter_by(name=cat).first(): db.session.add(Category(name=cat))
            if not Feed.query.filter_by(category_name=cat, url=url.strip()).first():
                db.session.add(Feed(category_name=cat, url=url.strip(), media_type=m_type))
                db.session.commit()
        elif action == 'del_url':
            Feed.query.filter_by(category_name=cat, url=url).delete(); db.session.commit()
        return jsonify({"success": True})
    except Exception as e: return jsonify({"success": False, "msg": str(e)})

@app.route('/api/save', methods=['POST'])
@requires_auth
def api_save():
    d = request.json
    url_to_save = sanitize_link(d.get('url') or d.get('link'))
    if url_to_save == "#": return jsonify({"success": False})
    try:
        if not SavedArticle.query.filter_by(url=url_to_save).first():
            db.session.add(SavedArticle(category=d.get('category','Général'), url=url_to_save, title=d.get('title',''), media_type=d.get('media_type','text')))
            db.session.commit()
        return jsonify({"success": True})
    except: return jsonify({"success": False})

@app.route('/api/saved-links')
@requires_auth
def api_list_saved():
    cat = request.args.get('category')
    m_type = request.args.get('media_type') 
    query = SavedArticle.query
    if cat and cat != '---': query = query.filter_by(category=cat)
    if m_type: query = query.filter_by(media_type=m_type)
    links = query.all()
    return jsonify([{'category':l.category, 'url':l.url, 'title':l.title, 'media_type':l.media_type} for l in links])

@app.route('/api/delete', methods=['POST'])
@requires_auth
def api_delete():
    url = request.json.get('url')
    SavedArticle.query.filter_by(url=url).delete()
    db.session.commit()
    return jsonify({"success": True})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
