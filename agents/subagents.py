"""Four specialized Disaster & Climate Sub-Agents under GeoShield Dispatch Commander."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

from .tools import (
    fetch_open_meteo_hydro,
    fetch_river_discharge,
    fetch_usgs_earthquakes,
    haversine_km,
)


@dataclass
class GeoBusMessage:
    sender: str
    recipient: str
    phase: str
    content: str
    confidence: float


@dataclass
class GeoMeshContext:
    zones: list[dict[str, Any]]
    baselines: dict[str, float]
    seen_quake_ids: set[str]
    hydro_reports: list[dict[str, Any]] = field(default_factory=list)
    quakes: list[dict[str, Any]] = field(default_factory=list)
    zone_scores: list[dict[str, Any]] = field(default_factory=list)
    dispatch_plan: list[dict[str, str]] = field(default_factory=list)
    messages: list[GeoBusMessage] = field(default_factory=list)

    def emit(self, sender: str, recipient: str, phase: str, content: str, confidence: float = 0.9) -> None:
        self.messages.append(GeoBusMessage(sender, recipient, phase, content, round(confidence, 2)))


class HydroMetSensorAgent:
    """Sub-Agent 1: Collects Open-Meteo rainfall, wind gust, soil moisture & river discharge in parallel."""

    name = "HydroMetSensorAgent"

    def run(self, ctx: GeoMeshContext) -> None:
        def _poll_zone(z: dict[str, Any]) -> dict[str, Any]:
            met = fetch_open_meteo_hydro(z["lat"], z["lon"])
            river = fetch_river_discharge(z["lat"], z["lon"])
            return {**z, **met, **river}

        with ThreadPoolExecutor(max_workers=6) as pool:
            ctx.hydro_reports = list(pool.map(_poll_zone, ctx.zones))

        peak_rain = max((h["rain_48h_mm"] for h in ctx.hydro_reports), default=0.0)
        ctx.emit(
            self.name,
            "SeismicFeedScoutAgent",
            "SENSE-HYDRO",
            f"Polled {len(ctx.hydro_reports)} zones via Open-Meteo + GloFAS. Peak 48h rain={peak_rain} mm.",
            confidence=0.95,
        )


class SeismicFeedScoutAgent:
    """Sub-Agent 2: Scans live USGS earthquake feed and correlates proximity to zones."""

    name = "SeismicFeedScoutAgent"

    def run(self, ctx: GeoMeshContext) -> None:
        res = fetch_usgs_earthquakes()
        ctx.quakes = res["quakes"]
        unseen = sum(1 for q in ctx.quakes if q["id"] not in ctx.seen_quake_ids)
        ctx.emit(
            self.name,
            "ExposureVulnerabilityCritic",
            "SENSE-SEISMIC",
            f"Ingested {len(ctx.quakes)} USGS M2.5+ quakes ({unseen} newly observed, source={res['source']}).",
            confidence=0.94,
        )


class ExposureVulnerabilityCritic:
    """Sub-Agent 3: Computes multi-hazard Utility Risk Score and dampens transient noise."""

    name = "ExposureVulnerabilityCritic"

    def run(self, ctx: GeoMeshContext) -> None:
        scored: list[dict[str, Any]] = []
        for h in ctx.hydro_reports:
            rain_risk = min(45.0, (h["rain_48h_mm"] / 120.0) * 45.0)
            gust_risk = min(20.0, max(0.0, (h["max_wind_gust_kmh"] - 25.0) / 60.0) * 20.0)
            river_risk = min(25.0, (h["peak_discharge_m3s"] / 400.0) * 25.0)
            soil_factor = 1.15 if h["mean_soil_moisture"] > 0.36 else 1.0

            seismic_risk = 0.0
            nearest_quake = "None within 600 km"
            for q in ctx.quakes:
                dist = haversine_km(h["lat"], h["lon"], q["lat"], q["lon"])
                if dist <= 600.0:
                    attenuated = max(0.0, (q["mag"] - 2.0) * 8.0 * (1.0 - dist / 650.0))
                    if attenuated > seismic_risk:
                        seismic_risk = attenuated
                        nearest_quake = f"M{q['mag']:.1f} @ {dist} km ({q['place'][:32]})"

            raw_risk = min(99.0, (rain_risk + gust_risk + river_risk) * soil_factor + seismic_risk)
            baseline = ctx.baselines.get(h["region"], raw_risk)
            delta = round(raw_risk - baseline, 1)

            if raw_risk >= 70:
                tier = "RED WATCH"
            elif raw_risk >= 45:
                tier = "ORANGE ADVISORY"
            elif raw_risk >= 22:
                tier = "YELLOW MONITOR"
            else:
                tier = "GREEN NOMINAL"

            scored.append(
                {
                    **h,
                    "seismic_risk": round(seismic_risk, 1),
                    "nearest_quake": nearest_quake,
                    "composite_risk": round(raw_risk, 1),
                    "baseline_risk": baseline,
                    "risk_delta": delta,
                    "alert_tier": tier,
                }
            )

        scored.sort(key=lambda r: r["composite_risk"], reverse=True)
        ctx.zone_scores = scored
        top = scored[0] if scored else {"region": "N/A", "composite_risk": 0, "alert_tier": "GREEN NOMINAL"}
        ctx.emit(
            self.name,
            "CivilDispatchRouterAgent",
            "CRITIQUE",
            f"Top exposure: {top['region']} risk={top['composite_risk']}/100 ({top['alert_tier']}).",
            confidence=0.91,
        )


class CivilDispatchRouterAgent:
    """Sub-Agent 4: Emits NDMA-aligned preparedness and evacuation actions."""

    name = "CivilDispatchRouterAgent"

    def run(self, ctx: GeoMeshContext) -> None:
        actions: list[dict[str, str]] = []
        for z in ctx.zone_scores[:3]:
            if z["composite_risk"] >= 45:
                actions.append(
                    {
                        "region": z["region"],
                        "tier": z["alert_tier"],
                        "protocol": "Pre-stage NDRF/SDRF pumps, verify dam spillway telemetry, issue SMS siren warning.",
                    }
                )
            elif z["composite_risk"] >= 22:
                actions.append(
                    {
                        "region": z["region"],
                        "tier": z["alert_tier"],
                        "protocol": "Clear storm-water culverts and track 6-hour Open-Meteo runoff delta.",
                    }
                )
            else:
                actions.append(
                    {
                        "region": z["region"],
                        "tier": z["alert_tier"],
                        "protocol": "Maintain routine automated telemetry sweep; no field dispatch required.",
                    }
                )

        ctx.dispatch_plan = actions
        ctx.emit(
            self.name,
            "GeoShield Commander",
            "DISPATCH",
            f"Generated {len(actions)} prioritized regional dispatch directives.",
            confidence=0.95,
        )
