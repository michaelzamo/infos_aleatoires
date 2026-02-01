🎲 Sérendipité - Lecteur RSS Aléatoire & Accessible
Sérendipité est une application web légère basée sur Flask (Python) qui vous permet de redécouvrir vos flux RSS. Au lieu de présenter une liste infinie d'articles non lus, elle vous propose un article au hasard tiré de vos sources préférées, favorisant la découverte et la lecture sans distraction.
L'application met un accent particulier sur l'accessibilité (modes daltoniens, taille de police) et la sécurité.
✨ Fonctionnalités
📖 Lecture & Découverte
Article Aléatoire : Tirage au sort d'un article parmi une catégorie de flux RSS.
Sauvegarde : Marquez des articles pour les lire plus tard (liste de lecture filtrable par catégorie).
Aperçu : Affiche la source, le titre et un résumé propre avant de visiter le lien.
♿ Accessibilité & Confort
Thèmes : Mode Clair ☀️ et Mode Sombre 🌙.
Daltonisme : Modes adaptés pour la Protanopie, Deutéranopie, Tritanopie et l'Achromatopsie.
Lisibilité : Curseur pour ajuster la taille du texte en temps réel.
Internationalisation : Interface disponible en Français 🇫🇷, Anglais 🇬🇧, Espagnol 🇪🇸 et Japonais 🇯🇵.
⚙️ Administration & Technique
Gestionnaire de Flux : Interface graphique (bouton ⚙️) pour ajouter/supprimer des catégories et des flux RSS.
Diagnostics : Outil pour tester la validité des flux et supprimer les liens morts.
Persistance : Aucune base de données complexe, tout est stocké dans des fichiers texte (feeds.txt, saved_links.txt).
🔒 Sécurité
Authentification : Protection par mot de passe (Basic Auth).
Anti-XSS : Nettoyage des titres et sources pour prévenir l'injection de code.
Anti-SSRF : Protection contre les requêtes vers le réseau local ou les métadonnées cloud.
🚀 Installation
Prérequis
Python 3.8 ou supérieur.
pip (gestionnaire de paquets Python).
1. Cloner ou télécharger le projet
Placez le fichier app.py dans un dossier.
2. Installer les dépendances
Créez un fichier requirements.txt avec le contenu suivant :
