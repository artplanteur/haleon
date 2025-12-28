"""Composant Avatar avec popup pour afficher les informations utilisateur."""

import reflex as rx
from haleon.auth.auth_state import AuthState


class AvatarState(rx.State):
    """État pour gérer l'affichage du popup avatar."""
    show_popup: bool = False
    timer_tick: int = 0  # Pour forcer la mise à jour du timer
    
    def toggle_popup(self):
        """Ouvre/ferme le popup."""
        self.show_popup = not self.show_popup
        if self.show_popup:
            # Démarrer le timer quand le popup s'ouvre
            return AvatarState.start_timer()
    
    def close_popup(self):
        """Ferme le popup."""
        self.show_popup = False
        return AvatarState.stop_timer()
    
    def set_show_popup(self, is_open: bool):
        """Met à jour l'état d'ouverture du popup."""
        self.show_popup = is_open
        if not is_open:
            return AvatarState.stop_timer()
    
    def start_timer(self):
        """Démarre le timer pour mettre à jour le compte à rebours."""
        return rx.call_script("""
            if (window.avatarTimer) clearInterval(window.avatarTimer);
            window.avatarTimer = setInterval(() => {
                // Forcer une mise à jour en déclenchant un événement
                window.dispatchEvent(new CustomEvent('avatar-timer-tick'));
            }, 1000);
        """)
    
    def stop_timer(self):
        """Arrête le timer."""
        return rx.call_script("""
            if (window.avatarTimer) {
                clearInterval(window.avatarTimer);
                window.avatarTimer = null;
            }
        """)
    
    def update_timer(self):
        """Met à jour le timer (appelé par l'événement JavaScript)."""
        self.timer_tick += 1


