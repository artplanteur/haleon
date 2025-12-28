"""Composants Callout (messages persistants)."""

import reflex as rx


def access_denied_callout(
    title: rx.Var | str,
    description: rx.Var | str,
    button_text: rx.Var | str,
    button_href: str = "/home",
) -> rx.Component:
    """Callout standard pour afficher un accès refusé sur une page."""
    return rx.center(
        rx.vstack(
            rx.callout.root(
                rx.callout.icon(
                    rx.text("!", weight="bold"),
                ),
                rx.callout.text(
                    rx.vstack(
                        rx.text(title, weight="bold", size="4"),
                        rx.text(description, size="3", color="gray.600"),
                        spacing="2",
                        align="start",
                    ),
                ),
                color_scheme="red",
                variant="soft",
                high_contrast=True,
                width="100%",
                max_width="720px",
            ),
            rx.button(
                button_text,
                on_click=rx.redirect(button_href),
                size="4",
                color_scheme="blue",
                margin_top="2",
            ),
            spacing="4",
            align="center",
            padding="8",
            width="100%",
        ),
        min_height="60vh",
    )



