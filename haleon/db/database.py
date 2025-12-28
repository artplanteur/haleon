"""Configuration de la base de données SQLite avec SQLModel."""

import os
import importlib
from pathlib import Path
from sqlmodel import SQLModel, create_engine, Session
from typing import Generator

# Chemin vers la base de données (en dehors du projet pour éviter les recompilations)
BASE_DIR = Path(__file__).parent.parent.parent
# Mettre la BDD dans le dossier parent du projet (en dehors de haleonv1)
DATA_DIR = BASE_DIR.parent / "haleon_data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "haleon.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Créer le moteur de base de données
engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})


def _discover_application_models():
    """Découvre et importe dynamiquement les modèles des applications.
    
    Scanne les dossiers dans apps/ et importe les modèles depuis apps/{app_code}/db/models.py
    """
    apps_dir = Path(__file__).parent.parent / "apps"
    
    if not apps_dir.exists():
        return
    
    # Importer les modèles core d'abord
    from haleon.db.model.users import Users
    from haleon.db.model.applications import Applications
    from haleon.db.model.user_app_access import UserApplicationAccess
    
    # Scanner les dossiers d'applications
    for app_dir in apps_dir.iterdir():
        if app_dir.is_dir() and not app_dir.name.startswith("__"):
            app_code = app_dir.name
            models_file = app_dir / "db" / "models.py"
            
            if models_file.exists():
                try:
                    # Construire le nom du module
                    module_name = f"haleon.apps.{app_code}.db.models"
                    # Importer le module pour que SQLModel enregistre les modèles
                    importlib.import_module(module_name)
                except (ImportError, AttributeError) as e:
                    # Ignorer les erreurs d'import (application peut ne pas avoir de modèles)
                    print(f"Warning: Could not import models from {app_code}: {e}")


def init_db():
    """Initialise la base de données en créant les tables si elles n'existent pas."""
    # Découvrir et importer tous les modèles (core + applications)
    _discover_application_models()
    
    # Créer toutes les tables (core + applications avec préfixe app_{appCode}_)
    SQLModel.metadata.create_all(engine)
    
    # Créer les triggers d'audit pour toutes les tables
    # Utiliser recreate_audit_triggers pour s'assurer que tous les triggers sont à jour
    from haleon.db.triggers import recreate_audit_triggers
    with Session(engine) as session:
        recreate_audit_triggers(session)

# Initialiser la DB une seule fois au chargement du module
_init_db_called = False
if not _init_db_called:
    init_db()
    _init_db_called = True


def get_session() -> Generator[Session, None, None]:
    """Générateur de session de base de données."""
    with Session(engine) as session:
        yield session










