from flask import Flask, jsonify, render_template_string
import feedparser
import random
import os

app = Flask(__name__)

RSS_FEEDS = [
    "https://www.lemonde.fr/rss/une.xml",
    "https://feeds.leparisien.fr/leparisien/une",
    "https://www.courrierinternational.com/feed/category/6260/rss.xml",
    "https://korben.info/feed",
    "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml"
]

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
            body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background-color: #f4f4f9; padding: 20px;}
            .card { background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); max-width: 500px; text-align: center; width: 100%; }
            h2 { margin: 20px 0; }
            .btn { background-color: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 50px; display: inline-block; margin-top: 20px; cursor: pointer; border: none; font-size: 1rem;}
        </style>
    </head>
    <body>
        <div class="card">
            <h1>Sérendipité</h1>
            <div id="content"><p>Cliquez pour découvrir.</p></div>
            <button class="btn" onclick="fetchRandomArticle()">Surprends-moi</button>
        </div>
        <script>
            async function fetchRandomArticle() {
                const contentDiv = document.getElementById('content');
                contentDiv.innerHTML = '<p>Recherche...</p>';
                try {
                    const response = await fetch('/get-random');
                    const data = await response.json();
                    if (data.error) { contentDiv.innerHTML = '<p style="color:red">Erreur: ' + data.error + '</p>'; return; }
                    contentDiv.innerHTML = `<strong>${data.source}</strong><h2>${data.title}</h2><p>${data.summary}</p><a href="${data.link}" target="_blank" class="btn" style="background-color: green;">Lire</a>`;
                } catch (e) { contentDiv.innerHTML = '<p>Erreur réseau.</p>'; }
            }
        </script>
    </body>
    </html>
    ''')

@app.route('/get-random')
def get_random():
    try:
        random_feed_url = random.choice(RSS_FEEDS)
        feed = feedparser.parse(random_feed_url)
        if not feed.entries: return jsonify({"error": "Flux vide", "source": random_feed_url})
        article = random.choice(feed.entries)
        # Nettoyage basique du résumé pour éviter les erreurs HTML
        summary = article.get('summary', 'Pas de description.')
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(summary, "html.parser")
        return jsonify({
            "source": feed.feed.get('title', 'Source inconnue'),
            "title": article.get('title', 'Sans titre'),
            "link": article.get('link', '#'),
            "summary": soup.get_text()[:250] + "..."
        })
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)