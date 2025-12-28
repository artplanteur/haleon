"""Page d'accueil simple avec navbar."""

import reflex as rx
from haleon.components.layout import layout
from haleon.auth.auth_state import AuthState
from haleon.state.i18n_state import I18nState
from haleon.components.welcome import welcome_message


class IndexPageState(I18nState):
    """État pour la page index."""
    
    def on_mount(self):
        """Charge les traductions au chargement de la page."""
        super().on_mount()


def index() -> rx.Component:
    """Page d'accueil avec contenu."""
    content = rx.center(
        rx.vstack(
            welcome_message(),
            rx.cond(
                AuthState.is_authenticated,
                rx.vstack(
                    rx.text(
                        IndexPageState.t_you_are_connected,
                        size="4",
                        color="green.600",
                        margin_top="4",
                    ),
                    rx.link(
                        rx.button(
                            IndexPageState.t_go_to_home,
                            color_scheme="blue",
                            size="3",
                        ),
                        href="/home",
                    ),
                    spacing="4",
                    margin_top="6",
                ),
                rx.text(
                    IndexPageState.t_connect_to_access,
                    size="4",
                    color="gray",
                    margin_top="4",
                ),
            ),
            spacing="6",
            align="center",
            min_height="70vh",
        ),
        width="100%",
    )
    
    return layout(content)







