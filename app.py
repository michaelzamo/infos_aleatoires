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
            /* --- 1. COULEURS DE BASE (Base Theme) --- */
            :root {
                /* Fonds et textes */
                --bg-body: #f0f2f5;
                --bg-card: #ffffff;
                --text-main: #333333;
                --text-sub: #666666;
                --tag-bg: #e9ecef;
                --select-bg: #f9f9f9;
                --select-border: #ddd;
                --shadow: rgba(0,0,0,0.05);

                /* Couleurs Sémantiques (Par défaut: Standard) */
                --col-primary: #007bff;      /* Bleu standard */
                --col-success: #28a745;      /* Vert standard */
                --col-error: #dc3545;        /* Rouge standard */
                --col-link-read: #28a745;    /* Vert pour bouton lire */
            }
            
            /* --- 2. MODE SOMBRE (Dark Mode) --- */
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

            /* --- 3. PROFILS DALTONISME (Overrides) --- */
            
            /* Protanopie (Rouge absent) & Deutéranopie (Vert absent) 
               Solution : Utiliser Bleu vs Orange/Jaune */
            body.protanopia, body.deuteranopia {
                --col-primary: #0072B2;      /* Bleu profond */
                --col-success: #56B4E9;      /* Bleu ciel (distinct de l'orange) */
                --col-error: #D55E00;        /* Vermillon/Orange fort */
                --col-link-read: #0072B2;    /* Bouton lire en bleu */
            }

            /* Tritanopie (Bleu absent - confusion bleu/vert et jaune/violet)
               Solution : Utiliser Teal/Turquoise vs Rouge/Rose */
            body.tritanopia {
                --col-primary: #000000;      
                --col-success: #009E73;      /* Vert bleuté (Teal) */
                --col-error: #CC79A7;        /* Rose rougeâtre */
                --col-link-read: #009E73;
            }

            /* Achromatopsie (Vision niveaux de gris) 
               Solution : Contraste maximal */
            body.achromatopsia {
                --col-primary: #000000;
                --col-success: #000000;      /* Noir (on se fie aux icônes) */
                --col-error: #000000;        /* Noir */
                --col-link-read: #444444;
                /* En mode sombre, on inverse */
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
            .settings-row {
                display: flex; justify-content: flex-end; margin-bottom: 20px;
            }
            .a11y-select {
                padding: 5px; font-size: 0.8rem; border-radius: 4px;
                border: 1px solid var(--select-border);
                background-color: var(--select-bg); color: var(--text-main);
            }

            /* Menu Catégories */
            .select-container { margin-bottom: 20px; }
            .cat-select {
                padding: 10px 15px; font-size: 1rem; border-radius: 8px; 
                border: 1px solid var(--select-border);
                background-color: var(--select-bg); color: var(--text-main);
                width: 100%; max-width: 300px; cursor: pointer; outline: none;
            }

            .source-tag { background: var(--tag-bg); padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; color: var(--text-sub); text-transform: uppercase; font-weight: bold; letter-spacing: 0.5px;}
            
            h2 { color: var(--text-main); }
            p { color: var(--text-sub); }

            /* Boutons utilisant les variables dynamiques */
            .btn { 
                background-color: var(--col-primary); 
                color: white; padding: 15px 30px; text-decoration: none; border-radius: 50px; 
                display: inline-block; margin-top: 20px; cursor: pointer; border: none; 
                font-size: 1rem; font-weight: 600; width: 80%; 
            }
            .btn-read { background-color: var(--col-link-read); }
            
            .btn-test { background: none; border: none; color: var(--text-sub); margin-top: 30px; font-size: 0.8rem; cursor: pointer; text-decoration: underline; opacity: 0.7;}
            
            /* Résultats utilisant les variables dynamiques */
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

            <div class="settings-row">
                <select id="colorBlindSelect" class="a11y-select" onchange="changeColorProfile()">
                    <option value="normal">Vision Normale</option>
                    <option value="protanopia">Protanopie (Rouge-)</option>
                    <option value="deuteranopia">Deutéranopie (Vert-)</option>
                    <option value="tritanopia">Tritanopie (Bleu-)</option>
                    <option value="achromatopsia">Monochromatie</option>
                </select>
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
            // --- GESTION DU THÈME & ACCESSIBILITÉ ---
            
            // 1. Initialisation au chargement
            const savedTheme = localStorage.getItem('theme');
            const savedProfile = localStorage.getItem('colorProfile') || 'normal';

            if (savedTheme === 'dark') {
                document.body.classList.add('dark-mode');
            }
            
            // Applique le profil de daltonisme sauvegardé
            applyColorProfile(savedProfile);
            document.getElementById('colorBlindSelect').value = savedProfile;

            // 2. Fonction Mode Sombre (Reste la même)
            function toggleTheme() {
                const body = document.body;
                body.classList.toggle('dark-mode');
                localStorage.setItem('theme', body.classList.contains('dark-mode') ? 'dark' : 'light');
            }

            // 3. Fonction Profils Daltonisme
            function changeColorProfile() {
                const select = document.getElementById('colorBlindSelect');
                const profile = select.value;
                applyColorProfile(profile);
                localStorage.setItem('colorProfile', profile);
            }

            function applyColorProfile(profile) {
                // On retire toutes les classes de vision
                document.body.classList.remove('protanopia', 'deuteranopia', 'tritanopia', 'achromatopsia');
                
                // On ajoute celle choisie (si ce n'est pas "normal")
                if (profile !== 'normal') {
                    document.body.classList.add(profile);
                }
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
                        // Note : data.error s'affichera en rouge (ou orange/noir selon le profil)
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
                        // Les classes status-ok et status-err changeront de couleur selon le profil CSS
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
