import reflex as rx
from .avatar import avatar


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
        avatar(),
        padding="0.75rem 1rem",
        border_bottom="1px solid #eee",
        align_items="center",
        width="100%",
    )
