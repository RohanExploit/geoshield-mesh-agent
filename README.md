# GeoShield Mesh — Autonomous Multi-Sensor Climate & Disaster Early-Warning Agent

**Student:** Amol Ghadge | **Course:** Artificial Intelligence (BTCOC701) | **Activity:** CAS Activity-I

GeoShield Mesh fuses live **Open-Meteo Rainfall/Wind/Soil Forecasts**, **GloFAS River Discharge**, **USGS Global M2.5+ Earthquake GeoJSON**, and **OpenStreetMap Nominatim Geocoding** under a 4-subagent early-warning commander.

## Multi-Agent Architecture
- **Lead Agent:** `GeoShield Dispatch Commander`
- **Sub-Agent 1:** `HydroMetSensorAgent`
- **Sub-Agent 2:** `SeismicFeedScoutAgent`
- **Sub-Agent 3:** `ExposureVulnerabilityCritic`
- **Sub-Agent 4:** `CivilDispatchRouterAgent`

## Quick Start
```bash
pip install -r requirements.txt
pytest -q
streamlit run app.py
```
