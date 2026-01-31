from flask import Flask, jsonify, render_template_string
import feedparser
import random
import os
import time

app = Flask(__name__)

def get_feeds_from_file():
    """Lit le fichier feeds.txt et retourne une liste d'URLs."""
    feed_list = []
    try:
        with open('feeds.txt', 'r') as f:
            for line in f:
                clean_line = line.strip()
                if clean_line and not clean_line.startswith('#'):
                    feed_list.append(clean_line)
    except FileNotFoundError:
        return []
    return feed_list

@app.route('/')
def home():
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
            h1 { font-size: 1.5rem; color: #333; margin-bottom: 0.5rem; }
            h2 { margin: 15px 0; font-size: 1.3rem; line-height: 1.4; color: #111; }
            .source-tag { background: #e9ecef; padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; color: #555; text-transform: uppercase; font-weight: bold; letter-spacing: 0.5px;}
            
            /* Bouton Principal */
            .btn { background-color: #007bff; color: white; padding: 15px 30px; text-decoration: none; border-radius: 50px; display: inline-block; margin-top: 20px; cursor: pointer; border: none; font-size: 1rem; font-weight: 600; box-shadow: 0 4px 6px rgba(0,123,255,0.2); transition: transform 0.2s, background 0.2s; width: 80%; }
            .btn:active { transform: scale(0.96); }
            
            /* Lien Lire l'article */
            .btn-read { background-color: #28a745; box-shadow: 0 4px 6px rgba(40,167,69,0.2); }

            /* Bouton Test (Discret) */
            .btn-test { background: none; border: none; color: #aaa; margin-top: 30px; font-size: 0.8rem; cursor: pointer; text-decoration: underline; }
            .btn-test:hover { color: #666; }

            /* Zone de résultats du test */
            #test-results { display: none; text-align: left; margin-top: 20px; background: #fafafa; padding: 15px; border-radius: 8px; border: 1px solid #eee; font-size: 0.85rem; max-height: 200px; overflow-y: auto; }
            .result-item { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #eee; }
            .result-item:last-child { border-bottom: none; }
            .status-ok { color: green; font-weight: bold; }
            .status-err { color: red; font-weight: bold; }
            .feed-url { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 200px; color: #555; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>Sérendipité</h1>
            <div id="content" style="min-height: 150px; display:flex; flex-direction:column; justify-content:center;">
                <p style="color:#777;">Cliquez sur le bouton pour découvrir un article au hasard.</p>
            </div>
            
            <button class="btn" onclick="fetchRandomArticle()" id="mainBtn">Surprends-moi</button>
            
            <br>
            <button class="btn-test" onclick="runDiagnostics()">Tester les flux RSS</button>
            <div id="test-results"></div>
        </div>

        <script>
            async function fetchRandomArticle() {
                const contentDiv = document.getElementById('content');
                const btn = document.getElementById('mainBtn');
                
                contentDiv.innerHTML = '<p>Recherche en cours...</p>';
                btn.disabled = true;
                btn.style.opacity = "0.7";

                try {
                    const response = await fetch('/get-random');
                    const data = await response.json();
                    
                    btn.disabled = false;
                    btn.style.opacity = "1";

                    if (data.error) { 
                        contentDiv.innerHTML = '<p style="color:red">Oups: ' + data.error + '</p>'; 
                        return; 
                    }
                    contentDiv.innerHTML = `
                        <div><span class="source-tag">${data.source}</span></div>
                        <h2>${data.title}</h2>
                        <p style="color:#444; font-size:0.95rem;">${data.summary}</p>
                        <a href="${data.link}" target="_blank" class="btn btn-read">Lire l'article</a>
                    `;
                } catch (e) { 
                    contentDiv.innerHTML = '<p>Erreur de connexion au serveur.</p>';
                    btn.disabled = false;
                }
            }

            async function runDiagnostics() {
                const resultsDiv = document.getElementById('test-results');
                resultsDiv.style.display = 'block';
                resultsDiv.innerHTML = '<p style="text-align:center;">Test en cours... (patience)</p>';
                
                try {
                    const response = await fetch('/test-sources');
                    const results = await response.json();
                    
                    let html = '';
                    results.forEach(item => {
                        const icon = item.valid ? '✅' : '❌';
                        const statusClass = item.valid ? 'status-ok' : 'status-err';
                        const count = item.count > 0 ? `(${item.count} articles)` : '(Vide)';
                        
                        html += `
                        <div class="result-item">
                            <span class="feed-url" title="${item.url}">${item.url.replace('https://', '').replace('http://', '')}</span>
                            <span class="${statusClass}">${icon} ${item.valid ? 'OK' : 'HS'}</span>
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
    ''')

@app.route('/get-random')
def get_random():
    try:
        current_feeds = get_feeds_from_file()
        if not current_feeds:
            return jsonify({"error": "Aucun flux dans feeds.txt", "source": "Système"})

        random_feed_url = random.choice(current_feeds)
        feed = feedparser.parse(random_feed_url)
        
        if not feed.entries: 
            return jsonify({"error": "Flux vide ou inaccessible", "source": random_feed_url})
            
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
    """Teste tous les flux et renvoie un rapport complet."""
    feeds = get_feeds_from_file()
    report = []
    
    for url in feeds:
        try:
            # On utilise une librairie légère pour ne pas bloquer trop longtemps
            feed = feedparser.parse(url)
            is_valid = False
            count = 0
            
            # Un flux est valide s'il a au moins une entrée et pas d'erreur critique
            if hasattr(feed, 'entries') and len(feed.entries) > 0:
                is_valid = True
                count = len(feed.entries)
            
            report.append({
                "url": url,
                "valid": is_valid,
                "count": count
            })
        except:
            report.append({
                "url": url,
                "valid": False,
                "count": 0
            })
            
    return jsonify(report)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
