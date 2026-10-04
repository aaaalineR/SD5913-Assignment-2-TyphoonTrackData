import csv
from pathlib import Path
from datetime import datetime
import math

import streamlit as st
import plotly.graph_objects as go


# ============================================================
# PAGE
# ============================================================

st.set_page_config(
    page_title="Tropical Cyclone Journeys · 2024",
    layout="wide",
)

st.title("Tropical Cyclone Journeys · 2024")

st.write(
    "Explore the journeys of tropical cyclones recorded in "
    "the Hong Kong Observatory 2024 best-track dataset."
)


# ============================================================
# DATA
# ============================================================

HERE = Path(__file__).parent
DATA = HERE / "data" / "HKO2024BST.csv"


# ============================================================
# INTENSITY
# Same colour language as the original static visualization
# ============================================================

INTENSITY_RANK = {
    "TD": 0,
    "TS": 1,
    "STS": 2,
    "T": 3,
    "ST": 4,
    "SuperT": 5,
}


INTENSITY_COLORS = {
    "TD": "#8fb6c4",
    "TS": "#609bb0",
    "STS": "#3f819c",
    "T": "#d39a43",
    "ST": "#d7663f",
    "SuperT": "#a13a3d",
}


# ============================================================
# SMOOTHING
# ============================================================

def catmull_rom(p0, p1, p2, p3, steps=30):

    points = []

    for i in range(steps):

        t = i / steps
        t2 = t * t
        t3 = t2 * t

        x = 0.5 * (
            2 * p1[0]
            + (-p0[0] + p2[0]) * t
            + (
                2 * p0[0]
                - 5 * p1[0]
                + 4 * p2[0]
                - p3[0]
            ) * t2
            + (
                -p0[0]
                + 3 * p1[0]
                - 3 * p2[0]
                + p3[0]
            ) * t3
        )

        y = 0.5 * (
            2 * p1[1]
            + (-p0[1] + p2[1]) * t
            + (
                2 * p0[1]
                - 5 * p1[1]
                + 4 * p2[1]
                - p3[1]
            ) * t2
            + (
                -p0[1]
                + 3 * p1[1]
                - 3 * p2[1]
                + p3[1]
            ) * t3
        )

        points.append((x, y))

    return points


def build_smooth_track(points):

    if len(points) < 2:
        return []

    coordinates = []

    for i in range(len(points) - 1):

        p1 = (
            points[i]["longitude"],
            points[i]["latitude"],
        )

        p2 = (
            points[i + 1]["longitude"],
            points[i + 1]["latitude"],
        )

        if i == 0:

            p0 = p1

        else:

            p0 = (
                points[i - 1]["longitude"],
                points[i - 1]["latitude"],
            )

        if i + 2 >= len(points):

            p3 = p2

        else:

            p3 = (
                points[i + 2]["longitude"],
                points[i + 2]["latitude"],
            )

        curve = catmull_rom(
            p0,
            p1,
            p2,
            p3,
            steps=30,
        )

        coordinates.extend(curve)

    coordinates.append(
        (
            points[-1]["longitude"],
            points[-1]["latitude"],
        )
    )

    return coordinates


# ============================================================
# DISTANCE FUNCTIONS
# ============================================================

def distance(p1, p2):

    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]

    return (dx * dx + dy * dy) ** 0.5


def cumulative_distances(coordinates):

    cumulative = [0.0]

    for i in range(1, len(coordinates)):

        segment = distance(
            coordinates[i - 1],
            coordinates[i],
        )

        cumulative.append(
            cumulative[-1] + segment
        )

    return cumulative


def point_at_distance(
    coordinates,
    cumulative,
    target,
):

    if not coordinates:

        return (
            (0, 0),
            0,
        )

    if target <= 0:

        return (
            coordinates[0],
            0,
        )

    if target >= cumulative[-1]:

        return (
            coordinates[-1],
            len(coordinates) - 1,
        )

    for i in range(1, len(cumulative)):

        if cumulative[i] >= target:

            previous_distance = cumulative[i - 1]
            current_distance = cumulative[i]

            segment_length = (
                current_distance
                - previous_distance
            )

            if segment_length == 0:

                return (
                    coordinates[i],
                    i,
                )

            t = (
                target
                - previous_distance
            ) / segment_length

            x = (
                coordinates[i - 1][0]
                + (
                    coordinates[i][0]
                    - coordinates[i - 1][0]
                ) * t
            )

            y = (
                coordinates[i - 1][1]
                + (
                    coordinates[i][1]
                    - coordinates[i - 1][1]
                ) * t
            )

            return (
                (x, y),
                i,
            )

    return (
        coordinates[-1],
        len(coordinates) - 1,
    )


