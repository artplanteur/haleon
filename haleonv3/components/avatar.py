import reflex as rx
from haleonv3.state.auth_state import AuthState


class AvatarState(rx.State):
    show_popup: bool = False

    def open_popup(self):
        self.show_popup = True

    def close_popup(self):
        self.show_popup = False


def avatar() -> rx.Component:
    return rx.box(
        rx.box(
            rx.avatar(
                fallback=AuthState.initials,
                size="3",
                radius="full",
                cursor="pointer",
            ),
            on_click=AvatarState.open_popup,
            cursor="pointer",
        ),
        rx.cond(
            AvatarState.show_popup,
            rx.box(
                rx.box(
                    position="fixed",
                    top="0",
                    left="0",
                    right="0",
                    bottom="0",
                    background="rgba(0,0,0,0.3)",
                    z_index="9998",
                    on_click=AvatarState.close_popup,
                ),
                rx.box(
                    rx.heading("Profile", size="4"),
                    rx.text(f"Name: {AuthState.given_name} {AuthState.family_name}"),
                    rx.text(f"Email: {AuthState.email}"),
                    rx.text(f"Country: {AuthState.country}"),
                    rx.button(
                        "Disconnect",
                        on_click=[
                            AvatarState.close_popup,
                            AuthState.logout,
                        ],
                        size="2",
                        color_scheme="red",
                    ),
                    background="white",
                    padding="16px",
                    border_radius="8px",
                    border="1px solid #ddd",
                    min_width="260px",
                    position="fixed",
                    top="50%",
                    left="50%",
                    transform="translate(-50%, -50%)",
                    z_index="9999",
                ),
            ),
        ),
    )
