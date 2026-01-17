# Spécification technique — Haleon (cible)

Ce document est une **spécification technique** (100% technique) destinée à définir l’application **avant** d’écrire le code.

- **Public**: équipe technique (débutant Python inclus).
- **But**: définir clairement l’architecture, l’arborescence, le modèle de données, l’audit, et les CRUD **sans coder**.
- **Principe**: si une information manque, on laisse un bloc “À compléter” et on pose une question.

> Auth SSO: considéré comme **déjà implémenté**. On décrit uniquement l’intégration attendue côté application (création/mise à jour user, permissions, etc.).

## Table des matières

1. Contexte et périmètre
2. Vocabulaire (définitions)
3. Architecture applicative (niveau 1 / niveau 2)
4. Arborescence cible (structure du projet)
5. Gestion d’état (State) — stratégie minimaliste
6. Authentification & autorisations (niveau 1)
7. Base de données (niveau 1) — tables, contraintes, index
8. Audit & traçabilité (table `logs`) — règles & bonnes pratiques
9. Spécification CRUD (niveau 1) — liste des fonctions attendues
10. Pages (niveau 1) — liste et objectifs
11. Spécification UI/Navigation (niveau 1) — écrans et comportements
12. Environnements & déploiement
13. Points ouverts / décisions à valider
13. Annexes (à compléter)

---

## 1. Contexte et périmètre

### 1.1. Vision produit

Logiciel d’entreprise composé de deux niveaux:

- **Niveau 1 (socle)**:
  - Connexion via SSO.
  - Gestion des permissions utilisateur en cascade (**active → validated → admin**).
  - Affichage dynamique des applications (modules) dans la barre de navigation.
  - Fonctionnalités utilisateur: thème jour/nuit, langue.
  - Fonctionnalités admin global: gestion utilisateurs, gestion applications, gestion droits modules, overview (KPI + audit).

- **Niveau 2 (modules / apps)**:
  - Une infinité de modules ajoutables.
  - Chaque module “hérite” des règles du niveau 1 (auth + langue) et applique des droits module (read/write/admin) en cascade.

### 1.2. Hors périmètre (pour ce document)

- Détails techniques de l’implémentation SSO (protocoles, IdP, etc.).
- Détails métier du module OOB (document séparé).

---

## 2. Vocabulaire (définitions)

- **Utilisateur**: personne identifiée via SSO.
- **Claim**: donnée fournie par le SSO (ex: `immutable_id`).
- **Niveau utilisateur (niveau 1)**:
  - `active`: accès au socle (niveau 1)
  - `validated`: accès aux modules (niveau 2)
  - `admin`: admin global (niveau 1) + admin de tous les modules
- **Module / App (niveau 2)**: sous-application affichée dans la navbar, pouvant avoir ses pages, son état, et ses données métier.
- **Droit module** (niveau 2): `read`, `write`, `admin` avec cascade (`admin` ⇒ `write` ⇒ `read`).

---

## 3. Architecture applicative (niveau 1 / niveau 2)

### 3.1. Principes

- Application web “single page” pilotée par Reflex.
- Un layout commun encapsule toutes les pages (navigation, contenu, footer).
- Les modules sont chargés/affichés dynamiquement via un identifiant `app_code` et la configuration stockée en base (table `applications`).

### 3.2. Séparation des responsabilités

- **UI**: composants réutilisables + pages.
- **State**: minimal, séparé par responsabilité.
- **Données**: modèles SQLModel + CRUD centralisés.

---

## 4. Arborescence cible (structure du projet)

Objectif: partir d’un **modèle existant** (`C:\python\haleonv2\haleon`) et définir une arborescence **claire, stable, professionnelle**, avec un rôle précis pour chaque dossier/fichier.

> Règle: ce document (niveau 1) décrit **uniquement** le socle.  
> Les détails d’un module (ex: OOB) sont décrits dans son document dédié.

### 4.1. Arborescence cible (Haleon niveau 1) — à implémenter dans ce projet