# ============================================================
# LOAD CSV
# ============================================================

def load_rows(path):

    rows = []

    with path.open(
        encoding="utf-8-sig",
        newline=""
    ) as handle:

        for line in csv.reader(handle):

            if (
                len(line) >= 12
                and line[1].isdigit()
            ):

                rows.append(line)

    return rows


table = load_rows(DATA)


# ============================================================
# GROUP CYCLONES
# ============================================================

tracks = {}

for row in table:

    name = row[0]

    year = int(row[1])
    month = int(row[2])
    day = int(row[3])
    hour = int(row[4])

    intensity = row[5]

    latitude = int(row[6]) / 100
    longitude = int(row[7]) / 100

    point = {
        "time": datetime(
            year,
            month,
            day,
            hour,
        ),
        "intensity": intensity,
        "latitude": latitude,
        "longitude": longitude,
    }

    if name not in tracks:

        tracks[name] = []

    tracks[name].append(point)


# ============================================================
# SORT
# ============================================================

for points in tracks.values():

    points.sort(
        key=lambda point: point["time"]
    )


# ============================================================
# INFO
# ============================================================

st.write(
    f"Loaded {len(table)} observations "
    f"from {len(tracks)} tropical cyclones."
)


# ============================================================
# SELECT CYCLONE
# ============================================================

cyclone_names = sorted(
    tracks.keys()
)

selected_name = st.selectbox(
    "Select a tropical cyclone",
    cyclone_names,
)

selected_points = tracks[selected_name]


# ============================================================
# BUILD SMOOTH ROUTE
# ============================================================

smooth_coordinates = build_smooth_track(
    selected_points
)


# ============================================================
# JOURNEY SLIDER
# ============================================================

journey_position = st.slider(
    "Journey progression",
    min_value=0,
    max_value=100,
    value=0,
    step=1,
)


# ============================================================
# ROUTE DISTANCE
# ============================================================

cumulative = cumulative_distances(
    smooth_coordinates
)

total_length = cumulative[-1]


if total_length > 0:

    current_distance = (
        journey_position
        / 100
        * total_length
    )

else:

    current_distance = 0


# ============================================================
# CURRENT POSITION
# ============================================================

current_coordinate, route_index = point_at_distance(
    smooth_coordinates,
    cumulative,
    current_distance,
)


current_longitude = current_coordinate[0]
current_latitude = current_coordinate[1]


# ============================================================
# TIME INTERPOLATION
# ============================================================

if len(selected_points) > 1:

    time_position = (
        journey_position
        / 100
        * (len(selected_points) - 1)
    )

    lower_index = int(time_position)

    upper_index = min(
        lower_index + 1,
        len(selected_points) - 1,
    )

    fraction = (
        time_position
        - lower_index
    )

    lower_time = selected_points[
        lower_index
    ]["time"]

    upper_time = selected_points[
        upper_index
    ]["time"]

    time_difference = (
        upper_time
        - lower_time
    )

    current_time = (
        lower_time
        + time_difference * fraction
    )

else:

    current_time = selected_points[0]["time"]


# ============================================================
# CURRENT INTENSITY
# ============================================================

intensity_position = (
    journey_position
    / 100
    * (len(selected_points) - 1)
)

intensity_index = int(
    intensity_position
)

current_intensity = selected_points[
    intensity_index
]["intensity"]


current_marker_color = INTENSITY_COLORS.get(
    current_intensity,
    "#000000",
)


# ============================================================
# PRECISE LOCAL TANGENT
#
# The direction is calculated from a very small section
# around the current position on the smooth route.
# ============================================================

if total_length > 0:

    tangent_window = min(
        total_length * 0.006,
        0.25,
    )

    tangent_start_distance = max(
        0,
        current_distance - tangent_window,
    )

    tangent_end_distance = min(
        total_length,
        current_distance + tangent_window,
    )

    tangent_start, _ = point_at_distance(
        smooth_coordinates,
        cumulative,
        tangent_start_distance,
    )

    tangent_end, _ = point_at_distance(
        smooth_coordinates,
        cumulative,
        tangent_end_distance,
    )

