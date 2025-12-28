"""Page d'accueil de l'application."""

import reflex as rx
from haleon.auth.auth_state import AuthState
from haleon.components.layout import layout
from haleon.components.sidebar import SidebarState
from haleon.state.i18n_state import I18nState
from haleon.components.welcome import welcome_message


class HomePageState(I18nState):
    """État pour la page d'accueil."""
    
    def on_mount(self):
        """Charge les traductions et réinitialise le code d'application courante dans le sidebar."""
        # Appeler on_mount du parent pour charger les traductions
        super().on_mount()
        # Réinitialiser le code d'application courante dans le sidebar
        SidebarState.current_app_code_for_menu = ""


def render_app_card(app: rx.Var[dict]) -> rx.Component:
    """Fonction de rendu pour une carte d'application."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.cond(
                    app["icon"],
                    rx.text(app["icon"], size="6"),
                    rx.text("📱", size="6"),
                ),
                rx.vstack(
                    rx.text(app["name"], size="5", weight="bold"),
                    rx.cond(
                        app["description"],
                        rx.text(app["description"], size="3", color="gray"),
                        rx.text(HomePageState.t_no_description, size="3", color="gray"),
                    ),
                    spacing="1",
                    align="start",
                ),
                spacing="4",
                align="center",
            ),
            rx.link(
                rx.button(
                    HomePageState.t_access_button,
                    color_scheme="blue",
                    width="100%",
                ),
                href=app["route"],
            ),
            spacing="4",
            width="100%",
        ),
        padding="6",
        width="100%",
        class_name="app-card",
    )


def home_page() -> rx.Component:
    """Page d'accueil avec message générique si aucune application sélectionnée."""
    # Ne pas charger les applications ici, c'est fait dans le layout pour éviter les appels multiples
    content = rx.box(
        # Réinitialiser le code d'application courante dans le sidebar quand on charge la page d'accueil
        rx.box(on_mount=HomePageState.on_mount),
        rx.center(
            rx.vstack(
                welcome_message(),
                rx.cond(
                    AuthState.is_validated,
                    rx.vstack(
                        rx.text(
                            HomePageState.t_available_applications,
                            size="4",
                            weight="bold",
                            margin_top="6",
                        ),
                        rx.cond(
                            AuthState.accessible_apps,
                            rx.vstack(
                                rx.foreach(
                                    AuthState.accessible_apps,
                                    render_app_card,
                                ),
                                spacing="4",
                                width="100%",
                                max_width="800px",
                                # Utiliser le trigger comme key pour forcer le re-render quand les applications changent
                                key=AuthState._refresh_apps_trigger,
                            ),
                            rx.text(
                                HomePageState.t_no_applications_available,
                                size="4",
                                color="gray",
                            ),
                        ),
                        spacing="4",
                        width="100%",
                        max_width="800px",
                        margin_top="4",
                    ),
                    rx.text(
                        HomePageState.t_account_must_be_validated,
                        size="4",
                        color="orange.600",
                        margin_top="6",
                    ),
                ),
                spacing="6",
                align="center",
                min_height="70vh",
                padding="6",
            ),
        ),
        width="100%",
    )
    
    return layout(content)
