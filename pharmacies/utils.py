"""Location helpers: distance between two points, and preset Indore locations."""

import math

# Average radius of the Earth in kilometres.
EARTH_RADIUS_KM = 6371


def haversine_km(lat1, lng1, lat2, lng2):
    """
    Straight-line ("as the crow flies") distance in km between two points,
    using the Haversine formula, which treats the Earth as a sphere.

    Steps:
      1. Convert degrees to radians (Python's trig functions use radians).
      2. a = sin²(Δlat/2) + cos(lat1) · cos(lat2) · sin²(Δlng/2)
      3. c = 2 · asin(√a)    -> the angle between the points, seen from Earth's centre
      4. distance = Earth's radius × c
    """
    lat1, lng1, lat2, lng2 = map(math.radians, (float(lat1), float(lng1), float(lat2), float(lng2)))
    d_lat = lat2 - lat1
    d_lng = lng2 - lng1
    a = math.sin(d_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(d_lng / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return EARTH_RADIUS_KM * c


# Places in Indore a customer can choose when they do not share their location.
# key: (short name for the dropdown, latitude, longitude)
PRESET_LOCATIONS = {
    "rajwada": ("Rajwada (centre)", 22.7186, 75.8553),
    "vijay_nagar": ("Vijay Nagar", 22.7533, 75.8937),
    "palasia": ("Palasia", 22.7244, 75.8839),
    "bhawarkua": ("Bhawarkua", 22.6926, 75.8676),
}
DEFAULT_LOCATION = "rajwada"


def resolve_location(cleaned_data):
    """
    Decide where to measure distances from, using a LocationForm's cleaned data:
      1. the customer's own position (lat/lng from "Use my location"), if valid;
      2. otherwise the preset area they picked;
      3. otherwise the default (Rajwada).
    Returns a dict: label, lat, lng, is_gps.
    """
    lat = cleaned_data.get("lat")
    lng = cleaned_data.get("lng")
    if lat is not None and lng is not None:
        return {"label": "Your current location", "lat": lat, "lng": lng, "is_gps": True}

    key = cleaned_data.get("near") or DEFAULT_LOCATION
    name, preset_lat, preset_lng = PRESET_LOCATIONS[key]
    return {"label": f"{name}, Indore", "lat": preset_lat, "lng": preset_lng, "is_gps": False}
