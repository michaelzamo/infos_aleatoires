from flask import Flask, jsonify, render_template_string, request, Response, make_response
from flask_sqlalchemy import SQLAlchemy
import feedparser
import random
import os
import html
import json
import re
from functools import wraps
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# ==========================================
# CONFIGURATION
# ==========================================
basedir = os.path.abspath(os.path.dirname(__file__))

ADMIN_USERNAME = os.environ.get('ADMIN_USER')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASS')

if not ADMIN_USERNAME or not ADMIN_PASSWORD:
    print("⚠️  ATTENTION : Identifiants par défaut (admin/changezMoi123)")
    ADMIN_USERNAME = 'admin'
    ADMIN_PASSWORD = 'changezMoi123'

database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

if not database_url:
    database_url = 'sqlite:///' + os.path.join(basedir, 'data.db')

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024 

db = SQLAlchemy(app)

# ==========================================
# MODÈLES
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
    # Données par défaut si vide
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
# SÉCURITÉ & UTILITAIRES
# ==========================================
def check_auth(username, password):
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD

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

def is_safe_url(url):
    if not url: return False, "URL vide"
    url_lower = url.strip().lower()
    if not url_lower.startswith(('http://', 'https://')):
        return False, "Protocole invalide"
    forbidden = ['localhost', '127.', '0.0.0.0', '192.168.', '10.', '172.16.', '169.254.', '::1']
    for host in forbidden:
        if f"//{host}" in url_lower or f"@{host}" in url_lower or url_lower.startswith(host):
             return False, "Adresse interdite"
    return True, ""

def sanitize_category_name(name):
    if not isinstance(name, str): return "Inconnu"
    clean = re.sub(r'[^\w\s\-\.]', '', name)
    return clean.strip()[:100]

# --- CORRECTION MAJEURE ICI ---
def get_config_by_type(m_type):
    # 1. On récupère TOUTES les catégories existantes (même les vides)
    all_cats = Category.query.order_by(Category.name).all()
    # On initialise le dictionnaire avec des listes vides pour chaque catégorie
    data = {c.name: [] for c in all_cats}

    # 2. On récupère les flux du type demandé
    feeds = Feed.query.filter_by(media_type=m_type).all()
    
    # 3. On remplit les listes
    for f in feeds:
        if f.category_name in data:
            data[f.category_name].append(f.url)
        else:
            # Cas de sécurité si une catégorie a été supprimée salement
            data[f.category_name] = [f.url]
            
    return data

def get_full_export_data():
    feeds = Feed.query.all()
    feeds_list = []
    for f in feeds:
        feeds_list.append({
            "category": f.category_name,
            "url": f.url,
            "media_type": f.media_type
        })
    
    saved = SavedArticle.query.all()
    saved_list = []
    for s in saved:
        saved_list.append({
            "category": s.category,
            "url": s.url,
            "title": s.title,
            "media_type": s.media_type
        })
    return {"feeds": feeds_list, "saved": saved_list}

