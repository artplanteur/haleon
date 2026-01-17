import reflex as rx


def footer() -> rx.Component:
    return rx.box(
        rx.text("(c) 2026 Haleon"),
        padding="0.75rem 1rem",
        border_top="1px solid #eee",
        text_align="center",
        width="100%",
    )
