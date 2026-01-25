"""Welcome to Reflex! This file outlines the steps to create a basic app."""

import reflex as rx
from haleonv3.components.layout import layout
from haleonv3.auth.http_auth_routes import mount_http_auth_routes
from haleonv3.state.auth_state import AuthState
from haleonv3.apps.oob.admin_oob import admin_oob_page
from haleonv3.apps.oob.page import oob_page
from haleonv3.pages.admin import admin_page


class State(rx.State):
    """The app state."""


def index() -> rx.Component:
    return layout(
        rx.container(
            rx.center(
                rx.vstack(
                    rx.heading("Homepage", size="7"),
                    rx.text("Welcome to Haleon."),
                    rx.cond(
                        AuthState.is_authenticated,
                        rx.text("You're connected."),
                        rx.link(
                            rx.button("Connect", size="3"),
                            href="/auth/login",
                        ),
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
app.add_page(oob_page, route="/apps/oob")
app.add_page(admin_oob_page, route="/apps/oob/admin")
app.add_page(admin_page, route="/admin")