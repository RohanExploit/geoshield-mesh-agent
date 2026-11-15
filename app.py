"""GeoShield Mesh — Tactical Cartographic Radar UI for Multi-Sensor Hazard Fusion."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from agents.orchestrator import GeoShieldCommander

st.set_page_config(
    page_title="GeoShield Mesh | Spatial Hazard Early-Warning Agent",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600;700&family=IBM+Plex+Mono:wght@400;600&display=swap');

html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }
code, pre, .mono { font-family: 'IBM Plex Mono', monospace !important; }
.stApp { background: linear-gradient(160deg, #0B1324 0%, #0F172A 60%, #111D35 100%); }
.radar-header {
    border: 1px solid rgba(56, 189, 248, 0.35);
    border-left: 6px solid #38BDF8;
    background: rgba(15, 23, 42, 0.9);
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
}
.metric-box {
    background: rgba(30, 41, 59, 0.72);
    border: 1px solid rgba(148, 163, 184, 0.22);
    border-radius: 10px;
    padding: 0.9rem 1.05rem;
}
.bus-item {
    background: rgba(30, 41, 59, 0.65);
    border-left: 3px solid #38BDF8;
    padding: 0.7rem 0.95rem;
    border-radius: 0 8px 8px 0;
    margin-bottom: 0.55rem;
}
</style>
""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### Radar Target Control")
    custom_city = st.text_input("Inject Custom City/District (OSM Nominatim)", placeholder="e.g., Mahabaleshwar, India")
    with st.expander("AI Brain Keys (Optional — 90% Keyless)"):
        gemini_key = st.text_input("Gemini API Key Override", type="password")
        groq_key = st.text_input("Groq API Key Override", type="password")
    sweep_btn = st.button("Run Autonomous Hazard Sweep", type="primary", use_container_width=True)
    st.caption("Built by Amol Ghadge | BTCOC701 CAS Activity-I")

if "geoshield_res" not in st.session_state or sweep_btn:
    with st.spinner("GeoShield Commander fusing Open-Meteo, GloFAS River & USGS feeds..."):
        st.session_state.geoshield_res = GeoShieldCommander().run_sweep(
            custom_city=custom_city,
            gemini_key=gemini_key,
            groq_key=groq_key,
        )

res = st.session_state.geoshield_res
zones_df = pd.DataFrame(res["zone_scores"])
top_zone = res["zone_scores"][0] if res["zone_scores"] else {}

tier_color = "#EF4444" if "RED" in res["top_tier"] else ("#F97316" if "ORANGE" in res["top_tier"] else ("#EAB308" if "YELLOW" in res["top_tier"] else "#22C55E"))

st.markdown(
    f"""
<div class="radar-header">
  <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.8rem;">
    <div>
      <h2 style="margin:0; color:#F8FAFC;">GeoShield Mesh — Autonomous Climate &amp; Seismic Radar</h2>
      <div style="color:#94A3B8; margin-top:0.25rem;">Multi-sensor fusion across Open-Meteo Hydro, GloFAS River Discharge, USGS Earthquakes &amp; OSM Nominatim</div>
    </div>
    <div class="mono" style="padding:0.3rem 0.75rem; border-radius:999px; border:1px solid {tier_color}; color:{tier_color}; font-weight:600;">
      {res['top_tier']} · PEAK {top_zone.get('composite_risk', 0)}/100
    </div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(f'<div class="metric-box"><div style="color:#94A3B8;font-size:0.78rem;">ZONES MONITORED</div><div style="font-size:1.45rem;font-weight:700;">{len(zones_df)} Basins</div></div>', unsafe_allow_html=True)
with k2:
    st.markdown(f'<div class="metric-box"><div style="color:#94A3B8;font-size:0.78rem;">LIVE USGS QUAKES (24H)</div><div style="font-size:1.45rem;font-weight:700;">{len(res["quakes"])} Events</div></div>', unsafe_allow_html=True)
with k3:
    st.markdown(f'<div class="metric-box"><div style="color:#94A3B8;font-size:0.78rem;">AUTONOMOUS SWEEPS</div><div style="font-size:1.45rem;font-weight:700;">{res["memory"]["total_sweeps"]}</div></div>', unsafe_allow_html=True)
with k4:
    st.markdown(f'<div class="metric-box"><div style="color:#94A3B8;font-size:0.78rem;">10% AI SYNTHESIZER</div><div style="font-size:1.05rem;font-weight:700;padding-top:0.25rem;">{res["synthesis"]["provider"]}</div></div>', unsafe_allow_html=True)

