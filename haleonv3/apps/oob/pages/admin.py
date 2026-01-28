import reflex as rx

from haleonv3.components.layout import layout
from haleonv3.state.auth_state import AuthState
from haleonv3.apps.oob.state.access_state import OOBAccessState


def admin_oob_page() -> rx.Component:
    return layout(
        rx.container(
            rx.cond(
                AuthState.can_moderate_oob,
                rx.vstack(
                    rx.heading("OOB Admin", size="7"),
                    rx.hstack(
                        rx.select(
                            placeholder="Utilisateur",
                            value=OOBAccessState.selected_user_id,
                            on_change=OOBAccessState.set_selected_user,
                            data=OOBAccessState.user_options,
                            width="320px",
                        ),
                        rx.select(
                            placeholder="Niveau d'accès",
                            value=OOBAccessState.selected_access_level,
                            on_change=OOBAccessState.set_selected_access_level,
                            data=["none", "read", "write"],
                            width="160px",
                        ),
                        rx.select(
                            placeholder="Portfolio",
                            value=OOBAccessState.selected_portfolio,
                            on_change=OOBAccessState.set_selected_portfolio,
                            data=OOBAccessState.portfolios,
                            width="200px",
                        ),
                        spacing="3",
                        width="100%",
                    ),
                    rx.hstack(
                        rx.switch(
                            is_checked=OOBAccessState.is_portfolio_all_selected,
                            on_change=OOBAccessState.select_all_portfolio,
                        ),
                        rx.text("Select all portfolio"),
                        spacing="2",
                    ),
                    rx.box(
                        rx.foreach(
                            OOBAccessState.portfolio_vendors,
                            lambda vendor: rx.hstack(
                                rx.checkbox(
                                    is_checked=vendor["id"]
                                    in OOBAccessState.selected_vendor_ids,
                                    on_change=lambda v, vid=vendor["id"]: OOBAccessState.toggle_vendor_selection(
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
                        rx.button("Appliquer", on_click=OOBAccessState.apply_access_to_selected),
                        rx.button(
                            "Supprimer accès",
                            variant="soft",
                            on_click=OOBAccessState.remove_access_from_selected,
                        ),
                        spacing="3",
                    ),
                    spacing="4",
                    width="100%",
                ),
                rx.text("Access denied: OOB admins only."),
            ),
            on_mount=[
                OOBAccessState.load_users,
                OOBAccessState.load_vendors,
                OOBAccessState.load_access,
            ],
        )
    )
