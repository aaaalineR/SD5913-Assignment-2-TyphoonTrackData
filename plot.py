# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib", "cartopy"]
# ///

"""
Visualise 2024 Hong Kong Observatory tropical cyclone tracks.

V17 visual design:

    - geographic position -> location
    - trajectory -> movement
    - arrow direction -> movement direction
    - colour -> intensity
    - line width -> fixed
    - opacity -> fixed

Design goal:

    Confident lines + quiet hierarchy.

Weak cyclones remain visible and clear,
while stronger cyclones receive stronger colour emphasis.
"""

import csv
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

from matplotlib.lines import Line2D
from matplotlib.collections import LineCollection
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import FancyArrowPatch


# ==================================================
# FILE SETTINGS
# ==================================================

FILE = "HKO2024BST.csv"
PICTURE = "plot.png"

HERE = Path(__file__).parent
DATA = HERE / "data" / FILE
OUT = HERE / "out"


# ==================================================
# INTENSITY COLOUR STYLE
# ==================================================

# V17:
# The weak-intensity colours are slightly clearer
# than V16 so that the tracks feel definite rather
# than faded or uncertain.

INTENSITY_COLORS = [
    "#a9c2cc",   # TD
    "#789faf",   # TS
    "#4f829d",   # STS
    "#d69a43",   # T
    "#d5673f",   # ST
    "#9e3033",   # SuperT
]

INTENSITY_CMAP = LinearSegmentedColormap.from_list(
    "cyclone_intensity",
    INTENSITY_COLORS,
    N=256,
)


# ==================================================
# INTENSITY RANK
# ==================================================

INTENSITY_RANK = {
    "TD": 0,
    "TS": 1,
    "STS": 2,
    "T": 3,
    "ST": 4,
    "SuperT": 5,
}


# ==================================================
# HIGHLIGHTED CYCLONES
# ==================================================

HIGHLIGHT_NAMES = {
    "YAGI",
    "SHANSHAN",
    "GAEMI",
    "KONG-REY",
}


# ==================================================
# READ CSV
# ==================================================

def rows(path):
    """
    Keep only tropical cyclone observation rows.
    """

    kept = []

    with path.open(
        encoding="utf-8-sig",
        newline=""
    ) as handle:

        for line in csv.reader(handle):

            if len(line) >= 12 and line[1].isdigit():
                kept.append(line)

    return kept


# ==================================================
# DISTANCE
# ==================================================

def distance(p1, p2):
    """
    Simple distance in longitude/latitude space.
    """

    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]

    return (dx * dx + dy * dy) ** 0.5


# ==================================================
# SIMPLIFY TRACK
# ==================================================

def simplify_track(
    points,
    min_distance=2.5,
):
    """
    Reduce the number of geographic control points.

    This removes tiny positional changes while
    preserving the overall movement of the cyclone.
    """

    if len(points) <= 2:
        return points

    simplified = [
        points[0]
    ]

    last_kept = (
        points[0]["longitude"],
        points[0]["latitude"],
    )

    for point in points[1:-1]:

        current = (
            point["longitude"],
            point["latitude"],
        )

        if distance(
            last_kept,
            current
        ) >= min_distance:

            simplified.append(
                point
            )

            last_kept = current

    simplified.append(
        points[-1]
    )

    return simplified


# ==================================================
# CATMULL-ROM SPLINE
# ==================================================

def catmull_rom(
    p0,
    p1,
    p2,
    p3,
    steps=30,
):
    """
    Generate a smooth curve between p1 and p2.

    V17 uses fewer interpolation steps than V16
    to keep the trajectory smooth while reducing
    the overly floating / uncertain appearance.
    """

    curve = []

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

        curve.append(
            (x, y)
        )

    return curve


# ==================================================
# BUILD SMOOTH TRACK + CONTINUOUS INTENSITY
# ==================================================

def build_intensity_curve(points):
    """
    Build a smooth cyclone trajectory together with
    a continuously changing intensity value.

    Geometry:
        Catmull-Rom spline

    Intensity:
        continuously interpolated between control points
    """

    if len(points) < 2:
        return [], []

    coordinates = []
    intensities = []

    for i in range(
        len(points) - 1
    ):

        # ------------------------------------------
        # Current control points
        # ------------------------------------------

        p1 = (
            points[i]["longitude"],
            points[i]["latitude"],
        )

        p2 = (
            points[i + 1]["longitude"],
            points[i + 1]["latitude"],
        )

        # ------------------------------------------
        # Previous control point
        # ------------------------------------------

        if i == 0:

            p0 = p1

        else:

            p0 = (
                points[i - 1]["longitude"],
                points[i - 1]["latitude"],
            )

        # ------------------------------------------
        # Next control point
        # ------------------------------------------

        if i + 2 >= len(points):

            p3 = p2

        else:

            p3 = (
                points[i + 2]["longitude"],
                points[i + 2]["latitude"],
            )

        # ------------------------------------------
        # Intensity at both ends
        # ------------------------------------------

        start_intensity = INTENSITY_RANK[
            points[i]["intensity"]
        ]

        end_intensity = INTENSITY_RANK[
            points[i + 1]["intensity"]
        ]

        # ------------------------------------------
        # Generate smooth geometry
        # ------------------------------------------

        curve = catmull_rom(
            p0,
            p1,
            p2,
            p3,
            steps=30,
        )

        # ------------------------------------------
        # Interpolate intensity continuously
        # ------------------------------------------

        for j, coordinate in enumerate(curve):

            t = j / 30

            intensity_value = (
                start_intensity
                + (
                    end_intensity
                    - start_intensity
                ) * t
            )

            coordinates.append(
                coordinate
            )

            intensities.append(
                intensity_value
            )

    # ----------------------------------------------
    # Add final point
    # ----------------------------------------------

    coordinates.append(
        (
            points[-1]["longitude"],
            points[-1]["latitude"],
        )
    )

    intensities.append(
        INTENSITY_RANK[
            points[-1]["intensity"]
        ]
    )

    return coordinates, intensities


