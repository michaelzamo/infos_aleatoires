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
def get_saved_links(category_filter=None):
    links = []
    if not os.path.exists(SAVED_FILE):
        return links
    try:
        with open(SAVED_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line: continue
                parts = line.split('|')
                
                if len(parts) == 2:
                    cat, url, title = "Général", parts[0], parts[1]
                elif len(parts) >= 3:
                    cat = parts[0]
                    url = parts[1]
                    title = "|".join(parts[2:])
                else:
                    continue

                if category_filter and cat != category_filter:
                    continue
                    
                links.append({'category': cat, 'url': url, 'title': title})
    except Exception as e:
        print(f"Erreur lecture sauvegarde: {e}")
    return links

def save_link_to_file(category, url, title):
    current_links = get_saved_links()
    for link in current_links:
        if link['url'] == url:
            return False 
    
    with open(SAVED_FILE, 'a', encoding='utf-8') as f:
        clean_title = title.replace('\n', ' ').replace('\r', '')
        f.write(f"{category}|{url}|{clean_title}\n")
    return True

def delete_link_from_file(url_to_delete):
    if not os.path.exists(SAVED_FILE): return False
    lines_to_keep = []
    deleted = False
    
    with open(SAVED_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('|')
            current_url = parts[0] if len(parts) == 2 else parts[1] if len(parts) >= 3 else ""
            if current_url == url_to_delete:
                deleted = True
            else:
                lines_to_keep.append(line)
    
    with open(SAVED_FILE, 'w', encoding='utf-8') as f:
        f.writelines(lines_to_keep)
    return deleted

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
                --col-save: #6c757d;
                --border-rad: 16px;
            }
            
            body.dark-mode {
                --bg-body: #121212; --bg-card: #1e1e1e;
                --text-main: #e0e0e0; --text-sub: #aaaaaa;
                --tag-bg: #333; --select-bg: #2c2c2c; --select-border: #444;
                --shadow: rgba(0,0,0,0.5);
            }

            /* PROFILS DALTONISME */
            body.protanopia, body.deuteranopia { --col-primary: #0072B2; --col-success: #56B4E9; --col-error: #D55E00; --col-link-read: #0072B2; }
            body.tritanopia { --col-primary: #000000; --col-success: #009E73; --col-error: #CC79A7; --col-link-read: #009E73; }
            body.achromatopsia { --col-primary: #000000; --col-success: #000000; --col-error: #000000; --col-link-read: #444444; }
            body.dark-mode.achromatopsia { --col-primary: #ffffff; --col-success: #ffffff; --col-error: #ffffff; --col-link-read: #dddddd; }

            /* STYLES GÉNÉRAUX */
            body { 
                font-family: "Noto Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; 
                display: flex; justify-content: center; align-items: center; 
                min-height: 100vh; margin: 0; padding: 20px; box-sizing: border-box;
                background-color: var(--bg-body); color: var(--text-main);
                transition: background 0.3s, color 0.3s;
                font-size: calc(16px * var(--font-scale));
            }

            button, select, input, .btn, .cat-select, .a11y-select { font-size: 1em !important; }
            .source-tag, .setting-label, .btn-test, .saved-category-label { font-size: 0.8em !important; }

            .card { 
                background: var(--bg-card); padding: 2rem; border-radius: var(--border-rad); 
                box-shadow: var(--shadow); max-width: 500px; text-align: center; width: 100%; 
                max-height: 90vh; overflow-y: auto;
            }

            .header-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
            h1 { font-size: 1.5em; margin: 0; }
            .theme-toggle { background: none; border: none; cursor: pointer; padding: 5px; font-size: 1.2em; }

            .settings-container {
                display: flex; flex-direction: column; gap: 10px; margin-bottom: 20px;
                background: var(--tag-bg); padding: 10px; border-radius: 8px;
            }
            .settings-row { display: flex; justify-content: space-between; align-items: center; }
            .setting-label { color: var(--text-sub); font-weight: bold; text-transform: uppercase;}
            .a11y-select { padding: 4px; border-radius: 4px; border: 1px solid var(--select-border); background-color: var(--select-bg); color: var(--text-main); max-width: 120px; }
            input[type=range] { width: 80px; cursor: pointer; }

            .cat-select { padding: 10px; border-radius: 8px; border: 1px solid var(--select-border); background-color: var(--select-bg); color: var(--text-main); width: 100%; margin-bottom: 15px; }

            .source-tag { background: var(--tag-bg); padding: 4px 10px; border-radius: 20px; color: var(--text-sub); text-transform: uppercase; font-weight: bold; }
            h2 { margin: 15px 0; font-size: 1.3em; }
            p { color: var(--text-sub); line-height: 1.6; }

            .action-buttons { display: flex; flex-direction: column; gap: 10px; align-items: center; margin-top: 20px; }
            .btn { 
                background-color: var(--col-primary); color: white; padding: 12px 25px; 
                text-decoration: none; border-radius: 50px; border: none; font-weight: 600; width: 80%; cursor: pointer;
            }
            .btn-read { background-color: var(--col-link-read); }
            .btn-save { background-color: var(--col-save); display: none; }
            .btn-test { background: none; border: none; color: var(--text-sub); margin-top: 20px; cursor: pointer; text-decoration: underline; opacity: 0.7;}

            .saved-section { margin-top: 30px; border-top: 1px solid var(--select-border); padding-top: 15px; text-align: left; }
            .saved-title { font-size: 1em; font-weight: bold; margin-bottom: 10px; color: var(--text-main); display:flex; justify-content:space-between; align-items:center;}
            .saved-category-label { font-weight: normal; color: var(--text-sub); background: var(--tag-bg); padding: 2px 8px; border-radius: 10px;}
            
            .saved-list { list-style: none; padding: 0; margin: 0; }
            .saved-item { 
                display: flex; justify-content: space-between; align-items: center; 
                padding: 8px 0; border-bottom: 1px solid var(--select-border); font-size: 0.9em;
            }
            .saved-link { text-decoration: none; color: var(--col-primary); flex-grow: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-right: 10px; }
            .saved-delete { background: none; border: none; cursor: pointer; font-size: 1.2em; color: var(--col-error); padding: 0 5px; }
            
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
                        <option value="fr">Français</option><option value="en">English</option>
                        <option value="es">Español</option><option value="jp">日本語</option>
                    </select>
                </div>
                <div class="settings-row">
                    <span class="setting-label" data-i18n="lbl_vision">VISION</span>
                    <select id="colorBlindSelect" class="a11y-select" onchange="changeColorProfile()">
                        <option value="normal" data-i18n="vision_norm">Normale</option>
                        <option value="protanopia">Protanopia</option>
                        <option value="deuteranopia">Deutéranopie</option>
                        <option value="tritanopia">Tritanopie</option>
                        <option value="achromatopsia">Mono</option>
                    </select>
                </div>
                <div class="settings-row">
                    <span class="setting-label" data-i18n="lbl_size">TAILLE</span>
                    <div style="display:flex; align-items:center; gap:5px">
                        <span>A</span>
                        <input type="range" id="fontSlider" min="0.8" max="1.5" step="0.1" value="1" oninput="changeFontSize()">
                        <span>A</span>
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
                <div class="saved-title">
                    <span data-i18n="lbl_saved_list">Articles sauvegardés</span>
                    <span id="savedCatLabel" class="saved-category-label"></span>
                </div>
                <ul id="savedList" class="saved-list"></ul>
                <p id="noSavedMsg" style="display:none; font-size:0.8em; color:var(--text-sub); margin-top:10px;">(Aucun article sauvegardé dans cette catégorie)</p>
            </div>

            <button class="btn-test" onclick="runDiagnostics()" data-i18n="btn_test">Tester les flux</button>
            <div id="test-results" style="display:none; margin-top:10px;"></div>
        </div>

        <script>
            let currentArticleData = null;

            const translations = {
                fr: {
                    app_title: "Sérendipité", lbl_lang: "LANGUE", lbl_vision: "VISION", lbl_size: "TAILLE",
                    vision_norm: "Normale", intro_text: "Cliquez pour découvrir.", cat_prefix: "Catégorie : ",
                    btn_surprise: "Surprends-moi", btn_read: "Lire l'article", btn_save: "💾 Sauvegarder",
                    btn_test: "Tester les flux", lbl_saved_list: "Sauvegardes",
                    msg_loading: "Recherche...", msg_network_err: "Erreur réseau.", msg_empty: "Vide.",
                    status_valid: "OK", status_error: "HS", msg_saved: "Sauvegardé !", msg_deleted: "Supprimé."
                },
                en: {
                    app_title: "Serendipity", lbl_lang: "LANGUAGE", lbl_vision: "VISION", lbl_size: "SIZE",
                    vision_norm: "Normal", intro_text: "Click to discover.", cat_prefix: "Category: ",
                    btn_surprise: "Surprise me", btn_read: "Read article", btn_save: "💾 Save",
                    btn_test: "Test feeds", lbl_saved_list: "Saved",
                    msg_loading: "Searching...", msg_network_err: "Network error.", msg_empty: "Empty.",
                    status_valid: "OK", status_error: "ERR", msg_saved: "Saved!", msg_deleted: "Deleted."
                },
                es: {
                    app_title: "Serendipia", lbl_lang: "IDIOMA", lbl_vision: "VISIÓN", lbl_size: "TAMAÑO",
                    vision_norm: "Normal", intro_text: "Descubrir artículo.", cat_prefix: "Categoría: ",
                    btn_surprise: "Sorpréndeme", btn_read: "Leer artículo", btn_save: "💾 Guardar",
                    btn_test: "Probar feeds", lbl_saved_list: "Guardados",
                    msg_loading: "Buscando...", msg_network_err: "Error de red.", msg_empty: "Vacío.",
                    status_valid: "OK", status_error: "ERR", msg_saved: "¡Guardado!", msg_deleted: "Eliminado."
                },
                jp: {
                    app_title: "セレンディピティ", lbl_lang: "言語", lbl_vision: "色覚", lbl_size: "文字サイズ",
                    vision_norm: "通常", intro_text: "記事を発見。", cat_prefix: "カテゴリー：",
                    btn_surprise: "驚かせて", btn_read: "記事を読む", btn_save: "💾 保存",
                    btn_test: "フィードテスト", lbl_saved_list: "保存リスト",
                    msg_loading: "検索中...", msg_network_err: "エラー", msg_empty: "空",
                    status_valid: "有効", status_error: "エラー", msg_saved: "保存しました", msg_deleted: "削除しました"
                }
            };

            // INITIALISATION
            const savedTheme = localStorage.getItem('themeMode');
            const savedProfile = localStorage.getItem('colorProfile') || 'normal';
            const savedFontScale = localStorage.getItem('fontScale') || '1';
            const savedLang = localStorage.getItem('appLang') || 'fr';

            if (savedTheme === 'dark') document.body.classList.add('dark-mode');
            applyColorProfile(savedProfile); document.getElementById('colorBlindSelect').value = savedProfile;
            applyFontSize(savedFontScale); document.getElementById('fontSlider').value = savedFontScale;
            document.getElementById('langSelect').value = savedLang;
            applyLanguage(savedLang);

            loadSavedLinks();

            // UI FUNCTIONS
            function toggleTheme() {
                document.body.classList.toggle('dark-mode');
                localStorage.setItem('themeMode', document.body.classList.contains('dark-mode') ? 'dark' : 'light');
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
                    const k = el.getAttribute('data-i18n');
                    if(t[k]) el.textContent = t[k];
                    if (el.tagName === 'OPTION' && t[k]) el.textContent = t[k];
                });
            }
            function getTrans(k) { return translations[document.getElementById('langSelect').value][k] || k; }

            // LOGIC
            function resetView() {
                currentArticleData = null;
                document.getElementById('saveBtn').style.display = 'none';
                const cat = document.getElementById('categorySelect').value;
                document.getElementById('content').innerHTML = '<p>' + getTrans('cat_prefix') + cat + '</p>';
                document.getElementById('test-results').style.display = 'none';
                loadSavedLinks();
            }

            async function fetchRandomArticle() {
                const contentDiv = document.getElementById('content');
                const btn = document.getElementById('mainBtn');
                const saveBtn = document.getElementById('saveBtn');
                const category = document.getElementById('categorySelect').value;
                
                contentDiv.innerHTML = '<p>' + getTrans('msg_loading') + '</p>';
                btn.disabled = true; btn.style.opacity = "0.7";
                saveBtn.style.display = 'none';

                try {
                    const response = await fetch('/get-random?category=' + encodeURIComponent(category));
                    const data = await response.json();
                    btn.disabled = false; btn.style.opacity = "1";

                    if (data.error) { contentDiv.innerHTML = '<p class="status-err">' + data.error + '</p>'; return; }
                    
                    currentArticleData = data;
                    currentArticleData.category = category;

                    saveBtn.style.display = 'inline-block';
                    saveBtn.textContent = getTrans('btn_save');
                    
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

            async function saveCurrentArticle() {
                if (!currentArticleData) return;
                try {
                    const response = await fetch('/api/save', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            category: currentArticleData.category,
                            url: currentArticleData.link, 
                            title: currentArticleData.title
                        })
                    });
                    const res = await response.json();
                    if (res.success) {
                        document.getElementById('saveBtn').textContent = getTrans('msg_saved');
                        loadSavedLinks();
                    }
                } catch (e) { console.error(e); }
            }

            async function loadSavedLinks() {
                const category = document.getElementById('categorySelect').value;
                document.getElementById('savedCatLabel').textContent = category;

                try {
                    const response = await fetch('/api/saved-links?category=' + encodeURIComponent(category));
                    const links = await response.json();
                    const list = document.getElementById('savedList');
                    const msg = document.getElementById('noSavedMsg');
                    list.innerHTML = '';
                    
                    if (links.length === 0) {
                        msg.style.display = 'block';
                    } else {
                        msg.style.display = 'none';
                        links.forEach(item => {
                            const li = document.createElement('li');
                            li.className = 'saved-item';
                            li.innerHTML = `
                                <a href="${item.url}" target="_blank" class="saved-link">${item.title}</a>
                                <button class="saved-delete" onclick="deleteLink('${item.url}')" title="Supprimer">🗑</button>
                            `;
                            list.appendChild(li);
                        });
                    }
                } catch (e) { console.error(e); }
            }

            async function deleteLink(url) {
                if(!confirm("Supprimer ?")) return;
                try {
                    const response = await fetch('/api/delete', {
                        method: 'POST', headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({url: url})
                    });
                    const res = await response.json();
                    if(res.success) loadSavedLinks();
                } catch (e) { console.error(e); }
            }

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
    except Exception as e: return jsonify({"error": str(e)})

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

@app.route('/api/save', methods=['POST'])
def api_save():
    d = request.json
    success = save_link_to_file(d.get('category', 'Général'), d.get('url'), d.get('title', 'Sans titre'))
    return jsonify({"success": success})

@app.route('/api/saved-links')
def api_list_saved():
    cat_filter = request.args.get('category')
    return jsonify(get_saved_links(cat_filter))

@app.route('/api/delete', methods=['POST'])
def api_delete():
    d = request.json
    delete_link_from_file(d.get('url'))
    return jsonify({"success": True})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
