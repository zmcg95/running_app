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
# Simple estimation rules
# -----------------------------
MINUTES_PER_KM = 5
CALORIES_PER_KM = 60

# -----------------------------
# Page polish
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
# Helpers
# -----------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def nearest_node_manual(G, lat, lon):
    best = None
    best_dist = float("inf")

    for n, d in G.nodes(data=True):
        dist = haversine(lat, lon, d["y"], d["x"])
        if dist < best_dist:
            best_dist = dist
            best = n
    return best


def generate_alternative_routes(G, start, end, target_distance, tolerance, k=3):
    routes = []
    lengths, paths = nx.single_source_dijkstra(G, start, weight="length")

    for mid, dist1 in lengths.items():
        if abs(dist1 - target_distance / 2) > tolerance:
            continue
        try:
            path2 = nx.shortest_path(G, mid, end, weight="length")
            dist2 = sum(G[u][v][0]["length"] for u, v in zip(path2[:-1], path2[1:]))
            total = dist1 + dist2
            if abs(total - target_distance) <= tolerance:
                routes.append(paths[mid] + path2[1:])
                if len(routes) >= k:
                    break
        except nx.NetworkXNoPath:
            pass
    return routes


def route_to_gpx(G, route):
    gpx = gpxpy.gpx.GPX()
    track = gpxpy.gpx.GPXTrack()
    seg = gpxpy.gpx.GPXTrackSegment()
    gpx.tracks.append(track)
    track.segments.append(seg)

    for n in route:
        seg.points.append(
            gpxpy.gpx.GPXTrackPoint(G.nodes[n]["y"], G.nodes[n]["x"])
        )
    return gpx.to_xml()


def format_time(minutes):
    m = int(minutes)
    s = int((minutes - m) * 60)
    return f"{m}:{s:02d}"


# -----------------------------
# Surface breakdown
# -----------------------------
def surface_breakdown(G, route):
    totals = defaultdict(float)
    total = 0

    for u, v in zip(route[:-1], route[1:]):
        edge = G[u][v][0]
        length = edge["length"]
        total += length

        surface = edge.get("surface")
        highway = edge.get("highway")

        if surface in ["dirt", "earth", "ground", "grass", "mud", "sand"]:
            key = "Trail"
        elif surface in ["gravel", "fine_gravel", "pebblestone"]:
            key = "Gravel"
        elif surface in ["asphalt", "paved", "concrete"]:
            key = "Paved"
        elif highway in ["path", "footway", "track"]:
            key = "Trail"
        else:
            key = "Other"

        totals[key] += length

    return {k: int((v / total) * 100) for k, v in totals.items()}


# -----------------------------
# Flow / twistiness
# -----------------------------
def route_flow(G, route, distance_km):
    def bearing(a, b):
        lat1, lon1 = math.radians(G.nodes[a]["y"]), math.radians(G.nodes[a]["x"])
        lat2, lon2 = math.radians(G.nodes[b]["y"]), math.radians(G.nodes[b]["x"])
        dlon = lon2 - lon1
        x = math.sin(dlon) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        return math.degrees(math.atan2(x, y))

    bearings = [bearing(route[i], route[i + 1]) for i in range(len(route) - 1)]
    turns = sum(1 for i in range(len(bearings) - 1) if abs(bearings[i+1] - bearings[i]) > 30)

    tpk = turns / max(distance_km, 0.1)

    if tpk < 12:
        return "Smooth 🟢"
    elif tpk < 20:
        return "Moderate 🟡"
    else:
        return "Twisty 🔴"


# -----------------------------
# Static Folium route preview
# -----------------------------
def folium_route_preview(G, route):
    coords = [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in route]

    m = folium.Map(location=coords[0], zoom_start=14, tiles="OpenStreetMap")

    folium.PolyLine(
        coords,
        color="#1f77b4",
        weight=5,
        opacity=0.9
    ).add_to(m)

    folium.Marker(coords[0], icon=folium.Icon(color="green"), tooltip="Start").add_to(m)
    folium.Marker(coords[-1], icon=folium.Icon(color="red"), tooltip="End").add_to(m)

    m.fit_bounds(coords)
    return m


# -----------------------------
# Header
# -----------------------------
st.markdown(
    """
    <div style="background:#f0f7f4;padding:25px;border-radius:15px;text-align:center;">
        <h1>🏃 Trail Runner Route GPX Generator</h1>
        <p>Click map to set start/end. Generate runnable trail routes.</p>
    </div>
    """,
    unsafe_allow_html=True
)

# -----------------------------
# Controls
# -----------------------------
route_mode = st.radio("Route Type", ["Loop (1 click)", "Point-to-point (2 clicks)"])

target_distance = st.number_input(
    "Target Distance (meters)",
    min_value=500,
    max_value=50000,
    value=3000,
    step=500,
)

tolerance = st.number_input(
    "Distance Tolerance (meters)",
    min_value=50,
    max_value=5000,
    value=300,
    step=50,
)

if st.button("Reset map clicks"):
    st.session_state.clicks = []

# -----------------------------
# Main map
# -----------------------------
m = folium.Map(location=[52, 5], zoom_start=6)

for i, (lat, lon) in enumerate(st.session_state.clicks):
    folium.Marker(
        [lat, lon],
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

    with st.spinner("Generating routes..."):
        center = st.session_state.clicks[0]

        G = ox.graph_from_point(
            center,
            dist=10000,
            network_type="walk",
            custom_filter='["highway"~"path|footway|track"]'
        )

        G = G.to_undirected()
        G = G.subgraph(max(nx.connected_components(G), key=len)).copy()

        start = nearest_node_manual(G, *st.session_state.clicks[0])
        end = start if route_mode.startswith("Loop") else nearest_node_manual(
            G, *st.session_state.clicks[1]
        )

        routes = generate_alternative_routes(
            G, start, end, target_distance, tolerance
        )

    if not routes:
        st.warning("No routes found.")
    else:
        cols = st.columns(len(routes))
        for i, (col, r) in enumerate(zip(cols, routes)):
            with col:
                length_m = sum(G[u][v][0]["length"] for u, v in zip(r[:-1], r[1:]))
                km = length_m / 1000

                surfaces = surface_breakdown(G, r)
                flow = route_flow(G, r, km)

                st.markdown(
                    f"""
                    <div style="border:1px solid #ddd;border-radius:12px;padding:12px;">
                        <h4>Route {i+1}</h4>
                        <p><b>Distance:</b> {km:.2f} km</p>
                        <p><b>Est. Time:</b> ⏱️ {format_time(km * MINUTES_PER_KM)}</p>
                        <p><b>Calories:</b> 🔥 {int(km * CALORIES_PER_KM)} kcal</p>
                        <p><b>Flow:</b> {flow}</p>
                        <p><b>Surface:</b><br>
                        {" · ".join([f"{k} {v}%" for k,v in surfaces.items()])}
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st_folium(
                    folium_route_preview(G, r),
                    height=300,
                    width=300,
                )

                st.download_button(
                    "⬇️ Download GPX",
                    route_to_gpx(G, r),
                    f"route_{i+1}.gpx",
                    "application/gpx+xml",
                )
