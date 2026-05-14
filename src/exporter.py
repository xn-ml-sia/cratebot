import csv
import os
from datetime import datetime

class CSVExporter:
    """
    Handles the conversion of session history into downloadable CSV files
    aligned with Discogs Marketplace Import requirements.
    """
    def __init__(self, export_dir="exports"):
        self.export_dir = export_dir
        self._ensure_dir()

    def _ensure_dir(self):
        os.makedirs(self.export_dir, exist_ok=True)

    def export_session(self, records):
        """
        Converts a list of record dictionaries into a CSV file.
        Returns the absolute path to the generated file.
        """
        if not records:
            raise ValueError("No records available to export.")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"discogs_import_{timestamp}.csv"
        filepath = os.path.join(self.export_dir, filename)

        # Reordered to match Discogs Import requirements as closely as possible
        # Primary focus: release_id, price, media_condition
        fieldnames = [
            "release_id",
            "price",
            "media_condition",
            "sleeve_condition",
            "comments_accept_offer",
            "location",
            "external_id",
            # Metadata columns (for human reference in the same file)
            "artist",
            "title",
            "year",
            "verdict",
            "reason"
        ]

        try:
            with open(filepath, mode='w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for record in records:
                    # Create a filtered row that only contains the requested fieldnames
                    filtered_row = {k: record.get(k, "") for k in fieldnames}
                    writer.writerow(filtered_row)
            
            return filepath
        except Exception as e:
            raise IOError(f"Failed to write CSV: {e}")

    def clear_exports(self):
        """Removes all files in the export directory."""
        for file in os.listdir(self.export_dir):
            file_path = os.path.join(self.export_dir, file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(f"Error deleting {file_path}: {e}")
