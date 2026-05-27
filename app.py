"""
TypeCity Analytics — Choropleth Dashboard
==========================================
Page 1: City-wide metric explorer

  • 16×16 cell grid coloured by chosen metric
  • Subway lines overlaid (Orange N-S, Blue E-W)
  • Quarter boundary markers + labels
  • Per-cell hover detail
  • Quarter summary sidebar
  • Zoning breakdown bar chart

Run:
  streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="TypeCity Analytics",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Minimal CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* Metric cards in sidebar */
  .q-card {
      background: #1a1a2e;
      border-left: 4px solid;
      border-radius: 6px;
      padding: 12px 14px;
      margin-bottom: 10px;
  }
  .q-card.NW { border-color: #7eb8f7; }
  .q-card.NE { border-color: #ffd47e; }
  .q-card.SW { border-color: #a0a0a0; }
  .q-card.SE { border-color: #98d8a8; }
  .q-label   { font-size: 0.7rem; color: #888; text-transform: uppercase;
               letter-spacing: 0.08em; margin-bottom: 4px; }
  .q-value   { font-size: 1.45rem; font-weight: 700; color: #e0e0e0; }
  .q-sub     { font-size: 0.7rem; color: #999; margin-top: 2px; }
</style>
""", unsafe_allow_html=True)

# ── Data loading (cached) ─────────────────────────────────────────────────────
DATA_DIR = "typecity_data"

@st.cache_data
def load_data():
    cells     = pd.read_csv(f"{DATA_DIR}/cells.csv")
    quarters  = pd.read_csv(f"{DATA_DIR}/quarters.csv")
    districts = pd.read_csv(f"{DATA_DIR}/districts.csv")
    stations  = pd.read_csv(f"{DATA_DIR}/subway_stations.csv")
    ridership = pd.read_csv(f"{DATA_DIR}/ridership.csv")

    # Booleans survive CSV as strings — normalise
    stations["is_transfer"] = stations["is_transfer"].map(
        {"True": True, "False": False, True: True, False: False}
    )

    # Join district names into cells for hover text
    cells = cells.merge(
        districts[["district_id", "name"]].rename(columns={"name": "district_name"}),
        on="district_id", how="left",
    )

    # Total weekly boardings per station (for a quick reference)
    weekly = ridership.groupby("station_id")["boardings"].sum().reset_index()
    weekly.columns = ["station_id", "weekly_boardings"]
    stations = stations.merge(weekly, on="station_id", how="left")

    return cells, quarters, districts, stations

cells, quarters, districts, stations = load_data()


