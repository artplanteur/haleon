"""Composant Footer pour le pied de page."""

import reflex as rx


def footer() -> rx.Component:
    """Footer simple."""
    return rx.box(
        rx.hstack(
            rx.text("© 2025 Haleon", size="2", color="gray.600"),
            rx.spacer(),
            rx.text("v1.0", size="2", color="gray.500"),
            width="100%",
            padding="4",
            border_top="1px solid",
            border_color="gray.200",
            background_color="gray.50",
        ),
        width="100%",
    )










