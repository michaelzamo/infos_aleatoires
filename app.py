from flask import Flask, jsonify, render_template_string, request
import feedparser
import random
import os

app = Flask(__name__)

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
            /* --- 1. VARIABLES GLOBALES (Base) --- */
            :root {
                --font-scale: 1;
                /* Valeurs par défaut (Thème Simple) */
                --font-main: "Noto Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                --bg-body: #f0f2f5;
                --bg-card: #ffffff;
                --text-main: #333333;
                --text-sub: #666666;
                --tag-bg: #e9ecef;
                --select-bg: #f9f9f9;
                --select-border: #ddd;
                --shadow: 0 10px 25px rgba(0,0,0,0.05);
                --col-primary: #007bff;
                --col-success: #28a745;
                --col-error: #dc3545;
                --col-link-read: #28a745;
                --border-rad: 16px; /* Arrondi standard */
                --border-width: 1px;
                --border-style: solid;
                --btn-shadow: none;
            }

            /* --- 2. THÈMES VISUELS --- */

            /* A. Thème IRLANDAIS (Vert, Or, Serif) */
            body.theme-irish {
                --font-main: "Georgia", "Times New Roman", serif;
                --bg-body: #e8f5e9; /* Vert très pâle */
                --bg-card: #ffffff;
                --text-main: #1b5e20; /* Vert forêt foncé */
                --text-sub: #4caf50;
                --tag-bg: #c8e6c9;
                --select-bg: #ffffff;
                --select-border: #81c784;
                --col-primary: #2e7d32; /* Vert trèfle */
                --col-link-read: #ff8f00; /* Orange/Or */
                --shadow: 0 4px 15px rgba(46, 125, 50, 0.2);
                --border-rad: 8px;
            }
            /* Petit détail visuel pour le fond irlandais */
            body.theme-irish::before {
                content: ""; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
                background: radial-gradient(circle at 50% 50%, #e8f5e9 0%, #c8e6c9 100%);
                z-index: -1;
            }

            /* B. Thème JAPONAIS (Minimaliste, Rouge, Papier, Carré) */
            body.theme-japanese {
                --font-main: "Hiragino Kaku Gothic Pro", "Meiryo", sans-serif;
                --bg-body: #fcfaf2; /* Blanc cassé papier */
                --bg-card: #ffffff;
                --text-main: #2b2b2b;
                --text-sub: #999;
                --tag-bg: #f0f0f0;
                --select-bg: #fff;
                --select-border: #2b2b2b;
                --col-primary: #bc002d; /* Rouge Japon */
                --col-link-read: #2b2b2b; /* Noir encre */
                --border-rad: 0px; /* Pas d'arrondis */
                --shadow: 5px 5px 0px rgba(0,0,0,0.1); /* Ombre dure */
                --border-width: 1px;
            }
            /* Texture papier pour le Japon */
            body.theme-japanese .card {
                border: 1px solid #eee;
                background-image: linear-gradient(0deg, transparent 24%, #fcfaf2 25%, #fcfaf2 26%, transparent 27%, transparent 74%, #fcfaf2 75%, #fcfaf2 76%, transparent 77%, transparent), linear-gradient(90deg, transparent 24%, #fcfaf2 25%, #fcfaf2 26%, transparent 27%, transparent 74%, #fcfaf2 75%, #fcfaf2 76%, transparent 77%, transparent);
                background-size: 50px 50px;
            }

            /* C. Thème STEAMPUNK (Cuivre, Laiton, Industriel) */
            body.theme-steampunk {
                --font-main: "Courier New", Courier, monospace;
                --bg-body: #2b2b2b;
                --bg-card: #d8cba8; /* Couleur Parchemin */
                --text-main: #3e2723; /* Marron foncé */
                --text-sub: #5d4037;
                --tag-bg: #bcaaa4;
                --select-bg: #efebe9;
                --select-border: #5d4037;
                --col-primary: #8d6e63; /* Bronze */
                --col-link-read: #bf360c; /* Rouille */
                --border-rad: 2px;
                --border-width: 3px;
                --border-style: double;
                --shadow: 0 0 20px rgba(0,0,0,0.7);
                --btn-shadow: inset 0 0 5px rgba(0,0,0,0.5);
            }
            /* Fond industriel */
            body.theme-steampunk::before {
                content: ""; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
                background: repeating-linear-gradient(45deg, #2b2b2b, #2b2b2b 10px, #1a1a1a 10px, #1a1a1a 20px);
                z-index: -1;
            }

            /* --- 3. MODE SOMBRE (Overrides pour le thème Simple) --- */
            body.dark-mode:not(.theme-steampunk):not(.theme-irish):not(.theme-japanese) {
                --bg-body: #121212;
                --bg-card: #1e1e1e;
                --text-main: #e0e0e0;
                --text-sub: #aaaaaa;
                --tag-bg: #333333;
                --select-bg: #2c2c2c;
                --select-border: #444;
                --shadow: rgba(0,0,0,0.5);
            }
            /* Le mode sombre ajuste aussi les thèmes spécifiques si nécessaire */
            body.dark-mode.theme-japanese {
                --bg-body: #111; --bg-card: #222; --text-main: #fff; --bg-card-img: none;
            }


            /* --- 4. PROFILS DALTONISME (Priorité Haute) --- */
            body.protanopia { --col-primary: #0072B2 !important; --col-success: #56B4E9 !important; --col-error: #D55E00 !important; }
            body.deuteranopia { --col-primary: #0072B2 !important; --col-success: #56B4E9 !important; --col-error: #D55E00 !important; }
            body.tritanopia { --col-primary: #000000 !important; --col-success: #009E73 !important; --col-error: #CC79A7 !important; }
            body.achromatopsia { --col-primary: #000000 !important; --col-success: #000000 !important; --col-error: #000000 !important; }


            /* --- 5. STYLES GÉNÉRAUX --- */
            body { 
                font-family: var(--font-main);
                display: flex; justify-content: center; align-items: center; 
                min-height: 100vh; margin: 0; padding: 20px; box-sizing: border-box;
                background-color: var(--bg-body); color: var(--text-main);
                transition: background 0.3s, color 0.3s, font-family 0.3s;
                font-size: calc(16px * var(--font-scale));
            }

            /* Correction taille police formulaires */
            button, select, input, .btn, .cat-select, .a11y-select { font-size: 1em !important; }
            .source-tag, .setting-label, .btn-test { font-size: 0.8em !important; }

            .card { 
                background: var(--bg-card); padding: 2rem; 
                border-radius: var(--border-rad); 
                box-shadow: var(--shadow); 
                border: var(--border-width) var(--border-style) var(--select-border);
                max-width: 500px; text-align: center; width: 100%; position: relative; 
            }

            .header-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
            h1 { font-size: 1.5em; color: var(--text-main); margin: 0; }
            
            .theme-toggle { background: none; border: none; cursor: pointer; padding: 5px; font-size: 1.2em; filter: grayscale(100%); }

            .settings-container {
                display: flex; flex-direction: column; gap: 10px; margin-bottom: 20px;
                background: var(--tag-bg); padding: 10px; border-radius: var(--border-rad);
                border: 1px solid var(--select-border);
            }
            .settings-row { display: flex; justify-content: space-between; align-items: center; }
            .setting-label { color: var(--text-sub); font-weight: bold; text-transform: uppercase;}

            .a11y-select {
                padding: 4px; border-radius: 4px;
                border: 1px solid var(--select-border);
                background-color: var(--select-bg); color: var(--text-main);
                max-width: 140px;
            }
            
            .font-slider-group { display: flex; align-items: center; gap: 8px; }
            input[type=range] { width: 80px; cursor: pointer; accent-color: var(--col-primary); }

            .cat-select {
                padding: 10px 15px; border-radius: var(--border-rad);
                border: 1px solid var(--select-border);
                background-color: var(--select-bg); color: var(--text-main);
                width: 100%; max-width: 300px; cursor: pointer; outline: none; margin-top: 10px; margin-bottom: 20px;
            }

            .source-tag { background: var(--tag-bg); padding: 4px 10px; border-radius: 20px; color: var(--text-sub); text-transform: uppercase; font-weight: bold; letter-spacing: 0.5px;}
            h2 { color: var(--text-main); margin: 15px 0; font-size: 1.3em; }
            p { color: var(--text-sub); line-height: 1.6; }

            .btn { 
                background-color: var(--col-primary); color: white; padding: 15px 30px; 
                text-decoration: none; border-radius: 50px; display: inline-block; 
                margin-top: 20px; cursor: pointer; border: none; font-weight: 600; width: 80%; 
                box-shadow: var(--btn-shadow);
            }
            .btn-read { background-color: var(--col-link-read); }
            
            .btn-test { background: none; border: none; color: var(--text-sub); margin-top: 30px; cursor: pointer; text-decoration: underline; opacity: 0.7;}
            
            #test-results { display: none; text-align: left; margin-top: 20px; background: var(--tag-bg); padding: 15px; border-radius: var(--border-rad); font-size: 0.85em; max-height: 200px; overflow-y: auto; }
            .result-item { display: flex; justify-content: space-between; align-items: center; padding: 5px 0; border-bottom: 1px solid var(--select-border); }
            .status-ok { color: var(--col-success); font-weight: bold; } 
            .status-err { color: var(--col-error); font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="card">
            <div class="header-row">
                <h1 data-i18n="app_title">Sérendipité</h1>
                <button class="theme-toggle" onclick="toggleTheme()" id="themeBtn" title="Mode Nuit">🌓</button>
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
                    <span class="setting-label" data-i18n="lbl_theme">THÈME</span>
                    <select id="themeSelect" class="a11y-select" onchange="changeAppTheme()">
                        <option value="simple" data-i18n="th_simple">Simple</option>
                        <option value="irish" data-i18n="th_irish">Irlandais ☘️</option>
                        <option value="japanese" data-i18n="th_japanese">Japonais 🇯🇵</option>
                        <option value="steampunk" data-i18n="th_steampunk">Steampunk ⚙️</option>
                    </select>
                </div>
                <div class="settings-row">
                    <span class="setting-label" data-i18n="lbl_vision">VISION</span>
                    <select id="colorBlindSelect" class="a11y-select" onchange="changeColorProfile()">
                        <option value="normal" data-i18n="vision_norm">Normale</option>
                        <option value="protanopia">Protanopie (R-)</option>
                        <option value="deuteranopia">Deutéranopie (V-)</option>
                        <option value="tritanopia">Tritanopie (B-)</option>
                        <option value="achromatopsia">Mono</option>
                    </select>
                </div>
                <div class="settings-row">
                    <span class="setting-label" data-i18n="lbl_size">TAILLE</span>
                    <div class="font-slider-group">
                        <span style="font-size: 0.8em">A</span>
                        <input type="range" id="fontSlider" min="0.8" max="1.5" step="0.1" value="1" oninput="changeFontSize()">
                        <span style="font-size: 1.2em">A</span>
                    </div>
                </div>
            </div>
            
            <select id="categorySelect" class="cat-select" onchange="resetView()">
                {% for name in categories %}
                    <option value="{{ name }}">{{ name }}</option>
                {% endfor %}
            </select>

            <div id="content" style="min-height: 150px; display:flex; flex-direction:column; justify-content:center;">
                <p data-i18n="intro_text">Cliquez pour découvrir un article.</p>
            </div>
            
            <button class="btn" onclick="fetchRandomArticle()" id="mainBtn" data-i18n="btn_surprise">Surprends-moi</button>
            
            <br>
            <button class="btn-test" onclick="runDiagnostics()" data-i18n="btn_test">Tester les flux</button>
            <div id="test-results"></div>
        </div>

        <script>
            // --- DICTIONNAIRE DE TRADUCTION ---
            const translations = {
                fr: {
                    app_title: "Sérendipité",
                    lbl_lang: "LANGUE",
                    lbl_theme: "THÈME",
                    lbl_vision: "VISION",
                    lbl_size: "TAILLE",
                    th_simple: "Simple",
                    th_irish: "Irlandais",
                    th_japanese: "Japonais",
                    th_steampunk: "Steampunk",
                    vision_norm: "Normale",
                    intro_text: "Cliquez pour découvrir un article au hasard.",
                    cat_prefix: "Catégorie : ",
                    btn_surprise: "Surprends-moi",
                    btn_read: "Lire l'article",
                    btn_test: "Tester les flux RSS",
                    msg_loading: "Recherche en cours...",
                    msg_network_err: "Erreur réseau.",
                    msg_empty: "Aucun flux trouvé.",
                    msg_test_run: "Test en cours...",
                    status_valid: "VALIDE",
                    status_error: "ERREUR"
                },
                en: {
                    app_title: "Serendipity",
                    lbl_lang: "LANGUAGE",
                    lbl_theme: "THEME",
                    lbl_vision: "VISION",
                    lbl_size: "SIZE",
                    th_simple: "Simple",
                    th_irish: "Irish",
                    th_japanese: "Japanese",
                    th_steampunk: "Steampunk",
                    vision_norm: "Normal",
                    intro_text: "Click to discover a random article.",
                    cat_prefix: "Category: ",
                    btn_surprise: "Surprise me",
                    btn_read: "Read article",
                    btn_test: "Test RSS feeds",
                    msg_loading: "Searching...",
                    msg_network_err: "Network error.",
                    msg_empty: "No feeds found.",
                    msg_test_run: "Testing...",
                    status_valid: "VALID",
                    status_error: "ERROR"
                },
                es: {
                    app_title: "Serendipia",
                    lbl_lang: "IDIOMA",
                    lbl_theme: "TEMA",
                    lbl_vision: "VISIÓN",
                    lbl_size: "TAMAÑO",
                    th_simple: "Simple",
                    th_irish: "Irlandés",
                    th_japanese: "Japonés",
                    th_steampunk: "Steampunk",
                    vision_norm: "Normal",
                    intro_text: "Haz clic para descubrir un artículo.",
                    cat_prefix: "Categoría: ",
                    btn_surprise: "Sorpréndeme",
                    btn_read: "Leer artículo",
                    btn_test: "Probar feeds RSS",
                    msg_loading: "Buscando...",
                    msg_network_err: "Error de red.",
                    msg_empty: "No se encontraron feeds.",
                    msg_test_run: "Probando...",
                    status_valid: "VÁLIDO",
                    status_error: "ERROR"
                },
                jp: {
                    app_title: "セレンディピティ",
                    lbl_lang: "言語",
                    lbl_theme: "テーマ",
                    lbl_vision: "色覚設定",
                    lbl_size: "文字サイズ",
                    th_simple: "シンプル",
                    th_irish: "アイリッシュ",
                    th_japanese: "和風",
                    th_steampunk: "スチームパンク",
                    vision_norm: "通常",
                    intro_text: "クリックして記事を発見しましょう。",
                    cat_prefix: "カテゴリー：",
                    btn_surprise: "驚かせて",
                    btn_read: "記事を読む",
                    btn_test: "RSSフィードをテスト",
                    msg_loading: "検索中...",
                    msg_network_err: "ネットワークエラー",
                    msg_empty: "フィードが見つかりません",
                    msg_test_run: "テスト中...",
                    status_valid: "有効",
                    status_error: "エラー"
                }
            };

            // --- INITIALISATION ---
            const savedTheme = localStorage.getItem('themeMode'); // Dark/Light
            const savedAppTheme = localStorage.getItem('appTheme') || 'simple'; // Style (Irish, etc)
            const savedProfile = localStorage.getItem('colorProfile') || 'normal';
            const savedFontScale = localStorage.getItem('fontScale') || '1';
            const savedLang = localStorage.getItem('appLang') || 'fr';

            // 1. Appliquer les préférences
            if (savedTheme === 'dark') document.body.classList.add('dark-mode');
            
            applyAppTheme(savedAppTheme);
            document.getElementById('themeSelect').value = savedAppTheme;

            applyColorProfile(savedProfile);
            document.getElementById('colorBlindSelect').value = savedProfile;

            applyFontSize(savedFontScale);
            document.getElementById('fontSlider').value = savedFontScale;

            document.getElementById('langSelect').value = savedLang;
            applyLanguage(savedLang);

            // --- FONCTIONS ---
            
            // Mode Nuit (Luminosité)
            function toggleTheme() {
                document.body.classList.toggle('dark-mode');
                localStorage.setItem('themeMode', document.body.classList.contains('dark-mode') ? 'dark' : 'light');
            }

            // Thème Visuel (Style)
            function changeAppTheme() {
                const theme = document.getElementById('themeSelect').value;
                applyAppTheme(theme);
                localStorage.setItem('appTheme', theme);
            }

            function applyAppTheme(theme) {
                // Nettoie les classes de thèmes
                document.body.classList.remove('theme-irish', 'theme-japanese', 'theme-steampunk');
                // Ajoute la nouvelle (sauf si c'est 'simple' qui est le défaut)
                if (theme !== 'simple') {
                    document.body.classList.add('theme-' + theme);
                }
            }

            function changeColorProfile() {
                const profile = document.getElementById('colorBlindSelect').value;
                applyColorProfile(profile);
                localStorage.setItem('colorProfile', profile);
            }
            function applyColorProfile(profile) {
                document.body.classList.remove('protanopia', 'deuteranopia', 'tritanopia', 'achromatopsia');
                if (profile !== 'normal') document.body.classList.add(profile);
            }

            function changeFontSize() {
                const scale = document.getElementById('fontSlider').value;
                applyFontSize(scale);
                localStorage.setItem('fontScale', scale);
            }
            function applyFontSize(scale) {
                document.documentElement.style.setProperty('--font-scale', scale);
            }

            function changeLanguage() {
                const lang = document.getElementById('langSelect').value;
                applyLanguage(lang);
                localStorage.setItem('appLang', lang);
                resetView();
            }

            function applyLanguage(lang) {
                const t = translations[lang];
                document.querySelectorAll('[data-i18n]').forEach(el => {
                    const key = el.getAttribute('data-i18n');
                    // On gère les options des select séparément
                    if (el.tagName === 'OPTION') {
                         if (t[key]) el.textContent = t[key];
                    } else {
                         if (t[key]) el.textContent = t[key];
                    }
                });
            }

            function getTrans(key) {
                const lang = document.getElementById('langSelect').value;
                return translations[lang][key] || "Text Missing";
            }

            // --- LOGIQUE METIER ---
            function resetView() {
                const category = document.getElementById('categorySelect').value;
                const catPrefix = getTrans('cat_prefix');
                document.getElementById('content').innerHTML = '<p>' + catPrefix + category + '</p>';
                document.getElementById('test-results').style.display = 'none';
            }

            function getSelectedCategory() {
                return document.getElementById('categorySelect').value;
            }

            async function fetchRandomArticle() {
                const contentDiv = document.getElementById('content');
                const btn = document.getElementById('mainBtn');
                const category = getSelectedCategory();
                
                contentDiv.innerHTML = '<p>' + getTrans('msg_loading') + '</p>';
                btn.disabled = true; btn.style.opacity = "0.7";

                try {
                    const response = await fetch('/get-random?category=' + encodeURIComponent(category));
                    const data = await response.json();
                    btn.disabled = false; btn.style.opacity = "1";

                    if (data.error) { 
                        contentDiv.innerHTML = '<p class="status-err">' + data.error + '</p>'; 
                        return; 
                    }
                    
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

            async function runDiagnostics() {
                const resultsDiv = document.getElementById('test-results');
                const category = getSelectedCategory();
                resultsDiv.style.display = 'block';
                resultsDiv.innerHTML = '<p style="text-align:center;">' + getTrans('msg_test_run') + '</p>';
                
                try {
                    const response = await fetch('/test-sources?category=' + encodeURIComponent(category));
                    const results = await response.json();
                    if(results.length === 0) { resultsDiv.innerHTML = '<p>' + getTrans('msg_empty') + '</p>'; return; }

                    let html = '';
                    results.forEach(item => {
                        const icon = item.valid ? '✅' : '❌';
                        const statusClass = item.valid ? 'status-ok' : 'status-err';
                        const statusText = item.valid ? getTrans('status_valid') : getTrans('status_error');
                        html += `
                        <div class="result-item">
                            <span style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:180px;" title="${item.url}">${item.url.replace('https://', '')}</span>
                            <span class="${statusClass}">${icon} ${statusText}</span>
                        </div>`;
                    });
                    resultsDiv.innerHTML = html;
                } catch (e) { resultsDiv.innerHTML = '<p class="status-err">' + getTrans('msg_network_err') + '</p>'; }
            }
        </script>
    </body>
    </html>
    ''', categories=categories)
# ... [Le reste du code Python : get_random, test_sources est identique] ...
@app.route('/get-random')
def get_random():
    category_name = request.args.get('category')
    feeds_config = load_feeds_config()
    url_list = feeds_config.get(category_name)
    if not url_list:
        url_list = list(feeds_config.values())[0] if feeds_config else []
        if not url_list: return jsonify({"error": "Config Error"})

    try:
        random_feed_url = random.choice(url_list)
        feed = feedparser.parse(random_feed_url)
        if not feed.entries: return jsonify({"error": "Empty Feed", "source": random_feed_url})
        article = random.choice(feed.entries)
        
        summary = article.get('summary', '...')
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(summary, "html.parser")
        
        return jsonify({
            "source": feed.feed.get('title', 'Source'),
            "title": article.get('title', 'No Title'),
            "link": article.get('link', '#'),
            "summary": soup.get_text()[:250] + "..."
        })
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/test-sources')
def test_sources():
    category_name = request.args.get('category')
    feeds_config = load_feeds_config()
    url_list = feeds_config.get(category_name, [])
    report = []
    for url in url_list:
        try:
            feed = feedparser.parse(url)
            is_valid = (hasattr(feed, 'entries') and len(feed.entries) > 0)
            report.append({"url": url, "valid": is_valid})
        except:
            report.append({"url": url, "valid": False})
    return jsonify(report)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
