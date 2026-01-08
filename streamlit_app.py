import streamlit as st
import osmnx as ox
import networkx as nx
import random
import math
import gpxpy
import gpxpy.gpx
import folium
from streamlit_folium import st_folium

# -----------------------------
# Session state
# -----------------------------
if "clicks" not in st.session_state:
    st.session_state.clicks = []

# -----------------------------
# Helper: manual nearest node (Cloud-safe)
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

    # Single Dijkstra from start
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

            total_dist = dist1 + dist2

            if abs(total_dist - target_distance) <= tolerance:
                route = paths[mid_node] + path2[1:]
                routes.append(route)

                if len(routes) >= k:
                    break

        except nx.NetworkXNoPath:
            continue

    return routes

# -----------------------------
# Helper: export GPX
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
# UI
# -----------------------------
st.title("🏃 Trail Runner Route GPX Generator")
st.write("Click on the map to select your start/end point. Trails load automatically.")

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
m = folium.Map(
    location=[52.0, 5.0],
    zoom_start=6,
    tiles="OpenStreetMap"
)

for i, (lat, lon) in enumerate(st.session_state.clicks):
    label = "Start" if i == 0 else "End"
    color = "green" if i == 0 else "red"
    folium.Marker(
        [lat, lon],
        popup=label,
        icon=folium.Icon(color=color)
    ).add_to(m)

map_data = st_folium(m, height=500, width=700)

if map_data and map_data.get("last_clicked"):
    lat = map_data["last_clicked"]["lat"]
    lon = map_data["last_clicked"]["lng"]

    max_clicks = 1 if route_mode.startswith("Loop") else 2
    if len(st.session_state.clicks) < max_clicks:
        st.session_state.clicks.append((lat, lon))

# -----------------------------
# Generate routes
# -----------------------------
if st.button("Generate Routes"):
    needed_clicks = 1 if route_mode.startswith("Loop") else 2

    if len(st.session_state.clicks) < needed_clicks:
        st.warning("Please click on the map to select start/end points.")
        st.stop()

    with st.spinner("Loading trail network and generating routes..."):
        center_lat, center_lon = st.session_state.clicks[0]

        # Load only trails, 10km radius (FAST)
        G = ox.graph_from_point(
            (center_lat, center_lon),
            dist=10000,
            network_type="walk",
            simplify=True,
            custom_filter='["highway"~"path|footway|track"]'
        )

        G = G.to_undirected()

        # Keep largest connected component
        largest_cc = max(nx.connected_components(G), key=len)
        G = G.subgraph(largest_cc).copy()

        start_lat, start_lon = st.session_state.clicks[0]
        if route_mode.startswith("Loop"):
            end_lat, end_lon = start_lat, start_lon
        else:
            end_lat, end_lon = st.session_state.clicks[1]

        start_node = nearest_node_manual(G, start_lat, start_lon)
        end_node = nearest_node_manual(G, end_lat, end_lon)

        if start_node is None or end_node is None:
            st.warning("No nearby trails found. Try clicking closer to a path.")
            st.stop()

        routes = generate_alternative_routes(
            G,
            start_node,
            end_node,
            target_distance,
            tolerance,
            k=3
        )

    if not routes:
        st.warning("No routes found. Try increasing distance or tolerance.")
    else:
        st.success(f"{len(routes)} routes generated!")

        for i, r in enumerate(routes):
            length = sum(
                G[u][v][0]["length"]
                for u, v in zip(r[:-1], r[1:])
            )

            st.write(f"**Route {i+1}** — {length/1000:.2f} km")

            fig, ax = ox.plot_graph_route(
                G, r, show=False, close=False
            )
            st.pyplot(fig)

            gpx_data = route_to_gpx(G, r)
            st.download_button(
                f"Download Route {i+1} (GPX)",
                gpx_data,
                file_name=f"route_{i+1}.gpx",
                mime="application/gpx+xml",
            )
