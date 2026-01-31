from flask import Flask, jsonify, render_template_string
import feedparser
import random
import os

app = Flask(__name__)

def get_feeds_from_file():
    """Lit le fichier feeds.txt et retourne une liste d'URLs nettoyées."""
    feed_list = []
    try:
        # On ouvre le fichier situé au même endroit que le script
        with open('feeds.txt', 'r') as f:
            for line in f:
                # On enlève les espaces et les sauts de ligne
                clean_line = line.strip()
                # On ignore les lignes vides ou celles qui commencent par #
                if clean_line and not clean_line.startswith('#'):
                    feed_list.append(clean_line)
    except FileNotFoundError:
        # Si le fichier n'existe pas, on met une source de secours
        return ["https://www.lemonde.fr/rss/une.xml"]
    
    # Si le fichier est vide, on renvoie aussi le secours
    return feed_list if feed_list else ["https://www.lemonde.fr/rss/une.xml"]

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
            body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; background-color: #f4f4f9; padding: 20px; box-sizing: border-box;}
            .card { background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); max-width: 500px; text-align: center; width: 100%; }
            h2 { margin: 20px 0; font-size: 1.4rem; }
            .source-tag { background: #eee; padding: 4px 8px; border-radius: 4px; font-size: 0.8rem; color: #555; text-transform: uppercase; letter-spacing: 1px;}
            .btn { background-color: #007bff; color: white; padding: 15px 30px; text-decoration: none; border-radius: 50px; display: inline-block; margin-top: 20px; cursor: pointer; border: none; font-size: 1rem; font-weight: bold; transition: transform 0.2s;}
            .btn:active { transform: scale(0.95); }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>Sérendipité</h1>
            <div id="content"><p>Cliquez pour découvrir un article.</p></div>
            <button class="btn" onclick="fetchRandomArticle()">Surprends-moi</button>
        </div>
        <script>
            async function fetchRandomArticle() {
                const contentDiv = document.getElementById('content');
                contentDiv.innerHTML = '<p>Recherche en cours...</p>';
                try {
                    const response = await fetch('/get-random');
                    const data = await response.json();
                    if (data.error) { 
                        contentDiv.innerHTML = '<p style="color:red">Erreur: ' + data.error + '</p>'; 
                        return; 
                    }
                    contentDiv.innerHTML = `
                        <span class="source-tag">${data.source}</span>
                        <h2>${data.title}</h2>
                        <p>${data.summary}</p>
                        <a href="${data.link}" target="_blank" class="btn" style="background-color: #28a745;">Lire l'article</a>
                    `;
                } catch (e) { 
                    contentDiv.innerHTML = '<p>Erreur réseau ou serveur.</p>'; 
                }
            }
        </script>
    </body>
    </html>
    ''')

@app.route('/get-random')
def get_random():
    try:
        # 1. Charger la liste depuis le fichier
        current_feeds = get_feeds_from_file()
        
        # 2. Choisir un flux au hasard
        random_feed_url = random.choice(current_feeds)
        
        # 3. Parsing (Récupération)
        feed = feedparser.parse(random_feed_url)
        
        if not feed.entries: 
            return jsonify({"error": "Flux vide ou inaccessible", "source": random_feed_url})
            
        article = random.choice(feed.entries)
        
        # 4. Nettoyage HTML
        summary = article.get('summary', 'Pas de description.')
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(summary, "html.parser")
        clean_summary = soup.get_text()

        return jsonify({
            "source": feed.feed.get('title', 'Source inconnue'),
            "title": article.get('title', 'Sans titre'),
            "link": article.get('link', '#'),
            "summary": clean_summary[:250] + "..." if len(clean_summary) > 250 else clean_summary
        })
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
