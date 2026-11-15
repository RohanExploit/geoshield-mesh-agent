"""GeoShield Mesh — Tactical Spatial Radar UI with Live n8n Workflow Animation."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from agents.orchestrator import GeoShieldCommander
from agents.workflow_viz import render_n8n_workflow

st.set_page_config(
    page_title="GeoShield Mesh | Spatial Hazard Early-Warning Agent",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

REGIONS = {
    "Mahabaleshwar, India (Ghats Monsoon)": "Mahabaleshwar, India",
    "Kolhapur, India (Panchganga Basin)": "Kolhapur, India",
    "Ratnagiri, India (Konkan Coast)": "Ratnagiri, India",
    "Uttarkashi, India (Himalayan Seismic)": "Uttarkashi, India",
}

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600;700&family=IBM+Plex+Mono:wght@400;600&display=swap');
html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }
code, pre, .mono { font-family: 'IBM Plex Mono', monospace !important; }
.stApp { background: linear-gradient(160deg, #0B1324 0%, #0F172A 60%, #111D35 100%); }
@keyframes slideUp { from { opacity:0; transform:translateY(8px);} to { opacity:1; transform:translateY(0);} }
.radar-header {
    animation: slideUp .45s ease-out;
    border: 1px solid rgba(56, 189, 248, 0.35);
    border-left: 6px solid #38BDF8;
    background: rgba(15, 23, 42, 0.92);
    border-radius: 12px;
    padding: 1rem 1.35rem;
    margin-bottom: 0.9rem;
}
.metric-box {
    background: rgba(30, 41, 59, 0.78);
    border: 1px solid rgba(148, 163, 184, 0.22);
    border-radius: 10px;
    padding: 0.85rem 1rem;
    transition: transform .22s ease, border-color .22s ease;
}
.metric-box:hover { transform: translateY(-3px); border-color: #38BDF8; }
</style>
""",
    unsafe_allow_html=True,
)

if "geo_city" not in st.session_state:
    st.session_state.geo_city = "Mahabaleshwar, India"


def _apply_region() -> None:
    st.session_state.geo_city = REGIONS[st.session_state.geo_sample]
    st.session_state.geo_force = True


with st.sidebar:
    st.markdown("### Sample Basin Target")
    st.selectbox("Quick Sample City", list(REGIONS.keys()), key="geo_sample", on_change=_apply_region)
    st.markdown("### Radar Target Control")
    custom_city = st.text_input("Custom City / District (OSM Nominatim)", key="geo_city")
    with st.expander("AI Brain Keys (Optional)"):
        gemini_key = st.text_input("Gemini API Key Override", type="password")
        groq_key = st.text_input("Groq API Key Override", type="password")
    sweep_btn = st.button("Run Hazard Sweep", type="primary", width="stretch")
    st.caption("Amol Ghadge · BTCOC701")

if "geoshield_res" not in st.session_state or sweep_btn or st.session_state.pop("geo_force", False):
    with st.spinner("Fusing Open-Meteo Hydro, GloFAS River & USGS feeds..."):
        st.session_state.geoshield_res = GeoShieldCommander().run_sweep(
            custom_city=custom_city,
            gemini_key=gemini_key,
            groq_key=groq_key,
        )

res = st.session_state.geoshield_res
zones_df = pd.DataFrame(res["zone_scores"])
top_zone = res["zone_scores"][0] if res["zone_scores"] else {}
tier_color = "#EF4444" if "RED" in res["top_tier"] else ("#F97316" if "ORANGE" in res["top_tier"] else ("#EAB308" if "YELLOW" in res["top_tier"] else "#22C55E"))
msgs = res["messages"]

