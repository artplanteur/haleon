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
        rx.button(
            rx.avatar(
                name=AuthState.initials,
                size="3",
                radius="full",
            ),
            on_click=AvatarState.open_popup,
            variant="ghost",
            padding="0",
        ),
        rx.cond(
            AvatarState.show_popup,
            rx.box(
                rx.box(
                    rx.heading("Profile", size="4"),
                    rx.text(f"Name: {AuthState.given_name} {AuthState.family_name}"),
                    rx.text(f"Email: {AuthState.email}"),
                    rx.text(f"Country: {AuthState.country}"),
                    rx.button("Close", on_click=AvatarState.close_popup, size="2"),
                    background="white",
                    padding="16px",
                    border_radius="8px",
                    border="1px solid #ddd",
                    min_width="260px",
                ),
                position="fixed",
                inset="0",
                display="flex",
                align_items="center",
                justify_content="center",
                background="rgba(0,0,0,0.3)",
                z_index="1000",
            ),
        ),
    )
