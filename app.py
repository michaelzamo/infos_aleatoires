from flask import Flask, jsonify, render_template_string, request, Response
from flask_sqlalchemy import SQLAlchemy
import feedparser
import random
import os
import html
from functools import wraps
from dotenv import load_dotenv

# Charge les variables d'environnement
load_dotenv()

app = Flask(__name__)

# ==========================================
# CONFIGURATION ROBUSTE
# ==========================================
basedir = os.path.abspath(os.path.dirname(__file__))

ADMIN_USERNAME = os.environ.get('ADMIN_USER')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASS')

if not ADMIN_USERNAME or not ADMIN_PASSWORD:
    print("⚠️  ATTENTION : Identifiants par défaut (admin/changezMoi123)")
    ADMIN_USERNAME = 'admin'
    ADMIN_PASSWORD = 'changezMoi123'

# Configuration BDD : Priorité à PostgreSQL (Render), sinon SQLite avec chemin ABSOLU (Local)
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

if not database_url:
    # Correction critique : Chemin absolu pour éviter que le fichier ne disparaisse
    database_url = 'sqlite:///' + os.path.join(basedir, 'data.db')

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ==========================================
# MODÈLES (TABLES)
# ==========================================
# Nouvelle table pour gérer les catégories vides
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

class Feed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category_name = db.Column(db.String(100), nullable=False) # Lien par nom pour simplifier le JS
    url = db.Column(db.String(500), nullable=False)

class SavedArticle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100))
    url = db.Column(db.String(500), unique=True, nullable=False)
    title = db.Column(db.String(500))

# Initialisation BDD
with app.app_context():
    db.create_all()
    # Données par défaut si vide
    if not Category.query.first():
        default_cat = "Actualités"
        db.session.add(Category(name=default_cat))
        db.session.add(Feed(category_name=default_cat, url="https://www.lemonde.fr/rss/une.xml"))
        db.session.commit()

# ==========================================
# SÉCURITÉ
# ==========================================
def check_auth(username, password):
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD

