import asyncio  # Standard async utilities.
import pandas as pd  # DataFrame for fake API payload.
import reflex as rx  # Reflex state/events.
# Blank line for readability.
# Blank line for readability.
class OOBState(rx.State):  # OOB page state container.
    is_loading: bool = False  # Whether loading is in progress.
    progress: int = 0  # Progress percentage.
    rows: list[dict] = []  # Table rows to render.
    # Blank line for readability.
    @staticmethod  # Static helper to create fake API data.
    def _fake_api_dataframe(total_rows: int = 2000) -> pd.DataFrame:  # Build DF.
        return pd.DataFrame(  # Build DataFrame from dict.
            {  # Column data.
                "po": [f"PO-{idx:05d}" for idx in range(1, total_rows + 1)],  # PO ids.
                "vendor": [f"V{(idx % 7) + 1:03d}" for idx in range(1, total_rows + 1)],  # Vendors.
                "amount": [500 + (idx * 37) % 5000 for idx in range(1, total_rows + 1)],  # Amounts.
                "status": ["Open" if idx % 3 else "Closed" for idx in range(1, total_rows + 1)],  # Status.
            }  # End dict.
        )  # End DataFrame.
    # Blank line for readability.
    @rx.event(background=True)  # Run in background to avoid blocking UI.
    async def load_oob_data(self):  # Load data and update progress.
        total_steps = 40  # Simulated steps for progress.
        async with self:  # Lock state for updates.
            self.is_loading = True  # Mark loading.
            self.progress = 0  # Reset progress.
            self.rows = []  # Clear rows.
        # Blank line for readability.
        for step in range(1, total_steps + 1):  # Iterate steps.
            await asyncio.sleep(0.2)  # Simulate work.
            async with self:  # Lock state for progress update.
                self.progress = int(step / total_steps * 100)  # Update progress.
        # Blank line for readability.
        df = self._fake_api_dataframe()  # Simulate API response.
        async with self:  # Lock state for final update.
            self.rows = df.to_dict("records")  # Store rows.
            self.is_loading = False  # Mark done.
# End of file.
