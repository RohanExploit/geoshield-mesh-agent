"""Model-based persistent memory for GeoShield Mesh spatial hazard baselines."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_STATE: dict[str, Any] = {
    "agent_name": "GeoShield Dispatch Commander",
    "region_baselines": {},
    "seen_quake_ids": [],
    "dispatch_history": [],
    "total_sweeps": 0,
    "last_sweep_utc": None,
}


class HazardMemoryStore:
    """Persists regional hydro-met baselines, seen USGS earthquake IDs, and alert history."""

    def __init__(self, state_path: Path | str | None = None) -> None:
        base_dir = Path(__file__).resolve().parent.parent
        self.path = Path(state_path) if state_path else base_dir / "state" / "hazard_memory.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return json.loads(json.dumps(DEFAULT_STATE))
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            for key, val in DEFAULT_STATE.items():
                data.setdefault(key, json.loads(json.dumps(val)))
            return data
        except Exception:
            return json.loads(json.dumps(DEFAULT_STATE))

    def save(self, state: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def update_after_sweep(
        self,
        zone_scores: list[dict[str, Any]],
        quake_ids: list[str],
        top_alert_level: str,
        summary: str,
    ) -> dict[str, Any]:
        state = self.load()
        baselines: dict[str, float] = state["region_baselines"]
        for z in zone_scores:
            name = z["region"]
            score = float(z["composite_risk"])
            prev = baselines.get(name)
            baselines[name] = round(score if prev is None else (0.65 * prev + 0.35 * score), 1)

        seen = set(state.get("seen_quake_ids", []))
        new_quakes = [qid for qid in quake_ids if qid not in seen]
        state["seen_quake_ids"] = (state.get("seen_quake_ids", []) + new_quakes)[-200:]

        now_iso = datetime.now(timezone.utc).isoformat()
        state["total_sweeps"] = int(state.get("total_sweeps", 0)) + 1
        state["last_sweep_utc"] = now_iso
        peak = max((z["composite_risk"] for z in zone_scores), default=0.0)
        state["dispatch_history"].append(
            {
                "timestamp_utc": now_iso,
                "alert_level": top_alert_level,
                "peak_risk": round(peak, 1),
                "new_quakes_detected": len(new_quakes),
                "summary": summary[:200],
            }
        )
        state["dispatch_history"] = state["dispatch_history"][-30:]
        self.save(state)
        return state