# ── Sidebar controls ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏙️ TypeCity")
    st.caption("Formal types meet real analytics.")
    st.divider()

    # Metric selector
    METRICS = {
        "Population":           ("population",            "Blues",   "pop"),
        "Avg Household Income": ("avg_household_income",  "Greens",  "income"),
        "Residential Units":    ("residential_units",     "Purples", "units"),
        "Commercial Units":     ("commercial_units",      "Oranges", "units"),
        "Park Coverage %":      ("park_pct",              "YlGn",    "pct"),
    }

    metric_label = st.selectbox("📊 Metric", list(METRICS.keys()))
    col, colorscale, fmt_key = METRICS[metric_label]

    def fmt_val(v):
        if   fmt_key == "pop":    return f"{int(v):,}"
        elif fmt_key == "income": return f"${int(v):,}"
        elif fmt_key == "pct":    return f"{v:.1%}"
        else:                     return f"{int(v):,}"

    st.divider()
    st.markdown("**Overlays**")
    show_subway   = st.toggle("Subway lines",     value=True)
    show_stations = st.toggle("Subway stations",  value=True)
    show_quarters = st.toggle("Quarter borders",  value=True)
    show_labels   = st.toggle("Quarter labels",   value=True)

    st.divider()
    st.markdown("**Quarter Summary**")

    q_stats = (
        cells.groupby("quarter_id")
             .agg(population=("population", "sum"),
                  avg_income=("avg_household_income", "mean"))
             .reset_index()
             .merge(quarters[["quarter_id", "character"]], on="quarter_id")
             .sort_values("population", ascending=False)
    )
    total_pop = cells["population"].sum()

    BORDER = {"NW": "#7eb8f7", "NE": "#ffd47e", "SW": "#a0a0a0", "SE": "#98d8a8"}

    for _, row in q_stats.iterrows():
        pct = row.population / total_pop * 100
        st.markdown(f"""
        <div class="q-card {row.quarter_id}">
          <div class="q-label">{row.quarter_id} · {row.character}</div>
          <div class="q-value">{int(row.population):,}</div>
          <div class="q-sub">{pct:.1f}% of city &nbsp;·&nbsp; avg ${int(row.avg_income):,}</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()
    st.markdown("**City totals**")
    c1, c2 = st.columns(2)
    c1.metric("Population",  f"{total_pop:,}")
    c2.metric("Cells",       "256")
    c1.metric("Districts",   "16")
    c2.metric("Stations",    "17")


# ── Build hover-text matrix (16×16) ──────────────────────────────────────────
# Iterate y=15→0 (North at top) × x=0→15 (West to East)
hover_matrix = []
for y_val in range(15, -1, -1):
    row_texts = []
    for x_val in range(16):
        c = cells.loc[(cells.x == x_val) & (cells.y == y_val)].iloc[0]
        row_texts.append(
            f"<b>{c['district_name']}</b> &nbsp;·&nbsp; {c['quarter_id']}<br>"
            f"<span style='color:#aaa'>{c['cell_id']}</span><br>"
            f"── ── ── ── ── ──<br>"
            f"<b>{metric_label}:</b>  {fmt_val(c[col])}<br>"
            f"Population: {int(c['population']):,}<br>"
            f"Income: ${int(c['avg_household_income']):,}<br>"
            f"Zoning: {c['zoning_type']}<br>"
            f"Grid: ({x_val}, {y_val})"
        )
    hover_matrix.append(row_texts)


# ── Pivot metric to 16×16 matrix ─────────────────────────────────────────────
pivot = cells.pivot(index="y", columns="x", values=col)
z     = pivot.values[::-1].astype(float)   # row 0 = y=15 (North)


# ── Build Plotly figure ───────────────────────────────────────────────────────
fig = go.Figure()

# — Heatmap base layer —
fig.add_trace(go.Heatmap(
    z=z,
    x=list(range(16)),
    y=list(range(15, -1, -1)),
    colorscale=colorscale,
    showscale=True,
    hoverinfo="text",
    text=hover_matrix,
    hoverlabel=dict(bgcolor="#1a1a2e", font_color="#e0e0e0", font_size=12),
    colorbar=dict(
        thickness=14, len=0.85,
        bgcolor="rgba(0,0,0,0)",
        tickfont=dict(color="#aaa", size=10),
        title=dict(text=fmt_key, font=dict(color="#aaa", size=11), side="right"),
    ),
    xgap=1.5,
    ygap=1.5,
))

# — Quarter borders —
if show_quarters:
    border_style = dict(color="rgba(255,255,255,0.55)", width=2, dash="dot")
    # Vertical divider (x = 7.5)
    fig.add_shape(type="line",
        x0=7.5, x1=7.5, y0=-0.5, y1=15.5, line=border_style)
    # Horizontal divider (y = 7.5)
    fig.add_shape(type="line",
        x0=-0.5, x1=15.5, y0=7.5, y1=7.5, line=border_style)

# — Quarter labels —
if show_labels:
    for label, lx, ly in [("NW", 3.5, 11.5), ("NE", 11.5, 11.5),
                           ("SW", 3.5,  3.5), ("SE", 11.5,  3.5)]:
        fig.add_annotation(
            x=lx, y=ly, text=f"<b>{label}</b>",
            showarrow=False,
            font=dict(color="rgba(255,255,255,0.18)", size=40),
            xanchor="center", yanchor="middle",
        )

# — Subway lines —
if show_subway:
    # Orange Line: x = 8 (N-S spine)
    fig.add_shape(type="line",
        x0=8, x1=8, y0=-0.5, y1=15.5,
        line=dict(color="#FF8C00", width=3.5))

    # Blue Line: y = 8 (E-W spine)
    fig.add_shape(type="line",
        x0=-0.5, x1=15.5, y0=8, y1=8,
        line=dict(color="#1E90FF", width=3.5))

    # Legend annotations
    fig.add_annotation(x=8.3, y=15.0,
        text="<b>Orange Line</b>", showarrow=False,
        font=dict(color="#FF8C00", size=11), xanchor="left")
    fig.add_annotation(x=0.2, y=8.45,
        text="<b>Blue Line</b>", showarrow=False,
        font=dict(color="#1E90FF", size=11), xanchor="left")

# — Station markers —
if show_subway and show_stations:
    # Non-transfer Orange stations (exclude OL-5 Central, exclude y=16 terminus)
    ol = stations[
        stations.station_id.str.startswith("OL") &
        (~stations.is_transfer) &
        (stations.y <= 15)
    ]
    fig.add_trace(go.Scatter(
        x=ol.x, y=ol.y,
        mode="markers",
        marker=dict(color="#FF8C00", size=10, symbol="circle",
                    line=dict(color="#1a1a2e", width=2)),
        hovertext=ol.apply(
            lambda r: f"<b>{r['name']}</b><br>🟠 Orange Line<br>"
                      f"Mile {int(r.y)} · Stop {r.station_id}<br>"
                      f"Weekly boardings: {int(r.weekly_boardings):,}",
            axis=1
        ),
        hoverinfo="text",
        hoverlabel=dict(bgcolor="#1a1a2e", font_color="#e0e0e0"),
        showlegend=False,
    ))

    # Non-transfer Blue stations (exclude BL-5 Central, exclude x=16 terminus)
    bl = stations[
        stations.station_id.str.startswith("BL") &
        (~stations.is_transfer) &
        (stations.x <= 15)
    ]
    fig.add_trace(go.Scatter(
        x=bl.x, y=bl.y,
        mode="markers",
        marker=dict(color="#1E90FF", size=10, symbol="circle",
                    line=dict(color="#1a1a2e", width=2)),
        hovertext=bl.apply(
            lambda r: f"<b>{r['name']}</b><br>🔵 Blue Line<br>"
                      f"Mile {int(r.x)} · Stop {r.station_id}<br>"
                      f"Weekly boardings: {int(r.weekly_boardings):,}",
            axis=1
        ),
        hoverinfo="text",
        hoverlabel=dict(bgcolor="#1a1a2e", font_color="#e0e0e0"),
        showlegend=False,
    ))

    # Central Station — special star marker
    central = stations[stations.station_id == "OL-5"].iloc[0]
    fig.add_trace(go.Scatter(
        x=[central.x], y=[central.y],
        mode="markers+text",
        marker=dict(color="white", size=16, symbol="star",
                    line=dict(color="#333", width=1.5)),
        text=["Central Station"],
        textposition="top right",
        textfont=dict(color="white", size=10, family="monospace"),
        hovertext=[
            f"<b>Central Station</b><br>"
            f"🟠 Orange + 🔵 Blue Lines<br>"
            f"Transfer hub · Mile 8 × Mile 8<br>"
            f"OL weekly: {int(stations[stations.station_id=='OL-5']['weekly_boardings'].iloc[0]):,}<br>"
            f"BL weekly: {int(stations[stations.station_id=='BL-5']['weekly_boardings'].iloc[0]):,}"
        ],
        hoverinfo="text",
        hoverlabel=dict(bgcolor="#1a1a2e", font_color="#e0e0e0"),
        showlegend=False,
    ))

# — Layout —
fig.update_layout(
    title=dict(
        text=f"TypeCity · {metric_label}  <span style='color:#666;font-size:14px'>"
             f"(16 × 16 mile grid · {col})</span>",
        font=dict(size=17, color="#e0e0e0"),
        x=0.0, xanchor="left", pad=dict(l=0),
    ),
    paper_bgcolor="#0e1117",
    plot_bgcolor="#0e1117",
    xaxis=dict(
        title=dict(text="West  →  East (miles)", font=dict(color="#666", size=11)),
        tickvals=list(range(16)),
        ticktext=[str(i) for i in range(16)],
        showgrid=False, zeroline=False,
        color="#666", tickfont=dict(size=10),
        range=[-0.5, 15.5],
    ),
    yaxis=dict(
        title=dict(text="South  →  North (miles)", font=dict(color="#666", size=11)),
        tickvals=list(range(16)),
        ticktext=[str(i) for i in range(16)],
        showgrid=False, zeroline=False,
        color="#666", tickfont=dict(size=10),
        range=[-0.5, 15.5],
        scaleanchor="x",
        scaleratio=1,
    ),
    margin=dict(l=55, r=20, t=55, b=50),
)


# ── Main page ─────────────────────────────────────────────────────────────────
st.markdown("## 🏙️ TypeCity Analytics")
st.caption(
    "A formally-specified fictional city — explored through SQL, pandas, and data viz. "
    "Use the sidebar to change the metric and toggle overlays."
)
st.divider()

st.plotly_chart(fig, use_container_width=True)

st.divider()


# ── Zoning breakdown ──────────────────────────────────────────────────────────
with st.expander("📊 Zoning Distribution by Quarter", expanded=True):
    zone_counts = (
        cells.groupby(["quarter_id", "zoning_type"])["cell_id"]
             .count()
             .unstack(fill_value=0)
    )
    zone_pct = (zone_counts.div(zone_counts.sum(axis=1), axis=0) * 100).reset_index()
    zone_long = zone_pct.melt(id_vars="quarter_id",
                               var_name="Zoning Type",
                               value_name="Percent of Cells")

    ZONE_COLORS = {
        "Residential": "#7eb8f7",
        "Commercial":  "#ffd47e",
        "Industrial":  "#a0a0a0",
        "Mixed":       "#98d8a8",
        "Park":        "#5ab552",
    }

    zone_fig = px.bar(
        zone_long,
        x="quarter_id", y="Percent of Cells", color="Zoning Type",
        barmode="stack",
        color_discrete_map=ZONE_COLORS,
        text_auto=".0f",
        labels={"quarter_id": "Quarter"},
        category_orders={"quarter_id": ["NW", "NE", "SW", "SE"]},
    )
    zone_fig.update_traces(texttemplate="%{y:.0f}%", textposition="inside",
                           textfont_size=11, textfont_color="rgba(0,0,0,0.7)")
    zone_fig.update_layout(
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        font_color="#ccc",
        legend_title_text="Zoning Type",
        height=320,
        margin=dict(l=40, r=20, t=20, b=30),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.07)"),
        bargap=0.25,
    )
    st.plotly_chart(zone_fig, use_container_width=True)


# ── Raw data explorer (collapsed by default) ──────────────────────────────────
with st.expander("🗃️ Raw cell data"):
    q_filter = st.multiselect(
        "Filter by Quarter",
        options=["NW", "NE", "SW", "SE"],
        default=["NW", "NE", "SW", "SE"],
    )
    z_filter = st.multiselect(
        "Filter by Zoning",
        options=sorted(cells.zoning_type.unique()),
        default=sorted(cells.zoning_type.unique()),
    )

    display_cols = [
        "cell_id", "quarter_id", "district_name", "x", "y",
        "population", "avg_household_income", "zoning_type",
        "residential_units", "commercial_units", "park_pct",
    ]
    filtered = cells[
        cells.quarter_id.isin(q_filter) &
        cells.zoning_type.isin(z_filter)
    ][display_cols].sort_values(["quarter_id", "y", "x"])

    st.dataframe(filtered, use_container_width=True, height=300)
    st.caption(f"{len(filtered)} cells shown")
