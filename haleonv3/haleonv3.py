"""Welcome to Reflex! This file outlines the steps to create a basic app."""

import reflex as rx
from haleonv3.components.layout import layout
from haleonv3.auth.http_auth_routes import mount_http_auth_routes


class State(rx.State):
    """The app state."""


def index() -> rx.Component:
    return layout(
        rx.container(
            rx.center(
                rx.vstack(
                    rx.heading("Homepage", size="7"),
                    rx.text("Welcome to Haleon."),
                    rx.link(
                        rx.button("Connect", size="3"),
                        href="/auth/login",
                    ),
                    spacing="4",
                ),
                min_height="70vh",
            )
        )
    )


app = rx.App()
mount_http_auth_routes(app._api)
app.add_page(index, route="/")