> À ce stade, on définit la structure cible. On la remplira dossier/fichier au fur et à mesure du développement.

- **Racine projet**
  - `rxconfig.py` (configuration Reflex) — À compléter
  - `requirements.txt` — À compléter
  - `assets/` (thème, images) — À compléter
  - `locale/` (traductions JSON) — À compléter

- **`haleon/` (package)**
  - `__init__.py`
  - `haleon.py` (point d’entrée app)
  - `auth/` (niveau 1)
    - `__init__.py`
    - `sso.py` (existant, non spécifié ici)
    - `auth_state.py` (spécification dans section 5/6)
    - `permissions.py`
  - `state/` (niveau 1)
    - `__init__.py`
    - `i18n_state.py`
  - `components/` (niveau 1)
    - `__init__.py`
    - `layout.py`
    - `navbar.py`
    - `sidebar.py`
    - `footer.py`
    - `avatar.py`
  - `pages/` (niveau 1)
    - `index.py`
    - `home.py`
    - `app_view.py`
    - `admin/`
      - `users.py`
      - `applications.py`
      - `overview.py`
  - `db/` (niveau 1)
    - `__init__.py`
    - `database.py`
    - `model/`
      - `users.py`
      - `applications.py`
      - `logs.py`
    - `crud/`
      - `users.py`
      - `applications.py`
      - `logs.py`
  - `apps/` (niveau 2)
    - `<app_code>/...` (hors périmètre de ce document)

---

## 5. Gestion d’état (State) — stratégie minimaliste

### 5.1. États globaux (socle)

- **State Auth**:
  - utilisateur courant (ou non connecté)
  - flags `is_active/is_validated/is_admin`
  - liste des modules affichables (navbar)
  - actions: charger session, rafraîchir user, logout

- **State Langue / i18n**:
  - langue courante
  - traductions + fallback
  - action: changer langue

- **State UI (optionnel)**:
  - sidebar ouverte/fermée, modals, etc.

### 5.2. États par module

Chaque module peut définir son/ ses `State` spécifiques.
Règle: un State module ne duplique jamais auth/i18n.

### 5.3. Performance (réponse à la question “beaucoup de State”)

- Beaucoup de classes State ≠ problème.  
Le vrai risque: états trop gros, recalculs inutiles, accès DB trop fréquents.

Bonnes pratiques:
- garder les états petits (IDs + champs nécessaires),
- charger à la demande,
- centraliser l’accès DB dans les CRUD,
- éviter les refresh automatiques inutiles.

---

## 6. Authentification & autorisations (niveau 1)

### 6.1. Intégration SSO (fonctionnel)

À chaque connexion SSO:
- si l’utilisateur n’existe pas: création en base,
- si l’utilisateur existe: mise à jour de ses infos (prénom/nom/pays/claims utiles),
- première connexion: l’utilisateur devient automatiquement `active=True`,
- `validated` et `admin` sont gérés par un admin global.

#### Identifiant unique (SSO)

- Claim unique: **`immutable_id`** (clé unique en base).

### 6.2. Cascade niveau 1 (active → validated → admin)

Règles:
- `validated` implique `active`
- `admin` implique `validated`
- aucune combinaison incohérente n’est autorisée

### 6.3. Accès aux modules (MVP)

Règles:
- `active`: accès au niveau 1 uniquement
- `validated`: accès aux modules (niveau 2) + modules visibles dans la navbar
- `admin` (niveau 1): admin global du socle

Important (frontière niveau 1 / niveau 2):
- Le socle définit uniquement **qui voit/ouvre un module** (via `validated` et la liste `applications`).
- Les **autorisations internes** d’un module (ex: read/write/admin, accès par vendor, etc.) sont définies **dans le document du module** (ex: `OOB_Technical_Spec.md`) et implémentées **dans le module**.

---

## 7. Base de données (niveau 1) — tables, contraintes, index

Décision: niveau 1 = **3 tables** uniquement:
- `users`
- `applications`
- `logs` (audit)

### 7.1. Table `users`

**But**: stocker l’utilisateur SSO et son niveau d’accès (niveau 1).

