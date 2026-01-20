import asyncio  # Python async utilities (sleep, async/await support).
import pandas as pd  # Pandas provides the DataFrame structure.
import reflex as rx  # Reflex provides State and event decorators.


class OOBState(rx.State):  # Define a Reflex state class for this page.
    is_loading: bool = False  # True while data loads; drives the UI.
    progress: int = 0  # Integer percent for the progress bar.
    rows: list[dict] = []  # List of dict rows for rx.data_table.

    @staticmethod  # Static method: does not need "self".
    def _fake_api_dataframe(total_rows: int = 2000) -> pd.DataFrame:  # Create fake data.
        return pd.DataFrame(  # pd.DataFrame builds a table from a dict of columns.
            {
                "po": [f"PO-{idx:05d}" for idx in range(1, total_rows + 1)],  # range gives 1..N.
                "vendor": [f"V{(idx % 7) + 1:03d}" for idx in range(1, total_rows + 1)],  # % cycles vendors.
                "amount": [500 + (idx * 37) % 5000 for idx in range(1, total_rows + 1)],  # Simple numbers.
                "status": ["Open" if idx % 3 else "Closed" for idx in range(1, total_rows + 1)],  # Ternary.
            }
        )

    @rx.event(background=True)  # Background task so UI stays responsive.
    async def load_oob_data(self):  # Async function so we can "await".
        total_steps = 40  # Number of progress updates.
        async with self:  # Required by Reflex to safely update state.
            self.is_loading = True  # Start loading.
            self.progress = 0  # Reset progress.
            self.rows = []  # Clear old rows.

        for step in range(1, total_steps + 1):  # Loop steps for progress.
            await asyncio.sleep(0.2)  # Wait 0.2s to simulate work.
            async with self:  # Update state inside the lock.
                self.progress = int(step / total_steps * 100)  # Convert to percent.

        df = self._fake_api_dataframe()  # Call the helper to get a DataFrame.
        async with self:  # Update state safely again.
            self.rows = df.to_dict("records")  # to_dict turns rows into list of dicts.
            self.is_loading = False  # Done loading.