def avatar() -> rx.Component:
    """Composant avatar avec initiales et popup d'informations selon README ligne 61."""
    return rx.box(
        # Avatar cliquable - enveloppé dans un box pour gérer le clic
        rx.box(
            rx.avatar(
                fallback=AuthState.get_user_initials,
                size="3",
                radius="full",
                cursor="pointer",
                class_name="avatar-modern",
            ),
            on_click=AvatarState.toggle_popup,
            cursor="pointer",
        ),
        # Popup modal au centre de l'écran
        rx.cond(
            AvatarState.show_popup,
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
                    on_click=AvatarState.close_popup,
                    class_name="popup-overlay",
                ),
                # Contenu du popup au centre
                rx.box(
                    rx.vstack(
                        # Padding interne pour le contenu
                        # Header
                        rx.hstack(
                            rx.heading("Informations utilisateur", size="6"),
                            rx.spacer(),
                            rx.button(
                                "✕",
                                variant="ghost",
                                size="2",
                                on_click=AvatarState.close_popup,
                            ),
                            width="100%",
                            align="center",
                            padding_bottom="2",
                            padding_x="0",
                        ),
                        rx.divider(),
                        # Informations utilisateur
                        rx.vstack(
                            rx.hstack(
                                rx.text("Email:", weight="bold", size="3"),
                                rx.text(
                                    rx.cond(
                                        AuthState.current_user,
                                        AuthState.current_user.email,
                                        "N/A",
                                    ),
                                    size="3",
                                ),
                                spacing="3",
                                width="100%",
                                padding_y="2",
                            ),
                            rx.hstack(
                                rx.text("Prénom:", weight="bold", size="3"),
                                rx.text(
                                    rx.cond(
                                        AuthState.current_user,
                                        rx.cond(
                                            AuthState.current_user.first_name,
                                            AuthState.current_user.first_name,
                                            "N/A",
                                        ),
                                        "N/A",
                                    ),
                                    size="3",
                                ),
                                spacing="3",
                                width="100%",
                                padding_y="2",
                            ),
                            rx.hstack(
                                rx.text("Nom:", weight="bold", size="3"),
                                rx.text(
                                    rx.cond(
                                        AuthState.current_user,
                                        rx.cond(
                                            AuthState.current_user.family_name,
                                            AuthState.current_user.family_name,
                                            "N/A",
                                        ),
                                        "N/A",
                                    ),
                                    size="3",
                                ),
                                spacing="3",
                                width="100%",
                                padding_y="2",
                            ),
                            rx.hstack(
                                rx.text("Pays:", weight="bold", size="3"),
                                rx.hstack(
                                    rx.text(
                                        rx.cond(
                                            AuthState.current_user,
                                            rx.cond(
                                                AuthState.current_user.country,
                                                AuthState.current_user.country,
                                                "N/A",
                                            ),
                                            "N/A",
                                        ),
                                        size="3",
                                    ),
                                    rx.cond(
                                        AuthState.current_user,
                                        rx.cond(
                                            AuthState.current_user.country,
                                            rx.image(
                                                src="https://flagsapi.com/" + AuthState.current_user.country + "/shiny/32.png",
                                                alt="Country flag",
                                                width="20px",
                                                height="20px",
                                                border_radius="4px",
                                                margin_left="4px",
                                            ),
                                            rx.box(),
                                        ),
                                        rx.box(),
                                    ),
                                    spacing="2",
                                    align="center",
                                ),
                                spacing="3",
                                width="100%",
                                padding_y="2",
                            ),
                            rx.divider(),
                            # Section Permissions/Statut - Badges uniquement si présents
                            rx.cond(
                                AuthState.is_active | AuthState.is_validated | AuthState.is_admin,
                                rx.hstack(
                                    rx.cond(
                                        AuthState.is_active,
                                        rx.badge(
                                            "Actif",
                                            color_scheme="green",
                                            size="2",
                                        ),
                                        rx.box(),
                                    ),
                                    rx.cond(
                                        AuthState.is_validated,
                                        rx.badge(
                                            "Validé",
                                            color_scheme="blue",
                                            size="2",
                                        ),
                                        rx.box(),
                                    ),
                                    rx.cond(
                                        AuthState.is_admin,
                                        rx.badge(
                                            "Admin",
                                            color_scheme="purple",
                                            size="2",
                                        ),
                                        rx.box(),
                                    ),
                                    spacing="2",
                                    width="100%",
                                    padding_y="2",
                                ),
                                rx.box(),
                            ),
                            rx.divider(),
                            # Temps restant de session (compte à rebours live) - selon README
                            rx.hstack(
                                rx.text("Temps restant:", weight="bold", size="3"),
                                rx.text(
                                    AuthState.get_session_remaining_formatted,
                                    size="4",
                                    weight="bold",
                                    color="blue.600",
                                    id="session-timer-display",
                                    class_name="session-countdown",
                                ),
                                spacing="3",
                                width="100%",
                                padding_y="2",
                            ),
                            # Timer JavaScript pour mettre à jour le compte à rebours en temps réel
                            rx.box(
                                on_mount=rx.call_script("""
                                    if (window.avatarTimer) clearInterval(window.avatarTimer);
                                    const display = document.getElementById('session-timer-display');
                                    if (display) {
                                        const initialText = display.textContent;
                                        let [minutes, seconds] = initialText.split(':').map(Number);
                                        let totalSeconds = minutes * 60 + seconds;
                                        
                                        function updateTimer() {
                                            if (totalSeconds > 0) {
                                                totalSeconds--;
                                                const m = Math.floor(totalSeconds / 60);
                                                const s = totalSeconds % 60;
                                                display.textContent = String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');
                                            } else {
                                                display.textContent = '00:00';
                                                if (window.avatarTimer) {
                                                    clearInterval(window.avatarTimer);
                                                    window.avatarTimer = null;
                                                }
                                            }
                                        }
                                        updateTimer();
                                        window.avatarTimer = setInterval(updateTimer, 1000);
                                    }
                                """),
                                on_unmount=rx.call_script("""
                                    if (window.avatarTimer) {
                                        clearInterval(window.avatarTimer);
                                        window.avatarTimer = null;
                                    }
                                """),
                                display="none",
                            ),
                            spacing="2",
                            width="100%",
                            padding_y="2",
                        ),
                        rx.divider(),
                        # Bouton de déconnexion
                        rx.button(
                            "Déconnexion",
                            on_click=[
                                AvatarState.close_popup,
                                AuthState.logout,
                                AuthState.redirect_to_login,
                            ],
                            color_scheme="red",
                            width="100%",
                            margin_top="2",
                        ),
                        spacing="4",
                        width="100%",
                        padding_x="0",
                    ),
                    position="fixed",
                    top="50%",
                    left="50%",
                    transform="translate(-50%, -50%)",
                    z_index="9999",
                    class_name="popup-content",
                    width="480px",
                    max_width="90vw",
                    bg=rx.color_mode_cond("white", "#0f172a"),
                    padding="32px",
                ),
            ),
        ),
        position="relative",
    )
