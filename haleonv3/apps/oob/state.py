import reflex as rx


class OOBState(rx.State):
    rows: list[dict] = [
        {"po": "PO-001", "vendor": "V001", "amount": 1200, "status": "Open"},
        {"po": "PO-002", "vendor": "V002", "amount": 800, "status": "Closed"},
        {"po": "PO-003", "vendor": "V001", "amount": 500, "status": "Open"},
    ]

    search: str = ""
    sort_key: str = "po"
    sort_desc: bool = False

    def set_search(self, value: str):
        self.search = value

    def toggle_sort(self, key: str):
        if self.sort_key == key:
            self.sort_desc = not self.sort_desc
        else:
            self.sort_key = key
            self.sort_desc = False

    @rx.var
    def filtered_rows(self) -> list[dict]:
        text = (self.search or "").lower().strip()
        data = self.rows

        if text:
            data = [
                r for r in data
                if text in str(r.get("po", "")).lower()
                or text in str(r.get("vendor", "")).lower()
                or text in str(r.get("status", "")).lower()
            ]

        return sorted(
            data,
            key=lambda r: r.get(self.sort_key),
            reverse=self.sort_desc,
        )