st.markdown(
    f"""
<div class="radar-header">
  <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.6rem;">
    <div>
      <h2 style="margin:0; color:#F8FAFC;">GeoShield Mesh — Climate &amp; Seismic Early-Warning</h2>
      <div class="mono" style="color:#94A3B8; font-size:0.82rem;">Open-Meteo Hydro · GloFAS River · USGS Quakes · OSM Nominatim</div>
    </div>
    <div class="mono" style="padding:0.3rem 0.8rem; border-radius:999px; border:1px solid {tier_color}; color:{tier_color}; font-weight:700;">
      {res['top_tier']} · PEAK {top_zone.get('composite_risk', 0)}/100
    </div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

k1, k2, k3, k4 = st.columns(4)
k1.markdown(f'<div class="metric-box"><div style="color:#94A3B8;font-size:0.72rem;">ZONES ACTIVE</div><div style="font-size:1.45rem;font-weight:700;color:#F8FAFC;">{len(zones_df)} Basins</div></div>', unsafe_allow_html=True)
k2.markdown(f'<div class="metric-box"><div style="color:#94A3B8;font-size:0.72rem;">USGS QUAKES (24H)</div><div style="font-size:1.45rem;font-weight:700;color:#38BDF8;">{len(res["quakes"])} Events</div></div>', unsafe_allow_html=True)
k3.markdown(f'<div class="metric-box"><div style="color:#94A3B8;font-size:0.72rem;">SWEEPS LOGGED</div><div style="font-size:1.45rem;font-weight:700;color:#F8FAFC;">{res["memory"]["total_sweeps"]}</div></div>', unsafe_allow_html=True)
k4.markdown(f'<div class="metric-box"><div style="color:#94A3B8;font-size:0.72rem;">AI TIER</div><div style="font-size:1.05rem;font-weight:700;color:#F8FAFC;padding-top:0.2rem;">{res["synthesis"]["model"]}</div></div>', unsafe_allow_html=True)

st.markdown("")
wf_nodes = [
    {"title": "OSM Geocode Trigger", "role": "Commander", "phase": "TRIGGER", "metric": f"{len(zones_df)} basins", "payload": f"Target city '{custom_city}' resolved alongside Western Maharashtra basins", "confidence": 0.98, "color": "#38BDF8", "icon": "🛰️"},
    {"title": "HydroMetSensor", "role": "Scout 1", "phase": "HYDRO", "metric": f"{top_zone.get('rain_48h_mm', 0)} mm max", "payload": msgs[0]["content"] if len(msgs) > 0 else "Queried 48h Rain + GloFAS discharge", "confidence": msgs[0]["confidence"] if len(msgs) > 0 else 0.94, "color": "#0EA5E9", "icon": "🌧️"},
    {"title": "SeismicFeedScout", "role": "Scout 2", "phase": "SEISMIC", "metric": f"{len(res['quakes'])} quakes", "payload": msgs[1]["content"] if len(msgs) > 1 else "Ingested USGS M2.5+ feed", "confidence": msgs[1]["confidence"] if len(msgs) > 1 else 0.95, "color": "#A855F7", "icon": "🌋"},
    {"title": "VulnerabilityCritic", "role": "Critic", "phase": "FUSE", "metric": f"Peak {top_zone.get('composite_risk', 0)}/100", "payload": msgs[2]["content"] if len(msgs) > 2 else res["top_tier"], "confidence": msgs[2]["confidence"] if len(msgs) > 2 else 0.92, "color": "#F97316", "icon": "🛡️"},
    {"title": "CivilDispatchRouter", "role": "Planner", "phase": "DISPATCH", "metric": f"{len(res['dispatch_plan'])} protocols", "payload": msgs[3]["content"] if len(msgs) > 3 else "Generated NDMA alerts", "confidence": msgs[3]["confidence"] if len(msgs) > 3 else 0.93, "color": "#22C55E", "icon": "📢"},
    {"title": "Hazard Memory + Map", "role": "Memory", "phase": "PERSIST", "metric": res["synthesis"]["provider"].split()[0], "payload": f"Updated {res['memory']['total_sweeps']} historical sweeps", "confidence": 0.99, "color": "#38BDF8", "icon": "🗺️"},
]
render_n8n_workflow(
    wf_nodes,
    theme={"mode": "dark", "bg": "#081020", "card_bg": "#111C33", "border": "rgba(56,189,248,0.3)", "accent": "#38BDF8", "text": "#F8FAFC", "muted": "#94A3B8"},
    engine_label=f"GeoShield Spatial DAG · {res['synthesis']['provider']}",
)

t_map, t_matrix, t_peas = st.tabs(["Spatial Radar & Hazard Breakdown", "Dispatch & Seismic Tables", "Agent Bus & Memory"])

with t_map:
    col_l, col_r = st.columns([1.3, 1])
    with col_l:
        fig_geo = go.Figure()
        fig_geo.add_trace(
            go.Scattergeo(
                lat=zones_df["lat"],
                lon=zones_df["lon"],
                text=[f"{r['region']} ({r['composite_risk']}/100)" for _, r in zones_df.iterrows()],
                marker=dict(size=[max(14, r["composite_risk"] * 0.5) for _, r in zones_df.iterrows()], color=zones_df["composite_risk"], colorscale="YlOrRd", cmin=0, cmax=100, line=dict(width=1.4, color="#F8FAFC"), colorbar=dict(title="Risk")),
                name="Basins",
            )
        )
        if res["quakes"]:
            qdf = pd.DataFrame(res["quakes"][:25])
            fig_geo.add_trace(go.Scattergeo(lat=qdf["lat"], lon=qdf["lon"], text=[f"M{r['mag']:.1f} {r['place']}" for _, r in qdf.iterrows()], marker=dict(size=qdf["mag"] * 2.4, color="#38BDF8", symbol="diamond", opacity=0.75), name="USGS Quakes"))
        fig_geo.update_layout(
            geo=dict(bgcolor="rgba(15,23,42,0.5)", landcolor="#1E293B", oceancolor="#0B1324", showocean=True, showcountries=True, countrycolor="#334155", center=dict(lat=float(zones_df["lat"].mean()), lon=float(zones_df["lon"].mean())), projection_scale=4.5),
            paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#E2E8F0"), height=340, margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h", y=1.02),
        )
        st.plotly_chart(fig_geo, width="stretch")

    with col_r:
        fig_stack = go.Figure()
        fig_stack.add_trace(go.Bar(name="48h Rain (mm)", x=zones_df["region"], y=zones_df["rain_48h_mm"], marker_color="#38BDF8"))
        fig_stack.add_trace(go.Bar(name="Wind Gust (km/h)", x=zones_df["region"], y=zones_df["max_wind_gust_kmh"], marker_color="#A855F7"))
        fig_stack.add_trace(go.Bar(name="Composite Risk", x=zones_df["region"], y=zones_df["composite_risk"], marker_color="#F97316"))
        fig_stack.update_layout(barmode="group", title="Multi-Hazard Drivers by Region", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(15,23,42,0.55)", font=dict(color="#E2E8F0"), height=340, margin=dict(l=10, r=10, t=35, b=10))
        st.plotly_chart(fig_stack, width="stretch")

    st.dataframe(
        zones_df[["region", "alert_tier", "composite_risk", "rain_48h_mm", "peak_discharge_m3s", "max_wind_gust_kmh", "nearest_quake"]],
        width="stretch",
        hide_index=True,
        column_config={
            "composite_risk": st.column_config.ProgressColumn("Composite Risk", min_value=0, max_value=100, format="%.1f/100"),
            "rain_48h_mm": st.column_config.NumberColumn("48h Rain", format="%.1f mm"),
            "peak_discharge_m3s": st.column_config.NumberColumn("River Flow", format="%.1f m³/s"),
        },
    )
    with st.expander(f"AI Readiness Summary ({res['synthesis']['provider']})", expanded=False):
        st.write(res["synthesis"]["text"])

with t_matrix:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### NDMA Dispatch Matrix")
        st.dataframe(pd.DataFrame(res["dispatch_plan"]), width="stretch", hide_index=True)
    with c2:
        st.markdown("#### Live USGS M2.5+ Feed")
        if res["quakes"]:
            st.dataframe(pd.DataFrame(res["quakes"][:15])[["mag", "place", "depth_km", "lat", "lon"]], width="stretch", hide_index=True)

with t_peas:
    mdf = pd.DataFrame(msgs)
    if not mdf.empty:
        st.plotly_chart(px.bar(mdf, x="sender", y="confidence", color="phase", title="Sub-Agent Confidence", height=240).update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(15,23,42,0.55)", font=dict(color="#E2E8F0")), width="stretch")
        st.dataframe(mdf[["phase", "sender", "recipient", "confidence", "content"]], width="stretch", hide_index=True)
    if res["memory"].get("dispatch_history"):
        hist_df = pd.DataFrame(res["memory"]["dispatch_history"])
        st.plotly_chart(px.area(hist_df, x="timestamp_utc", y="peak_risk", title="Historical Peak Risk Trend", height=220).update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(15,23,42,0.55)", font=dict(color="#E2E8F0")), width="stretch")
    st.table(pd.DataFrame([{"PEAS": "P", "Spec": "Flood/quake recall & low false alarm"}, {"PEAS": "E", "Spec": "Open-Meteo, GloFAS, USGS, OSM Nominatim"}, {"PEAS": "A", "Spec": "Geo Radar, NDMA Protocols, Memory Logger"}, {"PEAS": "S", "Spec": "Hydro rain/soil, River m³/s, Seismic JSON"}]))