# ==================================================
# DRAW CONTINUOUS INTENSITY CURVE
# ==================================================

def plot_continuous_intensity_curve(
    ax,
    coordinates,
    intensities,
):
    """
    Draw one smooth cyclone trajectory.

    V17:
        - colour represents intensity
        - line width is fixed
        - opacity is fixed
        - lines are slightly more definite
    """

    if len(coordinates) < 2:
        return

    # ----------------------------------------------
    # Create tiny line segments
    # ----------------------------------------------

    segments = []

    for i in range(
        len(coordinates) - 1
    ):

        segments.append(
            [
                coordinates[i],
                coordinates[i + 1],
            ]
        )

    # ----------------------------------------------
    # Create LineCollection
    # ----------------------------------------------

    collection = LineCollection(
        segments,

        cmap=INTENSITY_CMAP,

        # V17:
        # Slightly stronger and more definite
        # than V16.
        linewidths=1.1,

        alpha=0.85,

        capstyle="round",
        joinstyle="round",

        zorder=3,
    )

    # ----------------------------------------------
    # Give every segment its intensity value
    # ----------------------------------------------

    collection.set_array(
        intensities[:-1]
    )

    collection.set_clim(
        0,
        5,
    )

    # ----------------------------------------------
    # Tell Cartopy these are lon/lat coordinates
    # ----------------------------------------------

    collection.set_transform(
        ccrs.PlateCarree()
    )

    # ----------------------------------------------
    # Add collection to map
    # ----------------------------------------------

    ax.add_collection(
        collection
    )


# ==================================================
# DRAW DIRECTION ARROWS
# ==================================================

def add_direction_arrows(
    ax,
    coordinates,
    intensities,
):
    """
    Add a small number of subtle directional arrows
    along one cyclone trajectory.

    V17:
        - fewer arrows than V16
        - smaller arrows
        - arrows act as directional punctuation
          rather than a repeated texture
    """

    if len(coordinates) < 30:
        return

    # ----------------------------------------------
    # Determine arrow count
    # ----------------------------------------------

    if len(coordinates) < 90:

        arrow_count = 1

    elif len(coordinates) < 180:

        arrow_count = 2

    else:

        arrow_count = 3


    # ----------------------------------------------
    # Keep arrows away from both ends
    # ----------------------------------------------

    usable_start = int(
        len(coordinates) * 0.18
    )

    usable_end = int(
        len(coordinates) * 0.82
    )

    if usable_end <= usable_start:
        return


    # ----------------------------------------------
    # Evenly distribute arrow positions
    # ----------------------------------------------

    positions = []

    for i in range(
        arrow_count
    ):

        fraction = (
            i + 1
        ) / (
            arrow_count + 1
        )

        index = int(
            usable_start
            + fraction
            * (
                usable_end
                - usable_start
            )
        )

        positions.append(
            index
        )


    # ----------------------------------------------
    # Draw each arrow
    # ----------------------------------------------

    for index in positions:

        # Shorter arrow segment than V16.
        half_length = 4

        start_index = max(
            0,
            index - half_length,
        )

        end_index = min(
            len(coordinates) - 1,
            index + half_length,
        )

        if end_index <= start_index:
            continue

        start = coordinates[
            start_index
        ]

        end = coordinates[
            end_index
        ]


        # ------------------------------------------
        # Use local intensity for arrow colour
        # ------------------------------------------

        intensity_value = intensities[
            min(
                index,
                len(intensities) - 1,
            )
        ]

        color = INTENSITY_CMAP(
            intensity_value / 5
        )


        # ------------------------------------------
        # Small directional cue
        # ------------------------------------------

        arrow = FancyArrowPatch(

            start,
            end,

            transform=ccrs.PlateCarree(),

            arrowstyle="-|>",

            # Smaller than V16.
            mutation_scale=5,

            linewidth=0.75,

            color=color,

            alpha=0.90,

            zorder=4,
        )

        ax.add_patch(
            arrow
        )


# ==================================================
# MAIN
# ==================================================