else:

    tangent_start = current_coordinate
    tangent_end = current_coordinate


# ============================================================
# DIRECTION
#
# Plotly marker angle:
# 0 degrees = pointing upward.
#
# atan2(dx, dy) gives clockwise angle from north/up.
# ============================================================

dx = tangent_end[0] - tangent_start[0]
dy = tangent_end[1] - tangent_start[1]

direction_length = (
    dx * dx
    + dy * dy
) ** 0.5


if direction_length > 0:

    arrow_angle = math.degrees(
        math.atan2(
            dx,
            dy,
        )
    )

else:

    arrow_angle = 0


# ============================================================
# INFORMATION
# ============================================================

st.subheader(
    selected_name
)

col1, col2, col3 = st.columns(3)

with col1:

    st.metric(
        "Time",
        current_time.strftime(
            "%Y-%m-%d %H:%M"
        ),
    )

with col2:

    st.metric(
        "Intensity",
        current_intensity,
    )

with col3:

    st.metric(
        "Position",
        (
            f"{current_latitude:.1f}° N, "
            f"{current_longitude:.1f}° E"
        ),
    )


# ============================================================
# MAP
# ============================================================

fig = go.Figure()


# ============================================================
# ALL CYCLONE ROUTES
# ============================================================

for name, points in tracks.items():

    if len(points) < 2:
        continue

    route = build_smooth_track(
        points
    )

    if name == selected_name:

        line_width = 3
        opacity = 0.9

    else:

        line_width = 1
        opacity = 0.18

    fig.add_trace(
        go.Scattergeo(
            lon=[
                coordinate[0]
                for coordinate in route
            ],
            lat=[
                coordinate[1]
                for coordinate in route
            ],
            mode="lines",
            name=name,
            line=dict(
                width=line_width,
            ),
            opacity=opacity,
            showlegend=False,
        )
    )


# ============================================================
# CURRENT POSITION
#
# FIXED-SCREEN-SIZE DIRECTIONAL MARKER
#
# Unlike the previous polygon, this marker uses pixel size.
# Therefore it stays visually readable when the map is
# zoomed in or zoomed out.
# ============================================================

fig.add_trace(
    go.Scattergeo(

        lon=[
            current_longitude
        ],

        lat=[
            current_latitude
        ],

        mode="markers",

        marker=dict(

            # Wide arrow gives a stronger shaft/head
            # relationship than the normal arrow symbol.
            symbol="arrow-wide",

            # IMPORTANT:
            # marker size is in PIXELS, not map coordinates.
            size=28,

            color=current_marker_color,

            # White outline around the arrow.
            line=dict(
                color="white",
                width=4,
            ),

            # Rotate according to the local cyclone direction.
            angle=arrow_angle,

            # 0 degrees points upward.
            angleref="up",
        ),

        name=selected_name,

        showlegend=False,

        hovertemplate=(
            "<b>%{text}</b>"
            "<extra></extra>"
        ),

        text=[
            (
                f"{selected_name}<br>"
                f"{current_time.strftime('%Y-%m-%d %H:%M')}<br>"
                f"Intensity: {current_intensity}"
            )
        ],
    )
)


# ============================================================
# INTENSITY LEGEND
# ============================================================

for intensity, color in INTENSITY_COLORS.items():

    fig.add_trace(
        go.Scattergeo(
            lon=[None],
            lat=[None],
            mode="markers",
            marker=dict(
                size=10,
                color=color,
            ),
            name=intensity,
            showlegend=True,
        )
    )


# ============================================================
# MAP STYLE
# ============================================================

fig.update_geos(
    projection_type="equirectangular",

    lonaxis=dict(
        range=[100, 180]
    ),

    lataxis=dict(
        range=[5, 45]
    ),

    showland=True,

    landcolor="#f1f2f2",

    showocean=True,

    oceancolor="#d9dddf",

    showcountries=True,

    countrycolor="white",

    coastlinecolor="white",
)


# ============================================================
# LAYOUT
# ============================================================

fig.update_layout(

    height=650,

    margin=dict(
        l=0,
        r=0,
        t=20,
        b=0,
    ),

    legend=dict(
        title="Intensity",
    ),
)


# ============================================================
# DISPLAY
# ============================================================

st.plotly_chart(
    fig,
    use_container_width=True,
)