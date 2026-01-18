import reflex as rx
from .avatar import avatar
from haleonv3.state.auth_state import AuthState


def navbar() -> rx.Component:
    return rx.hstack(
        rx.link(
            rx.image(
                src="/haleon_logo.png",
                height="32px",
                alt="Haleon",
            ),
            href="/",
        ),
        rx.spacer(),
        rx.cond(
            AuthState.is_authenticated,
            avatar(),
            rx.box(),
        ),
        rx.color_mode.button(),
        padding="0.75rem 1rem",
        border_bottom="1px solid #eee",
        align_items="center",
        width="100%",
    )
