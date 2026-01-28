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
  - Affichage des modules (apps) dans la barre de navigation (actuellement déclarés dans le code).
  - Fonctionnalités utilisateur: thème jour/nuit, langue.
  - Fonctionnalités admin global: gestion utilisateurs, vendors, rôles (par app), overview (KPI + audit).

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

### 3.1. Principes (état actuel du code)

- Application web “single page” pilotée par Reflex.
- Un layout commun encapsule toutes les pages (navigation, contenu, footer).
- Les pages/modules sont aujourd’hui **déclarés dans le code** (voir `haleonv3/haleonv3.py`) et les droits sont stockés en base via `user_role`.
- La table `applications` décrite plus bas était une **intention** de la spec initiale, mais **n’est pas implémentée** dans le code actuel.

### 3.2. Séparation des responsabilités

- **UI**: composants réutilisables + pages.
- **State**: minimal, séparé par responsabilité.
- **Données**: modèles SQLModel + CRUD centralisés.

---

## 4. Arborescence (structure du projet)

Objectif: partir d’un **modèle existant** (`C:\python\haleonv2\haleon`) et définir une arborescence **claire, stable, professionnelle**, avec un rôle précis pour chaque dossier/fichier.

> Règle: ce document (niveau 1) décrit **uniquement** le socle.  
> Les détails d’un module (ex: OOB) sont décrits dans son document dédié.

### 4.1. Arborescence actuelle (référence)

> Cette section a été mise à jour pour refléter le code réel dans `c:\python\haleonv3`.

- **Racine projet**
  - `rxconfig.py` (configuration Reflex) — À compléter
  - `requirements.txt` — À compléter
  - `assets/` (thème, images) — À compléter
  - `locale/` (traductions JSON) — À compléter

- **`haleonv3/` (package)**
  - `__init__.py`
  - `haleonv3.py` (point d’entrée app / pages)
  - `auth/` (niveau 1)
    - `__init__.py`
    - `sso.py`
    - `http_auth_routes.py` (routes `/auth/login`, `/auth/callback`, `/auth/me`)
  - `state/` (niveau 1)
    - `__init__.py`
    - `auth_state.py` (profil + droits globaux)
    - `admin_state.py` (admin users/vendors)
    - `roles_state.py` (admin rôles)
  - `components/` (niveau 1)
    - `__init__.py`
    - `layout.py`
    - `navbar.py`
    - `footer.py`
    - `avatar.py`
  - `pages/` (niveau 1)
    - `admin.py`
  - `db/` (niveau 1)
    - `__init__.py`
    - `database.py`
    - `audit_listeners.py` (audit DB auto via events SQLAlchemy)
    - `model/`
      - `users.py`
      - `vendor.py`
      - `user_role.py`
      - `user_vendor_access.py`
      - `logs.py`
    - `crud/`
      - `users.py`
      - `vendors.py`
  - `apps/` (niveau 2)
    - `oob/` (module OOB: pages/state/crud/schema)

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
- Le socle définit uniquement **qui voit/ouvre un module** (via `validated`, `is_admin`, et les rôles en base `user_role`).
- Les **autorisations internes** d’un module (ex: read/write/admin, accès par vendor, etc.) sont définies **dans le document du module** (ex: `OOB_Technical_Spec.md`) et implémentées **dans le module**.

---

## 7. Base de données (niveau 1) — tables, contraintes, index (état actuel du code)

Décision (implémentation actuelle): niveau 1 = **5 tables**:
- `users`
- `vendor`
- `user_role`
- `user_vendor_access`
- `logs` (audit)

### 7.1. Table `users`

**But**: stocker l’utilisateur SSO et son niveau d’accès (niveau 1).

**Champs (implémentés) — avec types**:
- `id`: `int` (PK, auto)
- `immutable_id`: `str` (NOT NULL, UNIQUE, longueur max 20)
- `email`: `str | None` (nullable)
- `given_name`: `str | None` (nullable)
- `family_name`: `str | None` (nullable)
- `country`: `str | None` (nullable)
- `session_id`: `str | None` (nullable, indexé)
- `source_domain`: `int` (NOT NULL, default 0)
- `is_active`: `bool` (NOT NULL, default `False`, devient `True` à la 1ère connexion SSO)
- `is_validated`: `bool` (NOT NULL, default `False`)
- `is_admin`: `bool` (NOT NULL, default `False`)
- `created_at`: `datetime` (NOT NULL, default “now”)
- `updated_at`: `datetime` (NOT NULL, default “now”, mis à jour par le code lors des updates)
- `last_login_at`: `datetime | None` (nullable)

**Contraintes**:
- unicité sur `immutable_id`
 - règles de cohérence:
   - si `is_admin=True` alors `is_validated=True` et `is_active=True`
   - si `is_validated=True` alors `is_active=True`

**Index recommandés**:
- `immutable_id`
- `session_id`
- (optionnel) `last_login_at`

