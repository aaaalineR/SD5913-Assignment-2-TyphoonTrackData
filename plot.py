# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib", "cartopy"]
# ///

"""
Visualise 2024 Hong Kong Observatory tropical cyclone tracks.

V18 visual design:

    - geographic position -> location
    - trajectory -> movement path
    - directional strokes -> movement direction
    - colour -> intensity
    - fixed stroke width
    - subtle guide line underneath

The main visual language is no longer a continuous line.

Instead, each cyclone is represented by a sequence of
small directional strokes that collectively form a route.

This is intended to create a movement-field feeling rather
than a collection of worm-like continuous curves.
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

    Small positional changes are removed while the
    overall cyclone trajectory is preserved.
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
    continuously changing intensity values.

    Returns:

        coordinates
        intensity values
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
        # Intensity values
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
        # Interpolate intensity
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
    # Add final coordinate
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
# DRAW VERY FAINT GUIDE TRAJECTORY
# ==================================================

def draw_guide_trajectory(
    ax,
    coordinates,
):
    """
    Draw the complete cyclone trajectory as a very
    subtle guide.

    This preserves the continuity of the real path
    without making the continuous line the main
    visual element.
    """

    if len(coordinates) < 2:
        return

    ax.plot(
        [
            point[0]
            for point in coordinates
        ],
        [
            point[1]
            for point in coordinates
        ],

        color="#8d9aa0",

        linewidth=0.45,

        alpha=0.10,

        transform=ccrs.PlateCarree(),

        solid_capstyle="round",
        solid_joinstyle="round",

        zorder=2,
    )


# ==================================================
# DRAW DIRECTIONAL STROKES
# ==================================================

def draw_directional_strokes(
    ax,
    coordinates,
    intensities,
):
    """
    Replace the continuous visual line with a sequence
    of short directional strokes.

    The strokes follow the original smooth trajectory.

    Each stroke:

        - has a clear direction
        - uses the local intensity colour
        - has a fixed width
        - is visually separated from the next stroke

    Together, the strokes form the cyclone route.
    """

    if len(coordinates) < 20:
        return


    # ==================================================
    # DETERMINE STROKE COUNT
    # ==================================================

    # Short trajectories:
    # fewer strokes
    #
    # Long trajectories:
    # more strokes

    if len(coordinates) < 80:

        stroke_count = 3

    elif len(coordinates) < 150:

        stroke_count = 5

    elif len(coordinates) < 250:

        stroke_count = 7

    else:

        stroke_count = 9


    # ==================================================
    # KEEP STROKES AWAY FROM THE ENDS
    # ==================================================

    start_margin = int(
        len(coordinates) * 0.08
    )

    end_margin = int(
        len(coordinates) * 0.08
    )

    usable_start = start_margin

    usable_end = (
        len(coordinates)
        - end_margin
        - 1
    )

    if usable_end <= usable_start:
        return


    # ==================================================
    # DISTANCE BETWEEN STROKES
    # ==================================================

    usable_length = (
        usable_end
        - usable_start
    )

    spacing = (
        usable_length
        / stroke_count
    )


    # ==================================================
    # DRAW EACH STROKE
    # ==================================================

    for i in range(
        stroke_count
    ):

        # ----------------------------------------------
        # Center position of this directional stroke
        # ----------------------------------------------

        center_index = int(
            usable_start
            + (
                i + 0.5
            ) * spacing
        )


        # ----------------------------------------------
        # Length of directional stroke
        # ----------------------------------------------

        stroke_half_length = max(
            4,
            int(
                spacing * 0.18
            ),
        )


        start_index = max(
            0,
            center_index
            - stroke_half_length,
        )

        end_index = min(
            len(coordinates) - 1,
            center_index
            + stroke_half_length,
        )


        if end_index <= start_index:
            continue


        # ----------------------------------------------
        # Coordinates
        # ----------------------------------------------

        start = coordinates[
            start_index
        ]

        end = coordinates[
            end_index
        ]


        # ----------------------------------------------
        # Local intensity
        # ----------------------------------------------

        local_index = min(
            center_index,
            len(intensities) - 1,
        )

        intensity_value = (
            intensities[
                local_index
            ]
        )


        # ----------------------------------------------
        # Convert intensity to colour
        # ----------------------------------------------

        color = INTENSITY_CMAP(
            intensity_value / 5
        )


        # ----------------------------------------------
        # Create directional stroke
        # ----------------------------------------------

        arrow = FancyArrowPatch(

            start,
            end,

            transform=ccrs.PlateCarree(),

            arrowstyle="-|>",

            # Small arrowhead.
            mutation_scale=5.5,

            # Fixed stroke width.
            linewidth=1.0,

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
    # MAP BACKGROUND
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
    # SUBTLE GRID
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
        # Skip invalid tracks
        # ----------------------------------------------

        if len(original_points) < 2:
            continue


        # ----------------------------------------------
        # Simplify original observations
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
        # and continuous intensity
        # ----------------------------------------------

        coordinates, intensity_values = (
            build_intensity_curve(
                simplified
            )
        )


        if len(coordinates) < 2:
            continue


        # ----------------------------------------------
        # Layer 1:
        # very faint complete trajectory
        # ----------------------------------------------

        draw_guide_trajectory(
            ax,
            coordinates,
        )


        # ----------------------------------------------
        # Layer 2:
        # directional strokes
        # ----------------------------------------------

        draw_directional_strokes(
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

                linewidth=1.0,

                alpha=0.90,

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