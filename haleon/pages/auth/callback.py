"""SSO callback page.

This page exists only to receive the IdP redirect and trigger AuthState logic.
Route: /auth/callback
Query params expected: ?code=...&state=...
"""

import reflex as rx
from haleon.components.layout import layout
from haleon.auth.auth_state import AuthState


def auth_callback_page() -> rx.Component:
    content = rx.center(
        rx.vstack(
            rx.heading("Connexion SSO…", size="6"),
            rx.text(
                "Veuillez patienter pendant la finalisation de votre authentification.",
                color="gray",
            ),
            rx.cond(
                AuthState.sso_error,
                rx.text(AuthState.sso_error, color="red"),
                rx.box(),
            ),
            spacing="4",
            align="center",
            min_height="60vh",
        ),
        width="100%",
    )
    return layout(content)


