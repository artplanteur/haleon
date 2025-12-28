"""Composant Navbar avec bouton hamburger, applications et avatar."""

import reflex as rx
from haleon.auth.auth_state import AuthState
from haleon.state.i18n_state import I18nState
from haleon.components.sidebar import SidebarState
from haleon.components.avatar import avatar


class NavbarState(I18nState):
    """État pour la navbar."""
    pass


def render_app_button(app: rx.Var[dict]) -> rx.Component:
    """Fonction de rendu pour un bouton d'application."""
    return rx.link(
        rx.button(
            rx.cond(
                app["icon"],
                rx.text(app["icon"], size="4"),
                rx.text("", size="4"),
            ),
            app["name"],
            variant="ghost",
            size="2",
            class_name="nav-link",
        ),
        href=app["route"],
    )


def navbar() -> rx.Component:
    """Navbar avec menu hamburger, boutons d'applications et avatar."""
    return rx.box(
        rx.hstack(
            # Logo cliquable (gauche) - ramène à la page d'accueil
            rx.link(
                rx.image(
                    src="/haleon_logo.png",
                    alt="Haleon Logo",
                    height="40px",
                    width="auto",
                    class_name="header-logo-image",
                ),
                href="/home",
                margin_right="2",
            ),
            # Bouton hamburger (après le logo) - toujours visible
            rx.button(
                "☰",
                on_click=SidebarState.open_drawer,
                variant="ghost",
                class_name="header-btn",
            ),
            # Spacer pour pousser les apps au centre
            rx.spacer(),
            # Boutons des applications (centré) - seulement si connecté
            rx.cond(
                AuthState.is_authenticated,
                rx.hstack(
                    rx.foreach(
                        AuthState.accessible_apps,
                        render_app_button,
                    ),
                    spacing="2",
                    align="center",
                    justify="center",
                    # Utiliser le trigger comme key pour forcer le re-render quand les applications changent
                    key=AuthState._refresh_apps_trigger,
                ),
            ),
            # Spacer pour équilibrer avec l'avatar à droite
            rx.spacer(),
            # Avatar ou bouton de connexion (droite)
            rx.cond(
                AuthState.is_authenticated,
                avatar(),
                rx.button(
                    NavbarState.t_login_with_john_doe,
                    on_click=AuthState.simulate_sso_login,
                    size="3",
                    color_scheme="blue",
                    class_name="login-btn",
                ),
            ),
            width="100%",
            align="center",
            class_name="header-container",
            style={
                "padding": "1rem 1.5rem !important",
            },
        ),
        width="100%",
    )
