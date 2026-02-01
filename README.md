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
* **Persistance :** Aucune base de données complexe, tout est stocké dans des fichiers texte (`feeds.txt`, `saved_links.txt`).

### 🔒 Sécurité
* **Authentification :** Protection par mot de passe (Basic Auth).
* **Anti-XSS :** Nettoyage des titres et sources pour prévenir l'injection de code.
* **Anti-SSRF :** Protection contre les requêtes vers le réseau local ou les métadonnées cloud.

---

## 🚀 Installation

### Prérequis
* Python 3.8 ou supérieur.
* `pip` (gestionnaire de paquets Python).

### 1. Cloner ou télécharger le projet
Placez le fichier `app.py` dans un dossier.

### 2. Installer les dépendances
Créez un fichier `requirements.txt` avec le contenu suivant :
```text
flask
feedparser
beautifulsoup4
gunicorn
```

Puis lancez l'installation :
```bash
pip install -r requirements.txt
```

### 3. Lancer l'application
```bash
python app.py
```
L'application sera accessible à l'adresse : `http://localhost:5000`

---

## 🔐 Configuration & Sécurité

### Identifiants par défaut
Lors de la première connexion, l'application vous demandera de vous authentifier.
* **Utilisateur :** `admin`
* **Mot de passe :** `changezMoi123`

### Changer le mot de passe
Il est **impératif** de changer le mot de passe par défaut pour une mise en ligne.

**Méthode 1 : Variables d'environnement (Recommandé)**
Définissez les variables avant de lancer le script.

*Sur Linux/Mac :*
```bash
export ADMIN_USER="monNom"
export ADMIN_PASS="monNouveauMotDePasse"
python app.py
```

*Sur Windows (CMD) :*
```cmd
set ADMIN_USER=monNom
set ADMIN_PASS=monNouveauMotDePasse
python app.py
```

**Méthode 2 : Modifier le code**
Ouvrez `app.py` et modifiez les lignes suivantes au début du fichier :
```python
ADMIN_USERNAME = os.environ.get('ADMIN_USER', 'votre_login')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASS', 'votre_mot_de_passe_secret')
```

---

## 📂 Structure des fichiers

* **`app.py`** : Le cœur de l'application (Backend Flask, Logique, Frontend HTML/JS/CSS).
* **`feeds.txt`** : Stocke la liste de vos flux RSS (format texte).
* **`saved_links.txt`** : Stocke vos articles sauvegardés.
* **`requirements.txt`** : Liste des dépendances.

---

## ☁️ Déploiement (Render / Heroku)

Cette application est prête pour le cloud ("Cloud Ready").

1.  Assurez-vous d'avoir le fichier `requirements.txt` à la racine.
2.  Sur votre hébergeur (ex: Render), définissez la **commande de lancement (Start Command)** :
    ```bash
    gunicorn app:app
    ```
3.  Ajoutez vos **Variables d'Environnement** (`ADMIN_USER`, `ADMIN_PASS`) dans l'interface de votre hébergeur.
4.  L'application écoutera automatiquement sur le port défini par l'hébergeur.

> **⚠️ Important :** En production, assurez-vous toujours d'utiliser le protocole **HTTPS** pour chiffrer votre mot de passe lors de la connexion.

---

## 📄 Licence

Ce projet est open-source. Sentez-vous libre de le modifier et de l'améliorer pour votre usage personnel.
