# Haleon v1 - Nouveau Projet Reflex

## Contexte général

Cette application fonctionnera en deux niveau. Le premier niveau (parent) consistera en une interface utilisateur avec une connexion que nous simulerons dans un premier temps et qui sera en SSO plus tard. Le second niveau heritera des niveaux  d'accès du premier niveau pour afficher ou non les differentes applications se trouvant toutes dans le dossier apps. Ainsi une interface admin présente dans le menu permettra de gérer la base de données. L'objectif est de conserver les information utilisateur au premier niveau pour les utiliser dans toute l'application. La base de données, pour le fonctionnant de l'application aura ces 3 tables par defaut (et d'autres suivant les applications développées) définie par SQLModel:

class Users(SQLModel, table=True):
    """Modèle de table Users pour la gestion des utilisateurs."""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    family_name: Optional[str] = None
    first_name: Optional[str] = None
    session_id: Optional[str] = None
    is_connected: bool = Field(default=False)
    is_validated: bool = Field(default=False)
    is_active: bool = Field(default=True)
    is_admin: bool = Field(default=False)
    last_connection: Optional[datetime] = Field(default=None)
    country: Optional[str] = None  # Ajouté pour correspondre aux claims SSO

class Applications(SQLModel, table=True):
    """Modèle de table Applications pour stocker les applications disponibles."""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str  # "App 1", "App 2", etc.
    code: str = Field(unique=True, index=True)  # "app1", "app2" (pour les routes)
    label: Optional[str] = None  # Label affiché dans la navbar
    description: Optional[str] = None
    route: str  # "/app1", "/app2"
    icon: Optional[str] = None  # Emoji ou nom d'icône
    is_active: bool = Field(default=True)  # Pour désactiver une app
    minimum_requirement: str = Field(default="validated")  # "active", "validated", ou "admin"
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None

class UserApplicationAccess(SQLModel, table=True):
    """Modèle de table de liaison pour gérer les permissions utilisateur ↔ application."""
    
    __table_args__ = (
        UniqueConstraint('user_id', 'application_id', name='unique_user_app_access'),
    )
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    application_id: int = Field(foreign_key="applications.id", index=True)
    granted_at: datetime = Field(default_factory=datetime.now)
    granted_by: Optional[int] = Field(foreign_key="users.id", default=None)  # Admin qui a accordé
    # Permissions granulaires
    can_read: bool = Field(default=True)
    can_write: bool = Field(default=False)
    can_delete: bool = Field(default=False)


## Fonctionnement général
-Le layout général se composera d'une menu drawer sur le flanc gauche, d'une navbar en haut avec les applications ajouté par l admin et en haut a droite un avatar avec les initials de l'utilisateur connecté, d'une partie centrale qui affichera l'application en cours d'utilisation et d'un footer.
-Les permissions doivent être codée en cascade de sorte qu'une seule vérification soient nécessaire pour chaque niveau d'accès.
-Utilisation des toasts reflex pour chaque échange avec la base de donnée pour confirmer une action. Rouge = Erreur, Vert = Succès
-Un menu utilisant le "drawer" in built de Reflex. Ce drawer apparaitra au clique sur un bouton hamburger en haut a gauche.
-Une partie du menu sera l'inteface admin utilisant la permission admin, qui doit se composer en 3 partie: 1. Utilisation d'une grid reflex pour afficher les Users avec les informations pertinentes ainsi que des toggles pour modifer le status is_validated, is_active ou is_admin (il doit etre impossible de s'enlever soit meme de l'état admin). 2._Une vue avec 2 tables "Applications" et "UserApplicationAccess". En plus d'afficher les information des tables, la table Applications offrira la possibilité d'ajouter une application (formulaire proposant un nom de dossier parmi ceux existant sur le path /apps, un label qui sera utiliser pour les liens vers cette application et une description) ou de supprimer une Application. De même pour la table UserApplicationAccess affichera les accès existant et la possibilité de choisir un utilisateur dropdown avec une interface de recherche intelligente pour selectionner un utilisateur existant et une applications également existantes dans les tables vues précédemment. 3.Vue d'ensemble des tables en live: statistique de chacune des tables du core model, et la possibiliter de drill down dans une application pour avoir une overview des tables d'une application. Il s'agira ici d'ajouter un prefixe standard pour les tables dédiées aux application: app_appID_appName c'est à dire par exemple app_1_Comment pour une table s'appelant Comment qui appartient à l'application qui a comme ID=1.
-Le menu contient également une partie pour les utilisateurs validés, is_validated=1: la possibilité de switcher day/night toggle avec la fonctionnalité propre à reflex "Dark Mode Toggle" doit etre presente ici
-Concernant le navbar, il affichera des boutons pour accéder aux applications ajoutés par l'admin dans la table apps. En haut a droite, l'avatar avec les initials permettra enm cliquant d'afficher un popup avec le remaining time de la session en cours (compter a rebour live) et des informations utiles pour le user connecté: email, Nom, preénom country... et un bouton de deconnexion
-Au centre, il s'agira d'afficher un message générique si aucune application est selectionnée, sinon charger l'application choisie par l'utilisateur via les boutons de la navbar

## Fonctionnement des aspects principaux de la Base de données
La base de données est créée uniquement lors de la premiere utilisation de l'application en suivant les modeles proposées. en aucun cas la BDD sera reconstruite si elle existe deja.
Un aspect particulier de la table Users est qu'elle sera automatiquement populée. Lors de la connexion d'un utilisateur, il s'agira de vérifier si l'utilisateur est deja présent dans la bdd (email) et de:
-mettre a jour si utilisateur deja existant
-ajouter l'utilisateur s'il n'existe pas encore avec un niveau is_validated = False
-un email doit obligatoirement repondre à ce critère: @haleon.com
La table UserApplicationAccess n'offrira que des choix existant dans les tables Users et Applications lors de sa population. Autrement dit elle dependera directement des deux autres tables parents.

## Vue d'ensemble

Ce document décrit la structure et les fichiers à conserver ou refaire lors de la restructuration de l'application Haleon. Il identifie les composants réutilisables (base de données, thème, CRUD) et ceux qui doivent être refaits (pages, états Reflex, configuration).

---

## Structure de l'application proposée

```
haleon/
├── assets/                    # Assets statiques (CSS, images)
│   └── theme.css              # ✅ À CONSERVER - Thème personnalisé
├── data/                      # Base de données SQLite (généré)
│   └── haleon.db             # ❌ À IGNORER - Fichier généré
├── haleon/
│   ├── apps/                  # Applications métier
│   │   └── OOB/              # ⚠️ À ÉVALUER - Application spécifique pour chaque dossier dans apps/
│   ├── auth/                  # Authentification
│   │   ├── auth_state.py     
│   │   ├── oauth_config.py   
│   │   ├── oauth_handler.py  
│   │   └── permissions.py   
│   ├── components/            # Composants UI réutilisables
│   │   ├── layout.py         
│   │   ├── navbar.py         
│   │   ├── sidebar.py        
│   │   ├── avatar.py         
│   │   └── footer.py         
│   ├── db/                    # ✅ À CONSERVER ENTIÈREMENT
│   │   ├── database.py       # ✅ Configuration BDD
│   │   ├── model/            # ✅ Modèles SQLModel
│   │   │   ├── users.py
│   │   │   ├── applications.py
│   │   │   └── user_app_access.py
│   │   ├── crud/             # ✅ Opérations CRUD
│   │   │   ├── users.py
│   │   │   ├── applications.py
│   │   │   └── user_app_access.py
│   │   └── seed.py           # ✅ Données initiales
│   ├── pages/                
│
│   └── haleon.py             
├── rxconfig.py               
└── requirements.txt          
```

---


## 📋 Vue d'ensemble

Ce projet est une version propre et restructurée de l'application Haleon, créée à partir des fichiers réutilisables de l'ancien projet.

## ✅ Fichiers copiés (réutilisables)

### Base de données (100% réutilisable)
- ✅ `haleon/db/database.py` - Configuration BDD
- ✅ `haleon/db/model/` - Tous les modèles SQLModel
- ✅ `haleon/db/crud/` - Toutes les opérations CRUD
- ✅ `haleon/db/seed.py` - Script de seeding

### Authentification (partiellement réutilisable)
- ✅ `haleon/auth/oauth_config.py` - Configuration OAuth
- ✅ `haleon/auth/oauth_handler.py` - Handler OAuth
- ✅ `haleon/auth/permissions.py` - Système de permissions

### Thème
- ✅ `assets/theme.css` - Thème personnalisé

## 🚀 Démarrage

1. **Activer l'environnement virtuel :**
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

2. **Installer les dépendances :**
   ```powershell
   pip install -r requirements.txt
   ```

3. **Lancer l'application :**
   ```powershell
   reflex run
   ```

## 📁 Structure du projet


## ⚠️ À développer

Les éléments suivants doivent être créés proprement :

1. **États Reflex** (`haleon/auth/auth_state.py`)
   - Créer un état d'authentification simple
   - Éviter les recompilations
   - Utiliser `rx.SessionStorage` correctement si nécessaire

2. **Pages** (`haleon/pages/`)
   - Page d'accueil
   - Pages admin (une par une)
   - Page de connexion
   - Callback OAuth

3. **Composants UI** (`haleon/components/`)
   - Layout
   - Navbar
   - Sidebar
   - Footer

## 🔧 Configuration

### Exclure le dossier data/ du hot reload

Le fichier `.web/vite.config.js` est déjà configuré pour exclure le dossier `data/` du watch, évitant ainsi les recompilations lors des modifications de la BDD.

### Variable d'environnement (optionnel)

Pour exclure le dossier `data/` du hot reload Reflex, vous pouvez définir :

```powershell
$env:REFLEX_HOT_RELOAD_EXCLUDE_PATHS = "data"
```

## 📝 Notes

- La base de données est créée automatiquement dans `data/haleon.db`
- Les tables sont créées au démarrage de l'application la première fois UNIQUEMENT



