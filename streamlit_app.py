import streamlit as st
import folium
from streamlit_folium import st_folium
import streamlit.components.v1 as components
import math
import gpxpy
import gpxpy.gpx
import json

# --------------------------------------------------
# Page Setup
# --------------------------------------------------
st.set_page_config(layout="wide")
st.title("🚁 Drone Route Planner with Timeline & Speed Controls")

# --------------------------------------------------
# Session State
# --------------------------------------------------
st.session_state.setdefault("clicks", [])
st.session_state.setdefault("route_ready", False)
st.session_state.setdefault("coords", None)
st.session_state.setdefault("distance", 0)
st.session_state.setdefault("eta", 0)

# --------------------------------------------------
# Helpers
# --------------------------------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def interpolate_points(start, end, steps=200):
    lat1, lon1 = start
    lat2, lon2 = end
    return [(lat1 + (lat2 - lat1) * i / steps, lon1 + (lon2 - lon1) * i / steps) for i in range(steps+1)]

def create_gpx(coords, altitude):
    gpx = gpxpy.gpx.GPX()
    track = gpxpy.gpx.GPXTrack()
    gpx.tracks.append(track)
    segment = gpxpy.gpx.GPXTrackSegment()
    track.segments.append(segment)
    for lat, lon in coords:
        segment.points.append(gpxpy.gpx.GPXTrackPoint(lat, lon, elevation=altitude))
    return gpx.to_xml()

# --------------------------------------------------
# Controls
# --------------------------------------------------
col1, col2, col3 = st.columns([2,2,2])

with col1:
    altitude = st.slider("Flight Altitude (meters)", 10, 200, 50)

with col2:
    speed = st.slider("Speed (m/s)", 1, 25, 10)

with col3:
    speed_factor = st.selectbox("Animation Speed", ["Real-time", "2x", "5x", "10x"])
    factor_map = {"Real-time": 1, "2x": 2, "5x":5, "10x":10}
    speed_multiplier = factor_map[speed_factor]

st.markdown("Click TWO points on the map: **Start** and **Destination**.")

# --------------------------------------------------
# Click Map
# --------------------------------------------------
click_map = folium.Map(location=[52, 5], zoom_start=6)
for lat, lon in st.session_state.clicks:
    folium.Marker([lat, lon]).add_to(click_map)

map_data = st_folium(click_map, height=500, width=1000, key="click_map")
if map_data and map_data.get("last_clicked") and len(st.session_state.clicks)<2:
    st.session_state.clicks.append((map_data["last_clicked"]["lat"], map_data["last_clicked"]["lng"]))

# --------------------------------------------------
# Build Route
# --------------------------------------------------
if len(st.session_state.clicks)==2 and not st.session_state.route_ready:
    start, end = st.session_state.clicks
    distance = haversine(start[0], start[1], end[0], end[1])
    eta = distance / speed
    coords = interpolate_points(start, end)
    st.session_state.coords = coords
    st.session_state.distance = distance
    st.session_state.eta = eta
    st.session_state.route_ready = True

# --------------------------------------------------
# Display Animation with Timeline
# --------------------------------------------------
if st.session_state.route_ready:
    st.subheader("📊 Flight Info")
    st.write(f"Distance: **{st.session_state.distance/1000:.2f} km**")
    st.write(f"Estimated Time: **{st.session_state.eta/60:.2f} minutes**")
    st.write(f"Altitude: **{altitude} m**")

    coords = st.session_state.coords
    coords_json = json.dumps(coords)

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8" />
        <link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
        <style>
            #map {{ width: 100%; height: 500px; }}
            #timeline {{ width: 100%; height: 20px; background: #ddd; position: relative; margin-top: 5px; border-radius: 10px; }}
            #timeline-dot {{ width: 14px; height: 14px; background: red; border-radius: 50%; position: absolute; top: 3px; left: 0%; }}
        </style>
    </head>
    <body>
        <div id="map"></div>
        <div id="timeline"><div id="timeline-dot"></div></div>

        <script>
            var coords = {coords_json};
            var map = L.map('map').setView(coords[0], 14);
            L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{ maxZoom: 19 }}).addTo(map);

            var polyline = L.polyline(coords, {{color: 'blue'}}).addTo(map);
            map.fitBounds(polyline.getBounds());

            var droneIcon = L.circleMarker(coords[0], {{
                radius: 8, color:'red', fillColor:'red', fillOpacity:1
            }}).addTo(map);

            var i = 0;
            var interval = 50 / {speed_multiplier}; // adjust speed multiplier
            var timelineDot = document.getElementById('timeline-dot');

            function moveDrone() {{
                if(i<coords.length){{
                    droneIcon.setLatLng(coords[i]);
                    timelineDot.style.left = (i/coords.length*100) + "%";
                    i++;
                }} else {{
                    clearInterval(animation);
                }}
            }}
            var animation = setInterval(moveDrone, interval);
        </script>
    </body>
    </html>
    """
    components.html(html_code, height=550)

    gpx_data = create_gpx(st.session_state.coords, altitude)
    st.download_button("⬇️ Download Drone Route (GPX)", gpx_data, file_name="drone_route.gpx", mime="application/gpx+xml")

# --------------------------------------------------
# Reset Mission
# --------------------------------------------------
if st.button("Reset Mission"):
    st.session_state.clicks = []
    st.session_state.route_ready = False
    st.session_state.coords = None
