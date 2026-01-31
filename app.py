from flask import Flask, jsonify, render_template_string, request
import feedparser
import random
import os
import json

app = Flask(__name__)

SAVED_FILE = 'saved_links.txt'

# --- GESTION DES FLUX ---
def load_feeds_config():
    feeds_data = {}
    current_category = None
    try:
        with open('feeds.txt', 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'): continue
                if line.startswith('[') and line.endswith(']'):
                    current_category = line[1:-1]
                    feeds_data[current_category] = []
                elif current_category:
                    feeds_data[current_category].append(line)
    except FileNotFoundError:
        return {"Défaut": ["https://www.lemonde.fr/rss/une.xml"]}
    return feeds_data

# --- GESTION DES SAUVEGARDES ---
def get_saved_links():
    links = []
    if not os.path.exists(SAVED_FILE):
        return links
    try:
        with open(SAVED_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if '|' in line:
                    parts = line.strip().split('|', 1)
                    links.append({'url': parts[0], 'title': parts[1]})
    except Exception:
        pass
    return links

def save_link_to_file(url, title):
    # On vérifie d'abord si le lien existe déjà pour éviter les doublons
    current_links = get_saved_links()
    for link in current_links:
        if link['url'] == url:
            return False # Déjà existant
    
    with open(SAVED_FILE, 'a', encoding='utf-8') as f:
        # On nettoie le titre des retours à la ligne éventuels
        clean_title = title.replace('\n', ' ').replace('\r', '')
        f.write(f"{url}|{clean_title}\n")
    return True

def delete_link_from_file(url_to_delete):
    links = get_saved_links()
    new_links = [l for l in links if l['url'] != url_to_delete]
    
    with open(SAVED_FILE, 'w', encoding='utf-8') as f:
        for link in new_links:
            f.write(f"{link['url']}|{link['title']}\n")
    return len(links) != len(new_links)

@app.route('/')
def home():
    feeds_config = load_feeds_config()
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
            /* --- VARIABLES --- */
            :root {
                --font-scale: 1;
                --bg-body: #f0f2f5; --bg-card: #ffffff;
                --text-main: #333; --text-sub: #666;
                --tag-bg: #e9ecef; --select-bg: #f9f9f9; --select-border: #ddd;
                --shadow: 0 10px 25px rgba(0,0,0,0.05);
                --col-primary: #007bff; --col-success: #28a745; --col-error: #dc3545; --col-link-read: #28a745;
                --col-save: #6c757d; /* Gris pour sauvegarder */
                --border-rad: 16px;
            }
            
            body.dark-mode {
                --bg-body: #121212; --bg-card: #1e1e1e;
                --text-main: #e0e0e0; --text-sub: #aaaaaa;
                --tag-bg: #333; --select-bg: #2c2c2c; --select-border: #444;
                --shadow: rgba(0,0,0,0.5);
            }

            /* Styles Généraux */
            body { 
                font-family: "Noto Sans", sans-serif; 
                display: flex; justify-content: center; align-items: center; 
                min-height: 100vh; margin: 0; padding: 20px; box-sizing: border-box;
                background-color: var(--bg-body); color: var(--text-main);
                transition: background 0.3s, color 0.3s;
                font-size: calc(16px * var(--font-scale));
            }

            /* Correction taille police formulaires */
            button, select, input, .btn, .cat-select, .a11y-select { font-size: 1em !important; }
            .source-tag, .setting-label, .btn-test { font-size: 0.8em !important; }

            .card { 
                background: var(--bg-card); padding: 2rem; border-radius: var(--border-rad); 
                box-shadow: var(--shadow); max-width: 500px; text-align: center; width: 100%; 
                max-height: 90vh; overflow-y: auto; /* Permet le scroll si la liste est longue */
            }

            .header-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
            h1 { font-size: 1.5em; margin: 0; }
            .theme-toggle { background: none; border: none; cursor: pointer; padding: 5px; font-size: 1.2em; }

            .settings-container {
                display: flex; flex-direction: column; gap: 10px; margin-bottom: 20px;
                background: var(--tag-bg); padding: 10px; border-radius: var(--border-rad);
            }
            .settings-row { display: flex; justify-content: space-between; align-items: center; }
            .setting-label { color: var(--text-sub); font-weight: bold; text-transform: uppercase;}
            .a11y-select { padding: 4px; border-radius: 4px; border: 1px solid var(--select-border); background-color: var(--select-bg); color: var(--text-main); max-width: 120px; }
            input[type=range] { width: 80px; cursor: pointer; }

            .cat-select { padding: 10px; border-radius: var(--border-rad); border: 1px solid var(--select-border); background-color: var(--select-bg); color: var(--text-main); width: 100%; margin-bottom: 15px; }

            .source-tag { background: var(--tag-bg); padding: 4px 10px; border-radius: 20px; color: var(--text-sub); text-transform: uppercase; font-weight: bold; }
            h2 { margin: 15px 0; font-size: 1.3em; }
            p { color: var(--text-sub); line-height: 1.6; }

            /* BOUTONS D'ACTION */
            .action-buttons { display: flex; flex-direction: column; gap: 10px; align-items: center; margin-top: 20px; }
            
            .btn { 
                background-color: var(--col-primary); color: white; padding: 12px 25px; 
                text-decoration: none; border-radius: 50px; border: none; font-weight: 600; width: 80%; cursor: pointer;
            }
            .btn-read { background-color: var(--col-link-read); }
            .btn-save { background-color: var(--col-save); display: none; } /* Caché par défaut */

            .btn-test { background: none; border: none; color: var(--text-sub); margin-top: 20px; cursor: pointer; text-decoration: underline; opacity: 0.7;}

            /* SECTION SAUVEGARDE */
            .saved-section { margin-top: 30px; border-top: 1px solid var(--select-border); padding-top: 15px; text-align: left; }
            .saved-title { font-size: 1em; font-weight: bold; margin-bottom: 10px; color: var(--text-main); }
            .saved-list { list-style: none; padding: 0; margin: 0; }
            .saved-item { 
                display: flex; justify-content: space-between; align-items: center; 
                padding: 8px 0; border-bottom: 1px solid var(--select-border); font-size: 0.9em;
            }
            .saved-link { text-decoration: none; color: var(--col-primary); flex-grow: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-right: 10px; }
            .saved-delete { background: none; border: none; cursor: pointer; font-size: 1.2em; color: var(--col-error); padding: 0 5px; }
            .saved-delete:hover { transform: scale(1.2); }

            .status-ok { color: var(--col-success); font-weight: bold; } 
            .status-err { color: var(--col-error); font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="card">
            <div class="header-row">
                <h1 data-i18n="app_title">Sérendipité</h1>
                <button class="theme-toggle" onclick="toggleTheme()" id="themeBtn">🌓</button>
            </div>

            <div class="settings-container">
                <div class="settings-row">
                    <span class="setting-label" data-i18n="lbl_lang">LANGUE</span>
                    <select id="langSelect" class="a11y-select" onchange="changeLanguage()">
                        <option value="fr">Français 🇫🇷</option>
                        <option value="en">English 🇬🇧</option>
                        <option value="es">Español 🇪🇸</option>
                        <option value="jp">日本語 🇯🇵</option>
                    </select>
                </div>
                <div class="settings-row">
                    <span class="setting-label" data-i18n="lbl_vision">VISION</span>
                    <select id="colorBlindSelect" class="a11y-select" onchange="changeColorProfile()">
                        <option value="normal" data-i18n="vision_norm">Normale</option>
                        <option value="protanopia">Protanopia (R-)</option>
                        <option value="deuteranopia">Deutéranopie (V-)</option>
                        <option value="tritanopia">Tritanopie (B-)</option>
                        <option value="achromatopsia">Mono</option>
                    </select>
                </div>
                <div class="settings-row">
                    <span class="setting-label" data-i18n="lbl_size">TAILLE</span>
                    <div style="display:flex; align-items:center; gap:5px">
                        <span style="font-size:0.8em">A</span>
                        <input type="range" id="fontSlider" min="0.8" max="1.5" step="0.1" value="1" oninput="changeFontSize()">
                        <span style="font-size:1.2em">A</span>
                    </div>
                </div>
            </div>
            
            <select id="categorySelect" class="cat-select" onchange="resetView()">
                {% for name in categories %}
                    <option value="{{ name }}">{{ name }}</option>
                {% endfor %}
            </select>

            <div id="content" style="min-height: 100px;">
                <p data-i18n="intro_text">Cliquez pour découvrir un article.</p>
            </div>
            
            <div class="action-buttons">
                <button class="btn" onclick="fetchRandomArticle()" id="mainBtn" data-i18n="btn_surprise">Surprends-moi</button>
                <button class="btn btn-save" onclick="saveCurrentArticle()" id="saveBtn" data-i18n="btn_save">💾 Sauvegarder</button>
            </div>
            
            <div class="saved-section">
                <div class="saved-title" data-i18n="lbl_saved_list">Articles sauvegardés</div>
                <ul id="savedList" class="saved-list">
                    </ul>
            </div>

            <button class="btn-test" onclick="runDiagnostics()" data-i18n="btn_test">Tester les flux</button>
            <div id="test-results" style="display:none; margin-top:10px;"></div>
        </div>

        <script>
            // --- ETAT GLOBAL ---
            let currentArticleData = null; // Stocke l'article affiché

            // --- TRADUCTIONS ---
            const translations = {
                fr: {
                    app_title: "Sérendipité", lbl_lang: "LANGUE", lbl_vision: "VISION", lbl_size: "TAILLE",
                    vision_norm: "Normale", intro_text: "Cliquez pour découvrir.", cat_prefix: "Catégorie : ",
                    btn_surprise: "Surprends-moi", btn_read: "Lire l'article", btn_save: "💾 Sauvegarder",
                    btn_test: "Tester les flux", lbl_saved_list: "Articles sauvegardés",
                    msg_loading: "Recherche...", msg_network_err: "Erreur réseau.", msg_empty: "Vide.",
                    status_valid: "OK", status_error: "HS", msg_saved: "Sauvegardé !", msg_deleted: "Supprimé."
                },
                en: {
                    app_title: "Serendipity", lbl_lang: "LANGUAGE", lbl_vision: "VISION", lbl_size: "SIZE",
                    vision_norm: "Normal", intro_text: "Click to discover.", cat_prefix: "Category: ",
                    btn_surprise: "Surprise me", btn_read: "Read article", btn_save: "💾 Save",
                    btn_test: "Test feeds", lbl_saved_list: "Saved Articles",
                    msg_loading: "Searching...", msg_network_err: "Network error.", msg_empty: "Empty.",
                    status_valid: "OK", status_error: "ERR", msg_saved: "Saved!", msg_deleted: "Deleted."
                },
                es: {
                    app_title: "Serendipia", lbl_lang: "IDIOMA", lbl_vision: "VISIÓN", lbl_size: "TAMAÑO",
                    vision_norm: "Normal", intro_text: "Descubrir artículo.", cat_prefix: "Categoría: ",
                    btn_surprise: "Sorpréndeme", btn_read: "Leer artículo", btn_save: "💾 Guardar",
                    btn_test: "Probar feeds", lbl_saved_list: "Artículos guardados",
                    msg_loading: "Buscando...", msg_network_err: "Error de red.", msg_empty: "Vacío.",
                    status_valid: "OK", status_error: "ERR", msg_saved: "¡Guardado!", msg_deleted: "Eliminado."
                },
                jp: {
                    app_title: "セレンディピティ", lbl_lang: "言語", lbl_vision: "色覚", lbl_size: "文字サイズ",
                    vision_norm: "通常", intro_text: "記事を発見。", cat_prefix: "カテゴリー：",
                    btn_surprise: "驚かせて", btn_read: "記事を読む", btn_save: "💾 保存",
                    btn_test: "フィードテスト", lbl_saved_list: "保存された記事",
                    msg_loading: "検索中...", msg_network_err: "エラー", msg_empty: "空",
                    status_valid: "有効", status_error: "エラー", msg_saved: "保存しました", msg_deleted: "削除しました"
                }
            };

            // --- INITIALISATION ---
            const savedTheme = localStorage.getItem('theme');
            const savedProfile = localStorage.getItem('colorProfile') || 'normal';
            const savedFontScale = localStorage.getItem('fontScale') || '1';
            const savedLang = localStorage.getItem('appLang') || 'fr';

            if (savedTheme === 'dark') document.body.classList.add('dark-mode');
            applyColorProfile(savedProfile); document.getElementById('colorBlindSelect').value = savedProfile;
            applyFontSize(savedFontScale); document.getElementById('fontSlider').value = savedFontScale;
            document.getElementById('langSelect').value = savedLang;
            applyLanguage(savedLang);
            
            // Chargement initial des liens sauvegardés
            loadSavedLinks();

            // --- FONCTIONS UI ---
            function toggleTheme() {
                document.body.classList.toggle('dark-mode');
                localStorage.setItem('theme', document.body.classList.contains('dark-mode') ? 'dark' : 'light');
            }
            function changeColorProfile() {
                const p = document.getElementById('colorBlindSelect').value;
                applyColorProfile(p); localStorage.setItem('colorProfile', p);
            }
            function applyColorProfile(p) {
                document.body.classList.remove('protanopia', 'deuteranopia', 'tritanopia', 'achromatopsia');
                if (p !== 'normal') document.body.classList.add(p);
            }
            function changeFontSize() {
                const s = document.getElementById('fontSlider').value;
                applyFontSize(s); localStorage.setItem('fontScale', s);
            }
            function applyFontSize(s) { document.documentElement.style.setProperty('--font-scale', s); }
            function changeLanguage() {
                const l = document.getElementById('langSelect').value;
                applyLanguage(l); localStorage.setItem('appLang', l); resetView();
            }
            function applyLanguage(l) {
                const t = translations[l];
                document.querySelectorAll('[data-i18n]').forEach(el => {
                    const key = el.getAttribute('data-i18n');
                    if (t[key]) el.textContent = t[key];
                });
            }
            function getTrans(k) { return translations[document.getElementById('langSelect').value][k] || k; }

            // --- LOGIQUE ARTICLES ---
            function resetView() {
                currentArticleData = null;
                document.getElementById('saveBtn').style.display = 'none';
                document.getElementById('content').innerHTML = '<p>' + getTrans('cat_prefix') + document.getElementById('categorySelect').value + '</p>';
                document.getElementById('test-results').style.display = 'none';
            }

            async function fetchRandomArticle() {
                const contentDiv = document.getElementById('content');
                const btn = document.getElementById('mainBtn');
                const saveBtn = document.getElementById('saveBtn');
                
                contentDiv.innerHTML = '<p>' + getTrans('msg_loading') + '</p>';
                btn.disabled = true; btn.style.opacity = "0.7";
                saveBtn.style.display = 'none';

                try {
                    const response = await fetch('/get-random?category=' + encodeURIComponent(document.getElementById('categorySelect').value));
                    const data = await response.json();
                    btn.disabled = false; btn.style.opacity = "1";

                    if (data.error) { contentDiv.innerHTML = '<p class="status-err">' + data.error + '</p>'; return; }
                    
                    // On stocke les données pour la sauvegarde
                    currentArticleData = data;
                    saveBtn.style.display = 'inline-block';
                    saveBtn.textContent = getTrans('btn_save'); // Reset texte bouton
                    
                    contentDiv.innerHTML = `
                        <div><span class="source-tag">${data.source}</span></div>
                        <h2>${data.title}</h2>
                        <p>${data.summary}</p>
                        <a href="${data.link}" target="_blank" class="btn btn-read">${getTrans('btn_read')}</a>
                    `;
                } catch (e) { 
                    contentDiv.innerHTML = '<p class="status-err">' + getTrans('msg_network_err') + '</p>'; 
                    btn.disabled = false;
                }
            }

            // --- LOGIQUE SAUVEGARDE ---
            async function saveCurrentArticle() {
                if (!currentArticleData) return;
                
                try {
                    const response = await fetch('/api/save', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({url: currentArticleData.link, title: currentArticleData.title})
                    });
                    const res = await response.json();
                    if (res.success) {
                        document.getElementById('saveBtn').textContent = getTrans('msg_saved');
                        loadSavedLinks(); // Rafraichir la liste
                    }
                } catch (e) { console.error(e); }
            }

            async function loadSavedLinks() {
                try {
                    const response = await fetch('/api/saved-links');
                    const links = await response.json();
                    const list = document.getElementById('savedList');
                    list.innerHTML = '';
                    
                    links.forEach(item => {
                        const li = document.createElement('li');
                        li.className = 'saved-item';
                        li.innerHTML = `
                            <a href="${item.url}" target="_blank" class="saved-link">${item.title}</a>
                            <button class="saved-delete" onclick="deleteLink('${item.url}')" title="Supprimer">🗑</button>
                        `;
                        list.appendChild(li);
                    });
                } catch (e) { console.error(e); }
            }

            async function deleteLink(url) {
                if(!confirm("Supprimer ?")) return;
                try {
                    const response = await fetch('/api/delete', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({url: url})
                    });
                    const res = await response.json();
                    if(res.success) {
                        loadSavedLinks();
                    }
                } catch (e) { console.error(e); }
            }

            // --- DIAGNOSTICS ---
            async function runDiagnostics() {
                const d = document.getElementById('test-results');
                d.style.display = 'block'; d.innerHTML = getTrans('msg_test_run');
                try {
                    const r = await fetch('/test-sources?category=' + encodeURIComponent(document.getElementById('categorySelect').value));
                    const res = await r.json();
                    if(res.length===0) { d.innerHTML=getTrans('msg_empty'); return;}
                    let h=''; res.forEach(i=>{
                        h+=`<div style="display:flex;justify-content:space-between;border-bottom:1px solid #ddd;padding:5px;">
                            <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:150px;">${i.url.replace('https://','')}</span>
                            <span class="${i.valid?'status-ok':'status-err'}">${i.valid?'✅':'❌'}</span>
                           </div>`;
                    });
                    d.innerHTML=h;
                } catch(e) { d.innerHTML='Error'; }
            }
        </script>
    </body>
    </html>
    ''', categories=categories)

# --- ROUTES API ---

@app.route('/get-random')
def get_random():
    cat = request.args.get('category')
    cfg = load_feeds_config()
    urls = cfg.get(cat)
    if not urls: urls = list(cfg.values())[0] if cfg else []
    if not urls: return jsonify({"error": "Config Error"})

    try:
        url = random.choice(urls)
        feed = feedparser.parse(url)
        if not feed.entries: return jsonify({"error": "Empty Feed", "source": url})
        art = random.choice(feed.entries)
        
        summary = art.get('summary', '')
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(summary, "html.parser")
        
        return jsonify({
            "source": feed.feed.get('title', 'Source'),
            "title": art.get('title', 'No Title'),
            "link": art.get('link', '#'),
            "summary": soup.get_text()[:250] + "..."
        })
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/test-sources')
def test_sources():
    cat = request.args.get('category')
    cfg = load_feeds_config()
    urls = cfg.get(cat, [])
    rep = []
    for u in urls:
        try:
            f = feedparser.parse(u)
            rep.append({"url": u, "valid": (hasattr(f,'entries') and len(f.entries)>0)})
        except: rep.append({"url": u, "valid": False})
    return jsonify(rep)

# --- NOUVELLES ROUTES API POUR LA SAUVEGARDE ---

@app.route('/api/save', methods=['POST'])
def api_save():
    data = request.json
    success = save_link_to_file(data.get('url'), data.get('title', 'Sans titre'))
    return jsonify({"success": success})

@app.route('/api/saved-links')
def api_list_saved():
    return jsonify(get_saved_links())

@app.route('/api/delete', methods=['POST'])
def api_delete():
    data = request.json
    delete_link_from_file(data.get('url'))
    return jsonify({"success": True})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
