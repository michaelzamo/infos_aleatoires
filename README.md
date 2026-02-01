# 🎲 Sérendipité - Lecteur RSS Aléatoire & Accessible

**Sérendipité** est une application web légère basée sur Flask (Python) qui vous permet de redécouvrir vos flux RSS. Au lieu de présenter une liste infinie d'articles non lus, elle vous propose **un article au hasard** tiré de vos sources préférées, favorisant la découverte et la lecture sans distraction.

L'application met un accent particulier sur l'**accessibilité** (modes daltoniens, taille de police) et la **sécurité**.

---

## ✨ Fonctionnalités

### 📖 Lecture & Découverte
* **Article Aléatoire :** Tirage au sort d'un article parmi une catégorie de flux RSS.
* **Sauvegarde :** Marquez des articles pour les lire plus tard (liste de lecture filtrable par catégorie).
* **Aperçu :** Affiche la source, le titre et un résumé propre avant de visiter le lien.

### ♿ Accessibilité & Confort
* **Thèmes :** Mode Clair ☀️ et Mode Sombre 🌙.
* **Daltonisme :** Modes adaptés pour la Protanopie, Deutéranopie, Tritanopie et l'Achromatopsie.
* **Lisibilité :** Curseur pour ajuster la taille du texte en temps réel.
* **Internationalisation :** Interface disponible en Français 🇫🇷, Anglais 🇬🇧, Espagnol 🇪🇸 et Japonais 🇯🇵.

### ⚙️ Administration & Technique
* **Gestionnaire de Flux :** Interface graphique (bouton ⚙️) pour ajouter/supprimer des catégories et des flux RSS.
* **Diagnostics :** Outil pour tester la validité des flux et supprimer les liens morts.
* **Persistance :** Aucune base de données complexe, tout est stocké dans des fichiers texte.

### 🔒 Sécurité Avancée
* **Authentification :** Protection par mot de passe via variables d'environnement.
* **Anti-XSS :** Nettoyage des données pour prévenir l'injection de code.
* **Anti-SSRF :** Protection contre les requêtes vers le réseau local ou les métadonnées cloud.

---

## 🚀 Installation

### Prérequis
* Python 3.8 ou supérieur.
* `pip` (gestionnaire de paquets Python).

### 1. Cloner ou télécharger le projet
Placez le fichier `app.py` dans un dossier.

### 2. Installer les dépendances
Créez un fichier nommé `requirements.txt` à la racine avec le contenu suivant :
```text
flask
feedparser
beautifulsoup4
python-dotenv
gunicorn
```

Puis lancez l'installation dans votre terminal :
```bash
pip install -r requirements.txt
```

### 3. Configurer la sécurité (Indispensable)
Voir la section **"Configuration & Sécurité"** ci-dessous pour créer vos identifiants avant de lancer l'application.

### 4. Lancer l'application
```bash
python app.py
```
L'application sera accessible à l'adresse : `http://localhost:5000`

---

## 🔐 Configuration & Sécurité (Important)

Pour sécuriser l'application, les identifiants ne sont **jamais** stockés dans le code source. Nous utilisons des variables d'environnement.

### A. En développement (Sur votre ordinateur)

1.  Créez un fichier nommé **`.env`** (sans nom avant le point) à la racine du projet.
2.  Ajoutez-y vos identifiants secrets :
    ```ini
    ADMIN_USER=admin
    ADMIN_PASS=MonMotDePasseSecret123
    ```
3.  **Important :** Si vous utilisez Git, assurez-vous d'avoir un fichier `.gitignore` contenant la ligne `.env` pour ne jamais publier ce fichier sur Internet.

### B. En production (Render, Heroku, etc.)

Puisque le fichier `.env` n'est pas envoyé sur le serveur (pour des raisons de sécurité), vous devez configurer ces variables dans l'interface de votre hébergeur.

1.  Allez dans les paramètres de votre application (Settings).
2.  Cherchez la section **Environment Variables** (ou Config Vars).
3.  Ajoutez deux variables :
    * **Key:** `ADMIN_USER`  | **Value:** `admin`
    * **Key:** `ADMIN_PASS`  | **Value:** `VotreMotDePasseComplexe`

---

## 📂 Structure des fichiers

* **`app.py`** : Le code source de l'application.
* **`.env`** : Fichier contenant vos mots de passe (à créer, **ne pas partager**).
* **`.gitignore`** : Liste des fichiers à ignorer par Git (doit contenir `.env`).
* **`feeds.txt`** : Stocke la liste de vos flux RSS (généré automatiquement).
* **`saved_links.txt`** : Stocke vos articles sauvegardés (généré automatiquement).
* **`requirements.txt`** : Liste des dépendances Python.

---

## ☁️ Déploiement (Exemple sur Render)

Cette application est "Cloud Ready".

1.  Assurez-vous que votre fichier `requirements.txt` contient bien `gunicorn`.
2.  Sur Render, créez un nouveau "Web Service".
3.  Connectez votre dépôt GitHub.
4.  Définissez la **Start Command** :
    ```bash
    gunicorn app:app
    ```
5.  N'oubliez pas de définir vos variables d'environnement (`ADMIN_USER` et `ADMIN_PASS`) dans l'onglet "Environment".

> **⚠️ Note HTTPS :** En production, assurez-vous toujours d'accéder à votre site via **HTTPS** (le cadenas 🔒) pour que votre mot de passe soit chiffré lors de la connexion. Les hébergeurs comme Render l'activent par défaut.

---

## 📄 Licence

Ce projet est open-source. Sentez-vous libre de le modifier et de l'améliorer pour votre usage personnel.
