"""Page principale de l'application OOB."""

import reflex as rx
from haleon.apps.oob.state import OOBState
from haleon.components.layout import layout
from haleon.components.callouts import access_denied_callout
from haleon.auth.auth_state import AuthState
from haleon.state.i18n_state import I18nState


class OOBPageState(I18nState):
    """State pour la page OOB avec traductions."""
    
    def on_mount(self):
        """Charge les traductions au montage."""
        super().on_mount()


def page() -> rx.Component:
    """Page principale de l'application OOB."""
    
    def header():
        """Header avec titre et actions."""
        return rx.card(
            rx.hstack(
                rx.heading(OOBPageState.t_oob_purchasing_items, size="7", weight="bold"),
                rx.spacer(),
                rx.button(
                    OOBPageState.t_oob_download_excel,
                    on_click=OOBState.download_excel,
                    color_scheme="green",
                    size="3",
                    variant="outline",
                ),
                # Bouton Admin (seulement si l'utilisateur est admin)
                rx.cond(
                    OOBState.is_admin,
                    rx.button(
                        "📋 Admin OOB",
                        on_click=rx.redirect("/admin/oob/access"),
                        color_scheme="red",
                        size="3",
                        variant="outline",
                    ),
                ),
                spacing="4",
                align="center",
                width="100%",
                wrap="wrap",
            ),
            padding="6",
            width="100%",
        )
    
    def filters_row():
        """Ligne de filtres avec disposition sobre."""
        return rx.card(
            rx.vstack(
                # Ligne 1 : Barre de recherche (pleine largeur)
                rx.input(
                    placeholder=OOBPageState.t_oob_search_placeholder,
                    value=OOBState.search_query,
                    on_change=OOBState.set_search_query,
                    width="100%",
                    size="3",
                ),
                # Ligne 2 : Date from, Date to, Ship from, Ship to (sur la même ligne, taille alignée au texte)
                rx.hstack(
                    rx.vstack(
                        rx.text(OOBPageState.t_oob_from, size="2", color="gray", weight="medium"),
                        rx.input(
                            type="date",
                            value=OOBState.date_min,
                            on_change=OOBState.set_date_min,
                            size="3",
                        ),
                        spacing="1",
                        align="start",
                    ),
                    rx.vstack(
                        rx.text(OOBPageState.t_oob_to, size="2", color="gray", weight="medium"),
                        rx.input(
                            type="date",
                            value=OOBState.date_max,
                            on_change=OOBState.set_date_max,
                            size="3",
                        ),
                        spacing="1",
                        align="start",
                    ),
                    rx.vstack(
                        rx.text(OOBPageState.t_oob_ship_from, size="2", color="gray", weight="medium"),
                        rx.input(
                            placeholder=OOBPageState.t_oob_ship_from,
                            value=OOBState.ship_from,
                            on_change=OOBState.set_ship_from,
                            size="3",
                        ),
                        spacing="1",
                        align="start",
                    ),
                    rx.vstack(
                        rx.text(OOBPageState.t_oob_ship_to, size="2", color="gray", weight="medium"),
                        rx.input(
                            placeholder=OOBPageState.t_oob_ship_to,
                            value=OOBState.ship_to,
                            on_change=OOBState.set_ship_to,
                            size="3",
                        ),
                        spacing="1",
                        align="start",
                    ),
                    spacing="4",
                    align="start",
                    width="100%",
                ),
                # Ligne 3 : Document type et bouton Filtrer (sur la même ligne, taille alignée au texte)
                rx.vstack(
                    rx.text(OOBPageState.t_oob_document_types, size="2", color="gray", weight="medium"),
                    rx.hstack(
                        rx.popover.root(
                            rx.popover.trigger(
                                rx.button(
                                    OOBPageState.t_oob_select_types,
                                    variant="outline",
                                    size="3",
                                ),
                            ),
                            rx.popover.content(
                                rx.vstack(
                                    rx.checkbox(
                                        OOBPageState.t_oob_select_all,
                                        checked=OOBState.is_all_doc_types_selected,
                                        on_change=OOBState.toggle_all_doc_types,
                                    ),
                                    rx.divider(),
                                    rx.foreach(
                                        OOBState.doc_types_with_state,
                                        lambda doc_type: rx.checkbox(
                                            doc_type["description"],
                                            checked=doc_type["checked"],
                                            on_change=lambda checked: OOBState.toggle_doc_type(doc_type["code"], checked),
                                        ),
                                    ),
                                    spacing="2",
                                    width="100%",
                                ),
                                width="300px",
                            ),
                        ),
                        rx.button(
                            OOBPageState.t_oob_filter,
                            on_click=OOBState.apply_filters,
                            color_scheme="blue",
                            size="3",
                        ),
                        spacing="4",
                        align="start",
                    ),
                    spacing="1",
                    align="start",
                ),
                spacing="4",
                width="100%",
            ),
            padding="6",
            width="100%",
        )
    
    def items_table():
        """Tableau des purchasing items avec rx.table (affichage + tri manuel)."""
        
        def sortable_header(label: str, column_key: str):
            """En-tête de colonne avec tri."""
            is_sorted = OOBState.sort_column == column_key
            sort_icon = rx.cond(
                is_sorted & (OOBState.sort_direction == "asc"),
                rx.text("↑", size="2", color="blue"),
                rx.cond(
                    is_sorted & (OOBState.sort_direction == "desc"),
                    rx.text("↓", size="2", color="blue"),
                    rx.text("⇅", size="2", color="gray"),
                ),
            )
            
            return rx.table.column_header_cell(
                rx.hstack(
                    rx.text(label, size="3"),
                    sort_icon,
                    spacing="1",
                    align="center",
                ),
                on_click=lambda: OOBState.set_sort_column(column_key),
                class_name="cursor-pointer hover:bg-gray-100",
            )
        
        def po_row(item: dict):
            """Ligne d'une PO dans le tableau."""
            return rx.table.row(
                rx.table.cell(rx.text(item["Receipt Elmt"], size="3")),
                rx.table.cell(rx.text(item["Product ID"], size="3")),
                rx.table.cell(rx.text(item["Ship To"], size="3")),
                rx.table.cell(rx.text(item["Ship From"], size="3")),
                rx.table.cell(rx.text(item["Receipt Qty"], size="3")),
                rx.table.cell(rx.text(item["Ordered Qty"], size="3")),
                rx.table.cell(rx.text(item["Requirement Qty"], size="3")),
                rx.table.cell(rx.text(item["Doc Ext"], size="3")),
                rx.table.cell(rx.text(item["Doc Type"], size="3")),
                rx.table.cell(rx.text(item["Receipt Date"], size="3")),
                rx.table.cell(rx.text(item["Delivery Date"], size="3")),
                rx.table.cell(rx.text(item["Requirement Date"], size="3")),
                on_click=lambda: OOBState.select_po_from_row(item),
                class_name="cursor-pointer hover:bg-gray-100",
            )
        
        return rx.card(
            rx.cond(
                OOBState.has_data_table_items,
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            sortable_header("Receipt Elmt", "Receipt Elmt"),
                            sortable_header(OOBPageState.t_oob_product_id, "Product ID"),
                            sortable_header(OOBPageState.t_oob_ship_to_location, "Ship To"),
                            sortable_header(OOBPageState.t_oob_ship_from_location, "Ship From"),
                            sortable_header(OOBPageState.t_oob_receipt_quantity, "Receipt Qty"),
                            sortable_header(OOBPageState.t_oob_ordered_quantity, "Ordered Qty"),
                            sortable_header(OOBPageState.t_requirement_qty, "Requirement Qty"),
                            sortable_header(OOBPageState.t_oob_doc_ext, "Doc Ext"),
                            sortable_header(OOBPageState.t_oob_doc_type, "Doc Type"),
                            sortable_header(OOBPageState.t_oob_receipt_date, "Receipt Date"),
                            sortable_header(OOBPageState.t_oob_delivery_date, "Delivery Date"),
                            sortable_header(OOBPageState.t_oob_requirement_date, "Requirement Date"),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(
                            OOBState.data_table_items,
                            po_row,
                        ),
                    ),
                    width="100%",
                    variant="surface",
                ),
                rx.cond(
                    OOBState.loading,
                    rx.center(
                        rx.vstack(
                            rx.text("⏳", size="8"),
                            rx.text("Chargement...", size="4", color="gray", weight="medium"),
                            spacing="2",
                        ),
                        padding="8",
                    ),
                    rx.center(
                        rx.vstack(
                            rx.text("📭", size="8"),
                            rx.text(OOBPageState.t_oob_no_items, size="4", color="gray", weight="medium"),
                            spacing="2",
                        ),
                        padding="8",
                    ),
                ),
            ),
            padding="6",
            width="100%",
        )
    
    def comment_form():
        """Formulaire de commentaire et thread."""
        return rx.card(
            rx.vstack(
                rx.heading(OOBPageState.t_oob_line_details, size="6", weight="bold", margin_bottom="2"),
                rx.divider(),
                # PO Doc Ext (readonly)
                rx.vstack(
                    rx.text(OOBPageState.t_oob_doc_ext, size="2", color="gray", weight="medium"),
                    rx.input(
                        value=OOBState.selected_po,
                        is_read_only=True,
                        size="3",
                        placeholder=OOBPageState.t_oob_select_po,
                        width="100%",
                    ),
                    spacing="1",
                    width="100%",
                ),
                # Commentaire
                rx.vstack(
                    rx.text(OOBPageState.t_oob_add_comment, size="2", color="gray", weight="medium"),
                    rx.text_area(
                        placeholder=OOBPageState.t_oob_comment_placeholder,
                        value=OOBState.comment_text,
                        on_change=OOBState.set_comment_text,
                        rows="4",
                        size="3",
                        width="100%",
                    ),
                    rx.button(
                        OOBPageState.t_oob_send,
                        on_click=lambda: OOBState.submit_comment(OOBState.comment_text),
                        color_scheme="blue",
                        size="3",
                        width="100%",
                    ),
                    spacing="2",
                    width="100%",
                ),
                rx.divider(),
                # Thread de commentaires
                rx.vstack(
                    rx.heading(OOBPageState.t_oob_comments, size="5", weight="bold"),
                    rx.cond(
                        OOBState.selected_po,
                            rx.cond(
                            OOBState.has_comments,
                            rx.box(
                                rx.vstack(
                                    rx.foreach(
                                        OOBState.comments,
                                        lambda comment: rx.box(
                                            rx.vstack(
                                                # En-tête avec nom d'utilisateur et date de publication en haut à droite
                                                rx.hstack(
                                                    rx.text(
                                                        comment["username_display"],
                                                        weight="bold",
                                                        size="3",
                                                        color="gray.800",
                                                    ),
                                                    rx.spacer(),
                                                    rx.hstack(
                                                        rx.text(
                                                            OOBPageState.t_oob_posted_on,
                                                            size="1",
                                                            color="gray.500",
                                                            weight="medium",
                                                        ),
                                                        rx.text(
                                                            comment["created_at"],
                                                            size="1",
                                                            color="gray.600",
                                                        ),
                                                        spacing="1",
                                                    ),
                                                    spacing="3",
                                                    width="100%",
                                                    align="center",
                                                ),
                                                # Afficher le texte du commentaire ou le formulaire d'édition
                                                rx.cond(
                                                    OOBState.editing_comment_id == comment["id"],
                                                    # Mode édition
                                                    rx.vstack(
                                                        rx.text_area(
                                                            value=OOBState.editing_comment_text,
                                                            on_change=OOBState.set_editing_comment_text,
                                                            rows="3",
                                                            size="3",
                                                            width="100%",
                                                        ),
                                                        rx.hstack(
                                                            rx.button(
                                                                rx.hstack(
                                                                    rx.text("✓", size="3", weight="bold"),
                                                                    rx.text(
                                                                        OOBPageState.t_oob_save,
                                                                        size="2",
                                                                    ),
                                                                    spacing="2",
                                                                    align="center",
                                                                ),
                                                                on_click=lambda: OOBState.update_comment(comment["id"]),
                                                                color_scheme="green",
                                                                size="2",
                                                                padding_x="4",
                                                                padding_y="2",
                                                            ),
                                                            rx.button(
                                                                rx.hstack(
                                                                    rx.text("✕", size="3", weight="bold"),
                                                                    rx.text(
                                                                        OOBPageState.t_oob_cancel,
                                                                        size="2",
                                                                    ),
                                                                    spacing="2",
                                                                    align="center",
                                                                ),
                                                                on_click=OOBState.cancel_edit_comment,
                                                                variant="outline",
                                                                size="2",
                                                                padding_x="4",
                                                                padding_y="2",
                                                            ),
                                                            spacing="2",
                                                            width="100%",
                                                            justify="end",
                                                        ),
                                                        spacing="2",
                                                        width="100%",
                                                    ),
                                                    # Mode affichage
                                                    rx.text(
                                                        comment["comment"],
                                                        size="3",
                                                        line_height="1.6",
                                                        margin_top="2",
                                                        padding_y="2",
                                                    ),
                                                ),
                                                # Ligne du bas : date de modification + boutons d'action
                                                rx.hstack(
                                                    # Date de modification à gauche
                                                    rx.cond(
                                                        comment["updated_at"],
                                                        rx.hstack(
                                                            rx.text(
                                                                OOBPageState.t_oob_modified_on,
                                                                size="1",
                                                                color="gray.300",
                                                            ),
                                                            rx.text(
                                                                comment["updated_at"],
                                                                size="1",
                                                                color="gray.300",
                                                            ),
                                                            spacing="1",
                                                        ),
                                                    ),
                                                    rx.spacer(),
                                                    # Boutons d'action (seulement si propriétaire et pas en mode édition)
                                                    rx.cond(
                                                        (OOBState.editing_comment_id != comment["id"]) & OOBState.is_authenticated & (comment["username"] == OOBState.current_user_email),
                                                        rx.hstack(
                                                            rx.button(
                                                                rx.hstack(
                                                                    rx.text("✏️", size="2"),
                                                                    rx.text(
                                                                        OOBPageState.t_oob_edit,
                                                                        size="2",
                                                                    ),
                                                                    spacing="1",
                                                                    align="center",
                                                                ),
                                                                on_click=lambda: OOBState.start_edit_comment(comment["id"]),
                                                                variant="soft",
                                                                size="2",
                                                                color_scheme="blue",
                                                                padding_x="3",
                                                                padding_y="2",
                                                            ),
                                                            rx.button(
                                                                rx.hstack(
                                                                    rx.text("🗑️", size="2"),
                                                                    rx.text(
                                                                        OOBPageState.t_oob_delete,
                                                                        size="2",
                                                                    ),
                                                                    spacing="1",
                                                                    align="center",
                                                                ),
                                                                on_click=lambda: OOBState.delete_comment(comment["id"]),
                                                                variant="soft",
                                                                size="2",
                                                                color_scheme="red",
                                                                padding_x="3",
                                                                padding_y="2",
                                                            ),
                                                            spacing="2",
                                                        ),
                                                    ),
                                                    spacing="3",
                                                    width="100%",
                                                    align="center",
                                                    margin_top="3",
                                                ),
                                                spacing="2",
                                                width="100%",
                                            ),
                                            padding="10",
                                            padding_x="12",
                                            padding_y="10",
                                            margin_bottom="8",
                                            background_color=comment["user_color"],
                                            border_radius="8px",
                                            width="100%",
                                            transition="all 0.2s ease",
                                            _hover={
                                                "box_shadow": "0 4px 12px rgba(0,0,0,0.15)",
                                            },
                                        ),
                                    ),
                                    spacing="2",
                                    width="100%",
                                    padding="8",
                                ),
                                max_height="500px",
                                overflow_y="auto",
                                overflow_x="hidden",
                                width="100%",
                                padding="8",
                                padding_bottom="12",
                            ),
                            rx.center(
                                rx.vstack(
                                    rx.text("💬", size="6"),
                                    rx.text(OOBPageState.t_oob_no_comments, size="3", color="gray"),
                                    spacing="2",
                                ),
                                padding="6",
                            ),
                        ),
                        rx.center(
                            rx.vstack(
                                rx.text("👆", size="6"),
                                rx.text(OOBPageState.t_oob_select_po, size="3", color="gray"),
                                spacing="2",
                            ),
                            padding="6",
                        ),
                    ),
                    spacing="2",
                    width="100%",
                ),
                spacing="4",
                width="100%",
            ),
            padding="6",
            width="100%",
            height="100%",
            overflow_x="hidden",
        )
    
    content = rx.vstack(
        header(),
        filters_row(),
        rx.hstack(
            # Tableau à gauche
            rx.box(
                items_table(),
                flex="1",
                overflow_x="auto",
            ),
            # Formulaire à droite - sticky pour suivre le scroll
            rx.box(
                comment_form(),
                width="450px",
                position="sticky",
                top="20px",
                align_self="start",
                max_height="calc(100vh - 40px)",
                overflow_y="auto",
            ),
            spacing="6",
            width="100%",
            align="start",
        ),
        spacing="6",
        width="100%",
        padding="6",
    )
    
    # Vérifier l'authentification et l'accès à l'application
    def access_denied_content():
        """Contenu affiché lorsque l'accès est refusé."""
        return layout(
            access_denied_callout(
                "Accès refusé",
                "Vous devez être connecté et avoir accès à l'application OOB pour voir cette page.",
                "Retour à l'accueil",
                "/home",
            )
        )
    
    return rx.fragment(
        # Initialiser + charger les données uniquement quand on arrive sur la page OOB
        rx.cond(
            OOBState.is_authenticated,
            rx.box(on_mount=OOBState.on_page_mount),
        ),
        # Rediriger si non authentifié
        rx.cond(
            ~OOBState.is_authenticated,
            rx.box(
                on_mount=rx.redirect("/")
            ),
        ),
        # Afficher le contenu ou le message d'accès refusé
        rx.cond(
            OOBState.is_authenticated,
            rx.cond(
                # Vérifier que l'utilisateur a accès à l'application OOB
                # OOBState vérifie l'accès dans on_mount et met à jour has_oob_access
                OOBState.has_oob_access,
                layout(content),
                access_denied_content(),
            ),
            access_denied_content(),
        ),
    )









