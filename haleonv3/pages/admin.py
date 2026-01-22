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
                        rx.hstack(
                            rx.text("Trier par"),
                            rx.select(
                                value=AdminState.sort_value,
                                on_change=AdminState.set_sort_value,
                                data=[
                                        "source_domain",
                                    "email",
                                    "given_name",
                                    "family_name",
                                    "immutable_id",
                                    "id",
                                ],
                                width="240px",
                            ),
                            spacing="3",
                            width="100%",
                        ),
                        rx.cond(
                            AdminState.is_loading,
                            rx.spinner(size="4"),
                            rx.table.root(
                                rx.table.header(
                                    rx.table.row(
                                        rx.table.column_header_cell("ID"),
                                        rx.table.column_header_cell("Origine"),
                                        rx.table.column_header_cell("Email"),
                                        rx.table.column_header_cell("Prénom"),
                                        rx.table.column_header_cell("Nom"),
                                        rx.table.column_header_cell("Active"),
                                        rx.table.column_header_cell("Validated"),
                                        rx.table.column_header_cell("Admin"),
                                    )
                                ),
                                rx.table.body(
                                    rx.foreach(
                                        AdminState.current_users,
                                        lambda user: rx.table.row(
                                            rx.table.cell(user["id"]),
                                            rx.table.cell(user["source_domain"]),
                                            rx.table.cell(user["email"]),
                                            rx.table.cell(user["given_name"]),
                                            rx.table.cell(user["family_name"]),
                                            rx.table.cell(
                                                rx.switch(
                                                    is_checked=user["is_active"],
                                                    on_change=lambda v, uid=user["id"]: AdminState.toggle_active(
                                                        uid, v
                                                    ),
                                                    disabled=(
                                                        (user["email"] == AuthState.email)
                                                        | (user["immutable_id"] == AuthState.immutable_id)
                                                    ),
                                                )
                                            ),
                                            rx.table.cell(
                                                rx.switch(
                                                    is_checked=user["is_validated"],
                                                    on_change=lambda v, uid=user["id"]: AdminState.toggle_validated(
                                                        uid, v
                                                    ),
                                                    disabled=(
                                                        (user["email"] == AuthState.email)
                                                        | (user["immutable_id"] == AuthState.immutable_id)
                                                    ),
                                                )
                                            ),
                                            rx.table.cell(
                                                rx.switch(
                                                    is_checked=user["is_admin"],
                                                    on_change=lambda v, uid=user["id"]: AdminState.toggle_admin(
                                                        uid, v
                                                    ),
                                                    disabled=(
                                                        (user["email"] == AuthState.email)
                                                        | (user["immutable_id"] == AuthState.immutable_id)
                                                    ),
                                                )
                                            ),
                                        ),
                                    )
                                ),
                                width="100%",
                                variant="surface",
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
