"""Layout principal avec sidebar, navbar, contenu et footer."""

import reflex as rx
from haleon.auth.auth_state import AuthState
from haleon.components.navbar import navbar
from haleon.components.sidebar import sidebar
from haleon.components.footer import footer


def layout(content: rx.Component) -> rx.Component:
    """Layout principal avec sidebar, navbar, contenu central et footer."""
    return rx.vstack(
        # Charger l'utilisateur depuis la session serveur UNE SEULE FOIS au montage du layout
        # Les applications seront chargées automatiquement après le chargement de l'utilisateur
        rx.box(on_mount=AuthState.load_user_from_session),
        # Charger les applications après authentification
        # SIMPLE : Si accessible_apps est vide (première fois ou après vidage), on recharge
        # Le trigger dans la navbar force le re-render quand les apps changent
        rx.cond(
            AuthState.is_authenticated & 
            ~AuthState._loading_apps,
            rx.cond(
                ~AuthState.accessible_apps,
                rx.box(
                    on_mount=AuthState.load_accessible_applications,
                    key=AuthState._refresh_apps_trigger,
                ),
            ),
        ),
        # Sidebar (drawer) - toujours visible (le bouton hamburger est toujours visible)
        sidebar(),
        # Navbar (toujours affichée, avec bouton de connexion si non connecté)
        navbar(),
        # Contenu principal - 88% de largeur, centré
        rx.box(
            content,
            flex="1",
            width="88%",
            max_width="88%",
            padding="6",
            margin="0 auto",
            class_name="main-content",
        ),
        # Footer
        footer(),
        spacing="0",
        min_height="100vh",
        width="100%",
        class_name="main-container",
    )