**Champs (cible) — avec types**:
- `id`: `int` (PK, auto)
- `immutable_id`: `str` (NOT NULL, UNIQUE, longueur max 20)
- `first_name`: `str | None` (nullable)
- `family_name`: `str | None` (nullable)
- `country`: `str | None` (nullable)
- `is_active`: `bool` (NOT NULL, default `False`, devient `True` à la 1ère connexion SSO)
- `is_validated`: `bool` (NOT NULL, default `False`)
- `is_admin`: `bool` (NOT NULL, default `False`)
- `created_at`: `datetime` (NOT NULL, default “now”)
- `updated_at`: `datetime` (NOT NULL, default “now”, mis à jour à chaque update)
- `last_login_at`: `datetime | None` (nullable)

**Contraintes**:
- unicité sur `immutable_id`
 - règles de cohérence:
   - si `is_admin=True` alors `is_validated=True` et `is_active=True`
   - si `is_validated=True` alors `is_active=True`

**Index recommandés**:
- `immutable_id`
- `last_login_at`

### 7.2. Table `applications`

**But**: déclarer les modules disponibles.

**Champs (cible) — avec types**:
- `id`: `int` (PK, auto)
- `code`: `str` (NOT NULL, UNIQUE) — identifiant stable du module (ex: `oob`)
- `name`: `str` (NOT NULL)
- `description`: `str | None` (nullable)
- `icon`: `str | None` (nullable)
- `route`: `str | None` (nullable)
- `is_active`: `bool` (NOT NULL, default `True`)
- `minimum_requirement`: `str` (NOT NULL) ∈ {`active`, `validated`, `admin`}
- `created_at`: `datetime` (NOT NULL, default “now”)
- `updated_at`: `datetime` (NOT NULL, default “now”, mis à jour à chaque update)

**Contraintes**:
- unicité sur `code`

**Index recommandés**:
- `code`
- `is_active`

### 7.3. Table `logs` (audit — une seule table)

**But**: tracer toutes les opérations DB: INSERT/UPDATE/DELETE (qui/quand/table/champ/old/new).

**Champs (cible) — avec types**:
- `id`: `int` (PK, auto)
- `request_id`: `str | None` (nullable) — UUID en string (corrélation)
- `changed_at`: `datetime` (NOT NULL, default “now”)
- `actor_user_id`: `int | None` (nullable) — FK → `users.id`
- `actor_identifier`: `str | None` (nullable) — ex: `immutable_id`
- `actor_is_active`: `bool | None` (nullable)
- `actor_is_validated`: `bool | None` (nullable)
- `actor_is_admin`: `bool | None` (nullable)
- `source`: `str | None` (nullable) — ex: `admin-users`, `admin-applications`, `overview`
- `operation`: `str` (NOT NULL) ∈ {`INSERT`, `UPDATE`, `DELETE`}
- `table_name`: `str` (NOT NULL)
- `record_pk`: `str` (NOT NULL)
- `field_name`: `str | None` (nullable) — **règle**: 1 ligne par champ modifié (UPDATE/INSERT/DELETE) pour pouvoir reconstituer par requête SQL
- `old_value`: `str | None` (nullable) — texte (JSON sérialisé recommandé)
- `new_value`: `str | None` (nullable) — texte (JSON sérialisé recommandé)

**Index recommandés**:
- `(table_name, record_pk)`
- `changed_at`
- `actor_user_id`
- `request_id`

**Rétention**:
- conservation **5 ans**

---

## 8. Audit & traçabilité (table `logs`) — règles & bonnes pratiques

### 8.1. Clarification “SQLModel natif”

SQLModel est basé sur SQLAlchemy. Il n’existe pas un audit “automatique complet” dans SQLModel seul.  
On doit choisir une stratégie d’audit.

### 8.2. Stratégie retenue (MVP)

Décision MVP: **audit au niveau application** (via CRUD centralisé).  
Règle: **toute écriture DB** (insert/update/delete) doit passer par le CRUD correspondant.

