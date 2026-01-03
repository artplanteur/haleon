"""Page admin - Vue d'ensemble et statistiques."""

import reflex as rx
import logging
from haleon.auth.auth_state import AuthState
from haleon.components.layout import layout
from haleon.components.callouts import access_denied_callout
from haleon.state.i18n_state import I18nState
from haleon.db.database import get_session, engine
from haleon.db.crud.users import get_all_users
from haleon.db.crud.applications import get_all_applications
from haleon.db.crud.user_app_access import get_all_user_app_accesses
from haleon.db.crud.logs import (
    get_logs_count,
    get_logs_count_by_date_range,
    get_recent_logs,
)
from sqlalchemy import inspect, text
from datetime import datetime, timedelta

logger = logging.getLogger("haleon.pages.admin.overview")

class OverviewAdminState(I18nState):
    """État pour la vue d'ensemble."""
    
    state_auto_setters: bool = True
    
    def show_unauthorized_toast(self):
        """Affiche un toast d'erreur pour accès non autorisé."""
        return rx.toast.error(
            self.t("access_denied"),
            description=self.t("access_denied_description")
        )
    
    # Statistiques core
    users_count: int = 0
    applications_count: int = 0
    accesses_count: int = 0
    
    # Statistiques détaillées
    active_users_count: int = 0
    validated_users_count: int = 0
    admin_users_count: int = 0
    active_apps_count: int = 0
    
    # Statistiques des logs
    logs_total_count: int = 0
    logs_24h_count: int = 0
    logs_7d_count: int = 0
    logs_30d_count: int = 0
    
    # Tables d'applications
    selected_app_id: int = -1
    selected_app_name: str = ""  # Nom de l'application sélectionnée
    app_tables: list[dict] = []

    # Popup: affichage d'une table core (users/applications/access/logs)
    show_core_table_popup: bool = False
    core_table_title: str = ""
    core_table_name: str = ""
    core_table_rows: list[dict] = []
    core_table_columns: list[str] = []
    core_table_error: str = ""
    core_table_row_limit: int = 500

    def close_core_table_popup(self):
        self.show_core_table_popup = False
        self.core_table_title = ""
        self.core_table_name = ""
        self.core_table_rows = []
        self.core_table_columns = []
        self.core_table_error = ""

    def open_core_table(self, table_key: str):
        """Ouvre un popup avec la table core sélectionnée."""
        table_map = {
            "users": {"table": "users", "title": self.t_users},
            "applications": {"table": "applications", "title": self.t_applications},
            "access": {"table": "userapplicationaccess", "title": self.t_access},
            "logs": {"table": "logs", "title": "Logs"},
        }

        if table_key not in table_map:
            self.core_table_error = f"Table inconnue: {table_key}"
            self.show_core_table_popup = True
            return

        self.core_table_error = ""
        self.core_table_rows = []
        self.core_table_columns = []

        table_name = table_map[table_key]["table"]
        self.core_table_name = table_name
        self.core_table_title = table_map[table_key]["title"]

        session_gen = get_session()
        session = next(session_gen)
        try:
            inspector = inspect(engine)
            cols = inspector.get_columns(table_name)
            self.core_table_columns = [c["name"] for c in cols]

            # LIMIT côté SQL car on désactive la pagination UI
            limit = int(self.core_table_row_limit) if self.core_table_row_limit else 500
            result = session.execute(text(f'SELECT * FROM "{table_name}" LIMIT :limit'), {"limit": limit})
            keys = list(result.keys())
            rows = []
            for r in result.fetchall():
                mapping = dict(r._mapping)
                # Convertir les valeurs non JSON-friendly en string
                clean = {}
                for k, v in mapping.items():
                    if isinstance(v, (datetime,)):
                        clean[k] = v.isoformat(sep=" ", timespec="seconds")
                    else:
                        clean[k] = v
                rows.append(clean)
            # Garder l'ordre des colonnes
            self.core_table_columns = keys or self.core_table_columns
            self.core_table_rows = rows
        except Exception as e:
            self.core_table_error = str(e)
        finally:
            session.close()

        self.show_core_table_popup = True
    
    def on_mount(self):
        """Charge les traductions et les statistiques au chargement de la page."""
        # Charger les traductions
        super().on_mount()
        self.load_statistics()
    
    def load_statistics(self):
        """Charge les statistiques des tables core."""
        session_gen = get_session()
        session = next(session_gen)
        try:
            users = get_all_users(session)
            apps = get_all_applications(session)
            accesses = get_all_user_app_accesses(session)
            
            self.users_count = len(users)
            self.applications_count = len(apps)
            self.accesses_count = len(accesses)
            
            self.active_users_count = sum(1 for u in users if u.is_active)
            self.validated_users_count = sum(1 for u in users if u.is_validated)
            self.admin_users_count = sum(1 for u in users if u.is_admin)
            self.active_apps_count = sum(1 for a in apps if a.is_active)
            
            # Charger les statistiques des logs
            self.logs_total_count = get_logs_count(session)
            
            # Calculer les dates pour les périodes
            now = datetime.now()
            date_24h = now - timedelta(days=1)
            date_7d = now - timedelta(days=7)
            date_30d = now - timedelta(days=30)
            
            self.logs_24h_count = get_logs_count_by_date_range(session, date_24h, now)
            self.logs_7d_count = get_logs_count_by_date_range(session, date_7d, now)
            self.logs_30d_count = get_logs_count_by_date_range(session, date_30d, now)
        finally:
            session.close()
    
    def reload_current_app_tables(self):
        """Recharge les tables de l'application actuellement sélectionnée."""
        if self.selected_app_id != -1:
            self.load_app_tables(self.selected_app_id)
    
    def load_app_tables_from_value(self, value: str):
        """Charge les tables d'une application depuis le nom de l'application."""
        if not value:
            self.selected_app_id = -1
            self.selected_app_name = ""
            self.app_tables = []
            return
        
        # Trouver l'ID de l'application à partir de son nom
        session_gen = get_session()
        session = next(session_gen)
        try:
            from haleon.db.crud.applications import get_all_applications
            apps = get_all_applications(session)
            logger.debug("load_app_tables_from_value searching app=%s", value)
            
            for app in apps:
                if app.name == value:
                    logger.debug("load_app_tables_from_value app found: %s", app.name)
                    self.selected_app_name = app.name
                    self.load_app_tables(app.id)
                    return
            
            # Si l'application n'est pas trouvée
            logger.debug("load_app_tables_from_value app not found: %s", value)
            self.selected_app_id = -1
            self.selected_app_name = ""
            self.app_tables = []
        finally:
            session.close()
    
    def load_app_tables(self, app_id: int):
        """Charge les tables d'une application."""
        if app_id == -1:
            self.app_tables = []
            return
        
        session_gen = get_session()
        session = next(session_gen)
        try:
            # Récupérer l'application
            from haleon.db.crud.applications import get_application_by_id
            app = get_application_by_id(session, app_id)
            if not app:
                self.app_tables = []
                return
            
            # Chercher les tables avec le préfixe app_{appCode}_
            # Utiliser le code de l'application (ex: "OOB") au lieu de l'ID
            app_code = app.code.upper()  # Normaliser en majuscules
            prefix = f"app_{app_code}_"
            inspector = inspect(engine)
            all_tables = inspector.get_table_names()
            
            logger.debug("load_app_tables app_id=%s app_code=%s prefix=%s", app_id, app_code, prefix)
            
            app_tables = []
            for table_name in all_tables:
                # Comparaison insensible à la casse
                if table_name.upper().startswith(prefix.upper()):
                    logger.debug("load_app_tables table found: %s", table_name)
                    # Récupérer les colonnes avec leurs types
                    columns = inspector.get_columns(table_name)
                    column_names = [col["name"] for col in columns]
                    column_details = [
                        {
                            "name": col["name"],
                            "type": str(col["type"]),
                            "nullable": col.get("nullable", True),
                        }
                        for col in columns
                    ]
                    
                    # Compter le nombre de lignes
                    try:
                        result = session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                        row_count = result.scalar() or 0
                    except Exception as e:
                        logger.exception("load_app_tables count error for %s: %s", table_name, e)
                        row_count = 0
                    
                    # Récupérer un aperçu des données (max 3 lignes) et le formater en chaîne
                    preview_text = ""
                    try:
                        if row_count > 0:
                            result = session.execute(text(f"SELECT * FROM {table_name} LIMIT 3"))
                            rows = result.fetchall()
                            preview_lines = []
                            for row in rows:
                                # Prendre les 3 premières colonnes
                                row_parts = []
                                for i, col_name in enumerate(column_names[:3]):
                                    if i < len(row):
                                        value = row[i]
                                        if value is not None:
                                            str_value = str(value)
                                            if len(str_value) > 30:
                                                str_value = str_value[:27] + "..."
                                            row_parts.append(f"{col_name}: {str_value}")
                                        else:
                                            row_parts.append(f"{col_name}: NULL")
                                preview_lines.append(" | ".join(row_parts))
                            preview_text = "\n".join(preview_lines)
                        else:
                            preview_text = "Aucune donnée"
                    except Exception as e:
                        logger.exception("load_app_tables preview error for %s: %s", table_name, e)
                        preview_text = "Erreur lors du chargement"
                    
                    # Créer la chaîne de colonnes avec types (max 5)
                    columns_with_types = [f"{col['name']} ({col['type']})" for col in column_details[:5]]
                    columns_str = ", ".join(columns_with_types)
                    if len(column_details) > 5:
                        columns_str += f"... (+{len(column_details) - 5} autres)"
                    
                    app_tables.append({
                        "name": table_name,
                        "columns": column_names,
                        "column_details": column_details,
                        "column_count": len(columns),
                        "columns_display": columns_str,
                        "row_count": row_count,
                        "row_count_str": f"{row_count} ligne(s)" if row_count > 0 else "0 ligne",
                        "has_data": row_count > 0,
                        "preview_text": preview_text,
                    })
            
            self.app_tables = app_tables
            self.selected_app_id = app_id
            self.selected_app_name = app.name if app else ""
        finally:
            session.close()
    
    @rx.var
    def get_all_application_names(self) -> list[str]:
        """Récupère tous les noms d'applications pour le dropdown."""
        session_gen = get_session()
        session = next(session_gen)
        try:
            apps = get_all_applications(session)
            return [a.name for a in apps]
        finally:
            session.close()


