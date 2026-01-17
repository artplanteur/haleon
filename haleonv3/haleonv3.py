"""Welcome to Reflex! This file outlines the steps to create a basic app."""

import reflex as rx
from haleonv3.components.layout import layout


class State(rx.State):
    """The app state."""


def index() -> rx.Component:
    return layout(
        rx.container(
            rx.center(
                rx.vstack(
                    rx.heading("Homepage", size="7"),
                    rx.text("Bienvenue dans Haleon."),
                    rx.button("Se connecter", size="3"),
                    spacing="4",
                ),
                min_height="70vh",
            )
        )
    )


app = rx.App()
app.add_page(index, route="/")
