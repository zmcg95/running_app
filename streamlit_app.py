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
# Helper: generate routes
# -----------------------------
def generate_alternative_routes(G, start, end, target_distance, tolerance, k=3):
    routes = []
    attempts = 0
    max_attempts = 1000
    nodes_list = list(G.nodes)

    while len(routes) < k and attempts < max_attempts:
        attempts += 1
        mid_node = random.choice(nodes_list)

        try:
            path1 = nx.shortest_path(G, start, mid_node, weight="length")
            path2 = nx.shortest_path(G, mid_node, end, weight="length")
            route = path1 + path2[1:]

            length = sum(
                G[u][v][0]["length"] for u, v in zip(route[:-1], route[1:])
            )

            if abs(length - target_distance) <= tolerance:
                if route not in routes:
                    routes.append(route)

        except (nx.NetworkXNoPath, KeyError):
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
# Streamlit UI
# -----------------------------
st.title("🏃 Trail Runner Route GPX Generator")
st.write(
    "Click on the map to select your start/end point. "
    "The trail network is loaded automatically around your first click."
)

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
    else:
        with st.spinner("Loading trail network and generating routes..."):
            center_lat, center_lon = st.session_state.clicks[0]

            # Load 40km radius around first click
            G = ox.graph_from_point(
                (center_lat, center_lon),
                dist=10000,
                network_type="walk",
                simplify=True
            )

            G = G.to_undirected()

            # Largest connected component
            largest_cc = max(nx.connected_components(G), key=len)
            G = G.subgraph(largest_cc).copy()

            # Keep trail-like paths only
            trail_nodes = set()
            for u, v, k, d in G.edges(keys=True, data=True):
                if d.get("highway") in ["footway", "path", "track"]:
                    trail_nodes.update([u, v])

            G = G.subgraph(trail_nodes).copy()

            start_lat, start_lon = st.session_state.clicks[0]
            if route_mode.startswith("Loop"):
                end_lat, end_lon = start_lat, start_lon
            else:
                end_lat, end_lon = st.session_state.clicks[1]

            # Fast nearest-node lookup
            start_node = ox.distance.nearest_nodes(
                G, start_lon, start_lat
            )
            end_node = ox.distance.nearest_nodes(
                G, end_lon, end_lat
            )

            routes = generate_alternative_routes(
                G,
                start_node,
                end_node,
                target_distance,
                tolerance,
                k=3
            )

        if not routes:
            st.warning("No routes found. Try increasing tolerance or distance.")
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
