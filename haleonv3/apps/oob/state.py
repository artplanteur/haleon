import asyncio  # Provides async utilities like sleep.
import pandas as pd  # DataFrame = table-like data structure.
import reflex as rx  # Reflex State and event decorators.


class OOBState(rx.State):  # State container for the OOB page.
    is_loading: bool = False  # True while loading data.
    progress: int = 0  # Percentage for the progress bar.
    rows: list[dict] = []  # Final rows displayed in the table.

    @staticmethod  # Static helper (no "self" needed).
    def _fake_api_dataframe(total_rows: int = 800) -> pd.DataFrame:  # Fake API response.
        return pd.DataFrame(  # Build a DataFrame from a dict of columns.
            {
                "po": [f"PO-{idx:05d}" for idx in range(1, total_rows + 1)],  # range -> 1..N.
                "vendor": [f"V{(idx % 7) + 1:03d}" for idx in range(1, total_rows + 1)],  # % cycles.
                "amount": [500 + (idx * 37) % 5000 for idx in range(1, total_rows + 1)],  # Numeric.
                "status": ["Open" if idx % 3 else "Closed" for idx in range(1, total_rows + 1)],  # Ternary.
            }
        )

    @rx.event(background=True)  # Background task so UI stays responsive.
    async def load_oob_data(self):  # Simulate API call + update progress.
        total_steps = 30  # Number of progress ticks.
        async with self:  # Required to safely update Reflex state.
            self.is_loading = True  # Show progress UI.
            self.progress = 0  # Reset progress value.
            self.rows = []  # Clear old data.

        for step in range(1, total_steps + 1):  # Loop to simulate work.
            await asyncio.sleep(0.2)  # Wait to mimic API latency.
            async with self:  # Update progress safely.
                self.progress = int(step / total_steps * 100)  # Convert to %.

        df = self._fake_api_dataframe()  # Get DataFrame from "API".
        async with self:  # Final state update.
            self.rows = df.to_dict("records")  # DataFrame -> list of dicts.
            self.is_loading = False  # Hide progress UI.
