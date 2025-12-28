"""Menu admin pour l'application OOB."""

from typing import List, Dict


def get_admin_menu_items() -> List[Dict[str, str]]:
    """
    Retourne les items de menu admin pour l'application OOB.
    
    Returns:
        Liste de dictionnaires avec les items de menu au format:
        [{"text": "...", "icon": "...", "href": "...", "is_admin": True}]
    """
    return [
        {
            "text": "Admin OOB",
            "icon": "📋",
            "href": "/admin/oob/access",
            "is_admin": True,
        }
    ]









