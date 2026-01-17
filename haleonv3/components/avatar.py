import reflex as rx


class AvatarState(rx.State):
    show_popup: bool = False

    def toggle_popup(self):
        self.show_popup = not self.show_popup

    def close_popup(self):
        self.show_popup = False


def avatar() -> rx.Component:
    return rx.box(
        rx.button(
            "User",
            on_click=AvatarState.toggle_popup,
            size="2",
        ),
        rx.cond(
            AvatarState.show_popup,
            rx.box(
                rx.text("Profil utilisateur (placeholder)"),
                rx.button("Close", on_click=AvatarState.close_popup, size="2"),
                position="fixed",
                top="60px",
                right="16px",
                background="white",
                border="1px solid #ddd",
                padding="12px",
                border_radius="8px",
                box_shadow="0 4px 12px rgba(0, 0, 0, 0.1)",
                z_index="1000",
            ),
        ),
    )
