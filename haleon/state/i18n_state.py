"""État pour la gestion de l'internationalisation (i18n).

Ce module garde la même API qu'avant (ex: `t_email`, `t_oob_ship_from`, etc.),
mais génère automatiquement ces `@rx.var` à partir des clés des fichiers
`locale/en/*.json` afin d'éviter des centaines de propriétés redondantes.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Dict, Optional

import reflex as rx

logger = logging.getLogger("haleon.state.i18n")


class I18nState(rx.State):
    """État pour gérer les traductions de l'application."""
    
    locale: str = rx.LocalStorage(sync=True)
    _translations: Dict[str, Dict[str, str]] = {}
    
    def on_mount(self):
        """Charge les traductions au montage du composant."""
        if not self.locale or self.locale == "":
            self.locale = "en"
        self.load_translations()
    
    def load_translations(self):
        """Charge les fichiers de traduction depuis le dossier locale/<locale>."""
        base_dir = Path(__file__).parent.parent.parent
        locale_dir = base_dir / "locale" / self.locale
        
        if not locale_dir.exists():
            logger.warning("Locale directory not found: %s", locale_dir)
            return
        
        self._translations = {}
        for json_file in locale_dir.glob("*.json"):
            module_name = json_file.stem
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    self._translations[module_name] = json.load(f)
            except Exception as e:
                logger.exception("Error loading translation file %s: %s", json_file, e)
    
    def set_locale(self, new_locale: str):
        """Change la locale et recharge les traductions."""
        if new_locale not in ["en", "fr", "es", "pt", "ar"]:
            return
        self.locale = new_locale
        self.load_translations()
    
    @rx.var
    def translations_common(self) -> Dict[str, str]:
        """Retourne les traductions du module common."""
        if not self._translations:
            self.load_translations()
        return self._translations.get("common", {}) or {}
    
    @rx.var
    def translations_oob(self) -> Dict[str, str]:
        """Retourne les traductions du module oob."""
        if not self._translations:
            self.load_translations()
        return self._translations.get("oob", {}) or {}
    
    def _get_translation(self, key: str, module: str = "common", default: Optional[str] = None) -> str:
        """Helper interne pour obtenir une traduction."""
        if not self._translations:
            self.load_translations()
        translations = self._translations.get(module, {})
        return translations.get(key, default or key)
    
    def t(self, key: str, module: str = "common", default: Optional[str] = None) -> str:
        """Retourne la traduction pour une clé donnée (pour usage dans les méthodes d'état)."""
        if not self._translations:
            self.load_translations()
        translations = self._translations.get(module, {})
        return translations.get(key, default or key)
    
    @rx.var
    def current_locale(self) -> str:
        """Retourne la locale actuelle."""
        return self.locale
    
    @rx.var
    def is_french(self) -> bool:
        """Retourne True si la locale est française."""
        return self.locale == "fr"
    
    @rx.var
    def is_english(self) -> bool:
        """Retourne True si la locale est anglaise."""
        return self.locale == "en"
    
    @rx.var
    def current_locale_flag_url(self) -> str:
        """Retourne l'URL du drapeau correspondant à la locale actuelle."""
        flag_map = {
            "fr": "https://flagsapi.com/FR/shiny/32.png",
            "en": "https://flagsapi.com/GB/shiny/32.png",
            "es": "https://flagsapi.com/ES/shiny/32.png",
            "pt": "https://flagsapi.com/PT/shiny/32.png",
            "ar": "https://flagsapi.com/SA/shiny/32.png",
        }
        return flag_map.get(self.locale, "https://flagsapi.com/GB/shiny/32.png")
    

# -------------------------
# Dynamic generation of t_* vars (Option B)
# -------------------------
_VALID_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Preserve a few explicit defaults that existed in the previous hand-written properties.
# (Used only if the key is missing in the current locale file.)
_DEFAULTS: dict[str, dict[str, str]] = {
    "common": {
        "code_route_readonly": "* Le code et la route ne peuvent pas être modifiés",
        "core_tables_statistics": "Statistiques des tables core",
        "application_tables": "Tables des applications",
        "table": "Table",
        "structure": "Structure",
        "data_preview": "Aperçu des données",
        "no_tables_found": "Aucune table trouvée pour cette application",
        "select_app_to_see_tables": "Sélectionnez une application ci-dessus pour voir ses tables",
        "search_by_email": "Rechercher par email, prénom, nom ou pays...",
    },
    "oob": {
        "line_details": "Détails de la ligne",
    },
}


def _load_en_keys_for_module(module: str) -> list[str]:
    """(Deprecated) Kept for backward compatibility; use `_collect_keys_by_module()`."""
    try:
        base_dir = Path(__file__).parent.parent.parent
        p = base_dir / "locale" / "en" / f"{module}.json"
        if not p.exists():
            return []
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
        return [k for k in data.keys() if isinstance(k, str) and _VALID_KEY_RE.match(k)]
    except Exception:
        return []


def _load_keys_from_json(path: Path) -> list[str]:
    """Load translation keys from a JSON file, filtering invalid identifiers."""
    try:
        if not path.exists():
            return []
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
        if not isinstance(data, dict):
            return []
        return [k for k in data.keys() if isinstance(k, str) and _VALID_KEY_RE.match(k)]
    except Exception:
        return []


def _collect_keys_by_module() -> dict[str, list[str]]:
    """Collect the union of keys across ALL locales for each module.

    This makes the `t_*` API stable even if a key exists only in e.g. `fr/common.json`
    and was forgotten in `en/common.json`.
    """
    base_dir = Path(__file__).parent.parent.parent
    locale_root = base_dir / "locale"
    if not locale_root.exists():
        return {}

    acc: dict[str, set[str]] = {}
    for locale_dir in locale_root.iterdir():
        if not locale_dir.is_dir():
            continue
        for json_file in locale_dir.glob("*.json"):
            module = json_file.stem
            keys = _load_keys_from_json(json_file)
            if not keys:
                continue
            acc.setdefault(module, set()).update(keys)

    return {module: sorted(keys) for module, keys in acc.items()}


def _make_t_var(key: str, module: str = "common", default: Optional[str] = None):
    """Factory for @rx.var translation accessors."""
    
    @rx.var
    def _v(self) -> str:
        return self._get_translation(key, module=module, default=default)

    return _v


def _install_translation_vars():
    """Install t_* vars on I18nState from the union of locale/*/*.json keys."""
    keys_by_module = _collect_keys_by_module()
    if not keys_by_module:
        return

    for module, keys in keys_by_module.items():
        for key in keys:
            # Naming convention:
            # - common: t_<key>
            # - oob: t_oob_<key>
            # - others: t_<module>_<key>
            if module == "common":
                attr_name = f"t_{key}"
            elif module == "oob":
                attr_name = f"t_oob_{key}"
            else:
                attr_name = f"t_{module}_{key}"

            # Don't override explicit class members.
            if hasattr(I18nState, attr_name):
                continue

            default = _DEFAULTS.get(module, {}).get(key)
            setattr(I18nState, attr_name, _make_t_var(key, module=module, default=default))


_install_translation_vars()



