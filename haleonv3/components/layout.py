import reflex as rx
from .navbar import navbar
from .footer import footer
from haleonv3.state.auth_state import AuthState


def layout(content: rx.Component) -> rx.Component:
    return rx.box(
        navbar(),
        rx.box(
            content,
            width="100%",
            flex="1",
            padding="1rem",
        ),
        footer(),
        min_height="100vh",
        display="flex",
        flex_direction="column",
        width="100%",
        on_mount=AuthState.load_me,
    )
