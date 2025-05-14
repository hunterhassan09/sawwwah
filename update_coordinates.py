# -*- coding: utf-8 -*-
"""
Script to update university coordinates for map display.
"""
import os
import sys
import requests
import time

# Ensure the app context can be accessed
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.main import app
from src.models import db, University

# Nominatim API for geocoding (OpenStreetMap)
GEOCODING_URL = "https://nominatim.openstreetmap.org/search"

def get_coordinates(city, country):
    """Get latitude and longitude for a city and country using Nominatim API."""
    params = {
        "q": f"{city}, {country}",
        "format": "json",
        "limit": 1
    }
    
    headers = {
        "User-Agent": "UniversityWebsite/1.0"  # Required by Nominatim
    }
    
    try:
        response = requests.get(GEOCODING_URL, params=params, headers=headers)
        data = response.json()
        
        if data and len(data) > 0:
            return float(data[0]["lat"]), float(data[0]["lon"])
        else:
            print(f"No coordinates found for {city}, {country}")
            return None, None
    except Exception as e:
        print(f"Error getting coordinates for {city}, {country}: {e}")
        return None, None

def update_coordinates():
    """Update coordinates for all universities in the database."""
    with app.app_context():
        universities = University.query.all()
        updated_count = 0
        
        for uni in universities:
            if uni.latitude is None or uni.longitude is None:
                print(f"Getting coordinates for {uni.name} ({uni.city}, {uni.country})...")
                lat, lon = get_coordinates(uni.city, uni.country)
                
                if lat and lon:
                    uni.latitude = lat
                    uni.longitude = lon
                    updated_count += 1
                    print(f"Updated coordinates for {uni.name}: {lat}, {lon}")
                
                # Be nice to the API with a small delay
                time.sleep(1)
        
        if updated_count > 0:
            try:
                db.session.commit()
                print(f"Successfully updated coordinates for {updated_count} universities.")
            except Exception as e:
                db.session.rollback()
                print(f"Error committing to database: {e}")
        else:
            print("No universities were updated.")

if __name__ == "__main__":
    update_coordinates()
