"""Composant Sidebar/Drawer pour le menu de navigation."""

import reflex as rx
from haleon.auth.auth_state import AuthState
from haleon.state.i18n_state import I18nState
from haleon.apps.loader import get_application_admin_menu_items


class SidebarState(I18nState):
    """État pour gérer l'ouverture/fermeture du drawer."""
    drawer_open: bool = False
    current_app_code_for_menu: str = ""  # Code de l'application courante pour le menu
    
    def toggle_drawer(self):
        """Ouvre/ferme le drawer."""
        self.drawer_open = not self.drawer_open
    
    def open_drawer(self):
        """Ouvre le drawer."""
        self.drawer_open = True
    
    def close_drawer(self):
        """Ferme le drawer."""
        self.drawer_open = False
    
    def set_drawer_open(self, is_open: bool):
        """Met à jour l'état d'ouverture du drawer."""
        self.drawer_open = is_open
    
    @rx.var
    def application_admin_menu_items(self) -> list[dict]:
        """Récupère les items de menu admin de l'application courante uniquement (si on est sur une page d'application)."""
        # Ne charger les items que si on est sur une page d'application
        app_code = self.current_app_code_for_menu
        
        if not app_code:
            # Pas sur une page d'application, ne pas afficher les items
            return []
        
        try:
            # Charger uniquement les items de l'application courante
            items = get_application_admin_menu_items(app_code)
            return items
        except Exception as e:
            print(f"Erreur lors du chargement des items de menu pour {app_code}: {e}")
            return []


def sidebar_item(text: str, icon: str, href: str, is_admin: bool = False) -> rx.Component:
    """Item de navigation dans la sidebar."""
    # Si is_admin est un Var, utiliser rx.cond, sinon utiliser directement
    if isinstance(is_admin, bool):
        class_name = f"sidebar-item{' admin' if is_admin else ''}"
    else:
        # is_admin est un Var Reflex, utiliser rx.cond
        class_name = rx.cond(
            is_admin,
            "sidebar-item admin",
            "sidebar-item",
        )
    
    return rx.drawer.close(
        rx.link(
            rx.hstack(
                rx.text(icon, size="4"),
                rx.text(text, size="3"),
                spacing="2",
                align="center",
                width="100%",
                padding_x="0.75rem",
                padding_y="0.75rem",
                class_name=class_name,
            ),
            href=href,
            width="100%",
        ),
    )


def sidebar() -> rx.Component:
    """Sidebar/Drawer avec menu de navigation selon la doc Reflex."""
    return rx.drawer.root(
        rx.drawer.overlay(
            class_name="drawer-overlay",
        ),
        rx.drawer.content(
            rx.vstack(
                # Header avec titre et bouton fermer
                rx.hstack(
                    rx.heading(
                        SidebarState.t_menu,
                        size="6",
                        weight="bold",
                        class_name="sidebar-section-title",
                    ),
                    rx.spacer(),
                    rx.drawer.close(
                        rx.button(
                            "✕",
                            variant="ghost",
                            size="2",
                            class_name="header-btn",
                        ),
                    ),
                    width="100%",
                    align="center",
                    padding_bottom="4",
                ),
                rx.divider(margin_y="2"),
                # Contenu de navigation
                rx.vstack(
                    # Section Admin (si admin) - selon README ligne 59
                    rx.cond(
                        AuthState.is_admin,
                        rx.vstack(
                            rx.text(
                                SidebarState.t_administration,
                                size="3",
                                weight="bold",
                                color="red.600",
                                padding_x="0.75rem",
                                padding_y="2",
                                class_name="sidebar-section-title admin",
                            ),
                            sidebar_item(SidebarState.t_users, "👥", "/admin/users", is_admin=True),
                            sidebar_item(SidebarState.t_applications, "📦", "/admin/applications", is_admin=True),
                            sidebar_item(SidebarState.t_access, "🔑", "/admin/access", is_admin=True),
                            sidebar_item(SidebarState.t_overview, "📊", "/admin/overview", is_admin=True),
                            spacing="1",
                            width="100%",
                        ),
                    ),
                    # Section Admin des applications (items dynamiques)
                    rx.cond(
                        AuthState.is_admin,
                        rx.cond(
                            SidebarState.application_admin_menu_items,
                            rx.vstack(
                                rx.divider(margin_y="4"),
                                rx.foreach(
                                    SidebarState.application_admin_menu_items,
                                    lambda item: sidebar_item(
                                        item["text"],
                                        item["icon"],
                                        item["href"],
                                        is_admin=item.get("is_admin", True),  # Utilise is_admin du dict, par défaut True
                                    ),
                                ),
                                spacing="1",
                                width="100%",
                            ),
                        ),
                    ),
                    # Section Paramètres (toujours visible - dark mode accessible à tous) - selon README ligne 60
                    rx.vstack(
                        rx.cond(
                            AuthState.is_admin,
                            rx.divider(margin_y="4"),
                            rx.box(),
                        ),
                        rx.text(
                            SidebarState.t_settings,
                            size="3",
                            weight="bold",
                            padding_x="0.75rem",
                            padding_y="2",
                            class_name="sidebar-section-title",
                        ),
                        rx.hstack(
                            rx.color_mode_cond(
                                rx.text("🌙", size="4"),
                                rx.text("☀️", size="4"),
                            ),
                            rx.color_mode_cond(
                                rx.text(SidebarState.t_dark_mode, size="3"),
                                rx.text(SidebarState.t_light_mode, size="3"),
                            ),
                            rx.spacer(),
                            rx.color_mode.button(),
                            spacing="2",
                            align="center",
                            width="100%",
                            padding_x="0.75rem",
                            padding_y="0.75rem",
                            class_name="sidebar-item",
                        ),
                        # Sélecteur de langue avec drapeau
                        rx.hstack(
                            rx.image(
                                src=AuthState.current_locale_flag_url,
                                alt="Country flag",
                                width="24px",
                                height="24px",
                                border_radius="4px",
                            ),
                            rx.text(SidebarState.t_language, size="3"),
                            rx.spacer(),
                            rx.select(
                                ["fr", "en", "es", "pt", "ar"],
                                value=AuthState.locale,
                                on_change=AuthState.set_locale,
                                size="2",
                            ),
                            spacing="2",
                            align="center",
                            width="100%",
                            padding_x="0.75rem",
                            padding_y="0.75rem",
                            class_name="sidebar-item",
                        ),
                        spacing="1",
                        width="100%",
                    ),
                    rx.spacer(),
                    spacing="1",
                    width="100%",
                    padding_top="2",
                ),
                spacing="4",
                width="100%",
                height="100%",
                padding="1em",
            ),
            class_name="drawer-sidebar",
            width="320px",
            padding="0",
            bg=rx.color_mode_cond("white", "#0f172a"),
        ),
        direction="left",
        open=SidebarState.drawer_open,
        on_open_change=SidebarState.set_drawer_open,
        modal=True,
    )