### 8.3. Règles de log

- Chaque modification DB doit produire une ou plusieurs lignes dans `logs`.
- **Granularité**: 1 ligne par champ modifié (INSERT/UPDATE/DELETE) pour permettre la reconstitution par requête SQL.
  - `field_name` requis pour UPDATE ; recommandé aussi pour INSERT/DELETE.
- Les valeurs sensibles ne doivent jamais être loggées en clair (À compléter: liste des champs sensibles).

---

## 9. Spécification CRUD (niveau 1) — liste des fonctions attendues

> Ici on liste les fonctions attendues, leur but, entrées, sorties, erreurs possibles. **Sans coder**.

### 9.1. CRUD `users`

#### 9.1.1. `users_upsert_from_sso_claims(...)`

- **But**: créer ou mettre à jour l’utilisateur à chaque connexion SSO.
- **Entrées**:
  - `immutable_id: str`
  - `first_name: str | None`
  - `family_name: str | None`
  - `country: str | None`
  - `request_id: str | None`
  - `source: str` (ex: `sso-login`)
- **Sorties**:
  - `user` (objet `users`)
  - `result: str` ∈ {`created`, `updated`, `noop`}
- **Règles**:
  - première connexion ⇒ `is_active=True`
  - ne jamais casser la cascade (validated/admin)
- **Audit**: écrire dans `logs`
  - INSERT si user créé, UPDATE si user modifié
  - 1 ligne par champ modifié

#### 9.1.2. `users_get_by_immutable_id(...)`

- **But**: récupérer un utilisateur par identifiant SSO.
- **Entrées**: `immutable_id: str`
- **Sorties**: `user | None`
- **Erreurs**: aucune (retourne `None` si absent)

#### 9.1.3. `users_list(...)`

- **But**: lister les utilisateurs (admin).
- **Entrées (filtres)**:
  - `search: str | None` (sur nom / immutable_id)
  - `is_active: bool | None`
  - `is_validated: bool | None`
  - `is_admin: bool | None`
  - `limit: int` (default À définir)
  - `offset: int` (default 0)
- **Sorties**: `list[users]` + `total_count` (recommandé)

#### 9.1.4. `users_set_validated(...)`

- **But**: activer/désactiver `validated` (admin).
- **Entrées**:
  - `target_user_id: int`
  - `validated: bool`
  - `actor_user_id: int`
  - `request_id: str | None`
  - `source: str` (ex: `admin-users`)
- **Sorties**: `user` mis à jour
- **Règles**:
  - si `validated=True` alors forcer `is_active=True`
  - si `validated=False` alors forcer `is_admin=False`
- **Audit**: UPDATE (1 ligne par champ modifié)

#### 9.1.5. `users_set_admin(...)`

- **But**: activer/désactiver `admin` (admin).
- **Entrées**:
  - `target_user_id: int`
  - `admin: bool`
  - `actor_user_id: int`
  - `request_id: str | None`
  - `source: str` (ex: `admin-users`)
- **Sorties**: `user` mis à jour
- **Règles**:
  - si `admin=True` alors forcer `is_validated=True` et `is_active=True`
- **Audit**: UPDATE (1 ligne par champ modifié)

### 9.2. CRUD `applications`

#### 9.2.1. `applications_create(...)`

- **But**: créer une application (module) dans `applications`.
- **Entrées**:
  - `code: str`
  - `name: str`
  - `minimum_requirement: str` ∈ {`active`, `validated`, `admin`}
  - `description: str | None`
  - `icon: str | None`
  - `route: str | None`
  - `is_active: bool` (default `True`)
  - `actor_user_id: int`
  - `request_id: str | None`
  - `source: str` (ex: `admin-applications`)
- **Sorties**: `application` créé
- **Erreurs**:
  - `code` déjà existant
- **Audit**: INSERT (1 ligne par champ ou 1 ligne globale — À valider; recommandé 1/champ)

#### 9.2.2. `applications_update(...)`

