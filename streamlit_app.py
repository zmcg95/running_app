import streamlit as st
import folium
from streamlit_folium import st_folium
import math
import gpxpy
import gpxpy.gpx
from folium.plugins import TimestampedGeoJson
from datetime import datetime, timedelta

# -----------------------------
# Page Setup
# -----------------------------
st.set_page_config(layout="wide")
st.title("🚁 Drone Route Planner (A → B)")

# -----------------------------
# Session State
# -----------------------------
st.session_state.setdefault("clicks", [])

# -----------------------------
# Helpers
# -----------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def interpolate_points(start, end, steps=60):
    lat1, lon1 = start
    lat2, lon2 = end
    points = []
    for i in range(steps + 1):
        t = i / steps
        lat = lat1 + (lat2 - lat1) * t
        lon = lon1 + (lon2 - lon1) * t
        points.append((lat, lon))
    return points

def create_gpx(coords, altitude):
    gpx = gpxpy.gpx.GPX()
    track = gpxpy.gpx.GPXTrack()
    gpx.tracks.append(track)
    segment = gpxpy.gpx.GPXTrackSegment()
    track.segments.append(segment)

    for lat, lon in coords:
        segment.points.append(
            gpxpy.gpx.GPXTrackPoint(lat, lon, elevation=altitude)
        )

    return gpx.to_xml()

def create_animation(coords, speed_mps):
    features = []
    start_time = datetime.now()

    for i, (lat, lon) in enumerate(coords):
        timestamp = start_time + timedelta(seconds=i)
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [lon, lat],
            },
            "properties": {
                "time": timestamp.isoformat(),
                "icon": "circle",
                "iconstyle": {
                    "fillColor": "red",
                    "fillOpacity": 1,
                    "stroke": "true",
                    "radius": 6
                }
            },
        })

    return {
        "type": "FeatureCollection",
        "features": features,
    }

# -----------------------------
# Controls
# -----------------------------
col1, col2 = st.columns(2)

with col1:
    altitude = st.slider("Flight Altitude (meters)", 10, 200, 50)

with col2:
    speed = st.slider("Speed (m/s)", 1, 25, 10)

st.markdown("Click TWO points on the map: Start and Destination.")

# -----------------------------
# Map
# -----------------------------
m = folium.Map(location=[52, 5], zoom_start=6)

for lat, lon in st.session_state.clicks:
    folium.Marker([lat, lon]).add_to(m)

map_data = st_folium(m, height=500, width=900)

if map_data and map_data.get("last_clicked"):
    if len(st.session_state.clicks) < 2:
        st.session_state.clicks.append(
            (map_data["last_clicked"]["lat"],
             map_data["last_clicked"]["lng"])
        )

# -----------------------------
# Route Calculation
# -----------------------------
if len(st.session_state.clicks) == 2:
    start, end = st.session_state.clicks

    distance = haversine(start[0], start[1], end[0], end[1])
    eta = distance / speed

    coords = interpolate_points(start, end, steps=80)

    st.subheader("📊 Flight Info")
    st.write(f"Distance: **{distance/1000:.2f} km**")
    st.write(f"Estimated Time: **{eta/60:.2f} minutes**")
    st.write(f"Altitude: **{altitude} m**")

    # -----------------------------
    # Animated Map
    # -----------------------------
    route_map = folium.Map(location=start, zoom_start=14)

    # Draw route line
    folium.PolyLine(coords, color="blue", weight=4).add_to(route_map)

    # Add start and end markers
    folium.Marker(start, icon=folium.Icon(color="green")).add_to(route_map)
    folium.Marker(end, icon=folium.Icon(color="red")).add_to(route_map)

    # Add animation
    TimestampedGeoJson(
        create_animation(coords, speed),
        period="PT1S",
        add_last_point=True,
        auto_play=True,
        loop=False,
        max_speed=1,
        loop_button=True,
        date_options="YYYY/MM/DD HH:mm:ss",
        time_slider_drag_update=True,
    ).add_to(route_map)

    st.subheader("🛰️ Drone Route Animation")
    st_folium(route_map, height=500, width=900)

    # -----------------------------
    # GPX Download
    # -----------------------------
    gpx_data = create_gpx(coords, altitude)

    st.download_button(
        "⬇️ Download Drone Route (GPX)",
        gpx_data,
        file_name="drone_route.gpx",
        mime="application/gpx+xml"
    )

# -----------------------------
# Reset
# -----------------------------
if st.button("Reset Points"):
    st.session_state.clicks = []
