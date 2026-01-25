import reflex as rx

from haleonv3.components.layout import layout
from haleonv3.state.auth_state import AuthState
from haleonv3.state.oob_admin_state import OOBAdminState


def admin_oob_page() -> rx.Component:
    return layout(
        rx.container(
            rx.cond(
                AuthState.is_admin | AuthState.admin_apps.contains("oob"),
                rx.vstack(
                    rx.heading("OOB Admin", size="7"),
                    rx.hstack(
                        rx.select(
                            placeholder="Utilisateur",
                            value=OOBAdminState.selected_user_id,
                            on_change=OOBAdminState.set_selected_user,
                            data=OOBAdminState.user_options,
                            width="320px",
                        ),
                        rx.select(
                            placeholder="Niveau d'accès",
                            value=OOBAdminState.selected_access_level,
                            on_change=OOBAdminState.set_selected_access_level,
                            data=["read", "write"],
                            width="160px",
                        ),
                        rx.select(
                            placeholder="Portfolio",
                            value=OOBAdminState.selected_portfolio,
                            on_change=OOBAdminState.set_selected_portfolio,
                            data=OOBAdminState.portfolios,
                            width="200px",
                        ),
                        spacing="3",
                        width="100%",
                    ),
                    rx.hstack(
                        rx.switch(
                            is_checked=OOBAdminState.is_portfolio_all_selected,
                            on_change=OOBAdminState.select_all_portfolio,
                        ),
                        rx.text("Select all portfolio"),
                        spacing="2",
                    ),
                    rx.box(
                        rx.foreach(
                            OOBAdminState.portfolio_vendors,
                            lambda vendor: rx.hstack(
                                rx.checkbox(
                                    is_checked=vendor["id"]
                                    in OOBAdminState.selected_vendor_ids,
                                    on_change=lambda v, vid=vendor["id"]: OOBAdminState.toggle_vendor_selection(
                                        vid, v
                                    ),
                                ),
                                rx.text(vendor["code"]),
                                rx.text(vendor["portfolio"]),
                                spacing="3",
                            ),
                        ),
                        width="100%",
                    ),
                    rx.hstack(
                        rx.button("Appliquer", on_click=OOBAdminState.apply_access_to_selected),
                        rx.button(
                            "Supprimer accès",
                            variant="soft",
                            on_click=OOBAdminState.remove_access_from_selected,
                        ),
                        spacing="3",
                    ),
                    spacing="4",
                    width="100%",
                ),
                rx.text("Access denied: OOB admins only."),
            ),
            on_mount=[
                OOBAdminState.load_users,
                OOBAdminState.load_vendors,
                OOBAdminState.load_access,
            ],
        )
    )
