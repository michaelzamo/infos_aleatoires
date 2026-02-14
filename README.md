# Sérendipité 📰🎧

**Sérendipité** est une application web minimaliste conçue pour la découverte aléatoire de contenus. Elle vous permet d'explorer des articles et des podcasts au hasard à partir d'une sélection de flux RSS triés par catégories. Sortez de votre bulle de filtres et laissez-vous surprendre !

## ✨ Fonctionnalités

* **Mode Double** : Basculez facilement entre la découverte d'articles (texte) et de podcasts (audio avec lecteur intégré).
* **Surprends-moi** : Un bouton unique pour tirer au sort un contenu issu de la catégorie sélectionnée.
* **Sauvegardes** : Mettez de côté vos découvertes préférées d'un simple clic pour y revenir plus tard. Les sauvegardes se mettent à jour instantanément selon la catégorie choisie.
* **Gestionnaire d'administration** :
    * Ajoutez, testez et supprimez des flux RSS et des catégories.
    * Exportez et importez l'intégralité de votre base de données (catégories, flux, sauvegardes) au format JSON.
* **Accessibilité (a11y) & Personnalisation** :
    * **Thèmes** : Mode clair / Mode sombre.
    * **Profils de vision** : Filtres adaptés au daltonisme (Protanopia, Deuteranopia, Tritanopia, Achromatopsia).
    * **Taille du texte** : Ajustable dynamiquement.
* **Internationalisation (i118n)** : Interface disponible en Français, Anglais, Espagnol et Japonais.
* **Sécurité** : Accès protégé par une authentification HTTP basique.

---

## 🛠 Prérequis (Développement local)

* **Python 3.8+**
* **pip** (gestionnaire de paquets Python)

---

## 🚀 Installation locale

1. **Cloner le dépôt (ou télécharger les fichiers) :**
   ```bash
   git clone <votre-url-de-repo>
   cd serendipite
   ```

2. **Créer et activer un environnement virtuel (recommandé) :**
   ```bash
   python -m venv venv
   # Sous Linux/macOS :
   source venv/bin/activate
   # Sous Windows :
   venv\Scripts\activate
   ```

3. **Installer les dépendances :**
   Créez un fichier `requirements.txt` à la racine du projet contenant les lignes suivantes :
   ```text
   Flask==3.0.0
   Flask-SQLAlchemy==3.1.1
   feedparser==6.0.10
   python-dotenv==1.0.0
   beautifulsoup4==4.12.2
   gunicorn==21.2.0
   psycopg2-binary==2.9.9
   ```
   Puis installez-les via la commande :
   ```bash
   pip install -r requirements.txt
   ```

---

## ⚙️ Configuration (.env)

L'application utilise des variables d'environnement pour gérer la sécurité et la base de données. Créez un fichier nommé `.env` à la racine du projet pour vos tests locaux :

```env
# Identifiants pour l'authentification HTTP basique
ADMIN_USER=admin
ADMIN_PASS=changezMoi123

# URL de la base de données (Laissez vide pour utiliser SQLite en local)
DATABASE_URL=
```

---

## 💻 Utilisation locale

1. **Lancer le serveur de développement :**
   ```bash
   python app.py
   ```
2. **Accéder à l'application :**
   Ouvrez votre navigateur web et allez sur : `http://localhost:5000`
3. **Connexion :**
   Entrez les identifiants définis dans votre fichier `.env`.

---

## ☁️ Déploiement en production (Render + Neon)

Pour héberger l'application gratuitement sur internet, nous recommandons de combiner **Render** (pour l'hébergement du code) et **Neon** (pour la base de données PostgreSQL Serverless).

Assurez-vous d'avoir poussé votre code (incluant `app.py` et `requirements.txt`) sur un dépôt GitHub ou GitLab.

### Étape 1 : Créer la base de données avec Neon.tech
1. Créez un compte gratuit sur [Neon.tech](https://neon.tech/).
2. Créez un nouveau projet (ex: `serendipite-db`).
3. Sur le tableau de bord, copiez la chaîne de connexion (**Connection string**). Elle ressemble à ceci : 
   `postgresql://utilisateur:motdepasse@ep-nom-aleatoire.eu-central-1.aws.neon.tech/neondb?sslmode=require`

### Étape 2 : Déployer l'application web avec Render
1. Créez un compte gratuit sur [Render](https://render.com/).
2. Cliquez sur **New +** puis sélectionnez **Web Service**.
3. Connectez votre compte GitHub/GitLab et sélectionnez le dépôt de votre projet.
4. Configurez le service de la façon suivante :
   * **Name** : `serendipite-app` (ou le nom de votre choix)
   * **Region** : Choisissez la région la plus proche (ex: Frankfurt)
   * **Environment** : `Python`
   * **Build Command** : `pip install -r requirements.txt`
   * **Start Command** : `gunicorn app:app` *(gunicorn est un serveur HTTP optimisé pour la production)*
   * **Instance Type** : `Free`
5. Dans la section **Environment Variables**, ajoutez les clés suivantes :
   * `ADMIN_USER` : Le nom d'utilisateur de votre choix pour vous connecter.
   * `ADMIN_PASS` : Un mot de passe sécurisé.
   * `DATABASE_URL` : **Collez ici l'URL complète copiée depuis Neon à l'étape 1**.
6. Cliquez sur **Create Web Service**. 

Render va télécharger vos fichiers, installer les dépendances et lancer l'application. Au bout de quelques minutes, votre application sera en ligne et accessible via une URL du type `https://serendipite-app.onrender.com`.

---

## 📦 Sauvegarde et Migration

Grâce au bouton d'administration (⚙️) intégré à l'interface, vous pouvez à tout moment :
* **Exporter** l'intégralité de vos flux, catégories et articles sauvegardés dans un fichier `.json`.
* **Importer** ce même fichier pour restaurer votre configuration ou migrer vers une nouvelle instance (très utile après le passage de la base de données locale SQLite vers la base de données en ligne Neon PostgreSQL !).
