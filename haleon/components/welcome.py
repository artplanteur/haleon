import reflex as rx
from haleon.state.i18n_state import I18nState


class WelcomeState(I18nState):
    """État pour le composant welcome."""
    pass


def welcome_message() -> rx.Component:
    """Affiche un message de bienvenue générique."""
    return rx.vstack(
        rx.heading(
            WelcomeState.t_welcome_to_haleon,
            size="9",
            weight="bold",
            color_scheme="blue",
            text_align="center",
        ),
        rx.text(
            WelcomeState.t_select_app_from_nav,
            size="5",
            color="gray.600",
            text_align="center",
            margin_top="2",
        ),
        spacing="4",
        align="center",
        padding="8",
    )

