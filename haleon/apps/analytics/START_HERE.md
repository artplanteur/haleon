## Analytics app — guide minimal (conventions Haleon)

Ce dossier `haleon/apps/analytics/` est un **exemple de squelette** pour créer une nouvelle application “métier” dans `haleon/apps/`.

L’objectif : te donner le **minimum** à créer pour que l’app s’intègre proprement (auth, permissions, layout, menu admin, thème).

---

## 1) Deux façons d’intégrer une app dans Haleon

### Option A (recommandée aujourd’hui) — route explicite dans `haleon/haleon.py`
Comme l’app `oob`, tu ajoutes une page Reflex dédiée, par ex :

- route: `/apps/analytics`
- `on_load` ou `on_mount`: `AnalyticsState.on_mount`

✅ Avantage: **ça marche immédiatement** avec le code actuel.

### Option B — chargement dynamique via `/apps/[app_code]` (AppView + loader)
Le repo a un loader (`haleon/apps/loader.py`) capable d’importer `haleon.apps.<app>.page`.

⚠️ Attention: **actuellement** `haleon/pages/app_view.py` rend surtout OOB en dur et n’utilise pas encore systématiquement le composant chargé dynamiquement.
Si tu veux utiliser cette option, il faudra que `app_view_page()` rende `AppViewState.get_app_page_component()` quand `app_page_loaded=True`.

---

## 2) Structure minimale d’une app (dossier dans `haleon/apps/`)

### Fichiers minimum

- `__init__.py` *(recommandé)*: fait de ce dossier un package Python.
- `page.py`: expose une fonction `page()` qui retourne un `rx.Component`.
- `state.py` *(recommandé)*: ton `rx.State` (souvent hérité de `AuthState`).

### Optionnels (selon besoin)

- `db/models.py`: modèles SQLModel spécifiques à l’app (tables préfixées automatiquement par le système actuel).
- `db/crud.py`: opérations CRUD spécifiques app.
- `admin/menu.py`: items “Admin” spécifiques à l’app (affichés dans le drawer).
- `admin/...`: pages admin spécifiques.
- `schemas/pydantic.py`: schémas pour API externe / parsing.

---

## 3) Héritage des States (patterns recommandés)

### A) State “app” (métier) : hériter de `AuthState`
Utilise `AuthState` quand tu as besoin de :

- `current_user` (snapshot sérialisable)
- `is_authenticated`, `is_active`, `is_validated`, `is_admin`
- `load_user_from_session()` (session via cookie HttpOnly côté backend)
- `load_accessible_applications()` (menu navbar)

Pattern typique:

```python
import reflex as rx
from haleon.auth.auth_state import AuthState
from haleon.auth.permissions import ApplicationPermissions


class AnalyticsState(AuthState):
    state_auto_setters: bool = True

    has_access: bool = False

    def on_mount(self):
        # Charger user depuis la session (cookie HttpOnly)
        if not self.is_authenticated or not self.current_user:
            self.load_user_from_session()

        if not self.current_user:
            self.has_access = False
            return

        # Gate d’accès app (code: "analytics")
        self.has_access = ApplicationPermissions.can_access_app(self.current_user, "analytics")
```

### B) State “traductions UI” : hériter de `I18nState`
Quand une page a surtout besoin des traductions (labels), hérite de `I18nState` et fais `super().on_mount()`.

Exemple (comme `OOBPageState`):

```python
import reflex as rx
from haleon.state.i18n_state import I18nState


class AnalyticsPageState(I18nState):
    def on_mount(self):
        super().on_mount()
```

---

## 4) Variables / mécanismes Reflex à utiliser (conventions du repo)

### Variables persistées client (filtres, UI prefs)
Le repo utilise :

- `rx.LocalStorage(sync=True)` pour persister côté navigateur (dates, search, etc.).

Ex:

```python
import reflex as rx

class AnalyticsState(rx.State):
    date_min: str = rx.LocalStorage(sync=True)
    search_query: str = rx.LocalStorage(sync=True)
```

### Variables calculées (computed)
Utiliser `@rx.var` pour exposer des computed vars UI.

⚠️ Important: ne pas “shadow” une variable de base d’un parent (Reflex peut lever `ComputedVarShadowsBaseVarsError`).

---

## 5) “page.py” minimal (UI) + layout

Dans ce repo, les pages utilisent le layout commun:
- `haleon/components/layout.py` → sidebar + navbar + footer + chargement user/apps.

Template minimal :

```python
import reflex as rx
from haleon.components.layout import layout
from haleon.apps.analytics.state import AnalyticsState
from haleon.components.callouts import access_denied_callout


def page() -> rx.Component:
    content = rx.cond(
        AnalyticsState.has_access,
        rx.center(rx.heading("Analytics", size="8")),
        access_denied_callout("Accès refusé", "Vous n'avez pas accès à Analytics.", "Retour", "/home"),
    )
    return layout(content)
```

---

## 6) Menu admin “par app” (optionnel)

Si tu veux ajouter un item admin spécifique à l’app dans le drawer :

Créer `admin/menu.py` avec :

```python
from typing import List, Dict

def get_admin_menu_items() -> List[Dict[str, str]]:
    return [
        {"text": "Admin Analytics", "icon": "📊", "href": "/admin/analytics", "is_admin": True},
    ]
```

Le loader appelle automatiquement `get_admin_menu_items()` si le fichier existe.

---

## 7) Thème / CSS à connaître

Le thème est dans `assets/theme.css` et est automatiquement chargé.

### A) Variables CSS (utilisables partout)
Quelques variables importantes:

- `--bg-primary`, `--bg-secondary`, `--text-primary`, `--border-color`
- `--primary-color`, `--success-color`, `--error-color`
- `--border-radius`, `--shadow-md`

### B) Dark mode
Le dark mode est piloté via l’attribut:
- `[data-theme="dark"]`

Donc si tu ajoutes des classes CSS, pense à définir aussi la variante dark.

### C) Classes utiles déjà présentes
Exemples (non exhaustifs):

- `.main-container`, `.main-content`
- `.header-container`, `.sidebar-container`
- `.sidebar-item` (et `.sidebar-item.admin`)
- `.popup-overlay`, `.popup-content`

---

## 8) Checklist “je démarre une nouvelle app”

- Ajouter `__init__.py`, `state.py`, `page.py` dans `haleon/apps/analytics/`
- Ajouter une entrée “Application” en DB (table `applications`) avec code `analytics`
- Accorder un accès via `UserApplicationAccess` (UI admin)
- (Option A) ajouter une route explicite `/apps/analytics` dans `haleon/haleon.py`
- (Option B) activer le rendu dynamique dans `haleon/pages/app_view.py`




