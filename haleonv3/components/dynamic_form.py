from typing import Any

import reflex as rx


FORM_SCHEMAS: dict[str, list[dict[str, Any]]] = {
    "vendor": [
        {"name": "code", "label": "Code", "type": "text", "required": True},
        {"name": "description", "label": "Description", "type": "text"},
        {"name": "portfolio", "label": "Portfolio", "type": "text"},
        {"name": "is_active", "label": "Active", "type": "bool"},
    ],
    "access": [
        {"name": "user_id", "label": "User ID", "type": "number", "required": True},
        {"name": "vendor_id", "label": "Vendor ID", "type": "number", "required": True},
        {
            "name": "access_level",
            "label": "Access",
            "type": "select",
            "options": ["read", "write"],
        },
    ],
}


class DynamicFormState(rx.State):
    form_values: dict[str, dict[str, Any]] = {}
    last_submitted: dict[str, Any] = {}

    def update_field(self, form_id: str, field: str, value: Any):
        current = self.form_values.get(form_id, {})
        self.form_values = {
            **self.form_values,
            form_id: {**current, field: value},
        }

    def submit_form(self, form_id: str):
        data = self.form_values.get(form_id, {})
        self.last_submitted = {"form_id": form_id, "data": data}
        return rx.toast.success("Formulaire envoyé.")


def _render_field(form_id: str, field: dict[str, Any]) -> rx.Component:
    field_name = field.get("name", "")
    label = field.get("label", field_name)
    field_type = field.get("type", "text")
    placeholder = label or field_name

    if field_type == "bool":
        return rx.hstack(
            rx.switch(
                on_change=lambda v, f=field_name: DynamicFormState.update_field(
                    form_id, f, v
                ),
            ),
            rx.text(label),
            spacing="2",
        )

    if field_type == "select":
        return rx.select(
            placeholder=placeholder,
            data=field.get("options", []),
            on_change=lambda v, f=field_name: DynamicFormState.update_field(
                form_id, f, v
            ),
        )

    if field_type == "number":
        return rx.input(
            placeholder=placeholder,
            type_="number",
            on_change=lambda v, f=field_name: DynamicFormState.update_field(
                form_id, f, v
            ),
        )

    return rx.input(
        placeholder=placeholder,
        on_change=lambda v, f=field_name: DynamicFormState.update_field(form_id, f, v),
    )


def dynamic_form(form_id: str, trigger_label: str = "Open form") -> rx.Component:
    schema = FORM_SCHEMAS.get(form_id, [])
    return rx.popover.root(
        rx.popover.trigger(rx.button(trigger_label)),
        rx.popover.content(
            rx.vstack(
                rx.foreach(
                    schema,
                    lambda field: _render_field(form_id, field),
                ),
                rx.button(
                    "Submit",
                    on_click=lambda f=form_id: DynamicFormState.submit_form(f),
                ),
                spacing="3",
                width="320px",
            )
        ),
    )
