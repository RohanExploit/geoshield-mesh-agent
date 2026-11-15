"""Automated pytest suite for GeoShield Mesh multi-agent early-warning system."""

from __future__ import annotations

from pathlib import Path

from agents.llm_router import synthesize_with_fallback
from agents.memory import HazardMemoryStore
from agents.orchestrator import GeoShieldCommander
from agents.subagents import ExposureVulnerabilityCritic, GeoMeshContext
from agents.tools import haversine_km


def test_haversine_distance_reasonable() -> None:
    d = haversine_km(17.6805, 74.0183, 18.5204, 73.8567)  # Satara to Pune
    assert 80.0 < d < 120.0


def test_hazard_memory_deduplicates_quakes(tmp_path: Path) -> None:
    store = HazardMemoryStore(tmp_path / "haz.json")
    s1 = store.update_after_sweep([{"region": "Satara", "composite_risk": 35.0}], ["q1", "q2"], "YELLOW MONITOR", "ok")
    s2 = store.update_after_sweep([{"region": "Satara", "composite_risk": 55.0}], ["q2", "q3"], "ORANGE ADVISORY", "ok2")
    assert s1["seen_quake_ids"] == ["q1", "q2"]
    assert s2["seen_quake_ids"] == ["q1", "q2", "q3"]
    assert s2["total_sweeps"] == 2


def test_exposure_critic_scoring_tiers() -> None:
    critic = ExposureVulnerabilityCritic()
    ctx = GeoMeshContext(
        zones=[{"region": "Satara", "lat": 17.68, "lon": 74.01}],
        baselines={},
        seen_quake_ids=set(),
        hydro_reports=[
            {
                "region": "Satara",
                "lat": 17.68,
                "lon": 74.01,
                "rain_48h_mm": 130.0,
                "peak_rain_mm_hr": 25.0,
                "max_wind_gust_kmh": 75.0,
                "mean_soil_moisture": 0.42,
                "peak_discharge_m3s": 420.0,
            }
        ],
        quakes=[{"id": "q1", "place": "Near Satara", "mag": 4.8, "lat": 17.7, "lon": 74.1, "depth_km": 10.0}],
    )
    critic.run(ctx)
    assert ctx.zone_scores[0]["alert_tier"] == "RED WATCH"
    assert ctx.zone_scores[0]["composite_risk"] >= 70.0


def test_commander_sweep_mocked(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "agents.subagents.fetch_open_meteo_hydro",
        lambda lat, lon: {"rain_48h_mm": 18.0, "peak_rain_mm_hr": 4.0, "max_wind_gust_kmh": 22.0, "mean_soil_moisture": 0.25, "source": "mock"},
    )
    monkeypatch.setattr(
        "agents.subagents.fetch_river_discharge",
        lambda lat, lon: {"peak_discharge_m3s": 24.0, "source": "mock"},
    )
    monkeypatch.setattr(
        "agents.subagents.fetch_usgs_earthquakes",
        lambda: {"quakes": [], "source": "mock", "ok": True},
    )

    commander = GeoShieldCommander(memory_store=HazardMemoryStore(tmp_path / "haz.json"))
    out = commander.run_sweep(gemini_key="", groq_key="")
    assert len(out["messages"]) == 5
    assert out["memory"]["total_sweeps"] == 1
    assert synthesize_with_fallback("p", "s", lambda: "ok", "", "").provider == "Universal Keyless Engine"
