"""Headless autonomous runner for GeoShield Mesh spatial hazard sweeps."""

from __future__ import annotations

import json
import os

from agents.orchestrator import GeoShieldCommander


def main() -> None:
    custom_city = os.environ.get("GEOSHIELD_CUSTOM_CITY", "")
    commander = GeoShieldCommander()
    res = commander.run_sweep(custom_city=custom_city)
    print(
        json.dumps(
            {
                "top_alert_tier": res["top_tier"],
                "top_region": res["zone_scores"][0]["region"] if res["zone_scores"] else "N/A",
                "peak_risk": res["zone_scores"][0]["composite_risk"] if res["zone_scores"] else 0,
                "provider": res["synthesis"]["provider"],
                "total_sweeps": res["memory"]["total_sweeps"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
