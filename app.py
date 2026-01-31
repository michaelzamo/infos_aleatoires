from flask import Flask, jsonify, render_template_string, request
import feedparser
import random
import os

app = Flask(__name__)

def load_feeds_config():
    """
    Lit le fichier feeds.txt et le transforme en dictionnaire.
    Structure retournée : {'Nom Catégorie': ['url1', 'url2'], ...}
    """
    feeds_data = {}
    current_category = None

    try:
        # encoding='utf-8' est important pour les accents dans les noms de catégories
        with open('feeds.txt', 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                
                # Si la ligne est vide ou est un commentaire, on passe
                if not line or line.startswith('#'):
                    continue
                
                # Si c'est une catégorie entre crochets [Nom]
                if line.startswith('[') and line.endswith(']'):
                    current_category = line[1:-1] # On enlève les crochets
                    feeds_data[current_category] = []
                
                # Sinon, c'est une URL (si on a déjà une catégorie définie)
                elif current_category:
                    feeds_data[current_category].append(line)
                    
    except FileNotFoundError:
        # Fallback si le fichier n'existe pas
        return {"Défaut": ["https://www.lemonde.fr/rss/une.xml"]}
    
    return feeds_data

@app.route('/')
def home():
    feeds_config = load_feeds_config()
    categories = list(feeds_config.keys())
    
    # S'il n'y a pas de catégories, on met un message par défaut
    if not categories:
        categories = ["Aucune catégorie"]

    return render_template_string('''
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Info Aléatoire</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; background-color: #f0f2f5; padding: 20px; box-sizing: border-box;}
            .card { background: white; padding: 2rem; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); max-width: 500px; text-align: center; width: 100%; position: relative; }
            h1 { font-size: 1.5rem; color: #333; margin-bottom: 1rem; }
            
            .select-container { margin-bottom: 20px; }
            select {
                padding: 10px 15px; font-size: 1rem; border-radius: 8px; border: 1px solid #ddd;
                background-color: #f9f9f9; width: 100%; max-width: 300px; cursor: pointer; outline: none;
            }
            select:focus { border-color: #007bff; }

            .source-tag { background: #e9ecef; padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; color: #555; text-transform: uppercase; font-weight: bold; letter-spacing: 0.5px;}
            .btn { background-color: #007bff; color: white; padding: 15px 30px; text-decoration: none; border-radius: 50px; display: inline-block; margin-top: 20px; cursor: pointer; border: none; font-size: 1rem; font-weight: 600; box-shadow: 0 4px 6px rgba(0,123,255,0.2); transition: transform 0.2s; width: 80%; }
            .btn:active { transform: scale(0.96); }
            .btn-read { background-color: #28a745; box-shadow: 0 4px 6px rgba(40,167,69,0.2); }
            
            .btn-test { background: none; border: none; color: #aaa; margin-top: 30px; font-size: 0.8rem; cursor: pointer; text-decoration: underline; }
            #test-results { display: none; text-align: left; margin-top: 20px; background: #fafafa; padding: 15px; border-radius: 8px; border: 1px solid #eee; font-size: 0.85rem; max-height: 200px; overflow-y: auto; }
            .result-item { display: flex; justify-content: space-between; align-items: center; padding: 5px 0; border-bottom: 1px solid #eee; }
            .status-ok { color: green; } .status-err { color: red; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>Sérendipité</h1>
            
            <div class="select-container">
                <select id="categorySelect" onchange="resetView()">
                    {% for name in categories %}
                        <option value="{{ name }}">{{ name }}</option>
                    {% endfor %}
                </select>
            </div>

            <div id="content" style="min-height: 150px; display:flex; flex-direction:column; justify-content:center;">
                <p style="color:#777;">Cliquez pour découvrir un article.</p>
            </div>
            
            <button class="btn" onclick="fetchRandomArticle()" id="mainBtn">Surprends-moi</button>
            
            <br>
            <button class="btn-test" onclick="runDiagnostics()">Tester cette catégorie</button>
            <div id="test-results"></div>
        </div>

        <script>
            function resetView() {
                const category = document.getElementById('categorySelect').value;
                document.getElementById('content').innerHTML = '<p style="color:#777;">Catégorie : ' + category + '</p>';
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
                btn.disabled = true;
                btn.style.opacity = "0.7";

                try {
                    const response = await fetch('/get-random?category=' + encodeURIComponent(category));
                    const data = await response.json();
                    
                    btn.disabled = false;
                    btn.style.opacity = "1";

                    if (data.error) { 
                        contentDiv.innerHTML = '<p style="color:red">' + data.error + '</p>'; 
                        return; 
                    }
                    contentDiv.innerHTML = `
                        <div><span class="source-tag">${data.source}</span></div>
                        <h2>${data.title}</h2>
                        <p style="color:#444; font-size:0.95rem;">${data.summary}</p>
                        <a href="${data.link}" target="_blank" class="btn btn-read">Lire l'article</a>
                    `;
                } catch (e) { 
                    contentDiv.innerHTML = '<p>Erreur réseau.</p>';
                    btn.disabled = false;
                }
            }

            async function runDiagnostics() {
                const resultsDiv = document.getElementById('test-results');
                const category = getSelectedCategory();
                
                resultsDiv.style.display = 'block';
                resultsDiv.innerHTML = '<p style="text-align:center;">Test des flux...</p>';
                
                try {
                    const response = await fetch('/test-sources?category=' + encodeURIComponent(category));
                    const results = await response.json();
                    
                    if(results.length === 0) {
                        resultsDiv.innerHTML = '<p>Aucun flux trouvé.</p>';
                        return;
                    }

                    let html = '';
                    results.forEach(item => {
                        const icon = item.valid ? '✅' : '❌';
                        html += `
                        <div class="result-item">
                            <span style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:200px;" title="${item.url}">${item.url.replace('https://', '')}</span>
                            <span class="${item.valid ? 'status-ok' : 'status-err'}">${icon}</span>
                        </div>`;
                    });
                    resultsDiv.innerHTML = html;
                } catch (e) {
                    resultsDiv.innerHTML = '<p style="color:red">Erreur lors du test.</p>';
                }
            }
        </script>
    </body>
    </html>
    ''', categories=categories)

@app.route('/get-random')
def get_random():
    category_name = request.args.get('category')
    
    # On recharge la config à chaque appel (permet de modifier le fichier sans redémarrer)
    feeds_config = load_feeds_config()
    
    # Si la catégorie n'existe pas, on prend la première dispo
    url_list = feeds_config.get(category_name)
    if not url_list:
        if feeds_config:
            url_list = list(feeds_config.values())[0]
        else:
            return jsonify({"error": "Aucun flux configuré."})

    try:
        random_feed_url = random.choice(url_list)
        feed = feedparser.parse(random_feed_url)
        
        if not feed.entries: 
            return jsonify({"error": "Ce flux est vide ou inaccessible", "source": random_feed_url})
            
        article = random.choice(feed.entries)
        
        summary = article.get('summary', 'Pas de description.')
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(summary, "html.parser")
        clean_summary = soup.get_text()

        return jsonify({
            "source": feed.feed.get('title', 'Source inconnue'),
            "title": article.get('title', 'Sans titre'),
            "link": article.get('link', '#'),
            "summary": clean_summary[:200] + "..." if len(clean_summary) > 200 else clean_summary
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
