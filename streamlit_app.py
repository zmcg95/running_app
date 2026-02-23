import streamlit as st
import folium
from streamlit_folium import st_folium
import streamlit.components.v1 as components
import math
import gpxpy
import gpxpy.gpx
from folium.plugins import TimestampedGeoJson
from datetime import datetime, timedelta

# --------------------------------------------------
# Page Setup
# --------------------------------------------------
st.set_page_config(layout="wide")
st.title("🚁 Drone Route Planner (A → B)")

# --------------------------------------------------
# Session State
# --------------------------------------------------
st.session_state.setdefault("clicks", [])
st.session_state.setdefault("route_ready", False)
st.session_state.setdefault("route_map", None)
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

def interpolate_points(start, end, steps=100):
    lat1, lon1 = start
    lat2, lon2 = end
    return [
        (
            lat1 + (lat2 - lat1) * i / steps,
            lon1 + (lon2 - lon1) * i / steps
        )
        for i in range(steps + 1)
    ]

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

def create_animation(coords):
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

# --------------------------------------------------
# Controls
# --------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    altitude = st.slider("Flight Altitude (meters)", 10, 200, 50)

with col2:
    speed = st.slider("Speed (m/s)", 1, 25, 10)

st.markdown("Click TWO points on the map: **Start** and **Destination**.")

# --------------------------------------------------
# Click Map (Interactive)
# --------------------------------------------------
click_map = folium.Map(location=[52, 5], zoom_start=6)

for lat, lon in st.session_state.clicks:
    folium.Marker([lat, lon]).add_to(click_map)

map_data = st_folium(click_map, height=500, width=1000, key="click_map")

if map_data and map_data.get("last_clicked"):
    if len(st.session_state.clicks) < 2:
        st.session_state.clicks.append(
            (
                map_data["last_clicked"]["lat"],
                map_data["last_clicked"]["lng"]
            )
        )

# --------------------------------------------------
# Build Route ONCE
# --------------------------------------------------
if len(st.session_state.clicks) == 2 and not st.session_state.route_ready:

    start, end = st.session_state.clicks

    distance = haversine(start[0], start[1], end[0], end[1])
    eta = distance / speed

    coords = interpolate_points(start, end)

    route_map = folium.Map(location=start, zoom_start=14)

    # Draw path
    folium.PolyLine(coords, color="blue", weight=4).add_to(route_map)

    # Start / End markers
    folium.Marker(start, icon=folium.Icon(color="green")).add_to(route_map)
    folium.Marker(end, icon=folium.Icon(color="red")).add_to(route_map)

    # Animation layer
    TimestampedGeoJson(
        create_animation(coords),
        period="PT1S",
        add_last_point=True,
        auto_play=True,
        loop=False,
        max_speed=1,
    ).add_to(route_map)

    st.session_state.route_map = route_map
    st.session_state.coords = coords
    st.session_state.distance = distance
    st.session_state.eta = eta
    st.session_state.route_ready = True

# --------------------------------------------------
# Display Stable Animation (NO st_folium here)
# --------------------------------------------------
if st.session_state.route_ready:

    st.subheader("📊 Flight Info")
    st.write(f"Distance: **{st.session_state.distance/1000:.2f} km**")
    st.write(f"Estimated Time: **{st.session_state.eta/60:.2f} minutes**")
    st.write(f"Altitude: **{altitude} m**")

    st.subheader("🛰️ Drone Route Animation")

    map_html = st.session_state.route_map._repr_html_()

    components.html(
        map_html,
        height=550,
        scrolling=False
    )

    gpx_data = create_gpx(st.session_state.coords, altitude)

    st.download_button(
        "⬇️ Download Drone Route (GPX)",
        gpx_data,
        file_name="drone_route.gpx",
        mime="application/gpx+xml"
    )

# --------------------------------------------------
# Reset
# --------------------------------------------------
if st.button("Reset Mission"):
    st.session_state.clicks = []
    st.session_state.route_ready = False
    st.session_state.route_map = None
    st.session_state.coords = None