# ==========================================
# FRONTEND
# ==========================================
@app.route('/')
@requires_auth
def home():
    # Placeholder initial, le JS fera le vrai chargement
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
            
            body.achromatopsia { filter: grayscale(100%) contrast(110%); }
            body.protanopia { --col-success: #0077be; --col-error: #a8ad00; }
            body.deuteranopia { --col-success: #0050ef; --col-error: #d80073; }

            body { 
                font-family: "Noto Sans", sans-serif; display: flex; justify-content: center; align-items: center; 
                min-height: 100vh; margin: 0; padding: 20px; box-sizing: border-box;
                background-color: var(--bg-body); color: var(--text-main);
                transition: background 0.3s;
                font-size: calc(16px * var(--font-scale));
            }
            
            button:focus-visible, select:focus-visible, input:focus-visible, a:focus-visible {
                outline: 3px solid var(--col-primary); outline-offset: 3px; box-shadow: 0 0 8px rgba(0,0,0,0.2);
            }

            .card { 
                background: var(--bg-card); padding: 0; border-radius: var(--border-rad); 
                box-shadow: var(--shadow); max-width: 500px; width: 100%; 
                max-height: 90vh; overflow-y: auto; display: flex; flex-direction: column;
            }
            
            .card-content { padding: 2rem; }

            .tabs { display: flex; width: 100%; border-bottom: 1px solid var(--select-border); }
            .tab { 
                flex: 1; padding: 15px; text-align: center; cursor: pointer; 
                background: var(--bg-card); border: none; font-weight: bold;
                color: var(--text-sub); border-bottom: 3px solid transparent;
                transition: all 0.2s; font-size: 1em;
            }
            .tab:hover { background: var(--tag-bg); }
            .tab.active { color: var(--col-primary); border-bottom: 3px solid var(--col-primary); }
            
            .header-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
            .theme-toggle { background: none; border: none; cursor: pointer; padding: 5px; font-size: 1.2em; border-radius: 50%;}

            .settings-container, #managerSection {
                display:flex; flex-direction:column; gap:10px; margin-bottom:20px; 
                background:var(--tag-bg); padding:10px; border-radius:8px;
                font-size: calc(16px * var(--font-scale)) !important; 
            }
            .settings-container *, #managerSection * { font-size: 1em; }
            button, select, input { font-size: 1em; }
            
            .settings-row { display:flex; justify-content:space-between; align-items:center; }
            .setting-label { font-size:0.8em; font-weight:bold; color:var(--text-sub); }
            
            .a11y-select { 
                padding:4px; border-radius:4px; border:1px solid var(--select-border); background:var(--select-bg); 
                color:var(--text-main); max-width:120px; font-size: calc(16px * var(--font-scale));
            }
            
            .cat-row { display:flex; gap:10px; align-items:center; margin-bottom:15px; }
            .cat-select { 
                flex-grow:1; padding:10px; border-radius:8px; border:1px solid var(--select-border); 
                background:var(--select-bg); color:var(--text-main); font-size: calc(16px * var(--font-scale));
            }
            
            .btn-manage { background:none; border:none; cursor:pointer; color:var(--col-manage); padding:0 5px; font-size: calc(1.5em * var(--font-scale)); }
            .action-buttons { display:flex; flex-direction:column; gap:10px; align-items:center; margin-top:20px; }
            .btn { background:var(--col-primary); color:#fff; padding:12px 25px; border-radius:50px; border:none; font-weight:600; width:80%; cursor:pointer; }
            .btn-save { background:var(--col-save); display:none; }
            .btn-read { background:var(--col-success); text-decoration: none; padding: 10px 20px; border-radius: 20px; color: white; display: inline-block; margin-top: 10px;}
            
            audio { width: 100%; margin-top: 15px; }

            #managerSection { display:none; border:1px solid var(--select-border); }
            .man-row { display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; font-size:0.9em; gap: 5px;}
            .man-input { flex-grow:1; padding:5px; border-radius:4px; border:1px solid var(--select-border); background:var(--select-bg); color:var(--text-main); }
            .btn-small { padding:5px 10px; border-radius:4px; border:none; cursor:pointer; color:white; font-size:0.8em; white-space: nowrap;}
            .btn-add { background:var(--col-success); }
            .btn-del { background:var(--col-error); }
            .btn-imp { background:var(--col-manage); }
            .btn-test-cat { background:var(--col-primary); color:white; }
            
            .list-item { display:flex; justify-content:space-between; align-items:center; padding:8px 0; border-bottom:1px solid var(--select-border); font-size:0.9em; }
            .list-label { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; margin-right:10px; flex-grow:1; text-align:left; }
            .source-tag { background:var(--tag-bg); padding:4px 10px; border-radius:20px; font-size:0.8em; font-weight:bold; color:var(--text-sub); }
            .test-indicator { margin-right: 5px; font-size: 1.2em; }
        </style>
    </head>
    <body>
        <div class="card">
            <div class="tabs" role="tablist">
                <button class="tab active" id="tab-text" onclick="switchMode('text')" role="tab" aria-selected="true" aria-controls="panel-content">
                    📰 Articles
                </button>
                <button class="tab" id="tab-audio" onclick="switchMode('audio')" role="tab" aria-selected="false" aria-controls="panel-content">
                    🎧 Podcasts
                </button>
            </div>

            <div class="card-content" id="panel-content" role="tabpanel">
                <div class="header-row">
                    <h1 data-i18n="app_title">Sérendipité</h1>
                    <button class="theme-toggle" onclick="toggleTheme()" aria-label="Changer le thème"><span aria-hidden="true">🌓</span></button>
                </div>

                <div class="settings-container">
                    <div class="settings-row">
                        <label for="langSelect" class="setting-label" data-i18n="lbl_lang">LANGUE</label>
                        <select id="langSelect" class="a11y-select" onchange="changeLanguage()">
                            <option value="fr">Français</option><option value="en">English</option>
                            <option value="es">Español</option><option value="jp">日本語</option>
                        </select>
                    </div>
                    <div class="settings-row">
                        <label for="colorBlindSelect" class="setting-label" data-i18n="lbl_vision">VISION</label>
                        <select id="colorBlindSelect" class="a11y-select" onchange="changeColorProfile()">
                            <option value="normal" data-i18n="vision_norm">Normale</option>
                            <option value="protanopia">Protanopia</option><option value="deuteranopia">Deuteranopia</option>
                            <option value="tritanopia">Tritanopie</option><option value="achromatopsia">Mono</option>
                        </select>
                    </div>
                    <div class="settings-row">
                        <label for="fontSlider" class="setting-label" data-i18n="lbl_size">TAILLE</label>
                        <input type="range" id="fontSlider" min="0.8" max="1.5" step="0.1" value="1" oninput="changeFontSize()">
                    </div>
                </div>

                <div id="managerSection">
                    <div style="font-weight:bold; margin-bottom:10px; border-bottom:1px solid #ddd;" id="manTitle">
                        <span data-i18n="man_title">Gestion</span> <span id="manModeLabel">(Articles)</span>
                    </div>
                    
                    <div class="man-row" style="background:var(--bg-body); padding:5px; border-radius:4px; margin-bottom:10px;">
                        <button class="btn-small btn-imp" onclick="exportFeeds()" data-i18n="btn_export">⬇️ Export Full</button>
                        <button class="btn-small btn-imp" onclick="document.getElementById('importFile').click()" data-i18n="btn_import">⬆️ Import</button>
                        <input type="file" id="importFile" style="display:none" accept=".json" onchange="importFeeds(this)" aria-label="Import JSON">
                    </div>

                    <div class="man-row">
                        <input type="text" id="newCatInput" class="man-input" placeholder="Nouvelle catégorie..." data-i18n="ph_cat" aria-label="Nom catégorie">
                        <button class="btn-small btn-add" onclick="apiManage('add_cat')" data-i18n="btn_add">Ajouter</button>
                    </div>

                    <hr style="width:100%; border:0; border-top:1px solid var(--select-border); margin:10px 0;">

                    <div class="man-row">
                        <label for="managerCatSelect" style="font-weight:bold; font-size:0.9em;" data-i18n="lbl_manage">Gérer :</label>
                        <select id="managerCatSelect" class="man-input" onchange="renderFeedList()">
                        </select>
                    </div>
                    
                    <div class="man-row" style="justify-content: flex-end;">
                        <button class="btn-small btn-del" onclick="deleteCurrentCategory()" data-i18n="btn_del_cat">Supprimer cette catégorie</button>
                    </div>

                    <div id="feedEditorArea" class="feed-list" style="display:none;">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                            <button class="btn-small btn-test-cat" onclick="testCurrentCategory()" data-i18n="btn_test_cat">🧪 Tester ces flux</button>
                        </div>
                        
                        <div class="man-row">
                            <input type="text" id="newUrlInput" class="man-input" placeholder="http://..." data-i18n="ph_url" aria-label="URL flux">
                            <button class="btn-small btn-add" onclick="addUrlToCurrent()" data-i18n="btn_add_url">Ajouter URL</button>
                        </div>
                        <div id="feedListContainer"></div>
                    </div>
                </div>
                
                <div class="cat-row">
                    <label for="categorySelect" class="visually-hidden">Catégorie</label>
                    <select id="categorySelect" class="cat-select" onchange="resetView()" aria-label="Choisir catégorie">
                    </select>
                    <button class="btn-manage" onclick="toggleManager()" title="Gérer" aria-label="Gérer les flux">⚙️</button>
                </div>

                <div id="content" aria-live="polite" style="min-height: 100px;">
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
            </div>
        </div>

        <script>
            let currentData = null;
            let currentMediaType = 'text'; // 'text' ou 'audio'
            let currentManagerData = {};
            
            const translations = {
                fr: {
                    app_title: "Sérendipité", lbl_lang:"LANGUE", lbl_vision:"VISION", lbl_size:"TAILLE", vision_norm:"Normale",
                    intro_text:"Cliquez pour découvrir.", btn_surprise:"Surprends-moi", btn_save:"💾 Sauvegarder", btn_read:"Lire l'article", btn_listen:"🎧 Écouter",
                    lbl_saved:"Sauvegardes", man_title:"Gestion", btn_add:"Ajouter",
                    msg_loading:"Recherche...", status_ok:"OK", status_err:"ERREUR", msg_confirm: "Confirmer la suppression ?",
                    ph_cat:"Nouvelle catégorie...", lbl_manage:"Gérer :", btn_del_cat:"Supprimer cette catégorie",
                    ph_url:"http://...", btn_add_url:"Ajouter URL", opt_choose:"-- Choisir --", msg_no_feeds:"Aucun flux ici.",
                    msg_sel_cat:"Sélectionnez une catégorie", msg_bad_url:"L'URL doit commencer par http:// ou https://",
                    btn_export: "⬇️ Export (Tout)", btn_import: "⬆️ Import (Tout)", msg_imp_success: "Importation terminée !",
                    btn_test_cat: "🧪 Tester ces flux", msg_test_load: "Test en cours...",
                    mode_text: "(Articles)", mode_audio: "(Podcasts)"
                },
                en: {
                    app_title: "Serendipity", lbl_lang:"LANGUAGE", lbl_vision:"VISION", lbl_size:"SIZE", vision_norm:"Normal",
                    intro_text:"Click to discover.", btn_surprise:"Surprise me", btn_save:"💾 Save", btn_read:"Read article", btn_listen:"🎧 Listen",
                    lbl_saved:"Saved", man_title:"Manager", btn_add:"Add",
                    msg_loading:"Searching...", status_ok:"OK", status_err:"ERR", msg_confirm: "Confirm deletion?",
                    ph_cat:"New category...", lbl_manage:"Manage:", btn_del_cat:"Delete category",
                    ph_url:"http://...", btn_add_url:"Add URL", opt_choose:"-- Choose --", msg_no_feeds:"No feeds here.",
                    msg_sel_cat:"Select a category", msg_bad_url:"URL must start with http:// or https://",
                    btn_export: "⬇️ Export (Full)", btn_import: "⬆️ Import (Full)", msg_imp_success: "Import complete!",
                    btn_test_cat: "🧪 Test feeds", msg_test_load: "Testing...",
                    mode_text: "(Articles)", mode_audio: "(Podcasts)"
                },
                es: {
                    app_title: "Serendipia", lbl_lang:"IDIOMA", lbl_vision:"VISIÓN", lbl_size:"TAMAÑO", vision_norm:"Normal",
                    intro_text:"Descubrir.", btn_surprise:"Sorpréndeme", btn_save:"💾 Guardar", btn_read:"Leer", btn_listen:"🎧 Escuchar",
                    lbl_saved:"Guardados", man_title:"Gestión", btn_add:"Añadir",
                    msg_loading:"Buscando...", status_ok:"OK", status_err:"ERR", msg_confirm: "¿Confirmar?",
                    ph_cat:"Nueva categoría...", lbl_manage:"Gestionar:", btn_del_cat:"Eliminar categoría",
                    ph_url:"http://...", btn_add_url:"Añadir URL", opt_choose:"-- Elegir --", msg_no_feeds:"No hay feeds.",
                    msg_sel_cat:"Seleccione una categoría", msg_bad_url:"La URL debe comenzar con http:// o https://",
                    btn_export: "⬇️ Exportar", btn_import: "⬆️ Importar", msg_imp_success: "¡Importación completada!",
                    btn_test_cat: "🧪 Probar", msg_test_load: "Probando...",
                    mode_text: "(Artículos)", mode_audio: "(Podcasts)"
                },
                jp: {
                    app_title: "セレンディピティ", lbl_lang:"言語", lbl_vision:"色覚", lbl_size:"サイズ", vision_norm:"通常",
                    intro_text:"発見する。", btn_surprise:"驚かせて", btn_save:"💾 保存", btn_read:"読む", btn_listen:"🎧 聞く",
                    lbl_saved:"保存リスト", man_title:"管理", btn_add:"追加",
                    msg_loading:"検索中...", status_ok:"有効", status_err:"エラー", msg_confirm: "削除しますか？",
                    ph_cat:"新しいカテゴリ...", lbl_manage:"管理:", btn_del_cat:"削除",
                    ph_url:"http://...", btn_add_url:"URLを追加", opt_choose:"-- 選択 --", msg_no_feeds:"フィードなし",
                    msg_sel_cat:"カテゴリを選択", msg_bad_url:"URLはhttp://またはhttps://で",
                    btn_export: "⬇️ 輸出", btn_import: "⬆️ 輸入", msg_imp_success: "完了！",
                    btn_test_cat: "🧪 テスト", msg_test_load: "テスト中...",
                    mode_text: "(記事)", mode_audio: "(ポッドキャスト)"
                }
            };

            const savedP = localStorage.getItem('colorProfile')||'normal';
            const savedF = localStorage.getItem('fontScale')||'1';
            const savedL = localStorage.getItem('appLang')||'fr';
            if(localStorage.getItem('theme')==='dark') document.body.classList.add('dark-mode');
            
            applyColorProfile(savedP); document.getElementById('colorBlindSelect').value=savedP;
            applyFontSize(savedF); document.getElementById('fontSlider').value=savedF;
            applyLanguage(savedL); document.getElementById('langSelect').value=savedL;

            // Démarrage
            switchMode('text'); 

            function switchMode(mode) {
                currentMediaType = mode;
                
                document.querySelectorAll('.tab').forEach(t => {
                    t.classList.remove('active');
                    t.setAttribute('aria-selected', 'false');
                });
                document.getElementById('tab-' + mode).classList.add('active');
                document.getElementById('tab-' + mode).setAttribute('aria-selected', 'true');
                
                const labelKey = mode === 'text' ? 'mode_text' : 'mode_audio';
                document.getElementById('manModeLabel').textContent = getTrans(labelKey);

                loadCategoriesForMode();
                resetView();
            }

            async function loadCategoriesForMode() {
                const res = await fetch('/api/feeds/get_config?media_type=' + currentMediaType);
                const data = await res.json();
                
                const catSelect = document.getElementById('categorySelect');
                catSelect.innerHTML = '';
                
                const cats = Object.keys(data);
                if(cats.length === 0) {
                    const op = document.createElement('option');
                    op.textContent = "---";
                    catSelect.appendChild(op);
                } else {
                    cats.forEach(c => {
                        const op = document.createElement('option');
                        op.value = c;
                        op.textContent = c;
                        catSelect.appendChild(op);
                    });
                }
                
                loadSavedLinks();
                
                if(document.getElementById('managerSection').style.display === 'block') {
                    loadManagerData();
                }
            }

            function toggleTheme(){ 
                document.body.classList.toggle('dark-mode'); 
                localStorage.setItem('theme', document.body.classList.contains('dark-mode')?'dark':'light');
            }
            function changeColorProfile(){ 
                const p = document.getElementById('colorBlindSelect').value; applyColorProfile(p); localStorage.setItem('colorProfile', p); 
            }
            function applyColorProfile(p){
                document.body.classList.remove('protanopia','deuteranopia','tritanopia','achromatopsia');
                if(p!=='normal') document.body.classList.add(p);
            }
            function changeFontSize(){ const s = document.getElementById('fontSlider').value; applyFontSize(s); localStorage.setItem('fontScale', s); }
            function applyFontSize(s){ document.documentElement.style.setProperty('--font-scale', s); }
            
            function changeLanguage(){ 
                const l = document.getElementById('langSelect').value; applyLanguage(l); localStorage.setItem('appLang', l); 
                document.getElementById('manModeLabel').textContent = getTrans(currentMediaType === 'text' ? 'mode_text' : 'mode_audio');
                resetView(); 
                if(document.getElementById('managerSection').style.display === 'block') populateManagerSelect();
            }
            
            function applyLanguage(l){
                const t = translations[l];
                document.querySelectorAll('[data-i18n]').forEach(el => {
                    const key = el.getAttribute('data-i18n');
                    if(t[key]) {
                        if(el.tagName === 'INPUT' && el.hasAttribute('placeholder')) {
                            el.placeholder = t[key];
                        } else {
                            el.textContent = t[key];
                        }
                    }
                });
                document.getElementById('langSelect').value = l;
            }
            function getTrans(k){ return translations[document.getElementById('langSelect').value][k] || k; }

            // --- MANAGER LOGIC ---
            function toggleManager(){
                const m = document.getElementById('managerSection');
                m.style.display = m.style.display === 'block' ? 'none' : 'block';
                if(m.style.display === 'block') loadManagerData();
            }

            async function loadManagerData() {
                const res = await fetch('/api/feeds/get_config?media_type=' + currentMediaType);
                currentManagerData = await res.json();
                populateManagerSelect();
            }

            function populateManagerSelect() {
                const sel = document.getElementById('managerCatSelect');
                const prevVal = sel.value;
                sel.innerHTML = `<option value="" disabled selected>${getTrans('opt_choose')}</option>`;
                Object.keys(currentManagerData).forEach(cat => {
                    const opt = document.createElement('option');
                    opt.value = cat;
                    opt.textContent = cat;
                    sel.appendChild(opt);
                });
                if(prevVal && currentManagerData.hasOwnProperty(prevVal)) {
                    sel.value = prevVal;
                    renderFeedList();
                } else {
                    document.getElementById('feedEditorArea').style.display = 'none';
                }
            }

            function renderFeedList(testResults = null) {
                const cat = document.getElementById('managerCatSelect').value;
                if (!cat) return;

                const area = document.getElementById('feedEditorArea');
                const listContainer = document.getElementById('feedListContainer');
                area.style.display = 'block';
                listContainer.innerHTML = '';

                const urls = currentManagerData[cat] || [];
                
                if (urls.length === 0) {
                    listContainer.innerHTML = `<div class="empty-msg">${getTrans('msg_no_feeds')}</div>`;
                } else {
                    urls.forEach(url => {
                        const div = document.createElement('div');
                        div.className = 'man-row';
                        
                        let statusIcon = '';
                        if (testResults) {
                            const res = testResults.find(r => r.url === url);
                            if (res) {
                                statusIcon = res.valid 
                                    ? '<span class="test-indicator" title="OK" aria-label="Valide">✅</span>' 
                                    : '<span class="test-indicator" title="Erreur" aria-label="Invalide">❌</span>';
                            }
                        }

                        div.innerHTML = `
                            ${statusIcon}
                            <span style="overflow:hidden; text-overflow:ellipsis; font-size:0.9em;">${url.replace('https://','')}</span>
                            <button class="btn-small btn-del" onclick="apiManage('del_url', '${cat}', null, '${url}')" aria-label="Supprimer">🗑</button>
                        `;
                        listContainer.appendChild(div);
                    });
                }
            }

            async function testCurrentCategory() {
                const cat = document.getElementById('managerCatSelect').value;
                if (!cat) return;

                const btn = document.querySelector('.btn-test-cat');
                const oldText = btn.textContent;
                btn.textContent = getTrans('msg_test_load');
                btn.disabled = true;

                try {
                    const r = await fetch(`/test-sources?category=${encodeURIComponent(cat)}&media_type=${currentMediaType}`);
                    const results = await r.json();
                    renderFeedList(results);
                } catch(e) {
                    alert("Erreur test");
                } finally {
                    btn.textContent = oldText;
                    btn.disabled = false;
                }
            }

            function addUrlToCurrent() {
                const cat = document.getElementById('managerCatSelect').value;
                if(!cat) return alert(getTrans('msg_sel_cat'));
                apiManage('add_url', cat, 'newUrlInput');
            }

            function deleteCurrentCategory() {
                const cat = document.getElementById('managerCatSelect').value;
                if(!cat) return;
                apiManage('del_cat', cat);
            }

            function exportFeeds() {
                window.location.href = '/api/feeds/export';
            }

            async function importFeeds(input) {
                if (!input.files || !input.files[0]) return;
                const file = input.files[0];
                const formData = new FormData();
                formData.append('file', file);

                const btn = document.querySelector('.btn-imp'); 
                const oldText = btn.textContent;
                btn.textContent = "⏳ ...";
                btn.disabled = true;

                try {
                    const res = await fetch('/api/feeds/import', { method: 'POST', body: formData });
                    const json = await res.json();
                    if(json.success) {
                        alert(getTrans('msg_imp_success') + "\\n" + json.msg);
                        location.reload();
                    } else {
                        alert('Erreur: ' + (json.msg || 'Format invalide'));
                    }
                } catch(e) {
                    alert('Erreur upload: ' + e);
                } finally {
                    btn.textContent = oldText;
                    btn.disabled = false;
                    input.value = ''; 
                }
            }

            async function apiManage(action, category=null, inputId=null, url=null) {
                let payload = { action: action, category: category, media_type: currentMediaType };
                
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
                        alert(getTrans('msg_bad_url'));
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
                    if(action === 'add_cat' || action === 'del_cat') {
                        // On doit recharger la liste complète des catégories pour le mode actuel
                        await loadCategoriesForMode(); 
                        if(action === 'add_cat') document.getElementById('newCatInput').value = '';
                    } else {
                        // Pour ajout URL ou suppression URL, on recharge juste le manager data
                        await loadManagerData();
                        document.getElementById('managerCatSelect').value = category;
                        renderFeedList();
                        if(inputId) document.getElementById(inputId).value = '';
                    }
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
                    const r = await fetch(`/get-random?category=${encodeURIComponent(cat)}&media_type=${currentMediaType}`);
                    const d = await r.json();
                    btn.disabled=false; btn.style.opacity="1";
                    
                    if(d.error){ content.innerHTML='<p class="status-err">'+d.error+'</p>'; return;}
                    currentData = {...d, category: cat, media_type: currentMediaType};
                    
                    document.getElementById('saveBtn').style.display='inline-block';
                    
                    let mediaHtml = '';
                    let actionBtn = '';
                    
                    if (currentMediaType === 'audio' && d.audio_url) {
                        mediaHtml = `<audio controls autoplay><source src="${d.audio_url}" type="audio/mpeg">Votre navigateur ne supporte pas l'audio.</audio>`;
                        actionBtn = `<a href="${d.link}" target="_blank" class="btn btn-read">${getTrans('btn_listen')} (Site)</a>`;
                    } else {
                        actionBtn = `<a href="${d.link}" target="_blank" class="btn btn-read">${getTrans('btn_read')}</a>`;
                    }

                    content.innerHTML = `
                        <div><span class="source-tag">${d.source}</span></div>
                        <h2>${d.title}</h2>
                        <p>${d.summary}</p>
                        ${mediaHtml}
                        ${actionBtn}
                    `;
                } catch(e){ content.innerHTML='<p class="status-err">Erreur</p>'; btn.disabled=false; }
            }

            async function saveCurrentArticle(){
                if(!currentData) return;
                await fetch('/api/save', { method:'POST', headers:{'Content-Type':'application/json'},
                    body: JSON.stringify({
                        category: currentData.category,
                        url: currentData.link || currentData.url, 
                        title: currentData.title,
                        media_type: currentData.media_type
                    })
                });
                loadSavedLinks();
            }
            
            async function loadSavedLinks(){
                const cat = document.getElementById('categorySelect').value;
                const r = await fetch(`/api/saved-links?category=${encodeURIComponent(cat)}&media_type=${currentMediaType}`);
                const l = await r.json();
                const ul = document.getElementById('savedList');
                ul.innerHTML = '';
                l.forEach(i => {
                    let icon = i.media_type === 'audio' ? '🎧 ' : '';
                    ul.innerHTML += `<li class="list-item">
                        <a href="${i.url}" target="_blank" class="list-label" style="color:var(--col-primary)">${icon}${i.title}</a>
                        <button class="btn-small btn-del" onclick="deleteSaved('${i.url}')" aria-label="Supprimer">🗑</button>
                    </li>`;
                });
            }
            async function deleteSaved(url){
                if(confirm(getTrans('msg_confirm'))) {
                    await fetch('/api/delete', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({url})});
                    loadSavedLinks();
                }
            }
        </script>
    </body>
    </html>
    ''')

# ==========================================
# API ENDPOINTS
# ==========================================

@app.route('/get-random')
@requires_auth
def get_random():
    cat = request.args.get('category')
    m_type = request.args.get('media_type', 'text')
    
    config = get_config_by_type(m_type)
    urls = config.get(cat, [])
    
    if not urls: return jsonify({"error": "Catégorie vide"})
    try:
        url = random.choice(urls)
        feed = feedparser.parse(url)
        if not feed.entries: return jsonify({"error": "Flux vide", "source": url})
        
        art = random.choice(feed.entries)
        summary = art.get('summary', '') or art.get('subtitle', '')
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(summary, "html.parser")
        clean_summary = soup.get_text()[:300] + "..."
        
        audio_url = None
        if m_type == 'audio':
            if hasattr(art, 'enclosures'):
                for enc in art.enclosures:
                    if enc.type.startswith('audio'):
                        audio_url = enc.href
                        break
            if not audio_url and hasattr(art, 'links'):
                for link in art.links:
                    if link.type and link.type.startswith('audio'):
                        audio_url = link.href
                        break
        
        return jsonify({
            "source": html.escape(feed.feed.get('title', 'Source')),
            "title": html.escape(art.get('title', 'No Title')),
            "link": art.get('link', '#'),
            "summary": clean_summary,
            "audio_url": audio_url
        })
    except Exception as e: return jsonify({"error": str(e)})

@app.route('/test-sources')
@requires_auth
def test_sources():
    cat = request.args.get('category')
    m_type = request.args.get('media_type', 'text')
    
    config = get_config_by_type(m_type)
    urls = config.get(cat, [])
    
    rep = []
    for u in urls:
        try:
            f = feedparser.parse(u)
            rep.append({"url": u, "valid": (hasattr(f,'entries') and len(f.entries)>0)})
        except: rep.append({"url": u, "valid": False})
    return jsonify(rep)

@app.route('/api/feeds/get_config')
@requires_auth
def api_get_config():
    m_type = request.args.get('media_type', 'text')
    return jsonify(get_config_by_type(m_type))

@app.route('/api/feeds/get_all')
@requires_auth
def get_all_feeds():
    # Retourne la config texte par défaut pour compatibilité
    return jsonify(get_config_by_type('text'))

# --- EXPORT / IMPORT ---

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
def import_feeds():
    if 'file' not in request.files: return jsonify({"success": False, "msg": "No file"})
    file = request.files['file']
    if file.filename == '': return jsonify({"success": False, "msg": "Empty filename"})
        
    try:
        data = json.load(file)
        if not isinstance(data, dict): return jsonify({"success": False, "msg": "Invalid JSON"})
            
        count_cat = 0
        count_url = 0
        count_saved = 0
        
        if "feeds" in data and isinstance(data["feeds"], list):
            feeds_list = data["feeds"]
            for item in feeds_list:
                cat_name = item.get('category')
                url = item.get('url')
                m_type = item.get('media_type', 'text')
                
                safe_cat = sanitize_category_name(cat_name)
                if not safe_cat: continue
                
                if not Category.query.filter_by(name=safe_cat).first():
                    db.session.add(Category(name=safe_cat))
                    count_cat += 1
                
                is_valid, _ = is_safe_url(url)
                if is_valid:
                    trunc_url = url.strip()[:500]
                    if not Feed.query.filter_by(category_name=safe_cat, url=trunc_url).first():
                        db.session.add(Feed(category_name=safe_cat, url=trunc_url, media_type=m_type))
                        count_url += 1

        elif "feeds" in data and isinstance(data["feeds"], dict):
             for cat_name, urls in data["feeds"].items():
                safe_cat = sanitize_category_name(cat_name)
                if not Category.query.filter_by(name=safe_cat).first():
                    db.session.add(Category(name=safe_cat))
                    count_cat += 1
                for url in urls:
                    if is_safe_url(url)[0]:
                         if not Feed.query.filter_by(category_name=safe_cat, url=url).first():
                            db.session.add(Feed(category_name=safe_cat, url=url, media_type='text'))
                            count_url += 1

        if "saved" in data:
            for item in data["saved"]:
                try:
                    url = item.get('url')
                    title = item.get('title', 'Sans titre')
                    cat = item.get('category', 'Général')
                    m_type = item.get('media_type', 'text')
                    
                    if is_safe_url(url)[0]:
                        if not SavedArticle.query.filter_by(url=url[:500]).first():
                            db.session.add(SavedArticle(url=url[:500], title=title[:500], category=cat[:100], media_type=m_type))
                            count_saved += 1
                except: continue

        db.session.commit()
        return jsonify({"success": True, "msg": f"Importé: {count_url} flux, {count_saved} articles."})
        
    except Exception as e:
        return jsonify({"success": False, "msg": str(e)})


@app.route('/api/feeds/manage', methods=['POST'])
@requires_auth
def manage_feeds():
    d = request.json
    action = d.get('action')
    cat = d.get('category')
    url = d.get('url')
    m_type = d.get('media_type', 'text')
    
    try:
        if action == 'add_cat':
            if cat and not Category.query.filter_by(name=cat).first():
                db.session.add(Category(name=cat))
                db.session.commit()
        
        elif action == 'del_cat':
            Category.query.filter_by(name=cat).delete()
            Feed.query.filter_by(category_name=cat).delete()
            db.session.commit()
            
        elif action == 'add_url':
            is_valid, error_msg = is_safe_url(url)
            if not is_valid: return jsonify({"success": False, "msg": error_msg})
            
            if not Category.query.filter_by(name=cat).first():
                 db.session.add(Category(name=cat))
            
            if not Feed.query.filter_by(category_name=cat, url=url.strip()).first():
                db.session.add(Feed(category_name=cat, url=url.strip(), media_type=m_type))
                db.session.commit()
                
        elif action == 'del_url':
            # On supprime bien le flux correspondant (URL unique + catégorie)
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
                title=d.get('title', 'Sans titre'),
                media_type=d.get('media_type', 'text')
            ))
            db.session.commit()
        return jsonify({"success": True})
    except: return jsonify({"success": False})

@app.route('/api/saved-links')
@requires_auth
def api_list_saved():
    cat = request.args.get('category')
    m_type = request.args.get('media_type') 
    
    query = SavedArticle.query
    if cat and cat != '---':
        query = query.filter_by(category=cat)
    if m_type:
        query = query.filter_by(media_type=m_type)
        
    links = query.all()
    return jsonify([{'category':l.category, 'url':l.url, 'title':l.title, 'media_type':l.media_type} for l in links])

@app.route('/api/delete', methods=['POST'])
@requires_auth
def api_delete():
    url = request.json.get('url')
    SavedArticle.query.filter_by(url=url).delete()
    db.session.commit()
    return jsonify({"success": True})

@app.route('/reset-db-force')
@requires_auth
def reset_db_force():
    try:
        db.drop_all()
        db.create_all()
        return "Base de données réinitialisée avec succès."
    except Exception as e:
        return f"Erreur reset: {e}"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
