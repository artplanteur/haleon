import reflex as rx

from haleonv3.components.layout import layout
from haleonv3.state.admin_state import AdminState
from haleonv3.state.auth_state import AuthState
from haleonv3.state.oob_admin_state import OOBAdminState
from haleonv3.state.roles_state import RolesState


def admin_page() -> rx.Component:
    return layout(
        rx.container(
            rx.cond(
                AuthState.can_admin,
                rx.tabs(
                    rx.tabs_list(
                        rx.tabs_trigger("Users", value="users"),
                        rx.tabs_trigger("Vendors", value="vendors"),
                        rx.tabs_trigger("Roles", value="roles"),
                    ),
                    rx.tabs.content(
                        rx.vstack(
                            rx.heading("Admin Users", size="7"),
                            # Example: dynamic form for access grant (popover)
                            # from haleonv3.components.dynamic_form import dynamic_form
                            # dynamic_form("access", "Donner accès")
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
                                            rx.table.column_header_cell("Vendors"),
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
                                                rx.table.cell(
                                                        rx.popover.root(
                                                        rx.popover.trigger(
                                                            rx.button("Accès", size="1", variant="soft")
                                                        ),
                                                        rx.popover.content(
                                                            rx.vstack(
                                                                rx.foreach(
                                                                    OOBAdminState.vendor_access,
                                                                    lambda access: rx.cond(
                                                                        access["user_id"] == user["id"],
                                                                        rx.hstack(
                                                                            rx.text(access["vendor_code"]),
                                                                            rx.select(
                                                                                value=access["access_level"],
                                                                                on_change=lambda v, uid=user["id"], vid=access[
                                                                                    "vendor_id"
                                                                                ]: OOBAdminState.set_user_vendor_access(
                                                                                    uid, vid, v
                                                                                ),
                                                                                data=["read", "write"],
                                                                                width="120px",
                                                                            ),
                                                                            rx.button(
                                                                                "Remove",
                                                                                size="1",
                                                                                variant="soft",
                                                                                on_click=lambda uid=user[
                                                                                    "id"
                                                                                ], vid=access[
                                                                                    "vendor_id"
                                                                                ]: OOBAdminState.remove_user_vendor_access(
                                                                                    uid, vid
                                                                                ),
                                                                            ),
                                                                            spacing="2",
                                                                        ),
                                                                        rx.box(),
                                                                    ),
                                                                ),
                                                                spacing="2",
                                                                width="320px",
                                                            ),
                                                            side="right",
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
                    rx.tabs.content(
                        rx.vstack(
                            rx.heading("Vendors", size="7"),
                            # Example: use dynamic form instead of inline inputs
                            # from haleonv3.components.dynamic_form import dynamic_form
                            # dynamic_form("vendor", "Ajouter Vendor")
                            rx.hstack(
                                rx.input(
                                    placeholder="Code vendor",
                                    value=OOBAdminState.new_vendor_code,
                                    on_change=OOBAdminState.set_new_vendor_code,
                                    width="160px",
                                ),
                                rx.input(
                                    placeholder="Description",
                                    value=OOBAdminState.new_vendor_description,
                                    on_change=OOBAdminState.set_new_vendor_description,
                                    width="280px",
                                ),
                                rx.input(
                                    placeholder="Portfolio",
                                    value=OOBAdminState.new_vendor_portfolio,
                                    on_change=OOBAdminState.set_new_vendor_portfolio,
                                    width="160px",
                                ),
                                rx.button("Ajouter", on_click=OOBAdminState.create_vendor),
                                spacing="3",
                                width="100%",
                            ),
                            rx.hstack(
                                rx.input(
                                    placeholder="Filtrer par code",
                                    value=OOBAdminState.vendor_search,
                                    on_change=OOBAdminState.set_vendor_search,
                                    width="200px",
                                ),
                                rx.select(
                                    placeholder="Portfolio",
                                    value=OOBAdminState.portfolio_filter,
                                    on_change=OOBAdminState.set_portfolio_filter,
                                    data=OOBAdminState.portfolios,
                                    width="200px",
                                ),
                                rx.switch(
                                    is_checked=OOBAdminState.include_inactive,
                                    on_change=OOBAdminState.set_include_inactive,
                                ),
                                rx.text("Inclure inactifs"),
                                spacing="3",
                                width="100%",
                            ),
                            rx.cond(
                                OOBAdminState.is_loading_vendors,
                                rx.spinner(size="3"),
                                rx.table.root(
                                    rx.table.header(
                                        rx.table.row(
                                            rx.table.column_header_cell("Code"),
                                            rx.table.column_header_cell("Description"),
                                            rx.table.column_header_cell("Portfolio"),
                                            rx.table.column_header_cell("Active"),
                                            rx.table.column_header_cell("Users"),
                                        )
                                    ),
                                    rx.table.body(
                                        rx.foreach(
                                            OOBAdminState.filtered_vendors,
                                            lambda vendor: rx.table.row(
                                                rx.table.cell(vendor["code"]),
                                                rx.table.cell(vendor["description"]),
                                                rx.table.cell(vendor["portfolio"]),
                                                rx.table.cell(
                                                    rx.switch(
                                                        is_checked=vendor["is_active"],
                                                        on_change=lambda v, vid=vendor["id"]: OOBAdminState.toggle_vendor_active(
                                                            vid, v
                                                        ),
                                                    )
                                                ),
                                                rx.table.cell(
                                                    rx.popover.root(
                                                        rx.popover.trigger(
                                                            rx.button("Accès", size="1", variant="soft")
                                                        ),
                                                        rx.popover.content(
                                                            rx.vstack(
                                                                rx.foreach(
                                                                    OOBAdminState.vendor_access,
                                                                    lambda access: rx.cond(
                                                                        access["vendor_id"] == vendor["id"],
                                                                        rx.hstack(
                                                                            rx.text(access["user_email"]),
                                                                            rx.select(
                                                                                value=access["access_level"],
                                                                                on_change=lambda v, uid=access[
                                                                                    "user_id"
                                                                                ], vid=vendor[
                                                                                    "id"
                                                                                ]: OOBAdminState.set_user_vendor_access(
                                                                                    uid, vid, v
                                                                                ),
                                                                                data=["read", "write"],
                                                                                width="120px",
                                                                            ),
                                                                            spacing="2",
                                                                        ),
                                                                        rx.box(),
                                                                    ),
                                                                ),
                                                                spacing="2",
                                                                width="320px",
                                                            ),
                                                            side="right",
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
                        value="vendors",
                    ),
                    rx.tabs.content(
                        rx.vstack(
                            rx.heading("Local Roles", size="7"),
                            # Example: dynamic form for local role assignment
                            # FORM_SCHEMAS["role"] = [
                            #     {"name": "user_id", "label": "User ID", "type": "number", "required": True},
                            #     {"name": "app", "label": "App", "type": "text", "required": True},
                            #     {"name": "role", "label": "Role", "type": "select", "options": ["admin"]},
                            # ]
                            # dynamic_form("role", "Rendre admin")
                            rx.hstack(
                                rx.input(
                                    placeholder="Rechercher un utilisateur...",
                                    value=RolesState.user_search,
                                    on_change=RolesState.set_user_search,
                                    width="320px",
                                ),
                                spacing="3",
                                width="100%",
                            ),
                            rx.hstack(
                                rx.select(
                                    placeholder="Utilisateur",
                                    value=RolesState.selected_user_id,
                                    on_change=RolesState.set_selected_user,
                                    data=RolesState.user_options,
                                    width="320px",
                                ),
                                rx.select(
                                    placeholder="Application",
                                    value=RolesState.selected_app,
                                    on_change=RolesState.set_selected_app,
                                    data=RolesState.apps,
                                    width="240px",
                                ),
                                rx.button(
                                    "Rendre admin",
                                    on_click=RolesState.grant_selected_admin,
                                ),
                                spacing="3",
                                width="100%",
                            ),
                            rx.table.root(
                                rx.table.header(
                                    rx.table.row(
                                        rx.table.column_header_cell("App"),
                                        rx.table.column_header_cell("User"),
                                        rx.table.column_header_cell("Role"),
                                        rx.table.column_header_cell("Action"),
                                    )
                                ),
                                rx.table.body(
                                    rx.foreach(
                                        RolesState.roles,
                                        lambda role: rx.table.row(
                                            rx.table.cell(role["app"]),
                                            rx.table.cell(role["user_email"]),
                                            rx.table.cell(role["role"]),
                                            rx.table.cell(
                                                rx.button(
                                                    "Remove",
                                                    size="1",
                                                    variant="soft",
                                                    on_click=lambda uid=role[
                                                        "user_id"
                                                    ], app=role[
                                                        "app"
                                                    ]: RolesState.revoke_app_admin(
                                                        app, uid
                                                    ),
                                                )
                                            ),
                                        ),
                                    )
                                ),
                                width="100%",
                                variant="surface",
                            ),
                            spacing="4",
                            width="100%",
                        ),
                        value="roles",
                    ),
                    default_value="users",
                ),
                rx.text("Access denied: admin only."),
            ),
            on_mount=[
                AdminState.load_users,
                OOBAdminState.load_vendors,
                OOBAdminState.load_access,
                RolesState.load_apps,
                RolesState.load_users,
                RolesState.load_roles,
            ],
        )
    )
