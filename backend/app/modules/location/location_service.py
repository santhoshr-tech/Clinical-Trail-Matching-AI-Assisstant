import math
import logging
from typing import List, Dict, Any, Optional
from app.core.db import get_db_connection

logger = logging.getLogger(__name__)

# Built-in city coordinate lookup for robust fallback geocoding
CITY_COORDINATES: Dict[str, tuple[float, float]] = {
    "chennai": (13.0827, 80.2707),
    "salem": (11.6643, 78.1460),
    "coimbatore": (11.0168, 76.9558),
    "madurai": (9.9252, 78.1198),
    "bengaluru": (12.9716, 77.5946),
    "bangalore": (12.9716, 77.5946),
    "mumbai": (19.0760, 72.8777),
    "delhi": (28.6139, 77.2090),
    "new delhi": (28.6139, 77.2090),
    "hyderabad": (17.3850, 78.4867),
    "kolkata": (22.5726, 88.3639),
    "boston": (42.3601, -71.0589),
    "new york": (40.7128, -74.0060),
    "london": (51.5074, -0.1278),
    "tokyo": (35.6762, 139.6503),
}

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance in kilometers between two points 
    on the earth (specified in decimal degrees).
    """
    R = 6371.0  # Earth radius in kilometers

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    return round(distance, 1)

def get_nearby_trial_sites(
    user_lat: float,
    user_lon: float,
    radius_km: float = 50.0,
    condition: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Query trial sites within radius_km of user_lat, user_lon.
    Uses lat/lon from database, falling back to city coordinate lookup if needed.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        query = """
        SELECT 
            ts.id as site_id,
            ts.trial_id,
            ts.site_name,
            ts.facility_name,
            ts.city,
            ts.state,
            ts.country,
            ts.status as site_status,
            ts.latitude,
            ts.longitude,
            t.nct_id,
            t.title as trial_title,
            t.phase,
            t.conditions,
            t.recruitment_status
        FROM trial_sites ts
        JOIN trials t ON ts.trial_id = t.id;
        """
        cursor.execute(query)
        rows = cursor.fetchall()

    results = []
    for row in rows:
        r = dict(row)
        
        # Determine latitude/longitude
        lat = r.get("latitude")
        lon = r.get("longitude")

        if (lat is None or lon is None) and r.get("city"):
            city_key = r["city"].strip().lower()
            if city_key in CITY_COORDINATES:
                lat, lon = CITY_COORDINATES[city_key]

        if lat is None or lon is None:
            # Default to Chennai center if unknown
            lat, lon = 13.0827, 80.2707

        dist_km = haversine_distance(user_lat, user_lon, lat, lon)

        # Optional condition filter
        if condition and r.get("conditions"):
            if condition.lower() not in r["conditions"].lower():
                continue

        if dist_km <= radius_km:
            results.append({
                "site_id": r["site_id"],
                "trial_id": r["trial_id"],
                "nct_id": r["nct_id"],
                "trial_title": r["trial_title"],
                "site_name": r["site_name"],
                "facility_name": r["facility_name"],
                "city": r["city"],
                "state": r["state"],
                "country": r["country"],
                "phase": r["phase"],
                "conditions": r["conditions"],
                "recruitment_status": r["recruitment_status"],
                "latitude": lat,
                "longitude": lon,
                "distance_km": dist_km
            })

    # Sort results by distance ascending
    results.sort(key=lambda x: x["distance_km"])
    return results

def save_patient_address_location(patient_id: str, address_text: str) -> Dict[str, Any]:
    """
    Save address text to patients.location.
    Note: Raw live GPS coordinates are NEVER saved here - only address text.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM patients WHERE id = ?;", (patient_id,))
        if not cursor.fetchone():
            cursor.execute("""
            INSERT INTO patients (id, mrn_synthetic, age, gender, location, primary_diagnosis)
            VALUES (?, ?, 45, 'Female', ?, 'Non-Small Cell Lung Cancer');
            """, (patient_id, f"MRN-{patient_id}", address_text))
        else:
            cursor.execute("""
            UPDATE patients
            SET location = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?;
            """, (address_text, patient_id))
        conn.commit()

    return {"patient_id": patient_id, "saved_location": address_text, "status": "updated"}