- **But**: modifier une application (admin).
- **Entrées**:
  - `application_id: int`
  - champs modifiables: `name`, `description`, `icon`, `route`, `is_active`, `minimum_requirement`
  - `actor_user_id: int`
  - `request_id: str | None`
  - `source: str` (ex: `admin-applications`)
- **Sorties**: `application` mis à jour
- **Audit**: UPDATE (1 ligne par champ modifié)

#### 9.2.3. `applications_list(...)`

- **But**: lister les applications.
- **Entrées**:
  - `only_active: bool` (default `False`)
  - `minimum_requirement: str | None`
  - `limit: int` / `offset: int`
- **Sorties**: `list[applications]` + `total_count` (recommandé)

#### 9.2.4. `applications_get_by_code(...)`

- **But**: récupérer une application par `code`.
- **Entrées**: `code: str`
- **Sorties**: `application | None`

### 9.3. CRUD `logs` (lecture)

#### 9.3.1. `logs_list_recent(...)`

- **But**: récupérer les derniers logs (overview).
- **Entrées**:
  - `limit: int` (default À définir)
  - `table_name: str | None`
- **Sorties**: `list[logs]`

#### 9.3.2. `logs_search(...)`

- **But**: recherche/filtrage logs (admin).
- **Entrées (filtres)**:
  - `date_from: datetime | None`
  - `date_to: datetime | None`
  - `table_name: str | None`
  - `record_pk: str | None`
  - `actor_user_id: int | None`
  - `operation: str | None`
  - `request_id: str | None`
  - `limit: int` / `offset: int`
- **Sorties**: `list[logs]` + `total_count` (recommandé)

#### 9.3.3. `logs_kpis(...)`

- **But**: calculer KPI logs (24h/7j/30j + total).
- **Entrées**:
  - `now: datetime | None` (pour tests/reproductibilité, sinon “now”)
- **Sorties**:
  - `total`
  - `count_24h`
  - `count_7d`
  - `count_30d`

---

## 10. Spécification UI/Navigation (niveau 1) — écrans et comportements

### 10.1. Navigation globale

- **Navbar**:
  - liste des modules visibles (dynamique selon access)
  - actions: thème jour/nuit, langue
  - menu utilisateur: infos + logout

- **Sidebar admin**:
  - visible uniquement si `is_admin=True`
  - liens: utilisateurs, applications, overview

### 10.2. Écrans admin (cible)

- **Utilisateurs**
  - afficher liste + détails
  - actions: valider / retirer validation, passer admin / retirer admin
  - afficher dernière connexion

- **Applications**
  - CRUD applications (code, name, minimum_requirement, actif/inactif)

- **Overview**
  - KPI: nb users, nb apps, volume logs
  - tableaux / filtres logs

---

## 11. Pages (niveau 1) — liste et objectifs

> Liste des pages “socle” attendues. À compléter au fur et à mesure.

### 11.1. Pages publiques (non connectées)

- **Landing / index**
  - But: entrée de l’application, déclenchement du flux SSO si nécessaire.

### 11.2. Pages utilisateur (connectées)

- **Home**
  - But: page d’accueil après connexion.

### 11.3. Pages admin global (connectées, `is_admin=True`)

- **Admin / Utilisateurs**
  - But: valider un utilisateur, le passer admin, visualiser la dernière connexion.
- **Admin / Applications**
  - But: gérer la table `applications`.
- **Admin / Overview**
  - But: KPI + visualisation/filtrage des logs.

---

## 12. Environnements & déploiement

- Dev/Test: SQLite.
- Cible: Azure Data Lake (à préciser: service exact et compat audit/migrations).
- Déploiement sur machine virtuelle.

---

## 13. Points ouverts / décisions à valider

### 13.1. “Azure Data Lake”

À préciser:
- quel service relationnel (ou changement de modèle),
- stratégie migrations,
- stratégie audit dans l’environnement cible.

---

## 13. Annexes (à compléter)

- Liste des champs sensibles à ne jamais auditer.
- Conventions de nommage (`app_code`, pages, states, CRUD).
- Règles d’erreur et messages utilisateur.