def authenticate():
    return Response(
    'Connexion requise.\n', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

def is_safe_url(url):
    if not url: return False, "URL vide"
    url_lower = url.strip().lower()
    if not url_lower.startswith(('http://', 'https://')):
        return False, "Protocole invalide (http ou https requis)"
    
    forbidden_hosts = [
        'localhost', '127.', '0.0.0.0', '192.168.', '10.', '172.16.', '172.17.', 
        '169.254.', '::1', 'fd00:'
    ]
    for host in forbidden_hosts:
        if f"//{host}" in url_lower or f"@{host}" in url_lower or url_lower.startswith(host):
             return False, "Les adresses locales/privées sont interdites."
    return True, ""

# ==========================================
# LOGIQUE MÉTIER
# ==========================================
def get_full_config():
    # On récupère d'abord toutes les catégories (même vides)
    cats = Category.query.all()
    data = {c.name: [] for c in cats}
    
    # On remplit avec les flux
    feeds = Feed.query.all()
    for f in feeds:
        if f.category_name in data:
            data[f.category_name].append(f.url)
        else:
            # Cas rare : flux orphelin, on recrée la catégorie dans la structure
            data[f.category_name] = [f.url]
    return data

# ==========================================
# FRONTEND
# ==========================================
@app.route('/')
@requires_auth
def home():
    feeds_config = get_full_config()
    categories = list(feeds_config.keys())
    if not categories: categories = ["Aucune catégorie"]

    return render_template_string('''
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Info Aléatoire</title>
        <style>
            :root {
                --font-scale: 1;
                --bg-body: #f0f2f5; --bg-card: #ffffff;
                --text-main: #333; --text-sub: #666;
                --tag-bg: #e9ecef; --select-bg: #f9f9f9; --select-border: #ddd;
                --col-primary: #007bff; --col-success: #28a745; --col-error: #dc3545; 
                --col-save: #6c757d; --col-manage: #6610f2;
                --border-rad: 16px;
                --shadow: 0 10px 25px rgba(0,0,0,0.05);
            }
            body.dark-mode {
                --bg-body: #121212; --bg-card: #1e1e1e;
                --text-main: #e0e0e0; --text-sub: #aaaaaa;
                --tag-bg: #333; --select-bg: #2c2c2c; --select-border: #444;
                --shadow: rgba(0,0,0,0.5);
            }
            body.protanopia, body.deuteranopia { --col-primary: #0072B2; --col-success: #56B4E9; --col-error: #D55E00; }
            body.tritanopia { --col-primary: #000000; --col-success: #009E73; --col-error: #CC79A7; }
            body.achromatopsia { --col-primary: #000000; --col-success: #000000; --col-error: #000000; }
            body.dark-mode.achromatopsia { --col-primary: #ffffff; --col-success: #ffffff; --col-error: #ffffff; }

            body { 
                font-family: "Noto Sans", sans-serif; display: flex; justify-content: center; align-items: center; 
                min-height: 100vh; margin: 0; padding: 20px; box-sizing: border-box;
                background-color: var(--bg-body); color: var(--text-main);
                transition: background 0.3s;
                font-size: calc(16px * var(--font-scale));
            }

            .settings-container {
                display:flex; flex-direction:column; gap:10px; margin-bottom:20px; 
                background:var(--tag-bg); padding:10px; border-radius:8px;
                font-size: 1rem !important; 
            }
            .settings-container select, .settings-container input, .settings-container span, .settings-container label {
                font-size: 1em !important; 
            }
            button, select, input { font-size: 1em; }

            .card { 
                background: var(--bg-card); padding: 2rem; border-radius: var(--border-rad); 
                box-shadow: var(--shadow); max-width: 500px; width: 100%; 
                max-height: 90vh; overflow-y: auto;
            }
            .header-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
            .theme-toggle { background: none; border: none; cursor: pointer; padding: 5px; font-size: 1.2em; }
            
            .settings-row { display:flex; justify-content:space-between; align-items:center; }
            .setting-label { font-size:0.8em; font-weight:bold; color:var(--text-sub); }
            .a11y-select { padding:4px; border-radius:4px; border:1px solid var(--select-border); background:var(--select-bg); color:var(--text-main); max-width:120px;}
            
            .cat-row { display:flex; gap:10px; align-items:center; margin-bottom:15px; }
            .cat-select { flex-grow:1; padding:10px; border-radius:8px; border:1px solid var(--select-border); background:var(--select-bg); color:var(--text-main); }
            .btn-manage { background:none; border:none; font-size:1.5em; cursor:pointer; color:var(--col-manage); padding:0 5px;}
            
            .action-buttons { display:flex; flex-direction:column; gap:10px; align-items:center; margin-top:20px; }
            .btn { background:var(--col-primary); color:#fff; padding:12px 25px; border-radius:50px; border:none; font-weight:600; width:80%; cursor:pointer; }
            .btn-save { background:var(--col-save); display:none; }
            .btn-read { background:var(--col-success); }
            .btn-test { background:none; border:none; color:var(--text-sub); margin-top:20px; cursor:pointer; text-decoration:underline; font-size:0.8em; }

            #managerSection { display:none; background:var(--bg-body); padding:15px; border-radius:8px; border:1px solid var(--select-border); margin-bottom:20px; }
            .man-title { font-weight:bold; margin-bottom:10px; border-bottom:1px solid var(--select-border); padding-bottom:5px; }
            .man-row { display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; font-size:0.9em; }
            .man-input { flex-grow:1; margin-right:5px; padding:5px; border-radius:4px; border:1px solid var(--select-border); background:var(--select-bg); color:var(--text-main); }
            .btn-small { padding:5px 10px; border-radius:4px; border:none; cursor:pointer; color:white; font-size:0.8em; }
            .btn-add { background:var(--col-success); }
            .btn-del { background:var(--col-error); margin-left:5px;}
            .feed-list { margin-left:10px; margin-top:5px; border-left:2px solid var(--select-border); padding-left:10px; }

            .list-item { display:flex; justify-content:space-between; align-items:center; padding:8px 0; border-bottom:1px solid var(--select-border); font-size:0.9em; }
            .list-label { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; margin-right:10px; flex-grow:1; text-align:left; }
            .status-ok { color:var(--col-success); font-weight:bold; }
            .status-err { color:var(--col-error); font-weight:bold; }
            .source-tag { background:var(--tag-bg); padding:4px 10px; border-radius:20px; font-size:0.8em; font-weight:bold; color:var(--text-sub); }
        </style>
    </head>
    <body>
        <div class="card">
            <div class="header-row">
                <h1 data-i18n="app_title">Sérendipité</h1>
                <button class="theme-toggle" onclick="toggleTheme()">🌓</button>
            </div>

            <div class="settings-container">
                <div class="settings-row">
                    <span class="setting-label" data-i18n="lbl_lang">LANGUE</span>
                    <select id="langSelect" class="a11y-select" onchange="changeLanguage()">
                        <option value="fr">Français</option><option value="en">English</option>
                        <option value="es">Español</option><option value="jp">日本語</option>
                    </select>
                </div>
                <div class="settings-row">
                    <span class="setting-label" data-i18n="lbl_vision">VISION</span>
                    <select id="colorBlindSelect" class="a11y-select" onchange="changeColorProfile()">
                        <option value="normal" data-i18n="vision_norm">Normale</option>
                        <option value="protanopia">Protanopia</option><option value="deuteranopia">Deuteranopia</option>
                        <option value="tritanopia">Tritanopie</option><option value="achromatopsia">Mono</option>
                    </select>
                </div>
                <div class="settings-row">
                    <span class="setting-label" data-i18n="lbl_size">TAILLE</span>
                    <input type="range" id="fontSlider" min="0.8" max="1.5" step="0.1" value="1" oninput="changeFontSize()">
                </div>
            </div>

            <div id="managerSection">
                <div class="man-title" data-i18n="man_title">Gestion des flux</div>
                <div class="man-row">
                    <input type="text" id="newCatInput" class="man-input" placeholder="Nouvelle catégorie...">
                    <button class="btn-small btn-add" onclick="apiManage('add_cat')" data-i18n="btn_add">Ajouter</button>
                </div>
                <div id="managerContent"></div>
            </div>
            
            <div class="cat-row">
                <select id="categorySelect" class="cat-select" onchange="resetView()">
                    {% for name in categories %}
                        <option value="{{ name }}">{{ name }}</option>
                    {% endfor %}
                </select>
                <button class="btn-manage" onclick="toggleManager()" title="Gérer les flux">⚙️</button>
            </div>

            <div id="content" style="min-height: 100px;">
                <p data-i18n="intro_text">Cliquez pour découvrir.</p>
            </div>
            
            <div class="action-buttons">
                <button class="btn" onclick="fetchRandomArticle()" id="mainBtn" data-i18n="btn_surprise">Surprends-moi</button>
                <button class="btn btn-save" onclick="saveCurrentArticle()" id="saveBtn" data-i18n="btn_save">💾 Sauvegarder</button>
            </div>

            <div style="margin-top:30px; border-top:1px solid #ddd; padding-top:10px;">
                <div style="font-weight:bold; margin-bottom:5px;" data-i18n="lbl_saved">Sauvegardes</div>
                <ul id="savedList" style="list-style:none; padding:0;"></ul>
            </div>

            <button class="btn-test" onclick="runDiagnostics()" data-i18n="btn_test">Tester les flux</button>
            <div id="test-results" style="display:none; margin-top:10px;"></div>
        </div>

        <script>
            let currentData = null;
            const translations = {
                fr: {
                    app_title: "Sérendipité", lbl_lang:"LANGUE", lbl_vision:"VISION", lbl_size:"TAILLE", vision_norm:"Normale",
                    intro_text:"Cliquez pour découvrir.", btn_surprise:"Surprends-moi", btn_save:"💾 Sauvegarder", btn_read:"Lire",
                    btn_test:"Tester / Nettoyer flux", lbl_saved:"Articles sauvegardés", man_title:"Gestion des flux", btn_add:"Ajouter",
                    msg_loading:"Recherche...", status_ok:"OK", status_err:"ERREUR", msg_confirm: "Confirmer la suppression ?"
                },
                en: {
                    app_title: "Serendipity", lbl_lang:"LANGUAGE", lbl_vision:"VISION", lbl_size:"SIZE", vision_norm:"Normal",
                    intro_text:"Click to discover.", btn_surprise:"Surprise me", btn_save:"💾 Save", btn_read:"Read",
                    btn_test:"Test / Clean Feeds", lbl_saved:"Saved Articles", man_title:"Feed Manager", btn_add:"Add",
                    msg_loading:"Searching...", status_ok:"OK", status_err:"ERR", msg_confirm: "Confirm deletion?"
                },
                es: {
                    app_title: "Serendipia", lbl_lang:"IDIOMA", lbl_vision:"VISIÓN", lbl_size:"TAMAÑO", vision_norm:"Normal",
                    intro_text:"Descubrir.", btn_surprise:"Sorpréndeme", btn_save:"💾 Guardar", btn_read:"Leer",
                    btn_test:"Probar / Limpiar", lbl_saved:"Guardados", man_title:"Gestión de feeds", btn_add:"Añadir",
                    msg_loading:"Buscando...", status_ok:"OK", status_err:"ERR", msg_confirm: "¿Confirmar la eliminación?"
                },
                jp: {
                    app_title: "セレンディピティ", lbl_lang:"言語", lbl_vision:"色覚", lbl_size:"サイズ", vision_norm:"通常",
                    intro_text:"発見する。", btn_surprise:"驚かせて", btn_save:"💾 保存", btn_read:"読む",
                    btn_test:"テスト / クリーン", lbl_saved:"保存リスト", man_title:"フィード管理", btn_add:"追加",
                    msg_loading:"検索中...", status_ok:"有効", status_err:"エラー", msg_confirm: "本当に削除しますか？"
                }
            };

            const savedP = localStorage.getItem('colorProfile')||'normal';
            const savedF = localStorage.getItem('fontScale')||'1';
            const savedL = localStorage.getItem('appLang')||'fr';
            
            if(localStorage.getItem('theme')==='dark') document.body.classList.add('dark-mode');
            applyColorProfile(savedP); document.getElementById('colorBlindSelect').value=savedP;
            applyFontSize(savedF); document.getElementById('fontSlider').value=savedF;
            applyLanguage(savedL); document.getElementById('langSelect').value=savedL;
            
            loadSavedLinks();
            loadManagerData();

            function toggleTheme(){ 
                document.body.classList.toggle('dark-mode'); 
                localStorage.setItem('theme', document.body.classList.contains('dark-mode')?'dark':'light');
            }
            function changeColorProfile(){ 
                const p = document.getElementById('colorBlindSelect').value; 
                applyColorProfile(p); localStorage.setItem('colorProfile', p); 
            }
            function applyColorProfile(p){
                document.body.classList.remove('protanopia','deuteranopia','tritanopia','achromatopsia');
                if(p!=='normal') document.body.classList.add(p);
            }
            function changeFontSize(){ 
                const s = document.getElementById('fontSlider').value; 
                applyFontSize(s); localStorage.setItem('fontScale', s); 
            }
            function applyFontSize(s){ document.documentElement.style.setProperty('--font-scale', s); }
            function changeLanguage(){ 
                const l = document.getElementById('langSelect').value; 
                applyLanguage(l); localStorage.setItem('appLang', l); resetView(); 
            }
            function applyLanguage(l){
                const t = translations[l];
                document.querySelectorAll('[data-i18n]').forEach(el => {
                    if(t[el.getAttribute('data-i18n')]) el.textContent = t[el.getAttribute('data-i18n')];
                });
                document.getElementById('langSelect').value = l;
            }
            function getTrans(k){ return translations[document.getElementById('langSelect').value][k] || k; }

            function toggleManager(){
                const m = document.getElementById('managerSection');
                m.style.display = m.style.display === 'block' ? 'none' : 'block';
                if(m.style.display === 'block') loadManagerData();
            }

            async function loadManagerData() {
                const res = await fetch('/api/feeds/get_all');
                const data = await res.json();
                renderManager(data);
            }

            function renderManager(data) {
                const div = document.getElementById('managerContent');
                let html = '';
                for (const [cat, urls] of Object.entries(data)) {
                    html += `
                    <div style="margin-top:15px; border-top:1px solid #eee; padding-top:5px;">
                        <div class="man-row" style="font-weight:bold;">
                            <span>${cat}</span>
                            <button class="btn-small btn-del" onclick="apiManage('del_cat', '${cat}')">🗑 Cat</button>
                        </div>
                        <div class="man-row">
                            <input type="text" id="newUrl_${cat}" class="man-input" placeholder="http://...">
                            <button class="btn-small btn-add" onclick="apiManage('add_url', '${cat}', 'newUrl_${cat}')">+</button>
                        </div>
                        <div class="feed-list">`;
                    
                    urls.forEach(url => {
                        html += `
                        <div class="man-row">
                            <span style="overflow:hidden; text-overflow:ellipsis;">${url.replace('https://','').replace('http://','')}</span>
                            <button class="btn-small btn-del" onclick="apiManage('del_url', '${cat}', null, '${url}')">🗑</button>
                        </div>`;
                    });
                    html += `</div></div>`;
                }
                div.innerHTML = html;
            }

            async function apiManage(action, category=null, inputId=null, url=null) {
                let payload = { action: action, category: category };
                
                if (inputId) {
                    const val = document.getElementById(inputId).value;
                    if(!val) return;
                    payload.url = val;
                } else if (url) {
                    payload.url = url;
                } else if (action === 'add_cat') {
                    payload.category = document.getElementById('newCatInput').value;
                    if(!payload.category) return;
                }

                if ((action === 'add_url') && payload.url) {
                    if (!payload.url.startsWith('http')) {
                        alert("L'URL doit commencer par http:// ou https://");
                        return;
                    }
                }

                if(action.includes('del') && !confirm(getTrans('msg_confirm'))) return;

                const res = await fetch('/api/feeds/manage', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                const json = await res.json();
                if(json.success) {
                    if(action.includes('cat')) location.reload(); 
                    else loadManagerData();
                    if(inputId) document.getElementById(inputId).value = '';
                    if(action === 'add_cat') document.getElementById('newCatInput').value = '';
                } else {
                    alert('Erreur: ' + json.msg);
                }
            }

            function resetView(){
                currentData = null; document.getElementById('saveBtn').style.display='none';
                document.getElementById('content').innerHTML = '<p>'+getTrans('intro_text')+'</p>';
                loadSavedLinks();
            }

            async function fetchRandomArticle(){
                const cat = document.getElementById('categorySelect').value;
                const content = document.getElementById('content');
                const btn = document.getElementById('mainBtn');
                
                content.innerHTML = '<p>'+getTrans('msg_loading')+'</p>';
                btn.disabled=true; btn.style.opacity="0.7";
                document.getElementById('saveBtn').style.display='none';

                try {
                    const r = await fetch('/get-random?category='+encodeURIComponent(cat));
                    const d = await r.json();
                    btn.disabled=false; btn.style.opacity="1";
                    
                    if(d.error){ content.innerHTML='<p class="status-err">'+d.error+'</p>'; return;}
                    currentData = {...d, category: cat};
                    
                    document.getElementById('saveBtn').style.display='inline-block';
                    content.innerHTML = `
                        <div><span class="source-tag">${d.source}</span></div>
                        <h2>${d.title}</h2>
                        <p>${d.summary}</p>
                        <a href="${d.link}" target="_blank" class="btn btn-read">${getTrans('btn_read')}</a>
                    `;
                } catch(e){ content.innerHTML='<p class="status-err">Erreur</p>'; btn.disabled=false; }
            }

            async function saveCurrentArticle(){
                if(!currentData) return;
                await fetch('/api/save', { method:'POST', headers:{'Content-Type':'application/json'},
                    body: JSON.stringify({
                        category: currentData.category,
                        url: currentData.link || currentData.url, 
                        title: currentData.title
                    })
                });
                loadSavedLinks();
            }
            async function loadSavedLinks(){
                const cat = document.getElementById('categorySelect').value;
                const r = await fetch('/api/saved-links?category='+encodeURIComponent(cat));
                const l = await r.json();
                const ul = document.getElementById('savedList');
                ul.innerHTML = '';
                l.forEach(i => {
                    ul.innerHTML += `<li class="list-item">
                        <a href="${i.url}" target="_blank" class="list-label" style="color:var(--col-primary)">${i.title}</a>
                        <button class="btn-small btn-del" onclick="deleteSaved('${i.url}')">🗑</button>
                    </li>`;
                });
            }
            async function deleteSaved(url){
                if(confirm(getTrans('msg_confirm'))) {
                    await fetch('/api/delete', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({url})});
                    loadSavedLinks();
                }
            }

            async function runDiagnostics(){
                const cat = document.getElementById('categorySelect').value;
                const div = document.getElementById('test-results');
                div.style.display='block'; div.innerHTML = getTrans('msg_loading');
                
                const r = await fetch('/test-sources?category='+encodeURIComponent(cat));
                const d = await r.json();
                
                let h = '';
                d.forEach(i => {
                    const delBtn = i.valid ? '' : `<button class="btn-small btn-del" onclick="apiManage('del_url', '${cat}', null, '${i.url}')" title="Supprimer ce flux HS">🗑</button>`;
                    const status = i.valid ? `<span class="status-ok">${getTrans('status_ok')}</span>` : `<span class="status-err">${getTrans('status_err')}</span>`;
                    
                    h += `<div class="list-item">
                        <span class="list-label" title="${i.url}">${i.url.replace('https://','')}</span>
                        <div style="display:flex; gap:5px; align-items:center;">${status} ${delBtn}</div>
                    </div>`;
                });
                div.innerHTML = h || getTrans('msg_empty');
            }
        </script>
    </body>
    </html>
    ''', categories=categories)

# ==========================================
# API ENDPOINTS
# ==========================================

@app.route('/get-random')
@requires_auth
def get_random():
    cat = request.args.get('category')
    cfg = get_full_config()
    urls = cfg.get(cat, [])
    if not urls: return jsonify({"error": "Catégorie vide"})
    try:
        url = random.choice(urls)
        feed = feedparser.parse(url)
        if not feed.entries: return jsonify({"error": "Flux vide", "source": url})
        art = random.choice(feed.entries)
        summary = art.get('summary', '')
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(summary, "html.parser")
        return jsonify({
            "source": html.escape(feed.feed.get('title', 'Source')),
            "title": html.escape(art.get('title', 'No Title')),
            "link": art.get('link', '#'),
            "summary": soup.get_text()[:250] + "..."
        })
    except Exception as e: return jsonify({"error": str(e)})

@app.route('/test-sources')
@requires_auth
def test_sources():
    cat = request.args.get('category')
    cfg = get_full_config()
    urls = cfg.get(cat, [])
    rep = []
    for u in urls:
        try:
            f = feedparser.parse(u)
            rep.append({"url": u, "valid": (hasattr(f,'entries') and len(f.entries)>0)})
        except: rep.append({"url": u, "valid": False})
    return jsonify(rep)

@app.route('/api/feeds/get_all')
@requires_auth
def get_all_feeds():
    return jsonify(get_full_config())

@app.route('/api/feeds/manage', methods=['POST'])
@requires_auth
def manage_feeds():
    d = request.json
    action = d.get('action')
    cat = d.get('category')
    url = d.get('url')
    
    try:
        if action == 'add_cat':
            # FIX: On sauvegarde vraiment la catégorie
            if cat and not Category.query.filter_by(name=cat).first():
                db.session.add(Category(name=cat))
                db.session.commit()
        
        elif action == 'del_cat':
            # Suppression en cascade manuelle (pour être sûr)
            Category.query.filter_by(name=cat).delete()
            Feed.query.filter_by(category_name=cat).delete()
            db.session.commit()
            
        elif action == 'add_url':
            is_valid, error_msg = is_safe_url(url)
            if not is_valid: return jsonify({"success": False, "msg": error_msg})
            
            # On s'assure que la catégorie existe
            if not Category.query.filter_by(name=cat).first():
                 db.session.add(Category(name=cat))
            
            # On ajoute le flux
            if not Feed.query.filter_by(category_name=cat, url=url.strip()).first():
                db.session.add(Feed(category_name=cat, url=url.strip()))
                db.session.commit()
                
        elif action == 'del_url':
            Feed.query.filter_by(category_name=cat, url=url).delete()
            db.session.commit()
            
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "msg": str(e)})

@app.route('/api/save', methods=['POST'])
@requires_auth
def api_save():
    d = request.json
    url_to_save = d.get('url') or d.get('link')
    if not url_to_save: return jsonify({"success": False})
    
    try:
        if not SavedArticle.query.filter_by(url=url_to_save).first():
            db.session.add(SavedArticle(
                category=d.get('category', 'Général'),
                url=url_to_save,
                title=d.get('title', 'Sans titre')
            ))
            db.session.commit()
        return jsonify({"success": True})
    except: return jsonify({"success": False})

@app.route('/api/saved-links')
@requires_auth
def api_list_saved():
    cat = request.args.get('category')
    query = SavedArticle.query
    if cat:
        query = query.filter_by(category=cat)
    links = query.all()
    return jsonify([{'category':l.category, 'url':l.url, 'title':l.title} for l in links])

@app.route('/api/delete', methods=['POST'])
@requires_auth
def api_delete():
    url = request.json.get('url')
    SavedArticle.query.filter_by(url=url).delete()
    db.session.commit()
    return jsonify({"success": True})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