st.markdown("")
t_map, t_bus, t_peas = st.tabs(["Spatial Hazard Map & Basins", "Sub-Agent Dispatch Bus", "PEAS & Historical Memory"])

with t_map:
    col_l, col_r = st.columns([1.35, 1])
    with col_l:
        fig_geo = go.Figure()
        fig_geo.add_trace(
            go.Scattergeo(
                lat=zones_df["lat"],
                lon=zones_df["lon"],
                text=[f"{r['region']}<br>Risk: {r['composite_risk']}/100 ({r['alert_tier']})<br>Rain 48h: {r['rain_48h_mm']} mm" for _, r in zones_df.iterrows()],
                marker=dict(
                    size=[max(12, r["composite_risk"] * 0.45) for _, r in zones_df.iterrows()],
                    color=zones_df["composite_risk"],
                    colorscale="YlOrRd",
                    cmin=0,
                    cmax=100,
                    line=dict(width=1.2, color="#F8FAFC"),
                    colorbar=dict(title="Risk"),
                ),
                name="Monitored Basins",
            )
        )
        if res["quakes"]:
            qdf = pd.DataFrame(res["quakes"][:25])
            fig_geo.add_trace(
                go.Scattergeo(
                    lat=qdf["lat"],
                    lon=qdf["lon"],
                    text=[f"USGS M{r['mag']:.1f} — {r['place']}" for _, r in qdf.iterrows()],
                    marker=dict(size=qdf["mag"] * 2.5, color="#38BDF8", symbol="diamond", opacity=0.72),
                    name="USGS Earthquakes",
                )
            )
        fig_geo.update_layout(
            geo=dict(
                bgcolor="rgba(15,23,42,0.5)",
                landcolor="#1E293B",
                oceancolor="#0B1324",
                showocean=True,
                showcountries=True,
                countrycolor="#334155",
                center=dict(lat=float(zones_df["lat"].mean()), lon=float(zones_df["lon"].mean())),
                projection_scale=4.2,
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#E2E8F0"),
            height=380,
            margin=dict(l=0, r=0, t=10, b=0),
            legend=dict(orientation="h", y=1.02),
        )
        st.plotly_chart(fig_geo, use_container_width=True)

    with col_r:
        st.subheader("Commander Readiness Brief")
        st.info(res["synthesis"]["text"])
        st.subheader("Priority Dispatch Protocols")
        for d in res["dispatch_plan"]:
            st.markdown(f"**{d['region']}** (`{d['tier']}`): {d['protocol']}")

    st.subheader("Regional Multi-Sensor Telemetry Matrix")
    st.dataframe(
        zones_df[["region", "alert_tier", "composite_risk", "rain_48h_mm", "peak_discharge_m3s", "max_wind_gust_kmh", "nearest_quake"]],
        use_container_width=True,
        hide_index=True,
    )

with t_bus:
    st.subheader("Live Inter-Agent Coordination Trace")
    for m in res["messages"]:
        st.markdown(
            f'<div class="bus-item"><div class="mono" style="font-size:0.78rem;color:#38BDF8;">[{m["phase"]}] {m["sender"]} → {m["recipient"]} (conf={m["confidence"]})</div><div style="margin-top:0.2rem;">{m["content"]}</div></div>',
            unsafe_allow_html=True,
        )

with t_peas:
    st.subheader("PEAS Specification")
    st.table(
        pd.DataFrame(
            [
                {"Component": "P — Performance Measure", "Description": "Early flood/seismic risk recall, false-alarm suppression, spatial coverage accuracy, timely civil dispatch."},
                {"Component": "E — Environment", "Description": "Open-Meteo weather grid, GloFAS river basins, USGS seismic feed, OSM Nominatim, Streamlit Cloud & GitHub Actions."},
                {"Component": "A — Actuators", "Description": "Spatial Plotly hazard radar, NDMA tiered alert bulletins, EWMA regional baseline memory updater."},
                {"Component": "S — Sensors", "Description": "48h precipitation/wind/soil APIs, river discharge m³/s, USGS GeoJSON quakes, state/hazard_memory.json."},
            ]
        )
    )
    if res["memory"].get("dispatch_history"):
        hist_df = pd.DataFrame(res["memory"]["dispatch_history"])
        st.plotly_chart(px.area(hist_df, x="timestamp_utc", y="peak_risk", title="Historical Peak Risk Trend"), use_container_width=True)
