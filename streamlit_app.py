import streamlit as st
import osmnx as ox
import networkx as nx
import math
import gpxpy
import gpxpy.gpx
import folium
from streamlit_folium import st_folium

# -----------------------------
# Page styling
# -----------------------------
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        .route-card {
            border: 1px solid #ddd;
            border-radius: 14px;
            padding: 15px;
            margin-bottom: 20px;
            background-color: #fafafa;
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
# Helper: nearest node (cloud-safe)
# -----------------------------
def nearest_node_manual(G, lat, lon):
    min_dist = float("inf")
    nearest = None
    for node, data in G.nodes(data=True):
        dlat = math.radians(data["y"] - lat)
        dlon = math.radians(data["x"] - lon)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat)) * math.cos(math.radians(data["y"])) * math.sin(dlon/2)**2
        d = 6371000 * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        if d < min_dist:
            min_dist = d
            nearest = node
    return nearest

# -----------------------------
# Route generation (fast)
# -----------------------------
def generate_alternative_routes(G, start, end, target_distance, tolerance, k=3):
    routes = []
    lengths, paths = nx.single_source_dijkstra(G, start, weight="length")

    for mid, d1 in lengths.items():
        if abs(d1 - target_distance / 2) > tolerance:
            continue
        try:
            path2 = nx.shortest_path(G, mid, end, weight="length")
            d2 = sum(G[u][v][0]["length"] for u, v in zip(path2[:-1], path2[1:]))
            if abs(d1 + d2 - target_distance) <= tolerance:
                routes.append(paths[mid] + path2[1:])
                if len(routes) >= k:
                    break
        except nx.NetworkXNoPath:
            continue
    return routes

# -----------------------------
# GPX export
# -----------------------------
def route_to_gpx(G, route):
    gpx = gpxpy.gpx.GPX()
    seg = gpxpy.gpx.GPXTrackSegment()
    track = gpxpy.gpx.GPXTrack()
    gpx.tracks.append(track)
    track.segments.append(seg)
    for n in route:
        seg.points.append(gpxpy.gpx.GPXTrackPoint(G.nodes[n]["y"], G.nodes[n]["x"]))
    return gpx.to_xml()

# -----------------------------
# Folium route map (zoomed & square)
# -----------------------------
def make_route_map(G, route, color):
    coords = [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in route]
    lats, lons = zip(*coords)

    m = folium.Map(tiles="OpenStreetMap")
    folium.PolyLine(coords, color=color, weight=5).add_to(m)
    m.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]])
    return m

# -----------------------------
# Header
# -----------------------------
st.markdown(
    """
    <div style="
        background:#f0f7f4;
        padding:25px;
        border-radius:16px;
        text-align:center;
        border:1px solid #cce3dc;
        margin-bottom:25px;">
        <h1>🏃 Trail Runner Route GPX Generator</h1>
        <p>Click on the map to select your start/end point. Trails load automatically.</p>
    </div>
    """,
    unsafe_allow_html=True
)

# -----------------------------
# Controls
# -----------------------------
route_mode = st.radio("Route Type", ["Loop (1 click)", "Point-to-point (2 clicks)"])
target_distance = st.number_input("Target Distance (meters)", 3000, step=500)
tolerance = st.number_input("Distance Tolerance (meters)", 300, step=100)

if st.button("Reset map clicks"):
    st.session_state.clicks = []

# -----------------------------
# Click map
# -----------------------------
click_map = folium.Map(location=[52, 5], zoom_start=6)
for i, (lat, lon) in enumerate(st.session_state.clicks):
    folium.Marker([lat, lon], icon=folium.Icon(color="green" if i == 0 else "red")).add_to(click_map)

click_data = st_folium(click_map, height=450)

if click_data and click_data.get("last_clicked"):
    if len(st.session_state.clicks) < (1 if route_mode.startswith("Loop") else 2):
        st.session_state.clicks.append(
            (click_data["last_clicked"]["lat"], click_data["last_clicked"]["lng"])
        )

# -----------------------------
# Generate routes
# -----------------------------
if st.button("Generate Routes"):
    if len(st.session_state.clicks) < (1 if route_mode.startswith("Loop") else 2):
        st.warning("Please click on the map first.")
        st.stop()

    with st.spinner("Generating routes..."):
        center_lat, center_lon = st.session_state.clicks[0]
        G = ox.graph_from_point(
            (center_lat, center_lon),
            dist=10000,
            network_type="walk",
            simplify=True,
            custom_filter='["highway"~"path|footway|track"]'
        ).to_undirected()

        G = G.subgraph(max(nx.connected_components(G), key=len)).copy()

        start_lat, start_lon = st.session_state.clicks[0]
        end_lat, end_lon = (start_lat, start_lon) if route_mode.startswith("Loop") else st.session_state.clicks[1]

        start_node = nearest_node_manual(G, start_lat, start_lon)
        end_node = nearest_node_manual(G, end_lat, end_lon)

        routes = generate_alternative_routes(G, start_node, end_node, target_distance, tolerance)

    if not routes:
        st.warning("No routes found. Try adjusting distance or tolerance.")
    else:
        st.success(f"{len(routes)} routes generated!")

        colors = ["#2ecc71", "#3498db", "#e67e22"]

        for i, route in enumerate(routes):
            length = sum(G[u][v][0]["length"] for u, v in zip(route[:-1], route[1:]))

            st.markdown(f"""
            <div class="route-card">
                <h4>Route {i+1} — {length/1000:.2f} km</h4>
            </div>
            """, unsafe_allow_html=True)

            route_map = make_route_map(G, route, colors[i % len(colors)])
            st_folium(route_map, height=300)

            st.download_button(
                "⬇️ Download GPX",
                route_to_gpx(G, route),
                file_name=f"route_{i+1}.gpx",
                mime="application/gpx+xml"
            )
