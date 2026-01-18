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
                    rx.input(
                        placeholder="Search (PO, vendor, status)...",
                        value=OOBState.search,
                        on_change=OOBState.set_search,
                        width="300px",
                    ),
                    rx.hstack(
                        rx.button("Sort by PO", on_click=lambda: OOBState.toggle_sort("po")),
                        rx.button("Sort by Vendor", on_click=lambda: OOBState.toggle_sort("vendor")),
                        rx.button("Sort by Amount", on_click=lambda: OOBState.toggle_sort("amount")),
                        rx.button("Sort by Status", on_click=lambda: OOBState.toggle_sort("status")),
                        spacing="2",
                    ),
                    rx.data_table(
                        data=OOBState.filtered_rows,
                        columns=["po", "vendor", "amount", "status"],
                        pagination=True,
                    ),
                    spacing="4",
                ),
                rx.text("Access denied: validated users only."),
            )
        )
    )
