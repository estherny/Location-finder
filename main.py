import requests
import json
import math
import logging
from functools import partial
from multiprocessing import Pool
import os
from dotenv import load_dotenv

# Set up debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
API_KEY = os.getenv('GOOGLE_API_KEY', 'AIzaSyBSSMOifIZfbsxoB02RaWI1YOpIw78CXxM')

class LocationFinder:
    def __init__(self):
        self.geocoding_url = "https://maps.googleapis.com/maps/api/geocode/json"
        self.places_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        self.locations = []

    def get_coordinates(self, address):
        """Convert address to latitude and longitude with debug output"""
        params = {
            'address': address,
            'key': API_KEY
        }
        try:
            response = requests.get(self.geocoding_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            logger.debug(f"Geocoding API response: {json.dumps(data, indent=2)}")
            
            if data['status'] == 'OK':
                location = data['results'][0]['geometry']['location']
                logger.info(f"Resolved coordinates for '{address}': {location}")
                return location['lat'], location['lng']
            else:
                logger.error(f"Geocoding failed for '{address}': {data['status']}")
        except Exception as e:
            logger.error(f"Geocoding error: {str(e)}")
        return None, None

    def search_places(self, location_type, lat, lng, radius=15000):
        """Search for places with debug output and larger default radius"""
        params = {
            'location': f"{lat},{lng}",
            'radius': radius,
            'type': location_type,
            'key': API_KEY
        }
        try:
            response = requests.get(self.places_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            logger.debug(f"Places API response: {json.dumps(data, indent=2)}")
            
            if data['status'] == 'OK':
                logger.info(f"Found {len(data['results'])} places of type '{location_type}'")
                return data['results']
            else:
                logger.error(f"Places API error: {data['status']}")
        except Exception as e:
            logger.error(f"Places search error: {str(e)}")
        return []

    def haversine_distance(self, lat1, lon1, lat2, lon2):
        """Calculate the great-circle distance between two points on Earth"""
        # Convert degrees to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Radius of Earth in kilometers
        r = 6371
        return c * r

    def calculate_distances(self, user_lat, user_lng, places):
        """Calculate distances for all places from user's location"""
        results = []
        for place in places:
            if 'geometry' in place and 'location' in place['geometry']:
                place_lat = place['geometry']['location']['lat']
                place_lng = place['geometry']['location']['lng']
                distance = self.haversine_distance(user_lat, user_lng, place_lat, place_lng)
                
                results.append({
                    'name': place.get('name', 'Unknown'),
                    'address': place.get('vicinity', 'Address not available'),
                    'distance_km': round(distance, 2),
                    'rating': place.get('rating', 'No rating'),
                    'types': ', '.join(place.get('types', [])),
                    'coordinates': (place_lat, place_lng)
                })
        return results

    def find_nearest_locations(self, address, location_type):
        """Main function with forced fresh data and improved error handling"""
        logger.info(f"\nSearching for '{location_type}' near '{address}'")
        
        # Get coordinates with verification
        user_lat, user_lng = self.get_coordinates(address)
        if user_lat is None or user_lng is None:
            logger.error("Failed to resolve address coordinates")
            return []
        
        # Get fresh places data
        places = self.search_places(location_type, user_lat, user_lng)
        if not places:
            logger.warning("No locations found for the given type")
            return []
        
        # Calculate distances
        results = self.calculate_distances(user_lat, user_lng, places)
        
        # Sort by distance
        return sorted(results, key=lambda x: x['distance_km'])

def main():
    finder = LocationFinder()
    
    print("=== Nearest Location Finder ===")
    print("Note: This uses live Google API data - no caching")
    
    while True:
        try:
            address = input("\nEnter address (or 'quit' to exit): ").strip()
            if address.lower() == 'quit':
                break
                
            location_type = input("Location type (restaurant, gas_station, etc.): ").strip().lower()
            
            results = finder.find_nearest_locations(address, location_type)
            
            if results:
                print(f"\n🏆 Top {min(10, len(results))} Results Near '{address}':")
                for i, loc in enumerate(results[:10], 1):
                    print(f"\n{i}. {loc['name']} ({loc['distance_km']} km)")
                    print(f"   📍 {loc['address']}")
                    print(f"   ⭐ Rating: {loc['rating']}")
                    print(f"   🏷️ Type: {loc['types']}")
                    print(f"   🌐 Coordinates: {loc['coordinates']}")
            else:
                print("No results found. Try a different location or type.")
                
        except KeyboardInterrupt:
            print("\nOperation cancelled by user")
            break
        except Exception as e:
            print(f"\n⚠️ Error occurred: {str(e)}")
            logger.exception("Unexpected error")

if __name__ == "__main__":
    main()