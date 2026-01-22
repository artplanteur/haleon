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
            rx.hstack(
                rx.cond(
                    AuthState.can_admin,
                    rx.link(rx.button("Admin", size="2"), href="/admin"),
                    rx.box(),
                ),
                avatar(),
                spacing="3",
                align_items="center",
            ),
            rx.box(),
        ),
        rx.color_mode.button(),
        padding="0.75rem 1rem",
        border_bottom="1px solid #eee",
        align_items="center",
        width="100%",
    )
