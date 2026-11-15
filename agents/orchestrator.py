"""Lead GeoShield Dispatch Commander orchestrating 4 hazard sub-agents and memory."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .llm_router import SynthesisResult, synthesize_with_fallback
from .memory import HazardMemoryStore
from .subagents import (
    CivilDispatchRouterAgent,
    ExposureVulnerabilityCritic,
    GeoMeshContext,
    HydroMetSensorAgent,
    SeismicFeedScoutAgent,
)
from .tools import DEFAULT_ZONES, geocode_city


def _universal_geo_fallback(ctx: GeoMeshContext) -> str:
    top = ctx.zone_scores[0] if ctx.zone_scores else {}
    return (
        f"### GeoShield Autonomous Hazard Dispatch ({top.get('alert_tier', 'GREEN NOMINAL')})\n"
        f"- **Highest Risk Zone**: {top.get('region', 'N/A')} — Composite Risk `{top.get('composite_risk', 0)}/100` "
        f"(48h Rain `{top.get('rain_48h_mm', 0)} mm`, River `{top.get('peak_discharge_m3s', 0)} m³/s`, Wind `{top.get('max_wind_gust_kmh', 0)} km/h`).\n"
        f"- **Seismic Proximity**: {top.get('nearest_quake', 'None')} across {len(ctx.quakes)} live USGS events.\n"
        f"- **Priority Action**: {ctx.dispatch_plan[0]['protocol'] if ctx.dispatch_plan else 'Routine telemetry watch.'}"
    )


class GeoShieldCommander:
    """Goal-Based + Model-Based + Utility-Based Spatial Hazard Orchestrator."""

    def __init__(self, memory_store: HazardMemoryStore | None = None) -> None:
        self.memory = memory_store or HazardMemoryStore()
        self.subagents = [
            HydroMetSensorAgent(),
            SeismicFeedScoutAgent(),
            ExposureVulnerabilityCritic(),
            CivilDispatchRouterAgent(),
        ]

    def run_sweep(
        self,
        custom_city: str = "",
        gemini_key: str | None = None,
        groq_key: str | None = None,
    ) -> dict[str, Any]:
        zones = list(DEFAULT_ZONES)
        if custom_city.strip():
            resolved = geocode_city(custom_city)
            if resolved:
                zones.insert(0, resolved)

        state = self.memory.load()
        ctx = GeoMeshContext(
            zones=zones,
            baselines=state.get("region_baselines", {}),
            seen_quake_ids=set(state.get("seen_quake_ids", [])),
        )
        ctx.emit(
            "GeoShield Commander",
            "HydroMetSensorAgent",
            "DELEGATE",
            f"Initiating multi-sensor climate & seismic fusion sweep across {len(zones)} geographic zones.",
            confidence=0.98,
        )

        for agent in self.subagents:
            agent.run(ctx)

        top_tier = ctx.zone_scores[0]["alert_tier"] if ctx.zone_scores else "GREEN NOMINAL"
        prompt = (
            f"You are GeoShield Dispatch Commander. Provide a concise 3-bullet emergency readiness briefing "
            f"(Top Zone Telemetry, Seismic/Flood Interaction, Recommended Action) under 110 words.\n"
            f"Top 3 Zones: {ctx.zone_scores[:3]}\n"
            f"Dispatch Plan: {ctx.dispatch_plan}"
        )
        synthesis: SynthesisResult = synthesize_with_fallback(
            prompt=prompt,
            system_instruction="Be precise, calm, and NDMA-concise.",
            universal_fallback_fn=lambda: _universal_geo_fallback(ctx),
            gemini_key=gemini_key,
            groq_key=groq_key,
        )

        updated_state = self.memory.update_after_sweep(
            zone_scores=ctx.zone_scores,
            quake_ids=[q["id"] for q in ctx.quakes if q.get("id")],
            top_alert_level=top_tier,
            summary=synthesis.text,
        )

        return {
            "zone_scores": ctx.zone_scores,
            "quakes": ctx.quakes,
            "dispatch_plan": ctx.dispatch_plan,
            "messages": [asdict(m) for m in ctx.messages],
            "synthesis": asdict(synthesis),
            "memory": updated_state,
            "top_tier": top_tier,
        }
