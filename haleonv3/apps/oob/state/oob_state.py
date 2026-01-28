import asyncio
import pandas as pd
import reflex as rx


class OOBState(rx.State):
    is_loading: bool = False
    progress: int = 0
    rows: list[dict] = []

    @staticmethod
    def _fake_api_dataframe(total_rows: int = 800) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "po": [f"PO-{idx:05d}" for idx in range(1, total_rows + 1)],
                "vendor": [f"V{(idx % 7) + 1:03d}" for idx in range(1, total_rows + 1)],
                "amount": [500 + (idx * 37) % 5000 for idx in range(1, total_rows + 1)],
                "status": ["Open" if idx % 3 else "Closed" for idx in range(1, total_rows + 1)],
            }
        )

    @rx.event(background=True)
    async def load_oob_data(self):
        total_steps = 30
        async with self:
            self.is_loading = True
            self.progress = 0
            self.rows = []

        for step in range(1, total_steps + 1):
            await asyncio.sleep(0.2)
            async with self:
                self.progress = int(step / total_steps * 100)

        df = self._fake_api_dataframe()
        async with self:
            self.rows = df.to_dict("records")
            self.is_loading = False
