import reflex as rx
from haleonv3.components.layout import layout
from haleonv3.state.auth_state import AuthState
from haleonv3.apps.oob.state import OOBState


def oob_page() -> rx.Component:
    return layout(
        rx.container(
            rx.cond(
                AuthState.can_validated,
                rx.vstack(
                    rx.heading("OOB App", size="7"),
                    rx.data_table(
                        data=OOBState.rows,
                        columns=["po", "vendor", "amount", "status"],
                        search=True,
                        sort=True,
                        pagination=True,
                    ),
                    spacing="4",
                ),
                rx.text("Access denied: validated users only."),
            )
        )
    )