def main():

    # ==================================================
    # READ DATA
    # ==================================================

    table = rows(DATA)

    print(
        f"{DATA.name}: "
        f"{len(table)} rows. "
        f"The first one: {table[0]}"
    )


    # ==================================================
    # GROUP OBSERVATIONS BY CYCLONE
    # ==================================================

    tracks = {}

    for row in table:

        name = row[0]

        year = int(row[1])
        month = int(row[2])
        day = int(row[3])
        hour = int(row[4])

        intensity = row[5]

        latitude = int(
            row[6]
        ) / 100

        longitude = int(
            row[7]
        ) / 100

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

        tracks[name].append(
            point
        )


    # ==================================================
    # SORT CHRONOLOGICALLY
    # ==================================================

    for points in tracks.values():

        points.sort(
            key=lambda point:
            point["time"]
        )


    print(
        f"{len(tracks)} tropical cyclones found."
    )


    # ==================================================
    # CREATE FIGURE
    # ==================================================

    fig = plt.figure(
        figsize=(12, 7)
    )

    ax = plt.axes(
        projection=ccrs.PlateCarree()
    )


    # ==================================================
    # MAP EXTENT
    # ==================================================

    ax.set_extent(
        [
            100,
            180,
            5,
            45,
        ],

        crs=ccrs.PlateCarree()
    )

    ax.set_aspect(
        "equal"
    )


    # ==================================================
    # VERY LIGHT MAP BACKGROUND
    # ==================================================

    ax.add_feature(
        cfeature.OCEAN,
        facecolor="#f8f9fa",
        zorder=0,
    )

    ax.add_feature(
        cfeature.LAND,
        facecolor="#eceeef",
        edgecolor="#c9ced1",
        linewidth=0.45,
        zorder=0,
    )

    ax.add_feature(
        cfeature.COASTLINE,
        edgecolor="#aeb6ba",
        linewidth=0.5,
        alpha=0.65,
        zorder=1,
    )


    # ==================================================
    # VERY SUBTLE GRID
    # ==================================================

    ax.gridlines(
        draw_labels=False,
        linewidth=0.35,
        color="#9aa5aa",
        alpha=0.12,
        linestyle="-",
    )


    # ==================================================
    # DRAW CYCLONE FIELD
    # ==================================================

    for name, original_points in tracks.items():

        # ----------------------------------------------
        # Ignore tracks with insufficient observations
        # ----------------------------------------------

        if len(original_points) < 2:
            continue


        # ----------------------------------------------
        # Simplify geographic path
        # ----------------------------------------------

        simplified = simplify_track(
            original_points,
            min_distance=2.5,
        )


        print(
            f"{name}: "
            f"{len(original_points)} observations "
            f"-> {len(simplified)} control points"
        )


        # ----------------------------------------------
        # Build smooth trajectory
        # + continuous intensity
        # ----------------------------------------------

        coordinates, intensity_values = (
            build_intensity_curve(
                simplified
            )
        )


        if len(coordinates) < 2:
            continue


        # ----------------------------------------------
        # Draw trajectory
        # ----------------------------------------------

        plot_continuous_intensity_curve(
            ax,
            coordinates,
            intensity_values,
        )


        # ----------------------------------------------
        # Draw subtle direction arrows
        # ----------------------------------------------

        add_direction_arrows(
            ax,
            coordinates,
            intensity_values,
        )


    # ==================================================
    # LABEL ONLY FOUR CYCLONES
    # ==================================================

    label_offsets = {

        "YAGI": (
            8,
            6,
        ),

        "SHANSHAN": (
            8,
            7,
        ),

        "GAEMI": (
            8,
            7,
        ),

        "KONG-REY": (
            8,
            -12,
        ),
    }


    for name in HIGHLIGHT_NAMES:

        if name not in tracks:
            continue

        last = tracks[name][-1]

        offset = label_offsets[name]

        ax.annotate(
            name,

            (
                last["longitude"],
                last["latitude"],
            ),

            xytext=offset,

            textcoords="offset points",

            fontsize=9,

            color="#465158",

            fontweight="bold",

            transform=ccrs.PlateCarree(),

            zorder=6,
        )


    # ==================================================
    # TITLE
    # ==================================================

    ax.set_title(
        "Tropical Cyclone Journeys · 2024",

        fontsize=18,

        fontweight="bold",

        pad=16,
    )


    # ==================================================
    # INTENSITY LEGEND
    # ==================================================

    legend_items = []

    for intensity in [
        "TD",
        "TS",
        "STS",
        "T",
        "ST",
        "SuperT",
    ]:

        legend_items.append(
            Line2D(
                [0],
                [0],

                color=INTENSITY_COLORS[
                    INTENSITY_RANK[
                        intensity
                    ]
                ],

                linewidth=1.1,

                alpha=0.85,

                label=intensity,
            )
        )


    ax.legend(
        handles=legend_items,

        title="Intensity",

        loc="upper left",

        frameon=True,

        framealpha=0.92,
    )


    # ==================================================
    # SAVE
    # ==================================================

    OUT.mkdir(
        exist_ok=True
    )

    fig.savefig(
        OUT / PICTURE,

        dpi=180,

        bbox_inches="tight",
    )


    print(
        f"saved out/{PICTURE}"
    )


    plt.show()


# ==================================================
# RUN
# ==================================================

if __name__ == "__main__":
    main()