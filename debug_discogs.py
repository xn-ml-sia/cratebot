import discogs_client
import os
from dotenv import load_dotenv

load_dotenv()

def test_discogs_pipeline(artist, album):
    print(f"\n--- 🔍 STARTING DATA VERIFICATION ---")
    print(f"Target: {artist} - {album}")
    print(f"-------------------------------------\n")

    token = os.getenv("DISCOGS_TOKEN")
    if not token:
        print("❌ ERROR: DISCOGS_TOKEN not found in .env")
        return

    # Use the client as the bot does
    client = discogs_client.Client('VinylGatekeeper/1.0', user_token=token)

    try:
        # 1. SEARCH PHASE
        print(f"Step 1: Searching Discogs for '{artist} {album}'...")
        query = f"artist:{artist} AND release:{album}"
        results = client.search(query, type='release')
        
        if not results:
            print("❌ FAIL: Search returned zero results. Trying broad search...")
            results = client.search(f"{artist} {album}", type='release')
            if not results:
                print("❌ FAIL: No results found even with broad search.")
                return

        target = results[0]
        release_id = target.id
        print(f"✅ SUCCESS: Found Release: '{target.title}' (ID: {release_id})")

        # 2. HYDRATION PHASE
        print(f"\nStep 2: Hydrating full object for ID {release_id}...")
        # This is the critical part that has been failing
        full_release = client.get_release(release_id)
        print(f"✅ SUCCESS: Hydrated '{full_release.title}'")

        # 3. MARKETPLACE PHASE
        print(f"\nStep 3: Accessing marketplace_listings...")
        if hasattr(full_release, 'marketplace_listings'):
            listings = full_release.marketplace_listings
            print(f"✅ SUCCESS: Found {len(listings)} listings in 'marketplace_listings' attribute.")
            
            if len(listings) > 0:
                prices = []
                for i, l in enumerate(listings):
                    try:
                        # The library usually provides price as a float or string
                        p = float(l.price)
                        if p > 0:
                            prices.append(p)
                            print(f"   [Listing {i}] Price: ${p:.2f}")
                    except Exception as e:
                        print(f"   [Listing {i}] Error parsing price: {e}")

                if prices:
                    print(f"\n--- 💰 FINAL DATA ---")
                    print(f"Lowest: ${min(prices):.2f}")
                    print(f"Median: ${sum(prices)/len(prices):.2f}")
                    print(f"----------------------")
                else:
                    print("❌ FAIL: Listings exist, but no valid prices were found in them.")
            else:
                print("❌ FAIL: 'marketplace_listings' is an empty list [].")
        else:
            print("❌ FAIL: Object does NOT have 'marketplace_listings' attribute.")
            print(f"Available attributes on this object: {dir(full_release)}")

    except Exception as e:
        print(f"\n❌ CRITICAL ERROR during execution:")
        print(f"Type: {type(e).__name__}")
        print(f"Message: {str(e)}")

if __name__ == "__main__":
    # Testing the specific record you identified
    test_discogs_pipeline("Simon Baker", "Plastik 2014")
