import csv
from pathlib import Path
from datetime import datetime

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
# ROUTE DISTANCE
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
        return ((0, 0), 0)

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

    for i in range(
        1,
        len(cumulative),
    ):

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
# ROUTE POSITION
# ============================================================

if len(smooth_coordinates) > 1:

    route_index = int(
        journey_position
        / 100
        * (len(smooth_coordinates) - 1)
    )

else:

    route_index = 0


current_coordinate = smooth_coordinates[
    route_index
]


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
        time_position - lower_index
    )

    lower_time = selected_points[
        lower_index
    ]["time"]

    upper_time = selected_points[
        upper_index
    ]["time"]

    time_difference = (
        upper_time - lower_time
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


# ============================================================
# CURRENT POSITION
# ============================================================

current_longitude = current_coordinate[0]
current_latitude = current_coordinate[1]


# ============================================================
# CURRENT MARKER COLOR
# ============================================================

current_marker_color = INTENSITY_COLORS.get(
    current_intensity,
    "#000000",
)


# ============================================================
# CURRENT ARROW DIRECTION
# Based on the local direction of the smooth route
# ============================================================

if len(smooth_coordinates) >= 2:

    previous_index = max(
        0,
        route_index - 4,
    )

    next_index = min(
        len(smooth_coordinates) - 1,
        route_index + 4,
    )

    arrow_start = smooth_coordinates[
        previous_index
    ]

    arrow_end = smooth_coordinates[
        next_index
    ]

else:

    arrow_start = current_coordinate
    arrow_end = current_coordinate


# ============================================================
# SHORT ARROW
# Similar visual language to the original static image
# ============================================================

if len(smooth_coordinates) >= 2:

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

        arrow_half_length = min(
            total_length * 0.026,
            0.85,
        )

        arrow_start_distance = max(
            0,
            current_distance
            - arrow_half_length,
        )

        arrow_end_distance = min(
            total_length,
            current_distance
            + arrow_half_length,
        )

        arrow_start, _ = point_at_distance(
            smooth_coordinates,
            cumulative,
            arrow_start_distance,
        )

        arrow_end, _ = point_at_distance(
            smooth_coordinates,
            cumulative,
            arrow_end_distance,
        )


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
# CURRENT POSITION ARROW
# ============================================================

# Arrow shaft
fig.add_trace(
    go.Scattergeo(
        lon=[
            arrow_start[0],
            arrow_end[0],
        ],
        lat=[
            arrow_start[1],
            arrow_end[1],
        ],
        mode="lines",
        name="Current direction",
        line=dict(
            width=5,
            color=current_marker_color,
        ),
        opacity=0.95,
        showlegend=False,
        hoverinfo="skip",
    )
)


# Arrow head
#
# Plotly geo markers do not reliably support arbitrary
# rotation, so we construct a small triangular arrow head
# from the local route direction.

dx = arrow_end[0] - arrow_start[0]
dy = arrow_end[1] - arrow_start[1]

length = (dx * dx + dy * dy) ** 0.5

if length > 0:

    ux = dx / length
    uy = dy / length

    # Perpendicular direction
    px = -uy
    py = ux

    head_length = length * 0.38
    head_width = length * 0.26

    tip = arrow_end

    base_center = (
        arrow_end[0] - ux * head_length,
        arrow_end[1] - uy * head_length,
    )

    left = (
        base_center[0] + px * head_width,
        base_center[1] + py * head_width,
    )

    right = (
        base_center[0] - px * head_width,
        base_center[1] - py * head_width,
    )

    fig.add_trace(
        go.Scattergeo(
            lon=[
                left[0],
                tip[0],
                right[0],
                left[0],
            ],
            lat=[
                left[1],
                tip[1],
                right[1],
                left[1],
            ],
            mode="lines",
            fill="toself",
            fillcolor=current_marker_color,
            line=dict(
                width=0,
                color=current_marker_color,
            ),
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