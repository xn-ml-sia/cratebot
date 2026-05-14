import csv
import os
from datetime import datetime

class CSVExporter:
    def __init__(self, export_dir="exports"):
        self.export_dir = export_dir
        self._ensure_dir()

    def _ensure_dir(self):
        os.makedirs(self.export_dir, exist_ok=True)

    def export_session(self, records):
        if not records:
            raise ValueError("No records available to export.")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"discogs_import_{timestamp}.csv"
        filepath = os.path.join(self.export_dir, filename)
        fieldnames = ["release_id", "price", "media_condition", "sleeve_condition", "comments_accept_offer", "location", "external_id", "artist", "title", "year", "verdict", "reason"]
        with open(filepath, mode='w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for record in records:
                filtered_row = {k: record.get(k, "") for k in fieldnames}
                writer.writerow(filtered_row)
        return filepath

    def clear_exports(self):
        for file in os.listdir(self.export_dir):
            os.remove(os.path.join(self.export_dir, file))
