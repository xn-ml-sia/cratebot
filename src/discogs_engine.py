import discogs_client
import os
import requests
from dotenv import load_dotenv

load_dotenv()

class DiscogsEngine:
    def __init__(self):
        self.token = os.getenv("DISCOGS_TOKEN")
        if not self.token:
            raise ValueError("DISCOGS_TOKEN not found in environment.")
        
        self.client = discogs_client.Client('VinylGatekeeper/1.0', user_token=self.token)
        self.base_url = "https://api.discogs.com"
        self.headers = {
            "Authorization": f"Discogs token={self.token}",
            "User-Agent": "VinylGatekeeper/1.0"
        }

    def search_release(self, artist: str, album: str):
        """
        Searches for a specific release and returns metadata + NATIVE Discogs marketplace stats.
        """
        query_strict = f"artist:{artist} AND release:{album}"
        query_broad = f"{artist} {album}"

        try:
            # 1. SEARCH (Using library to find the ID)
            results = self.client.search(query_strict, type='release')
            if not results:
                results = self.client.search(query_broad, type='release')

            if not results:
                return {"error": f"No release found for '{artist} - {album}'"}

            release_id = results[0].id
            print(f"DEBUG: Found ID {release_id}. Fetching full release via direct API...")

            # 2. FETCH FULL RELEASE (The source of truth for native marketplace fields)
            release_url = f"{self.base_url}/releases/{release_id}"
            response = requests.get(release_url, headers=self.headers, timeout=15)
            
            if response.status_code != 200:
                print(f"DEBUG: Release Fetch Error {response.status_code}: {response.text}")
                return {"error": f"Discogs API error ({response.status_code})"}
            
            full_release = response.json()
            print(f"DEBUG: Successfully fetched {full_release.get('title')}")

            # 3. EXTRACT METADATA
            artist_names = []
            if 'artists' in full_release:
                for a in full_release['artists']:
                    artist_names.append(a.get('name', 'Unknown'))
            release_artist = ", ".join(artist_names) if artist_names else "Unknown Artist"

            # 4. NATIVE MARKETPLACE STATS
            # We are pulling directly from the fields you identified: 'lowest_price' and 'num_for_sale'
            lowest_price = full_release.get('lowest_price', 0.0)
            num_for_sale = full_release.get('num_for_sale', 0)

            return {
                "id": release_id,
                "title": full_release.get('title', 'Unknown Title'),
                "artist": release_artist,
                "year": full_release.get('year', 'Unknown'),
                "format": self._get_format(full_release),
                "current_price": lowest_price,
                "available_count": num_for_sale,
                "search_query_used": query_strict if "Strict" in str(results) else query_broad
            }

        except Exception as e:
            print(f"DEBUG: Engine Error: {e}")
            return {"error": f"Discogs error: {str(e)}"}

    def _get_format(self, release_dict):
        fmt = release_dict.get('format', 'Vinyl')
        return ", ".join(fmt) if isinstance(fmt, list) else str(fmt)

if __name__ == "__main__":
    engine = DiscogsEngine()
    print("Discogs Engine initialized.")