### 7.2. Table `vendor`

**But**: référentiel vendors (utilisé notamment par OOB).

**Champs (implémentés)**:
- `id`: `int` (PK, auto)
- `code`: `str` (NOT NULL, UNIQUE, indexé, max 10)
- `description`: `str | None`
- `portfolio`: `str | None` (indexé)
- `is_active`: `bool` (default `True`)
- `created_at`: `datetime`
- `updated_at`: `datetime`

### 7.3. Table `user_role`

**But**: droits “par application” (ex: admin sur `oob`).

**Champs (implémentés)**:
- `id`: `int` (PK)
- `user_id`: `int` (FK `users.id`, indexé)
- `app`: `str` (indexé)
- `role`: `str` (indexé)
- `created_at`, `updated_at`

**Contraintes**:
- unicité (`user_id`, `app`, `role`)

### 7.4. Table `user_vendor_access`

**But**: droits “par vendor” (read/write) utilisés par l’admin OOB.

**Champs (implémentés)**:
- `id`: `int` (PK)
- `user_id`: `int` (FK `users.id`, indexé)
- `vendor_id`: `int` (FK `vendor.id`, indexé)
- `access_level`: `str` (ex: `read`, `write`)
- `created_at`, `updated_at`

**Contraintes**:
- unicité (`user_id`, `vendor_id`)

### 7.5. Table `logs` (audit — une seule table)

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
- `source`: `str | None` (nullable) — ex: `sso-login`, `admin-users`, `admin-roles`, `module-oob:access-admin`
- `operation`: `str` (NOT NULL) ∈ {`INSERT`, `UPDATE`, `DELETE`}
- `table_name`: `str` (NOT NULL)
- `record_pk`: `str` (NOT NULL)
- `field_name`: `str | None` (nullable) — **règle**: 1 ligne par champ modifié (UPDATE/INSERT/DELETE) pour pouvoir reconstituer par requête SQL
- `old_value`: `str | None` (nullable) — texte (JSON sérialisé recommandé)
- `new_value`: `str | None` (nullable) — texte (JSON sérialisé recommandé)

**Index recommandés**:
- `changed_at`
- `(table_name, record_pk, changed_at)`
- `actor_user_id`
- `actor_identifier`
- `request_id`

**Rétention**:
- conservation **5 ans**

---

## 8. Audit & traçabilité (table `logs`) — règles & bonnes pratiques

### 8.1. Clarification “SQLModel natif”

SQLModel est basé sur SQLAlchemy. Il n’existe pas un audit “automatique complet” dans SQLModel seul.  
On doit choisir une stratégie d’audit.

### 8.2. Stratégie retenue (MVP)

Décision MVP (implémentée): **audit automatique via events SQLAlchemy**.

- Fichier: `haleonv3/db/audit_listeners.py`
- Events:
  - `before_flush`: log DELETE + log UPDATE (1 ligne par champ)
  - `after_flush`: log INSERT (1 ligne par champ, PK disponible après flush)
- Contexte acteur: le code métier peut renseigner `session.info["actor"]` (dict) pour remplir:
  - `request_id`, `source`
  - `actor_user_id`, `actor_identifier`
  - `actor_is_active`, `actor_is_validated`, `actor_is_admin`

Règle simple pour débutant:
- si tu veux “qui a fait quoi”, mets `session.info["actor"] = {...}` **avant** d’appeler un CRUD qui écrit (commit/flush).

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

### 9.2. CRUD `vendors`

Fonctions implémentées (voir `haleonv3/db/crud/vendors.py`):
- `create_vendor(session, code, description, portfolio, is_active=True)`
- `list_vendors(session, portfolio=None, code=None, include_inactive=True)`
- `toggle_vendor_active(session, vendor_id, is_active)`

### 9.3. CRUD `roles` (niveau 2 / admin)

Fonctions implémentées (voir `haleonv3/apps/oob/crud/roles.py`):
- `grant_role(session, user_id, app, role)`
- `revoke_role(session, user_id, app, role)`

### 9.4. CRUD `vendor access` (niveau 2 / admin)

Fonctions implémentées (voir `haleonv3/apps/oob/crud/access.py`):
- `grant_vendor_access(session, user_id, vendor_id, access_level)`
- `revoke_vendor_access(session, user_id, vendor_id)`

### 9.5. CRUD `logs` (lecture) — à implémenter si besoin

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
  - liens (implémentés): users, vendors, roles, accès OOB

### 10.2. Écrans admin (cible)

- **Utilisateurs**
  - afficher liste + détails
  - actions: valider / retirer validation, passer admin / retirer admin
  - afficher dernière connexion

- **Vendors**
  - CRUD vendors (code, description, portfolio, actif/inactif)

- **Roles**
  - gestion des rôles (ex: admin par app)

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
- **Admin / Vendors**
  - But: gérer la table `vendor`.
- **Admin / Roles**
  - But: gérer `user_role` (ex: admin par app).
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
