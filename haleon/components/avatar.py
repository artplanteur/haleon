"""Composant Avatar avec popup pour afficher les informations utilisateur."""

import reflex as rx
from haleon.auth.auth_state import AuthState


class AvatarState(rx.State):
    """État pour gérer l'affichage du popup avatar."""
    show_popup: bool = False
    
    def toggle_popup(self):
        """Ouvre/ferme le popup."""
        self.show_popup = not self.show_popup
    
    def close_popup(self):
        """Ferme le popup."""
        self.show_popup = False
    
    def set_show_popup(self, is_open: bool):
        """Met à jour l'état d'ouverture du popup."""
        self.show_popup = is_open


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
                            rx.heading(AuthState.t_user_info, size="6"),
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
                                rx.text(AuthState.t_email, weight="bold", size="3"),
                                rx.text(
                                    rx.cond(
                                        AuthState.current_user,
                                        AuthState.current_user.email,
                                        AuthState.t_na,
                                    ),
                                    size="3",
                                ),
                                spacing="3",
                                width="100%",
                                padding_y="2",
                            ),
                            rx.hstack(
                                rx.text(AuthState.t_first_name, weight="bold", size="3"),
                                rx.text(
                                    rx.cond(
                                        AuthState.current_user,
                                        rx.cond(
                                            AuthState.current_user.first_name,
                                            AuthState.current_user.first_name,
                                            AuthState.t_na,
                                        ),
                                        AuthState.t_na,
                                    ),
                                    size="3",
                                ),
                                spacing="3",
                                width="100%",
                                padding_y="2",
                            ),
                            rx.hstack(
                                rx.text(AuthState.t_last_name, weight="bold", size="3"),
                                rx.text(
                                    rx.cond(
                                        AuthState.current_user,
                                        rx.cond(
                                            AuthState.current_user.family_name,
                                            AuthState.current_user.family_name,
                                            AuthState.t_na,
                                        ),
                                        AuthState.t_na,
                                    ),
                                    size="3",
                                ),
                                spacing="3",
                                width="100%",
                                padding_y="2",
                            ),
                            rx.hstack(
                                rx.text(AuthState.t_country, weight="bold", size="3"),
                                rx.hstack(
                                    rx.text(
                                        rx.cond(
                                            AuthState.current_user,
                                            rx.cond(
                                                AuthState.current_user.country,
                                                AuthState.current_user.country,
                                                AuthState.t_na,
                                            ),
                                            AuthState.t_na,
                                        ),
                                        size="3",
                                    ),
                                    rx.cond(
                                        AuthState.current_user,
                                        rx.cond(
                                            AuthState.current_user.country,
                                            rx.image(
                                                src="https://flagsapi.com/" + AuthState.current_user.country + "/shiny/32.png",
                                                alt="",
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
                                            AuthState.t_active,
                                            color_scheme="green",
                                            size="2",
                                        ),
                                        rx.box(),
                                    ),
                                    rx.cond(
                                        AuthState.is_validated,
                                        rx.badge(
                                            AuthState.t_validated,
                                            color_scheme="blue",
                                            size="2",
                                        ),
                                        rx.box(),
                                    ),
                                    rx.cond(
                                        AuthState.is_admin,
                                        rx.badge(
                                            AuthState.t_admin,
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
                                rx.text(AuthState.t_remaining_time, weight="bold", size="3"),
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
                                    (function () {
                                      const display = document.getElementById('session-timer-display');
                                      if (!display) return;

                                      // IMPORTANT: le timer doit refléter la session, pas se "reset" quand on rouvre l'avatar.
                                      // On stocke une expiration globale (dans la page) et on ne la réinitialise pas à l'ouverture.
                                      if (!window.haleonSessionExpiryMs) {
                                        const initialText = (display.textContent || "").trim();
                                        let totalSeconds = 0;
                                        const parts = initialText.split(":");
                                        if (parts.length === 2) {
                                          const m = parseInt(parts[0], 10);
                                          const s = parseInt(parts[1], 10);
                                          if (!isNaN(m) && !isNaN(s)) totalSeconds = (m * 60 + s);
                                        }
                                        window.haleonSessionExpiryMs = Date.now() + (totalSeconds * 1000);
                                      }

                                      function fmt(sec) {
                                        const m = Math.floor(sec / 60);
                                        const s = sec % 60;
                                        return String(m).padStart(2, "0") + ":" + String(s).padStart(2, "0");
                                      }

                                      function tick() {
                                        const d = document.getElementById('session-timer-display');
                                        if (!d) return; // popup fermé
                                        const remaining = Math.max(0, Math.floor((window.haleonSessionExpiryMs - Date.now()) / 1000));
                                        d.textContent = fmt(remaining);
                                      }

                                      // Stop any previous interval for the avatar popup, but keep the expiry timestamp.
                                      if (window.avatarTimer) clearInterval(window.avatarTimer);
                                      tick();
                                      window.avatarTimer = setInterval(tick, 1000);
                                    })();
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
                            AuthState.t_logout,
                            on_click=[
                                AvatarState.close_popup,
                                AuthState.logout,
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