def overview_admin_page() -> rx.Component:
    """Page de vue d'ensemble."""
    
    def app_table_row(table_info: rx.Var[dict]):
        """Ligne d'une table d'application avec détails."""
        return rx.table.row(
            rx.table.cell(
                rx.vstack(
                    rx.text(table_info["name"], weight="bold", size="4"),
                    rx.text(table_info["row_count_str"], size="2", color="gray"),
                    spacing="1",
                    align="start",
                )
            ),
            rx.table.cell(
                rx.vstack(
                    rx.text(f"{table_info['column_count']} {OverviewAdminState.t_columns}", weight="medium"),
                    rx.text(table_info["columns_display"], size="2", color="gray"),
                    spacing="1",
                    align="start",
                )
            ),
            rx.table.cell(
                rx.box(
                    rx.text(
                        table_info["preview_text"],
                size="2",
                        color="gray",
                        white_space="pre-wrap",
                    ),
                    padding="2",
                    width="100%",
                    max_height="150px",
                    overflow_y="auto",
                ),
            ),
        )
    
    def core_table_popup():
        return rx.cond(
            OverviewAdminState.show_core_table_popup,
            rx.fragment(
                # Overlay
                rx.box(
                    position="fixed",
                    top="0",
                    left="0",
                    right="0",
                    bottom="0",
                    background_color="rgba(0, 0, 0, 0.5)",
                    z_index="9998",
                    on_click=OverviewAdminState.close_core_table_popup,
                    class_name="popup-overlay",
                ),
                # Popup content
                rx.box(
                    rx.card(
                        rx.vstack(
                            rx.hstack(
                                rx.heading(OverviewAdminState.core_table_title, size="6"),
                                rx.spacer(),
                                rx.button(
                                    "✕",
                                    variant="ghost",
                                    size="2",
                                    on_click=OverviewAdminState.close_core_table_popup,
                                ),
                                width="100%",
                                align="center",
                            ),
                            rx.divider(),
                            rx.cond(
                                OverviewAdminState.core_table_error,
                                rx.text(
                                    OverviewAdminState.core_table_error,
                                    color="red",
                                    size="3",
                                    white_space="pre-wrap",
                                ),
                                rx.box(
                                    rx.data_table(
                                        data=OverviewAdminState.core_table_rows,
                                        columns=OverviewAdminState.core_table_columns,
                                        search=True,
                                        pagination=False,
                                        sort=True,
                                        resizable=True,
                                        width="100%",
                                        class_name="core-table-datatable",
                                    ),
                                    width="100%",
                                    max_height="70vh",
                                    overflow_y="auto",
                                    overflow_x="auto",
                                    class_name="core-table-scroll",
                                    display="flex",
                                    flex_direction="column",
                                ),
                            ),
                            spacing="4",
                            width="100%",
                        ),
                        padding="24px",
                        width="88%",
                        max_width="88vw",
                        max_height="90vh",
                        overflow="hidden",
                    ),
                    position="fixed",
                    top="50%",
                    left="50%",
                    transform="translate(-50%, -50%)",
                    z_index="9999",
                    class_name="popup-content",
                    bg=rx.color_mode_cond("white", "#0f172a"),
                ),
            ),
        )

    content = rx.vstack(
        rx.heading(OverviewAdminState.t_overview, size="8", text_align="center", width="100%"),
        rx.heading(OverviewAdminState.t_core_tables_statistics, size="6", margin_top="6"),
        core_table_popup(),
        rx.grid(
            rx.box(
                rx.card(
                rx.vstack(
                    rx.heading(OverviewAdminState.t_users, size="5"),
                    rx.text(OverviewAdminState.users_count, size="8", weight="bold"),
                    rx.hstack(
                        rx.text(OverviewAdminState.t_active + ": ", size="2"),
                        rx.text(OverviewAdminState.active_users_count, size="2"),
                        spacing="1",
                    ),
                    rx.hstack(
                        rx.text(OverviewAdminState.t_validated + ": ", size="2"),
                        rx.text(OverviewAdminState.validated_users_count, size="2"),
                        spacing="1",
                    ),
                    rx.hstack(
                        rx.text(OverviewAdminState.t_admin + ": ", size="2"),
                        rx.text(OverviewAdminState.admin_users_count, size="2"),
                        spacing="1",
                    ),
                    spacing="2",
                ),
                padding="6",
                ),
                on_click=lambda: OverviewAdminState.open_core_table("users"),
                cursor="pointer",
            ),
            rx.box(
                rx.card(
                rx.vstack(
                    rx.heading(OverviewAdminState.t_applications, size="5"),
                    rx.text(OverviewAdminState.applications_count, size="8", weight="bold"),
                    rx.hstack(
                        rx.text(OverviewAdminState.t_active + ": ", size="2"),
                        rx.text(OverviewAdminState.active_apps_count, size="2"),
                        spacing="1",
                    ),
                    spacing="2",
                ),
                padding="6",
                ),
                on_click=lambda: OverviewAdminState.open_core_table("applications"),
                cursor="pointer",
            ),
            rx.box(
                rx.card(
                rx.vstack(
                    rx.heading(OverviewAdminState.t_access, size="5"),
                    rx.text(OverviewAdminState.accesses_count, size="8", weight="bold"),
                    spacing="2",
                ),
                padding="6",
                ),
                on_click=lambda: OverviewAdminState.open_core_table("access"),
                cursor="pointer",
            ),
            rx.box(
                rx.card(
                rx.vstack(
                    rx.heading("Logs", size="5"),
                    rx.text(OverviewAdminState.logs_total_count, size="8", weight="bold"),
                    rx.hstack(
                        rx.text("24h: ", size="2"),
                        rx.text(OverviewAdminState.logs_24h_count, size="2"),
                        spacing="1",
                    ),
                    rx.hstack(
                        rx.text("7j: ", size="2"),
                        rx.text(OverviewAdminState.logs_7d_count, size="2"),
                        spacing="1",
                    ),
                    rx.hstack(
                        rx.text("30j: ", size="2"),
                        rx.text(OverviewAdminState.logs_30d_count, size="2"),
                        spacing="1",
                    ),
                    spacing="2",
                ),
                padding="6",
                ),
                on_click=lambda: OverviewAdminState.open_core_table("logs"),
                cursor="pointer",
            ),
            columns="4",
            spacing="4",
            width="100%",
        ),
        rx.card(
            rx.vstack(
                rx.heading(OverviewAdminState.t_application_tables, size="6", margin_bottom="4"),
                rx.vstack(
                    rx.text(OverviewAdminState.t_select_application + ":", size="3", weight="medium", margin_bottom="2"),
                    rx.select(
                        OverviewAdminState.get_all_application_names,
                        placeholder=OverviewAdminState.t_select_application,
                        value=OverviewAdminState.selected_app_name,
                        on_change=OverviewAdminState.load_app_tables_from_value,
                        width="100%",
                        size="3",
                    ),
                    spacing="2",
                    width="100%",
                ),
                spacing="2",
                width="100%",
                    margin_bottom="4",
                ),
                rx.cond(
                    OverviewAdminState.app_tables,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                            rx.table.column_header_cell(OverviewAdminState.t_table),
                            rx.table.column_header_cell(OverviewAdminState.t_structure),
                            rx.table.column_header_cell(OverviewAdminState.t_data_preview),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(
                                OverviewAdminState.app_tables,
                                app_table_row,
                            ),
                        ),
                        width="100%",
                        variant="surface",
                    ),
                    rx.cond(
                        OverviewAdminState.selected_app_id != -1,
                        rx.center(
                            rx.text(
                                OverviewAdminState.t_no_tables_found,
                                size="4",
                                color="gray.500",
                                padding="8",
                            ),
                        ),
                        rx.center(
                            rx.text(
                                OverviewAdminState.t_select_app_to_see_tables,
                                size="4",
                                color="gray.400",
                                padding="8",
                                font_style="italic",
                            ),
                        ),
                    ),
                ),
                spacing="4",
                width="100%",
            padding="6",
        ),
        spacing="6",
        width="100%",
        padding="6",
    )
    
    return rx.fragment(
        # Afficher un toast d'erreur si l'utilisateur n'est pas admin
        rx.cond(
            ~AuthState.is_admin,
            rx.box(
                on_mount=OverviewAdminState.show_unauthorized_toast
            ),
        ),
        # Contenu principal ou message d'erreur
        rx.cond(
            AuthState.is_admin,
            layout(content),
            layout(
                access_denied_callout(
                    OverviewAdminState.t_access_denied,
                    OverviewAdminState.t_access_denied_description,
                    OverviewAdminState.t_back_to_home,
                    "/home",
                ),
            ),
        ),
    )

