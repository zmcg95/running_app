import streamlit as st
import osmnx as ox
import networkx as nx
import math
import gpxpy
import gpxpy.gpx
import folium
from streamlit_folium import st_folium
from collections import defaultdict
import random

# -----------------------------
# Constants
# -----------------------------
MINUTES_PER_KM = 5
CALORIES_PER_KM = 60

# -----------------------------
# Styles
# -----------------------------
st.markdown("""
<style>
.block-container { padding-top: 2rem; padding-bottom: 2rem; }
.green-box { background:#f0f7f4; padding:25px; border-radius:15px; margin-bottom:20px; text-align:center; }
.blue-box { background:#eef3ff; padding:25px; border-radius:15px; margin-bottom:20px; text-align:center; }
</style>
""", unsafe_allow_html=True)

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
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2*R*math.atan2(math.sqrt(a), math.sqrt(1-a))

def nearest_node_manual(G, lat, lon):
    best, best_dist = None, float("inf")
    for n, d in G.nodes(data=True):
        dist = haversine(lat, lon, d["y"], d["x"])
        if dist < best_dist:
            best, best_dist = n, dist
    return best

def path_length(G, path):
    return sum(G[u][v][0]["length"] for u,v in zip(path[:-1], path[1:]))

def edge_overlap(a,b):
    ea = set(zip(a[:-1], a[1:]))
    eb = set(zip(b[:-1], b[1:]))
    return len(ea & eb)/max(len(ea),1)

# Circular loop generator (start=end)
def generate_circular_loops(G, start, target, tol, k=3):
    routes = []
    lengths, paths = nx.single_source_dijkstra(G, start, weight="length")
    candidates = [n for n,d in lengths.items() if abs(d-target/2)<=tol]
    random.shuffle(candidates)

    for mid in candidates:
        try:
            out = paths[mid]
            back = nx.shortest_path(G, mid, start, weight="length")
            # only accept if backtrack <25% edges
            if edge_overlap(out, back) > 0.25:
                continue
            total = path_length(G, out)+path_length(G, back)
            if abs(total-target) > tol:
                continue
            # merge out+back excluding duplicate mid
            route = out + back[1:]
            routes.append(route)
            if len(routes) >= k:
                return routes
        except nx.NetworkXNoPath:
            continue
    # fallback
    if not routes:
        routes.append([start])
    return routes

def surface_breakdown(G, route):
    totals = defaultdict(float)
    total = 0
    for u,v in zip(route[:-1], route[1:]):
        e = G[u][v][0]
        totals[str(e.get("surface") or e.get("highway") or "unknown")] += e["length"]
        total += e["length"]
    return {k:int((v/total)*100) for k,v in totals.items()}

def route_flow(route, km):
    turns = sum(1 for i in range(len(route)-2) if route[i]!=route[i+2])
    tpk = turns/max(km,0.1)
    return "Smooth 🟢" if tpk<12 else "Moderate 🟡" if tpk<20 else "Twisty 🔴"

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
    folium.PolyLine(coords, weight=5, color="#1f77b4").add_to(m)
    folium.Marker(coords[0], icon=folium.Icon(color="green",icon="play")).add_to(m)
    folium.Marker(coords[-1], icon=folium.Icon(color="red",icon="stop")).add_to(m)
    m.fit_bounds(coords)
    return m

# -----------------------------
# UI
# -----------------------------
st.markdown('<div class="green-box"><h1>GPX Route Generator</h1><p>Click on the map to set your start point. Loop mode generates circular routes. Or select Point-to-point mode to customise start and end points. Download the routes directly in GPX format for free. </p></div>', unsafe_allow_html=True)

# Sport type
st.markdown('<div class="blue-box"><h3>Sport type</h3></div>', unsafe_allow_html=True)
_, mid, _ = st.columns([1,2,1])
with mid:
    st.session_state.transport_mode = st.radio("sport", ["🏃 Running","🚴 Cycling","🚶 Walking / Hiking"], horizontal=True, label_visibility="collapsed")

# Route type
st.markdown('<div class="blue-box"><h3>Route type</h3></div>', unsafe_allow_html=True)
_, mid, _ = st.columns([1,2,1])
with mid:
    route_mode = st.radio("route", ["Loop (1 click)","Point-to-point (2 clicks)"], horizontal=True, label_visibility="collapsed")

# Distance
st.markdown('<div class="blue-box"><h3>Distance</h3></div>', unsafe_allow_html=True)
target_distance = st.number_input("Target Distance (meters)", 500,50000,3000,500)
tolerance = st.number_input("Distance Tolerance (meters)",50,5000,300,50)

# Map
m = folium.Map(location=[52,5], zoom_start=6)
for lat, lon in st.session_state.clicks:
    folium.Marker([lat, lon]).add_to(m)
map_data = st_folium(m, height=450, width=700)
if map_data and map_data.get("last_clicked"):
    max_clicks = 1 if route_mode.startswith("Loop") else 2
    if len(st.session_state.clicks)<max_clicks:
        st.session_state.clicks.append((map_data["last_clicked"]["lat"], map_data["last_clicked"]["lng"]))

# Generate routes
if st.button("Generate Routes"):
    center = st.session_state.clicks[0]
    G = ox.graph_from_point(center, dist=10000, network_type="walk")
    G = G.to_undirected()
    start = nearest_node_manual(G, *center)

    if route_mode.startswith("Loop"):
        st.session_state.routes = generate_circular_loops(G, start, target_distance, tolerance)
    else:
        end = nearest_node_manual(G, *st.session_state.clicks[1])
        st.session_state.routes = [nx.shortest_path(G,start,end,weight="length")]

    st.session_state.graph = G

# Display + download
if st.session_state.routes:
    G = st.session_state.graph
    for i, route in enumerate(st.session_state.routes):
        km = path_length(G,route)/1000
        surfaces = surface_breakdown(G, route)
        st.markdown(f"""
        <div style="border:1px solid #ddd;border-radius:12px;padding:12px;">
        <h4>Route {i+1}</h4>
        <p><b>Distance:</b> {km:.2f} km</p>
        <p><b>Time:</b> ⏱️ {int(km*MINUTES_PER_KM)} min</p>
        <p><b>Calories:</b> 🔥 {int(km*CALORIES_PER_KM)} kcal</p>
        <p><b>Flow:</b> {route_flow(route,km)}</p>
        <p><b>Surface:</b> {" · ".join(f"{k} {v}%" for k,v in surfaces.items())}</p>
        </div>
        """, unsafe_allow_html=True)

        st_folium(folium_route_preview(G,route), height=300, width=300, key=f"map_{i}")
        st.download_button("⬇️ Download GPX", route_to_gpx(G,route), f"route_{i+1}.gpx", "application/gpx+xml", key=f"download_{i}")
