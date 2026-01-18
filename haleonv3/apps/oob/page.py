import reflex as rx
from haleonv3.components.layout import layout
from haleonv3.state.auth_state import AuthState


def oob_page() -> rx.Component:
    return layout(
        rx.container(
            rx.cond(
                AuthState.can_validated,
                rx.heading("OOB App", size="7"),
                rx.text("Access denied: validated users only."),
            )
        )
    )
