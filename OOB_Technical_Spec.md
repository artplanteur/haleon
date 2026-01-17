# Spécification technique — Module OOB (cible)

Ce document décrit la **spécification technique** du module **OOB** (niveau 2) et complète la spécification “Haleon (socle)”:
- Le socle (niveau 1) fournit: SSO, permissions globales, langue, thème, navigation, audit.
- Le module OOB définit: ses pages, ses états, ses données métier, ses CRUD métier, ses règles fonctionnelles.

> Règle: tout ce qui est “global” (auth, i18n, audit, navigation) reste dans le document Haleon.  
> Ici on ne documente que ce qui est spécifique à OOB.

## Table des matières

1. Objectif et périmètre OOB
2. Règles d’accès (read/write/admin) appliquées dans OOB
3. Écrans / navigation OOB
4. Gestion d’état (State) OOB
5. Modèle de données OOB (tables métier)
6. Audit OOB (événements importants + source)
7. Spécification CRUD OOB (liste des fonctions attendues)
8. Points ouverts / décisions à valider

---

## 1. Objectif et périmètre OOB

### 1.1. Objectif métier

Le module OOB consomme une API externe qui retourne des **PO (Purchase Orders)** filtrés par **vendor**.

Objectif du module:
- permettre à un utilisateur de consulter les PO des vendors auxquels il a accès,
- permettre à certains utilisateurs de modifier des PO (selon droits write),
- gérer des droits au niveau **vendor** (read/write) au sein de OOB.

### 1.2. Périmètre fonctionnel

À compléter.

### 1.3. Hors périmètre

À compléter.

---

## 2. Règles d’accès appliquées dans OOB

### 2.1. Héritage du socle (niveau 1)

Rappels:
- OOB hérite de l’auth (SSO) et des informations user (incluant `immutable_id`) du niveau 1.
- Le socle décide si l’utilisateur peut “ouvrir” OOB (au moins `validated=True`).

Décision: l’**autorisation interne OOB** est gérée **dans OOB** (niveau 2), pas dans le socle.

### 2.2. Droits OOB au niveau vendor (cible)

Concept:
- Un utilisateur possède des droits par vendor: `vendor_read` ou `vendor_write`.
- `vendor_write` implique `vendor_read`.

Règles:
- Un utilisateur sans droit sur un vendor ne doit jamais voir ses PO.
- Un utilisateur en `vendor_read` peut lister/consulter les PO du vendor.
- Un utilisateur en `vendor_write` peut modifier (ou déclencher des actions) sur les PO du vendor.

### 2.3. Mapping global admin (niveau 1) → OOB

Règle:
- Si `is_admin=True` au niveau 1, alors l’utilisateur est **admin OOB** (tous vendors, toutes actions) sauf règle contraire explicite (à éviter en MVP).

### 2.2. Autorisations par action (matrice)

À compléter (proposition initiale):
- voir liste vendors accessibles: read
- voir liste PO d’un vendor: vendor_read
- voir détail PO: vendor_read
- modifier une PO: vendor_write
- actions admin OOB (gestion des droits vendor): admin OOB

---

## 3. Écrans / navigation OOB

### 3.1. Entrée module

À compléter: page d’accueil OOB, layout interne éventuel, menus.

### 3.2. Liste des pages OOB

Proposition (à valider):
- **OOB / Vendors**
  - liste des vendors accessibles pour l’utilisateur
- **OOB / Purchase Orders**
  - liste des PO pour un vendor sélectionné (filtres/tri)
- **OOB / Purchase Order Detail**
  - détail d’une PO
  - actions de modification si `vendor_write`
- **OOB / Admin (optionnel)**
  - gestion des droits vendor (si on décide de le gérer via OOB et non via SSO)

### 3.3. Parcours utilisateur

À compléter: 3–5 parcours principaux.

---

## 4. Gestion d’état (State) OOB

### 4.1. Principes

- OOB hérite du State Auth et du State Langue (niveau 1).
- OOB ne duplique jamais les infos globales.
- OOB implémente ses règles read/write au niveau vendor.

### 4.2. États OOB (liste)

Proposition:
- `OOBState`
  - vendor sélectionné
  - liste des vendors (chargée via API)
  - liste des PO (chargée via API)
  - permissions calculées pour le vendor courant (`can_read_vendor`, `can_write_vendor`)
  - actions: charger vendors, charger PO, ouvrir détail PO, exécuter action “update” si autorisée

### 4.3. Données chargées au démarrage vs à la demande

À compléter.

---

## 5. Modèle de données OOB (tables métier)

Deux cas possibles:
- **Cas A (droits via SSO)**: OOB n’a pas besoin de table locale pour les droits vendor (uniquement consommation API).
- **Cas B (droits gérés dans OOB)**: OOB définit des tables métier locales pour stocker les droits vendor.

### 5.1. Tables

À compléter (si Cas B):
- `oob_vendor_access`
  - but: lier `immutable_id` à `vendor_id` avec un rôle `read/write`
  - champs: `id`, `immutable_id`, `vendor_id`, `role`, `created_at`, `updated_at`
  - contraintes: unicité (`immutable_id`, `vendor_id`)
  - index: `immutable_id`, `vendor_id`

### 5.2. Données de référence (si besoin)

À compléter.

---

## 6. Audit OOB (événements importants + source)

### 6.1. Événements à auditer

À compléter (exemples OOB):
- consultation liste PO (optionnel, souvent trop verbeux)
- consultation détail PO (optionnel)
- modification PO (obligatoire)
- changement de droits vendor (si Cas B)

### 6.2. Champ `source`

Convention proposée:
- `source="module-oob:<feature>"` (ex: `module-oob:admin-settings`)

À valider.

---

## 7. Spécification CRUD OOB (liste des fonctions attendues)

> Ici on liste les fonctions “service” OOB (principalement appels API + contrôles d’accès), sans coder.

### 7.1. Lecture

À compléter (proposition):
- `oob_list_vendors_for_user(immutable_id, ...)`
- `oob_list_pos_for_vendor(immutable_id, vendor_id, filters, ...)`
- `oob_get_po_detail(immutable_id, vendor_id, po_id, ...)`

### 7.2. Écriture

À compléter (proposition):
- `oob_update_po(immutable_id, vendor_id, po_id, patch, ...)`
- (optionnel) `oob_admin_set_vendor_access(immutable_id, target_immutable_id, vendor_id, role, ...)` (si Cas B)

### 7.3. Contrôles & erreurs

À compléter:
- validations
- erreurs attendues (droits, données invalides, conflits, etc.)

---

## 8. Points ouverts / décisions à valider

- Détails de l’API PO: endpoints, auth, pagination, filtres, format vendor_id, format po_id.
- Source de vérité des droits vendor:
  - via SSO (Cas A) ou via tables OOB (Cas B)
- Liste finale des pages OOB.
- Règles read/write par action (détail).

