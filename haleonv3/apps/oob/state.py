import reflex as rx


class OOBState(rx.State):
    rows: list[dict] = [
        {"po": "PO-001", "vendor": "V001", "amount": 1200, "status": "Open"},
        {"po": "PO-002", "vendor": "V002", "amount": 800, "status": "Closed"},
        {"po": "PO-003", "vendor": "V001", "amount": 500, "status": "Open"},
    ]
