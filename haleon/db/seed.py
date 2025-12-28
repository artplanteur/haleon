"""Script de seeding pour initialiser des données de test (optionnel)."""

from haleon.db.database import get_session, init_db
from haleon.db.crud.users import create_user, get_user_by_email
from haleon.db.model.users import Users


def seed_database():
    """Initialise la base de données avec des données de test."""
    # Initialiser la BDD
    init_db()
    
    session_gen = get_session()
    session = next(session_gen)
    try:
        # 1. Forcer John Doe en admin
        john_doe = get_user_by_email(session, "john.doe@haleon.com")
        if john_doe:
            # Mettre à jour pour forcer admin
            john_doe.is_admin = True
            john_doe.is_validated = True
            john_doe.is_active = True
            session.add(john_doe)
            session.commit()
            session.refresh(john_doe)
        else:
            # Créer John Doe en admin
            create_user(
                session=session,
                email="john.doe@haleon.com",
                first_name="John",
                family_name="Doe",
                country="FR",
                is_admin=True,
                audit_user=None,
                audit_source="seed",
            )
            # Forcer validated
            john_doe = get_user_by_email(session, "john.doe@haleon.com")
            if john_doe:
                john_doe.is_validated = True
                john_doe.is_active = True
                session.add(john_doe)
                session.commit()
        
        # 2. Créer utilisateur test 1 : Alice Martin (validated mais pas admin)
        alice = get_user_by_email(session, "alice.martin@haleon.com")
        if not alice:
            create_user(
                session=session,
                email="alice.martin@haleon.com",
                first_name="Alice",
                family_name="Martin",
                country="FR",
                is_admin=False,
                audit_user=None,
                audit_source="seed",
            )
            # Forcer validated
            alice = get_user_by_email(session, "alice.martin@haleon.com")
            if alice:
                alice.is_validated = True
                alice.is_active = True
                session.add(alice)
                session.commit()
        
        # 3. Créer utilisateur test 2 : Bob Dupont (actif mais pas validated)
        bob = get_user_by_email(session, "bob.dupont@haleon.com")
        if not bob:
            create_user(
                session=session,
                email="bob.dupont@haleon.com",
                first_name="Bob",
                family_name="Dupont",
                country="BE",
                is_admin=False,
                audit_user=None,
                audit_source="seed",
            )
            # Actif mais pas validated
            bob = get_user_by_email(session, "bob.dupont@haleon.com")
            if bob:
                bob.is_active = True
                bob.is_validated = False
                session.add(bob)
                session.commit()
    finally:
        session.close()


if __name__ == "__main__":
    seed_database()








