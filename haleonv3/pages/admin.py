import reflex as rx

from haleonv3.components.layout import layout
from haleonv3.state.admin_state import AdminState
from haleonv3.state.auth_state import AuthState


def admin_page() -> rx.Component:
    return layout(
        rx.container(
            rx.cond(
                AuthState.can_admin,
                rx.tabs(
                    rx.tabs_list(
                        rx.tabs_trigger("Users", value="users"),
                        rx.tabs_trigger("Vendor Access", value="vendor"),
                    ),
                    rx.tabs_content(
                        rx.vstack(
                            rx.heading("Admin Users", size="7"),
                            rx.input(
                                placeholder="Rechercher (email, prénom, nom, immutable_id)...",
                                value=AdminState.search_query,
                                on_change=AdminState.set_search_query,
                                width="100%",
                            ),
                            rx.cond(
                                AdminState.is_loading,
                                rx.spinner(size="4"),
                                rx.data_editor(
                                    columns=AdminState.columns,
                                    data=AdminState.filtered_users,
                                    on_cell_edited=AdminState.on_cell_edited,
                                    height="600px",
                                    width="100%",
                                ),
                            ),
                            spacing="4",
                            width="100%",
                        ),
                        value="users",
                    ),
                    rx.tabs_content(
                        rx.box(
                            rx.text("Vendor access management (à venir)"),
                            padding="1rem",
                        ),
                        value="vendor",
                    ),
                    default_value="users",
                ),
                rx.text("Access denied: admin only."),
            ),
            on_mount=AdminState.load_users,
        )
    )
