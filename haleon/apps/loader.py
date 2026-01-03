"""Système de chargement dynamique des applications."""

import os
import importlib
import logging
from pathlib import Path
from typing import Optional, Callable
import reflex as rx

logger = logging.getLogger("haleon.apps.loader")

def get_application_page(app_name: str, app_code: str) -> Optional[Callable[[], rx.Component]]:
    """
    Charge dynamiquement la page d'une application.
    
    Args:
        app_name: Nom de l'application (pour le dossier) - devrait être le code
        app_code: Code de l'application (normalisé : première lettre majuscule, reste minuscule)
        
    Returns:
        Fonction qui retourne un composant Reflex, ou None si l'app n'a pas de page
    """
    # Chemin vers le dossier des applications
    apps_dir = Path(__file__).parent
    
    # Chercher le dossier de manière insensible à la casse
    # Le code peut être "Oob" mais le dossier peut être "OOB"
    app_dir = None
    if apps_dir.exists():
        # Normaliser le code en majuscules pour la comparaison
        code_upper = app_code.upper()
        logger.debug("loader: searching folder code=%s (cmp=%s)", app_code, code_upper)
        
        # Essayer d'abord avec le code tel quel
        potential_dir = apps_dir / app_code
        if potential_dir.exists() and potential_dir.is_dir():
            app_dir = potential_dir
            logger.debug("loader: exact folder found: %s", app_dir.name)
        else:
            # Chercher dans tous les dossiers pour trouver celui qui correspond (insensible à la casse)
            for item in apps_dir.iterdir():
                if item.is_dir() and not item.name.startswith("__"):
                    # Comparer insensible à la casse (comparer les versions majuscules)
                    if item.name.upper() == code_upper:
                        app_dir = item
                        logger.debug("loader: matching folder found: %s", item.name)
                        break
    
    # Vérifier si le dossier existe
    if not app_dir or not app_dir.exists() or not app_dir.is_dir():
        return None
    
    # Chercher un fichier page.py ou __init__.py dans le dossier de l'app
    page_file = app_dir / "page.py"
    if not page_file.exists():
        page_file = app_dir / "__init__.py"
        if not page_file.exists():
            return None
    
    try:
        # Utiliser le nom réel du dossier trouvé
        # Sur Windows, app_dir.name peut retourner le nom avec une casse différente
        # On force l'utilisation du nom réel en le lisant depuis le système de fichiers
        actual_folder_name = app_dir.name
        # Normaliser en minuscule pour correspondre au code normalisé
        actual_folder_name = actual_folder_name.lower()
        logger.debug("loader: folder=%s normalized=%s", app_dir.name, actual_folder_name)
        
        # Construire le nom du module en utilisant le nom normalisé en minuscule
        if page_file.name == "__init__.py":
            module_name = f"haleon.apps.{actual_folder_name}"
        else:
            module_name = f"haleon.apps.{actual_folder_name}.page"
        
        logger.debug("loader: importing module %s", module_name)
        
        # Importer le module
        module = importlib.import_module(module_name)
        logger.debug("loader: module imported")
        
        # Chercher une fonction page() ou app_page()
        if hasattr(module, "page"):
            func = getattr(module, "page")
            logger.debug("loader: page() found")
            return func
        elif hasattr(module, "app_page"):
            func = getattr(module, "app_page")
            logger.debug("loader: app_page() found")
            return func
        elif hasattr(module, f"{app_code}_page"):
            func = getattr(module, f"{app_code}_page")
            logger.debug("loader: %s_page() found", app_code)
            return func
        
        logger.debug("loader: no page function found in %s", module_name)
        return None
    except (ImportError, AttributeError) as e:
        logger.exception("loader: import error for %s: %s", app_code, e)
        return None


def get_available_app_folders() -> list[str]:
    """Retourne la liste des dossiers d'applications disponibles."""
    apps_dir = Path(__file__).parent
    folders = []
    
    if not apps_dir.exists():
        return folders
    
    for item in apps_dir.iterdir():
        if item.is_dir() and not item.name.startswith("__"):
            folders.append(item.name)
    
    return sorted(folders)


def get_application_admin_menu_items(app_code: str) -> list[dict]:
    """
    Charge dynamiquement les items de menu admin d'une application.
    
    Args:
        app_code: Code de l'application (normalisé en minuscule)
        
    Returns:
        Liste de dictionnaires avec les items de menu au format:
        [{"text": "...", "icon": "...", "href": "...", "is_admin": True}]
    """
    apps_dir = Path(__file__).parent
    
    # Chercher le dossier de manière insensible à la casse
    code_upper = app_code.upper()
    app_dir = None
    
    # Essayer d'abord avec le code tel quel
    potential_dir = apps_dir / app_code
    if potential_dir.exists() and potential_dir.is_dir():
        app_dir = potential_dir
    else:
        # Chercher dans tous les dossiers pour trouver celui qui correspond (insensible à la casse)
        for item in apps_dir.iterdir():
            if item.is_dir() and not item.name.startswith("__"):
                if item.name.upper() == code_upper:
                    app_dir = item
                    break
    
    if not app_dir or not app_dir.exists() or not app_dir.is_dir():
        return []
    
    # Chercher le fichier admin/menu.py
    menu_file = app_dir / "admin" / "menu.py"
    
    if not menu_file.exists():
        return []
    
    try:
        # Utiliser le nom réel du dossier trouvé (peut être différent de app_code en casse)
        actual_folder_name = app_dir.name
        # Construire le nom du module avec le nom réel du dossier
        module_name = f"haleon.apps.{actual_folder_name}.admin.menu"
        
        # Importer le module
        module = importlib.import_module(module_name)
        
        # Chercher la fonction get_admin_menu_items()
        if hasattr(module, "get_admin_menu_items"):
            func = getattr(module, "get_admin_menu_items")
            # Appeler la fonction et retourner le résultat
            return func()
        
        return []
    except (ImportError, AttributeError) as e:
        # Ignorer les erreurs silencieusement
        return []







