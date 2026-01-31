from flask import Flask, jsonify, render_template_string, request
import feedparser
import random
import os

app = Flask(__name__)

def load_feeds_config():
    """Lit le fichier feeds.txt et le transforme en dictionnaire."""
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
            /* --- 1. COULEURS DE BASE --- */
            :root {
                /* Échelle de police par défaut (1 = 100%) */
                --font-scale: 1;

                --bg-body: #f0f2f5;
                --bg-card: #ffffff;
                --text-main: #333333;
                --text-sub: #666666;
                --tag-bg: #e9ecef;
                --select-bg: #f9f9f9;
                --select-border: #ddd;
                --shadow: rgba(0,0,0,0.05);

                --col-primary: #007bff;
                --col-success: #28a745;
                --col-error: #dc3545;
                --col-link-read: #28a745;
            }
            
            /* --- 2. MODE SOMBRE --- */
            body.dark-mode {
                --bg-body: #121212;
                --bg-card: #1e1e1e;
                --text-main: #e0e0e0;
                --text-sub: #aaaaaa;
                --tag-bg: #333333;
                --select-bg: #2c2c2c;
                --select-border: #444;
                --shadow: rgba(0,0,0,0.5);
            }

            /* --- 3. PROFILS DALTONISME --- */
            body.protanopia, body.deuteranopia {
                --col-primary: #0072B2;
                --col-success: #56B4E9;
                --col-error: #D55E00;
                --col-link-read: #0072B2;
            }
            body.tritanopia {
                --col-primary: #000000;      
                --col-success: #009E73;
                --col-error: #CC79A7;
                --col-link-read: #009E73;
            }
            body.achromatopsia {
                --col-primary: #000000;
                --col-success: #000000;
                --col-error: #000000;
                --col-link-read: #444444;
            }
            body.dark-mode.achromatopsia {
                --col-primary: #ffffff;
                --col-success: #ffffff;
                --col-error: #ffffff;
                --col-link-read: #dddddd;
            }

            /* --- STYLES GÉNÉRAUX --- */
            body { 
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; 
                display: flex; justify-content: center; align-items: center; 
                min-height: 100vh; margin: 0; padding: 20px; box-sizing: border-box;
                background-color: var(--bg-body); color: var(--text-main);
                transition: background-color 0.3s, color 0.3s;
                
                /* C'est ici que la magie de la taille opère */
                font-size: calc(16px * var(--font-scale));
            }

            .card { 
                background: var(--bg-card); padding: 2rem; border-radius: 16px; 
                box-shadow: 0 10px 25px var(--shadow); 
                max-width: 500px; text-align: center; width: 100%; position: relative; 
            }

            .header-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
            h1 { font-size: 1.5rem; color: var(--text-main); margin: 0; }
            
            .theme-toggle {
                background: none; border: none; font-size: 1.5rem; cursor: pointer;
                padding: 5px; border-radius: 50%;
            }

            /* Zone de réglages (Accessibilité) */
            .settings-container {
                display: flex; flex-direction: column; gap: 10px; margin-bottom: 20px;
                background: var(--tag-bg); padding: 10px; border-radius: 8px;
            }
            .settings-row {
                display: flex; justify-content: space-between; align-items: center;
            }
            .setting-label { font-size: 0.8rem; color: var(--text-sub); font-weight: bold;}

            .a11y-select {
                padding: 5px; font-size: 0.8rem; border-radius: 4px;
                border: 1px solid var(--select-border);
                background-color: var(--select-bg); color: var(--text-main);
            }
            
            /* Slider de police */
            .font-slider-group { display: flex; align-items: center; gap: 10px; }
            input[type=range] { width: 100px; cursor: pointer; }
            .font-icon { font-weight: bold; color: var(--text-sub); }

            /* Menu Catégories */
            .select-container { margin-bottom: 20px; margin-top: 10px;}
            .cat-select {
                padding: 10px 15px; font-size: 1rem; border-radius: 8px; 
                border: 1px solid var(--select-border);
                background-color: var(--select-bg); color: var(--text-main);
                width: 100%; max-width: 300px; cursor: pointer; outline: none;
            }

            .source-tag { background: var(--tag-bg); padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; color: var(--text-sub); text-transform: uppercase; font-weight: bold; letter-spacing: 0.5px;}
            
            h2 { color: var(--text-main); margin: 15px 0; font-size: 1.3em; }
            p { color: var(--text-sub); line-height: 1.6; }

            .btn { 
                background-color: var(--col-primary); 
                color: white; padding: 15px 30px; text-decoration: none; border-radius: 50px; 
                display: inline-block; margin-top: 20px; cursor: pointer; border: none; 
                font-size: 1rem; font-weight: 600; width: 80%; 
            }
            .btn-read { background-color: var(--col-link-read); }
            
            .btn-test { background: none; border: none; color: var(--text-sub); margin-top: 30px; font-size: 0.8rem; cursor: pointer; text-decoration: underline; opacity: 0.7;}
            
            #test-results { display: none; text-align: left; margin-top: 20px; background: var(--tag-bg); padding: 15px; border-radius: 8px; font-size: 0.85rem; max-height: 200px; overflow-y: auto; }
            .result-item { display: flex; justify-content: space-between; align-items: center; padding: 5px 0; border-bottom: 1px solid var(--select-border); }
            
            .status-ok { color: var(--col-success); font-weight: bold; } 
            .status-err { color: var(--col-error); font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="card">
            <div class="header-row">
                <h1>Sérendipité</h1>
                <button class="theme-toggle" onclick="toggleTheme()" id="themeBtn" title="Mode Sombre/Clair">🌓</button>
            </div>

            <div class="settings-container">
                <div class="settings-row">
                    <span class="setting-label">VISION</span>
                    <select id="colorBlindSelect" class="a11y-select" onchange="changeColorProfile()">
                        <option value="normal">Normale</option>
                        <option value="protanopia">Protanopie (R-)</option>
                        <option value="deuteranopia">Deutéranopie (V-)</option>
                        <option value="tritanopia">Tritanopie (B-)</option>
                        <option value="achromatopsia">Mono</option>
                    </select>
                </div>
                <div class="settings-row">
                    <span class="setting-label">TAILLE</span>
                    <div class="font-slider-group">
                        <span class="font-icon" style="font-size: 0.8rem">A</span>
                        <input type="range" id="fontSlider" min="0.8" max="1.5" step="0.1" value="1" oninput="changeFontSize()">
                        <span class="font-icon" style="font-size: 1.2rem">A</span>
                    </div>
                </div>
            </div>
            
            <div class="select-container">
                <select id="categorySelect" class="cat-select" onchange="resetView()">
                    {% for name in categories %}
                        <option value="{{ name }}">{{ name }}</option>
                    {% endfor %}
                </select>
            </div>

            <div id="content" style="min-height: 150px; display:flex; flex-direction:column; justify-content:center;">
                <p>Cliquez pour découvrir un article.</p>
            </div>
            
            <button class="btn" onclick="fetchRandomArticle()" id="mainBtn">Surprends-moi</button>
            
            <br>
            <button class="btn-test" onclick="runDiagnostics()">Tester les flux</button>
            <div id="test-results"></div>
        </div>

        <script>
            // --- GESTION DES REGLAGES (THEME, COULEURS, POLICE) ---
            
            // Initialisation au chargement
            const savedTheme = localStorage.getItem('theme');
            const savedProfile = localStorage.getItem('colorProfile') || 'normal';
            const savedFontScale = localStorage.getItem('fontScale') || '1';

            // 1. Theme
            if (savedTheme === 'dark') document.body.classList.add('dark-mode');
            
            // 2. Daltonisme
            applyColorProfile(savedProfile);
            document.getElementById('colorBlindSelect').value = savedProfile;

            // 3. Police
            applyFontSize(savedFontScale);
            document.getElementById('fontSlider').value = savedFontScale;


            // --- Fonctions ---
            function toggleTheme() {
                document.body.classList.toggle('dark-mode');
                localStorage.setItem('theme', document.body.classList.contains('dark-mode') ? 'dark' : 'light');
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
                // On modifie la variable CSS globale
                document.documentElement.style.setProperty('--font-scale', scale);
            }


            // --- LOGIQUE METIER (FLUX) ---
            function resetView() {
                const category = document.getElementById('categorySelect').value;
                document.getElementById('content').innerHTML = '<p>Catégorie : ' + category + '</p>';
                document.getElementById('test-results').style.display = 'none';
            }

            function getSelectedCategory() {
                return document.getElementById('categorySelect').value;
            }

            async function fetchRandomArticle() {
                const contentDiv = document.getElementById('content');
                const btn = document.getElementById('mainBtn');
                const category = getSelectedCategory();
                
                contentDiv.innerHTML = '<p>Recherche...</p>';
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
                        <a href="${data.link}" target="_blank" class="btn btn-read">Lire l'article</a>
                    `;
                } catch (e) { 
                    contentDiv.innerHTML = '<p class="status-err">Erreur réseau.</p>'; 
                    btn.disabled = false;
                }
            }

            async function runDiagnostics() {
                const resultsDiv = document.getElementById('test-results');
                const category = getSelectedCategory();
                resultsDiv.style.display = 'block';
                resultsDiv.innerHTML = '<p style="text-align:center;">Test en cours...</p>';
                
                try {
                    const response = await fetch('/test-sources?category=' + encodeURIComponent(category));
                    const results = await response.json();
                    if(results.length === 0) { resultsDiv.innerHTML = '<p>Aucun flux trouvé.</p>'; return; }

                    let html = '';
                    results.forEach(item => {
                        const icon = item.valid ? '✅' : '❌';
                        const statusClass = item.valid ? 'status-ok' : 'status-err';
                        const statusText = item.valid ? 'VALIDE' : 'ERREUR';
                        html += `
                        <div class="result-item">
                            <span style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:180px;" title="${item.url}">${item.url.replace('https://', '')}</span>
                            <span class="${statusClass}">${icon} ${statusText}</span>
                        </div>`;
                    });
                    resultsDiv.innerHTML = html;
                } catch (e) { resultsDiv.innerHTML = '<p class="status-err">Erreur test.</p>'; }
            }
        </script>
    </body>
    </html>
    ''', categories=categories)

# ... Le reste du fichier (routes get_random, test_sources) est identique ...
# ... Copiez les routes du message précédent si besoin ...

@app.route('/get-random')
def get_random():
    category_name = request.args.get('category')
    feeds_config = load_feeds_config()
    url_list = feeds_config.get(category_name)
    if not url_list:
        url_list = list(feeds_config.values())[0] if feeds_config else []
        if not url_list: return jsonify({"error": "Aucun flux configuré."})

    try:
        random_feed_url = random.choice(url_list)
        feed = feedparser.parse(random_feed_url)
        if not feed.entries: return jsonify({"error": "Flux vide ou erreur", "source": random_feed_url})
        article = random.choice(feed.entries)
        
        summary = article.get('summary', 'Pas de description.')
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(summary, "html.parser")
        
        return jsonify({
            "source": feed.feed.get('title', 'Source inconnue'),
            "title": article.get('title', 'Sans titre'),
            "link": article.get('link', '#'),
            "summary": soup.get_text()[:200] + "..."
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
