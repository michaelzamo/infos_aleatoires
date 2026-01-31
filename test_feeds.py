import feedparser

# Codes couleurs pour la console
VERT = '\033[92m'
ROUGE = '\033[91m'
RESET = '\033[0m'

print("--- DÉBUT DU TEST DES FLUX ---")

try:
    with open('feeds.txt', 'r') as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
except FileNotFoundError:
    print("Erreur : Le fichier feeds.txt est introuvable.")
    exit()

for url in urls:
    print(f"Test de : {url} ...", end=" ")
    
    try:
        # On tente de lire le flux
        feed = feedparser.parse(url)
        
        # Vérification 1 : Code HTTP (200 = OK)
        status = getattr(feed, 'status', 200) # Certains flux locaux n'ont pas de status, on assume 200
        
        # Vérification 2 : Y a-t-il des entrées (articles) ?
        nb_articles = len(feed.entries)
        
        if status == 200 and nb_articles > 0:
            print(f"{VERT}OK{RESET} ({nb_articles} articles trouvés)")
            # Optionnel : Afficher le titre du flux pour confirmer
            # print(f"    Titre détecté : {feed.feed.get('title', 'Inconnu')}")
        else:
            print(f"{ROUGE}ÉCHEC{RESET}")
            if status != 200:
                print(f"    -> Erreur HTTP : {status}")
            if nb_articles == 0:
                print(f"    -> Aucun article trouvé (flux vide ou format incorrect)")
                
    except Exception as e:
        print(f"{ROUGE}ERREUR CRITIQUE{RESET} : {str(e)}")

print("--- FIN DU TEST ---")
