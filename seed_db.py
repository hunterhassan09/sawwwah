# -*- coding: utf-8 -*-
"""
Script to parse university data from the extracted text file and populate the database.
"""
import re
import os
import sys

# Ensure the app context can be accessed
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.main import app # Import app to get context
from src.models import db, University

INPUT_FILE = "/home/ubuntu/website_content.txt"

def parse_rating(rating_str):
    """Converts star string to float."""
    if not rating_str:
        return None
    return float(rating_str.count("★"))

def parse_int(value_str):
    """Safely parses an integer."""
    if not value_str:
        return None
    try:
        # Remove non-digit characters like # or %
        cleaned_str = re.sub(r"\D", "", value_str)
        return int(cleaned_str) if cleaned_str else None
    except (ValueError, TypeError):
        return None

def extract_university_data(text_content):
    """Extracts university data blocks from the text content."""
    # Split by the form feed character which seems to delimit universities
    # Also handle potential variations in delimiters or start markers
    raw_blocks = re.split(r"\f(?=[A-Z][a-zA-Z\s\-]+ University)", text_content)

    universities = []
    # Skip the initial content (Table of Contents, etc.)
    start_index = 0
    for i, block in enumerate(raw_blocks):
        if "Cairo University" in block and "Key Information" in block: # Find the first real entry
            start_index = i
            break

    for block in raw_blocks[start_index:]:
        data = {
            "name": None, "certified": False, "rating": None, "city": None, "country": None,
            "founded_year": None, "type": None, "regional_rank": None, "world_rank": None,
            "acceptance_rate": None, "igcse_requirements": None, "advantages": None,
            "disadvantages": None, "website": None, "email": None, "region": "Egypt" # Default to Egypt based on PDF
        }

        # --- Basic Info --- 
        name_match = re.search(r"^([A-Z][a-zA-Z\s\-]+ University(?: Branch in Egypt)?(?: in [A-Za-z]+)?)\n", block, re.MULTILINE)
        if name_match:
            data["name"] = name_match.group(1).strip()
        else:
            # Try alternative name patterns if needed, or skip block
            continue # Skip if no name found

        if "Certified" in block:
            data["certified"] = True

        rating_match = re.search(r"(★+)", block)
        if rating_match:
            data["rating"] = parse_rating(rating_match.group(1))

        location_match = re.search(r"^([A-Za-z\s]+), ([A-Za-z]+)\n", block, re.MULTILINE)
        if location_match:
            data["city"] = location_match.group(1).strip()
            data["country"] = location_match.group(2).strip()
            # Simple logic for region - needs refinement if Gulf data is added
            if data["country"] != "Egypt":
                data["region"] = "Gulf" # Placeholder

        # --- Key Information --- 
        founded_match = re.search(r"Founded: (\d{4})", block)
        if founded_match:
            data["founded_year"] = parse_int(founded_match.group(1))

        type_match = re.search(r"Type: (Public|Private)", block)
        if type_match:
            data["type"] = type_match.group(1)

        regional_rank_match = re.search(r"Regional Rank: #?(\d+)", block)
        if regional_rank_match:
            data["regional_rank"] = parse_int(regional_rank_match.group(1))

        world_rank_match = re.search(r"World Rank: #?([\d\-]+|Not Ranked)", block)
        if world_rank_match:
            data["world_rank"] = world_rank_match.group(1).strip()

        acceptance_match = re.search(r"Acceptance Rate: (\d+)%?", block)
        if acceptance_match:
            data["acceptance_rate"] = parse_int(acceptance_match.group(1))

        # --- Text Sections --- 
        req_match = re.search(r"IGCSE Admission Requirements\n(.*?)(?:Advantages|Website:|\Z)", block, re.DOTALL | re.MULTILINE)
        if req_match:
            data["igcse_requirements"] = req_match.group(1).strip()

        adv_match = re.search(r"Advantages\n(.*?)(?:Disadvantages|Website:|\Z)", block, re.DOTALL | re.MULTILINE)
        if adv_match:
            data["advantages"] = adv_match.group(1).strip()

        disadv_match = re.search(r"Disadvantages\n(.*?)(?:Website:|\Z)", block, re.DOTALL | re.MULTILINE)
        if disadv_match:
            data["disadvantages"] = disadv_match.group(1).strip()

        # --- Contact --- 
        website_match = re.search(r"Website: (www\.[^\s|]+)", block)
        if website_match:
            data["website"] = "http://" + website_match.group(1) # Add protocol

        email_match = re.search(r"Email: ([^\s|]+@[^\s|]+)", block)
        if email_match:
            data["email"] = email_match.group(1)

        # Basic validation - ensure name and location are present
        if data["name"] and data["city"] and data["country"]:
            universities.append(data)
        else:
            print(f"Skipping block, missing essential data: {data['name']}")

    return universities

def seed_database():
    """Reads the text file, parses data, and populates the database."""
    print("Starting database seeding...")
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: Input file not found at {INPUT_FILE}")
        return
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    university_data_list = extract_university_data(content)
    print(f"Parsed {len(university_data_list)} universities from the file.")

    with app.app_context():
        # Clear existing data (optional, good for development)
        print("Clearing existing university data...")
        University.query.delete()
        db.session.commit()

        print("Adding new university data...")
        added_count = 0
        skipped_count = 0
        for data in university_data_list:
            # Check if university already exists (by name)
            existing_uni = University.query.filter_by(name=data["name"]).first()
            if existing_uni:
                print(f"Skipping duplicate: {data['name']}")
                skipped_count += 1
                continue

            uni = University(
                name=data["name"],
                region=data["region"],
                country=data["country"],
                city=data["city"],
                certified=data["certified"],
                rating=data["rating"],
                founded_year=data["founded_year"],
                type=data["type"],
                regional_rank=data["regional_rank"],
                world_rank=data["world_rank"],
                acceptance_rate=data["acceptance_rate"],
                igcse_requirements=data["igcse_requirements"],
                advantages=data["advantages"],
                disadvantages=data["disadvantages"],
                website=data["website"],
                email=data["email"]
            )
            db.session.add(uni)
            added_count += 1

        try:
            db.session.commit()
            print(f"Successfully added {added_count} universities. Skipped {skipped_count} duplicates.")
        except Exception as e:
            db.session.rollback()
            print(f"Error committing to database: {e}")

if __name__ == "__main__":
    seed_database()

