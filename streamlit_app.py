import streamlit as st
import osmnx as ox
import networkx as nx
import math
import gpxpy
import gpxpy.gpx
import folium
from streamlit_folium import st_folium
import matplotlib.pyplot as plt

# -----------------------------
# Simple estimation rules (easy to tweak)
# -----------------------------
MINUTES_PER_KM = 5
CALORIES_PER_KM = 60

# -----------------------------
# Page polish (padding)
# -----------------------------
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# -----------------------------
# Session state
# -----------------------------
if "clicks" not in st.session_state:
    st.session_state.clicks = []

# -----------------------------
# Helper: manual nearest node
# -----------------------------
def nearest_node_manual(G, lat, lon):
    min_dist = float("inf")
    nearest = None

    for node, data in G.nodes(data=True):
        node_lat = data["y"]
        node_lon = data["x"]

        R = 6371000
        phi1 = math.radians(lat)
        phi2 = math.radians(node_lat)
        dphi = math.radians(node_lat - lat)
        dlambda = math.radians(node_lon - lon)

        a = (
            math.sin(dphi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        d = R * c

        if d < min_dist:
            min_dist = d
            nearest = node

    return nearest

# -----------------------------
# Helper: fast route generation
# -----------------------------
def generate_alternative_routes(G, start, end, target_distance, tolerance, k=3):
    routes = []

    lengths, paths = nx.single_source_dijkstra(G, start, weight="length")

    for mid_node, dist1 in lengths.items():
        if abs(dist1 - target_distance / 2) > tolerance:
            continue

        try:
            path2 = nx.shortest_path(G, mid_node, end, weight="length")
            dist2 = sum(
                G[u][v][0]["length"]
                for u, v in zip(path2[:-1], path2[1:])
            )

            total = dist1 + dist2

            if abs(total - target_distance) <= tolerance:
                routes.append(paths[mid_node] + path2[1:])
                if len(routes) >= k:
                    break

        except nx.NetworkXNoPath:
            continue

    return routes

# -----------------------------
# Helper: GPX export
# -----------------------------
def route_to_gpx(G, route):
    gpx = gpxpy.gpx.GPX()
    track = gpxpy.gpx.GPXTrack()
    segment = gpxpy.gpx.GPXTrackSegment()
    gpx.tracks.append(track)
    track.segments.append(segment)

    for node in route:
        data = G.nodes[node]
        segment.points.append(
            gpxpy.gpx.GPXTrackPoint(data["y"], data["x"])
        )

    return gpx.to_xml()

# -----------------------------
# Helper: tight route plot
# -----------------------------
def plot_zoomed_route(G, route, padding=0.001):
    xs = [G.nodes[n]["x"] for n in route]
    ys = [G.nodes[n]["y"] for n in route]

    fig, ax = ox.plot_graph_route(
        G,
        route,
        show=False,
        close=False,
        figsize=(4, 4),
        node_size=0
    )

    ax.set_xlim(min(xs) - padding, max(xs) + padding)
    ax.set_ylim(min(ys) - padding, max(ys) + padding)
    ax.axis("off")

    return fig

# -----------------------------
# Helper: formatting
# -----------------------------
def format_time(minutes):
    m = int(minutes)
    s = int((minutes - m) * 60)
    return f"{m}:{s:02d}"

# -----------------------------
# Hero header
# -----------------------------
st.markdown(
    """
    <div style="
        background-color:#f0f7f4;
        padding:25px;
        border-radius:15px;
        text-align:center;
        margin-bottom:25px;
        border:1px solid #cce3dc;
    ">
        <h1 style="margin-bottom:10px;">🏃 Trail Runner Route GPX Generator</h1>
        <p style="font-size:16px; color:#444;">
            Click on the map to select your start/end point. Trails load automatically.
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

# -----------------------------
# Controls
# -----------------------------
route_mode = st.radio(
    "Route Type",
    ["Loop (1 click)", "Point-to-point (2 clicks)"]
)

target_distance = st.number_input(
    "Target Distance (meters)", value=3000, step=500
)

tolerance = st.number_input(
    "Distance Tolerance (meters)", value=300, step=100
)

if st.button("Reset map clicks"):
    st.session_state.clicks = []

# -----------------------------
# Map
# -----------------------------
m = folium.Map(location=[52, 5], zoom_start=6)

for i, (lat, lon) in enumerate(st.session_state.clicks):
    folium.Marker(
        [lat, lon],
        popup="Start" if i == 0 else "End",
        icon=folium.Icon(color="green" if i == 0 else "red"),
    ).add_to(m)

map_data = st_folium(m, height=450, width=700)

if map_data and map_data.get("last_clicked"):
    lat = map_data["last_clicked"]["lat"]
    lon = map_data["last_clicked"]["lng"]
    max_clicks = 1 if route_mode.startswith("Loop") else 2

    if len(st.session_state.clicks) < max_clicks:
        st.session_state.clicks.append((lat, lon))

# -----------------------------
# Generate Routes
# -----------------------------
if st.button("Generate Routes"):
    needed = 1 if route_mode.startswith("Loop") else 2

    if len(st.session_state.clicks) < needed:
        st.warning("Please click on the map.")
        st.stop()

    with st.spinner("Loading trails & generating routes..."):
        center_lat, center_lon = st.session_state.clicks[0]

        G = ox.graph_from_point(
            (center_lat, center_lon),
            dist=10000,
            network_type="walk",
            simplify=True,
            custom_filter='["highway"~"path|footway|track"]'
        )

        G = G.to_undirected()
        G = G.subgraph(max(nx.connected_components(G), key=len)).copy()

        start_lat, start_lon = st.session_state.clicks[0]
        end_lat, end_lon = (
            (start_lat, start_lon)
            if route_mode.startswith("Loop")
            else st.session_state.clicks[1]
        )

        start_node = nearest_node_manual(G, start_lat, start_lon)
        end_node = nearest_node_manual(G, end_lat, end_lon)

        routes = generate_alternative_routes(
            G, start_node, end_node, target_distance, tolerance
        )

    if not routes:
        st.warning("No routes found. Try adjusting distance or tolerance.")
    else:
        st.success(f"{len(routes)} routes generated!")

        cols = st.columns(len(routes))
        for i, (col, r) in enumerate(zip(cols, routes)):
            with col:
                length_m = sum(
                    G[u][v][0]["length"]
                    for u, v in zip(r[:-1], r[1:])
                )

                distance_km = length_m / 1000
                est_time_min = distance_km * MINUTES_PER_KM
                est_cal = distance_km * CALORIES_PER_KM

                st.markdown(
                    f"""
                    <div style="
                        border:1px solid #ddd;
                        border-radius:12px;
                        padding:12px;
                        background-color:#fafafa;
                    ">
                        <h4 style="margin-bottom:8px;">Route {i+1}</h4>
                        <p><strong>Distance:</strong> {distance_km:.2f} km</p>
                        <p><strong>Est. Time:</strong> ⏱️ {format_time(est_time_min)}</p>
                        <p><strong>Est. Calories:</strong> 🔥 {int(est_cal)} kcal</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                fig = plot_zoomed_route(G, r)
                st.pyplot(fig)

                st.download_button(
                    "⬇️ Download GPX",
                    route_to_gpx(G, r),
                    file_name=f"route_{i+1}.gpx",
                    mime="application/gpx+xml",
                )
