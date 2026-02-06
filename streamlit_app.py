import streamlit as st
import osmnx as ox
import networkx as nx
import math
import gpxpy
import gpxpy.gpx
import folium
from streamlit_folium import st_folium
from collections import defaultdict

# -----------------------------
# Constants
# -----------------------------
MINUTES_PER_KM = 5
CALORIES_PER_KM = 60

# -----------------------------
# Styles
# -----------------------------
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        .green-box {
            background:#f0f7f4;
            padding:25px;
            border-radius:15px;
            margin-bottom:20px;
            text-align:center;
        }
        .blue-box {
            background:#eef3ff;
            padding:25px;
            border-radius:15px;
            margin-bottom:20px;
            text-align:center;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# -----------------------------
# Session state
# -----------------------------
st.session_state.setdefault("clicks", [])
st.session_state.setdefault("routes", None)
st.session_state.setdefault("graph", None)
st.session_state.setdefault("transport_mode", "🏃 Running")

# -----------------------------
# Helpers
# -----------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def nearest_node_manual(G, lat, lon):
    best, best_dist = None, float("inf")
    for n, d in G.nodes(data=True):
        dist = haversine(lat, lon, d["y"], d["x"])
        if dist < best_dist:
            best, best_dist = n, dist
    return best


def path_length(G, path):
    return sum(G[u][v][0]["length"] for u, v in zip(path[:-1], path[1:]))


def overlap_ratio(path_a, path_b):
    edges_a = set(zip(path_a[:-1], path_a[1:]))
    edges_b = set(zip(path_b[:-1], path_b[1:]))
    return len(edges_a & edges_b) / max(len(edges_a), 1)


def generate_loop_routes(G, start, target_distance, tolerance, k=3):
    routes = []
    lengths, paths = nx.single_source_dijkstra(G, start, weight="length")

    for mid, out_dist in lengths.items():
        if abs(out_dist - target_distance / 2) > tolerance:
            continue

        try:
            back = nx.shortest_path(G, mid, start, weight="length")
            total = out_dist + path_length(G, back)

            if abs(total - target_distance) > tolerance:
                continue

            if overlap_ratio(paths[mid], back) > 0.3:
                continue  # reject out-and-back

            routes.append(paths[mid] + back[1:])
            if len(routes) >= k:
                break

        except nx.NetworkXNoPath:
            continue

    return routes


def surface_breakdown(G, route):
    totals = defaultdict(float)
    total = 0

    for u, v in zip(route[:-1], route[1:]):
        edge = G[u][v][0]
        length = edge["length"]
        total += length
        key = edge.get("surface") or edge.get("highway") or "unknown"
        totals[str(key)] += length

    return {k: int((v / total) * 100) for k, v in totals.items()}


def route_flow(route, km):
    turns = sum(1 for i in range(len(route) - 2) if route[i] != route[i + 2])
    tpk = turns / max(km, 0.1)
    return "Smooth 🟢" if tpk < 12 else "Moderate 🟡" if tpk < 20 else "Twisty 🔴"


def format_time(minutes):
    m = int(minutes)
    s = int((minutes - m) * 60)
    return f"{m}:{s:02d}"


def route_to_gpx(G, route):
    gpx = gpxpy.gpx.GPX()
    track = gpxpy.gpx.GPXTrack()
    seg = gpxpy.gpx.GPXTrackSegment()
    track.segments.append(seg)
    gpx.tracks.append(track)

    for n in route:
        seg.points.append(gpxpy.gpx.GPXTrackPoint(G.nodes[n]["y"], G.nodes[n]["x"]))

    return gpx.to_xml()


def folium_route_preview(G, route):
    coords = [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in route]
    m = folium.Map(location=coords[0], zoom_start=14)
    folium.PolyLine(coords, weight=5).add_to(m)
    m.fit_bounds(coords)
    return m

# -----------------------------
# Header
# -----------------------------
st.markdown(
    """
    <div class="green-box">
        <h1>GPX Route Generator</h1>
        <p>Click on the map to dictate where routes should start and/or end.
        Use 1 click for auto generated routes.</p>
    </div>
    """,
    unsafe_allow_html=True
)

# -----------------------------
# Sport type (centered)
# -----------------------------
st.markdown('<div class="blue-box"><h3>Sport type</h3></div>', unsafe_allow_html=True)
_, mid, _ = st.columns([1, 2, 1])
with mid:
    st.session_state.transport_mode = st.radio(
        "sport",
        ["🏃 Running", "🚴 Cycling", "🚶 Walking / Hiking"],
        horizontal=True,
        label_visibility="collapsed",
    )

st.markdown(
    f'<div class="blue-box" style="padding:10px;"><b>Selected mode:</b> {st.session_state.transport_mode}</div>',
    unsafe_allow_html=True,
)

# -----------------------------
# Route type (centered)
# -----------------------------
st.markdown('<div class="blue-box"><h3>Route type</h3></div>', unsafe_allow_html=True)
_, mid, _ = st.columns([1, 2, 1])
with mid:
    route_mode = st.radio(
        "route",
        ["Loop (1 click)", "Point-to-point (2 clicks)"],
        horizontal=True,
        label_visibility="collapsed",
    )

# -----------------------------
# Distance
# -----------------------------
st.markdown('<div class="blue-box"><h3>Distance</h3></div>', unsafe_allow_html=True)
target_distance = st.number_input("Target Distance (meters)", 500, 50000, 3000, 500)
tolerance = st.number_input("Distance Tolerance (meters)", 50, 5000, 300, 50)

# -----------------------------
# Map
# -----------------------------
m = folium.Map(location=[52, 5], zoom_start=6)
for i, (lat, lon) in enumerate(st.session_state.clicks):
    folium.Marker([lat, lon]).add_to(m)

map_data = st_folium(m, height=450, width=700)

if map_data and map_data.get("last_clicked"):
    max_clicks = 1 if route_mode.startswith("Loop") else 2
    if len(st.session_state.clicks) < max_clicks:
        st.session_state.clicks.append(
            (map_data["last_clicked"]["lat"], map_data["last_clicked"]["lng"])
        )

# -----------------------------
# Generate routes
# -----------------------------
if st.button("Generate Routes"):
    center = st.session_state.clicks[0]
    G = ox.graph_from_point(center, dist=10000, network_type="walk")
    G = G.to_undirected()
    start = nearest_node_manual(G, *center)

    if route_mode.startswith("Loop"):
        st.session_state.routes = generate_loop_routes(
            G, start, target_distance, tolerance
        )
    else:
        end = nearest_node_manual(G, *st.session_state.clicks[1])
        st.session_state.routes = [
            nx.shortest_path(G, start, end, weight="length")
        ]

    st.session_state.graph = G

# -----------------------------
# Display routes + download
# -----------------------------
if st.session_state.routes:
    G = st.session_state.graph
    cols = st.columns(len(st.session_state.routes))

    for i, (col, route) in enumerate(zip(cols, st.session_state.routes)):
        with col:
            length_m = path_length(G, route)
            km = length_m / 1000
            surfaces = surface_breakdown(G, route)
            flow = route_flow(route, km)

            st.markdown(
                f"""
                <div style="border:1px solid #ddd;border-radius:12px;padding:12px;">
                    <h4>Route {i+1}</h4>
                    <p><b>Distance:</b> {km:.2f} km</p>
                    <p><b>Est. Time:</b> ⏱️ {format_time(km * MINUTES_PER_KM)}</p>
                    <p><b>Calories:</b> 🔥 {int(km * CALORIES_PER_KM)} kcal</p>
                    <p><b>Flow:</b> {flow}</p>
                    <p><b>Surface:</b><br>
                    {" · ".join(f"{k} {v}%" for k, v in surfaces.items())}
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )

            st_folium(folium_route_preview(G, route), height=300, width=300)

            st.download_button(
                "⬇️ Download GPX",
                route_to_gpx(G, route),
                f"route_{i+1}.gpx",
                "application/gpx+xml",
            )
