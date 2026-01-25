import reflex as rx
from haleonv3.apps.oob.state import OOBState
from haleonv3.state.auth_state import AuthState


def oob_page() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.cond(
                AuthState.can_oob_admin,
                rx.link(rx.button("Admin OOB", size="2"), href="/apps/oob/admin"),
                rx.box(),
            ),
            rx.cond(
                OOBState.is_loading,
                rx.vstack(
                    rx.hstack(
                        rx.text("Chargement :"),
                        rx.text(OOBState.progress, font_weight="bold"),
                        rx.text("%", font_weight="bold"),
                        spacing="2",
                    ),
                    rx.progress(
                        value=OOBState.progress,
                        max=100,
                        width="100%",
                    ),
                    width="100%",
                    spacing="3",
                ),
                rx.data_table(
                    data=OOBState.rows,
                    columns=["po", "vendor", "amount", "status"],
                    search=True,
                    sort=True,
                    pagination=True,
                    width="100%",
                ),
            ),
            spacing="4",
            width="100%",
        ),
        on_mount=OOBState.load_oob_data,
        width="100%",
    )
