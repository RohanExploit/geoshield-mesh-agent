"""Keyless live geo-hazard sensors: Open-Meteo Forecast/Flood, USGS Quakes, OSM Nominatim."""

from __future__ import annotations

import math
from typing import Any

import requests

HEADERS = {"User-Agent": "GeoShield-Mesh-Agent/1.0"}

DEFAULT_ZONES = [
    {"region": "Satara (Koyna Basin)", "lat": 17.6805, "lon": 74.0183},
    {"region": "Kolhapur (Panchganga)", "lat": 16.7050, "lon": 74.2433},
    {"region": "Sangli (Krishna Basin)", "lat": 16.8524, "lon": 74.5815},
    {"region": "Pune (Mutha Basin)", "lat": 18.5204, "lon": 73.8567},
    {"region": "Mumbai Coastal", "lat": 19.0760, "lon": 72.8777},
    {"region": "Ratnagiri Konkan", "lat": 16.9902, "lon": 73.3120},
]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute great-circle distance in kilometers between two coordinates."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(2 * r * math.asin(math.sqrt(a)), 1)


def geocode_city(query: str, timeout: float = 4.5) -> dict[str, Any] | None:
    """Resolve a custom city/district name using OpenStreetMap Nominatim."""
    clean = query.strip()
    if not clean:
        return None
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": clean, "format": "json", "limit": 1},
            headers=HEADERS,
            timeout=timeout,
        )
        resp.raise_for_status()
        hits = resp.json()
        if not hits:
            return None
        return {
            "region": clean.title(),
            "lat": round(float(hits[0]["lat"]), 4),
            "lon": round(float(hits[0]["lon"]), 4),
        }
    except Exception:
        return None


def fetch_open_meteo_hydro(lat: float, lon: float, timeout: float = 5.0) -> dict[str, Any]:
    """Fetch live Open-Meteo 48h precipitation, wind gusts, and soil moisture."""
    try:
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "hourly": "precipitation,wind_gusts_10m,soil_moisture_0_to_1cm",
                "forecast_days": 2,
                "timezone": "auto",
            },
            headers=HEADERS,
            timeout=timeout,
        )
        resp.raise_for_status()
        hourly = resp.json().get("hourly", {})
        rain = [float(x or 0) for x in hourly.get("precipitation", [])[:48]]
        gusts = [float(x or 0) for x in hourly.get("wind_gusts_10m", [])[:48]]
        soil = [float(x or 0) for x in hourly.get("soil_moisture_0_to_1cm", [])[:48]]
        return {
            "rain_48h_mm": round(sum(rain), 1),
            "peak_rain_mm_hr": round(max(rain, default=0.0), 1),
            "max_wind_gust_kmh": round(max(gusts, default=0.0), 1),
            "mean_soil_moisture": round(sum(soil) / max(len(soil), 1), 3),
            "source": "live-open-meteo-forecast",
        }
    except Exception as exc:
        return {
            "rain_48h_mm": 12.4,
            "peak_rain_mm_hr": 3.2,
            "max_wind_gust_kmh": 24.0,
            "mean_soil_moisture": 0.28,
            "source": f"open-meteo-backup ({type(exc).__name__})",
        }


def fetch_river_discharge(lat: float, lon: float, timeout: float = 5.0) -> dict[str, Any]:
    """Fetch GloFAS river discharge telemetry from Open-Meteo Flood API."""
    try:
        resp = requests.get(
            "https://flood-api.open-meteo.com/v1/flood",
            params={"latitude": lat, "longitude": lon, "daily": "river_discharge", "forecast_days": 5},
            headers=HEADERS,
            timeout=timeout,
        )
        resp.raise_for_status()
        vals = [float(x or 0) for x in resp.json().get("daily", {}).get("river_discharge", [])]
        return {
            "peak_discharge_m3s": round(max(vals, default=0.0), 2),
            "source": "live-glofas-flood-api",
        }
    except Exception as exc:
        return {"peak_discharge_m3s": 18.5, "source": f"flood-backup ({type(exc).__name__})"}


def fetch_usgs_earthquakes(timeout: float = 5.0) -> dict[str, Any]:
    """Fetch live USGS M2.5+ global earthquakes from the past 24 hours."""
    try:
        resp = requests.get(
            "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson",
            headers=HEADERS,
            timeout=timeout,
        )
        resp.raise_for_status()
        features = resp.json().get("features", [])
        quakes = []
        for feat in features[:40]:
            props = feat.get("properties", {})
            coords = feat.get("geometry", {}).get("coordinates", [0, 0, 0])
            quakes.append(
                {
                    "id": feat.get("id", ""),
                    "place": props.get("place", "Unknown"),
                    "mag": float(props.get("mag") or 0.0),
                    "lon": float(coords[0]),
                    "lat": float(coords[1]),
                    "depth_km": float(coords[2]) if len(coords) > 2 else 10.0,
                }
            )
        return {"quakes": quakes, "source": "live-usgs-geojson", "ok": True}
    except Exception as exc:
        return {"quakes": [], "source": f"usgs-backup ({type(exc).__name__})", "ok": False}
