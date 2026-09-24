# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib", "cartopy"]
# ///

import csv
from datetime import datetime
from pathlib import Path
import math

import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

from matplotlib.lines import Line2D
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import FancyArrowPatch


# ============================================================
# FILE SETTINGS
# ============================================================

FILE = "HKO2024BST.csv"
PICTURE = "plot.png"

HERE = Path(__file__).parent

DATA = HERE / "data" / FILE
OUT = HERE / "out"


# ============================================================
# INTENSITY
# ============================================================

INTENSITY_RANK = {
    "TD": 0,
    "TS": 1,
    "STS": 2,
    "T": 3,
    "ST": 4,
    "SuperT": 5,
}


# Blue -> yellow -> orange -> red
INTENSITY_COLORS = [
    "#8fb6c4",   # TD
    "#609bb0",   # TS
    "#3f819c",   # STS
    "#d39a43",   # T
    "#d7663f",   # ST
    "#a13a3d",   # SuperT
]


INTENSITY_CMAP = LinearSegmentedColormap.from_list(
    "cyclone_intensity",
    INTENSITY_COLORS,
    N=256,
)


# ============================================================
# LABELS
# ============================================================

HIGHLIGHT_NAMES = {
    "YAGI",
    "SHANSHAN",
    "GAEMI",
    "KONG-REY",
}


# ============================================================
# READ CSV
# ============================================================

def rows(path):

    kept = []

    with path.open(
        encoding="utf-8-sig",
        newline=""
    ) as handle:

        for line in csv.reader(handle):

            if (
                len(line) >= 12
                and line[1].isdigit()
            ):
                kept.append(line)

    return kept


# ============================================================
# DISTANCE
# ============================================================

def distance(p1, p2):

    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]

    return math.sqrt(
        dx * dx + dy * dy
    )


# ============================================================
# SIMPLIFY TRACK
# ============================================================

def simplify_track(
    points,
    min_distance=2.5,
):

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


# ============================================================
# CATMULL-ROM SPLINE
# ============================================================

def catmull_rom(
    p0,
    p1,
    p2,
    p3,
    steps=30,
):

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


# ============================================================
# BUILD SMOOTH TRACK
# ============================================================

def build_smooth_track(points):

    if len(points) < 2:
        return []

    coordinates = []

    for i in range(
        len(points) - 1
    ):

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

        coordinates.extend(
            curve
        )

    coordinates.append(
        (
            points[-1]["longitude"],
            points[-1]["latitude"],
        )
    )

    return coordinates


# ============================================================
# BUILD CONTINUOUS INTENSITY VALUES
# ============================================================

def build_intensity_values(
    points,
    coordinate_count,
):

    if len(points) < 2:
        return []

    values = []

    for i in range(
        len(points) - 1
    ):

        start_value = INTENSITY_RANK[
            points[i]["intensity"]
        ]

        end_value = INTENSITY_RANK[
            points[i + 1]["intensity"]
        ]

        for j in range(30):

            t = j / 30

            value = (
                start_value
                + (
                    end_value
                    - start_value
                ) * t
            )

            values.append(
                value
            )

    values.append(
        INTENSITY_RANK[
            points[-1]["intensity"]
        ]
    )

    if len(values) > coordinate_count:

        values = values[
            :coordinate_count
        ]

    while len(values) < coordinate_count:

        values.append(
            values[-1]
        )

    return values


# ============================================================
# CUMULATIVE DISTANCE
# ============================================================

def cumulative_distances(
    coordinates
):

    distances = [0.0]

    total = 0.0

    for i in range(
        1,
        len(coordinates)
    ):

        total += distance(
            coordinates[i - 1],
            coordinates[i]
        )

        distances.append(
            total
        )

    return distances


# ============================================================
# POINT AT DISTANCE
# ============================================================

def point_at_distance(
    coordinates,
    cumulative,
    target,
):

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
        len(cumulative)
    ):

        if cumulative[i] >= target:

            previous_distance = (
                cumulative[i - 1]
            )

            current_distance = (
                cumulative[i]
            )

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
# DRAW SUBTLE ROUTE
# ============================================================

def draw_subtle_route(
    ax,
    coordinates,
):

    if len(coordinates) < 2:
        return

    ax.plot(

        [
            p[0]
            for p in coordinates
        ],

        [
            p[1]
            for p in coordinates
        ],

        color="#50717d",

        linewidth=0.45,

        alpha=0.13,

        transform=ccrs.PlateCarree(),

        solid_capstyle="round",

        solid_joinstyle="round",

        zorder=2,
    )


# ============================================================
# DRAW SHORT THICK ARROW
# ============================================================

def draw_arrow(
    ax,
    start,
    end,
    color,
):

    arrow = FancyArrowPatch(

        start,
        end,

        transform=ccrs.PlateCarree(),

        # Compact arrow shape
        arrowstyle="-|>",

        # Make the arrow head visually stronger
        mutation_scale=9.5,

        # Thick but short
        linewidth=2.15,

        color=color,

        alpha=0.95,

        zorder=5,
    )

    ax.add_patch(
        arrow
    )


# ============================================================
# DRAW ARROW FIELD
# ============================================================

def draw_arrow_field(
    ax,
    coordinates,
    intensities,
):

    if len(coordinates) < 2:
        return

    cumulative = (
        cumulative_distances(
            coordinates
        )
    )

    total_length = cumulative[-1]

    if total_length <= 0:
        return


    # ========================================================
    # V23
    #
    # More arrows
    # Shorter arrows
    #
    # The route should read like:
    #
    #       →  →  →  →  →  →  →
    #
    # instead of:
    #
    #       ----------->
    #                ----------->
    #
    # ========================================================

    arrow_spacing = 2.45


    arrow_count = int(
        total_length
        / arrow_spacing
    )


    # Prevent too few arrows
    arrow_count = max(
        4,
        arrow_count,
    )


    # Prevent excessive clutter
    arrow_count = min(
        18,
        arrow_count,
    )


    # ========================================================
    # MARGINS
    # ========================================================

    margin = (
        total_length
        * 0.04
    )


    usable_length = (
        total_length
        - margin * 2
    )


    if usable_length <= 0:
        return


    # ========================================================
    # EVENLY DISTRIBUTED ARROWS
    # ========================================================

    if arrow_count == 1:

        targets = [
            total_length / 2
        ]

    else:

        spacing = (
            usable_length
            / (
                arrow_count - 1
            )
        )

        targets = [

            margin
            + spacing * i

            for i in range(
                arrow_count
            )
        ]


    # ========================================================
    # DRAW
    # ========================================================

    for target in targets:

        center, index = (
            point_at_distance(
                coordinates,
                cumulative,
                target,
            )
        )


        # ====================================================
        # V23 SHORT ARROW
        # ====================================================
        #
        # Much shorter than V22.
        #
        # This is the most important visual change.
        # ====================================================

        half_length = min(

            total_length * 0.026,

            0.85,
        )


        start_target = max(
            0,
            target
            - half_length,
        )


        end_target = min(
            total_length,
            target
            + half_length,
        )


        start, _ = (
            point_at_distance(
                coordinates,
                cumulative,
                start_target,
            )
        )


        end, _ = (
            point_at_distance(
                coordinates,
                cumulative,
                end_target,
            )
        )


        # ====================================================
        # INTENSITY COLOUR
        # ====================================================

        index = min(
            index,
            len(intensities) - 1,
        )


        intensity = (
            intensities[index]
        )


        color = INTENSITY_CMAP(
            intensity / 5
        )


        # ====================================================
        # DRAW ARROW
        # ====================================================

        draw_arrow(

            ax,

            start,

            end,

            color,
        )


# ============================================================
# MAIN
# ============================================================

def main():

    # ========================================================
    # READ DATA
    # ========================================================

    table = rows(
        DATA
    )

    print(
        f"{DATA.name}: "
        f"{len(table)} rows. "
        f"The first one: "
        f"{table[0]}"
    )


    # ========================================================
    # GROUP CYCLONES
    # ========================================================

    tracks = {}


    for row in table:

        name = row[0]

        year = int(
            row[1]
        )

        month = int(
            row[2]
        )

        day = int(
            row[3]
        )

        hour = int(
            row[4]
        )

        intensity = row[5]

        latitude = (
            int(row[6])
            / 100
        )

        longitude = (
            int(row[7])
            / 100
        )


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


    # ========================================================
    # SORT BY TIME
    # ========================================================

    for points in tracks.values():

        points.sort(
            key=lambda point:
            point["time"]
        )


    print(
        f"{len(tracks)} tropical cyclones found."
    )


    # ========================================================
    # FIGURE
    # ========================================================

    fig = plt.figure(
        figsize=(12, 7)
    )


    ax = plt.axes(
        projection=ccrs.PlateCarree()
    )


    # ========================================================
    # MAP EXTENT
    # ========================================================

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


    # ========================================================
    # MAP BACKGROUND
    # ========================================================

    # Ocean

    ax.add_feature(

        cfeature.OCEAN,

        facecolor="#d9dddf",

        zorder=0,
    )


    # Land

    ax.add_feature(

        cfeature.LAND,

        facecolor="#f1f2f2",

        edgecolor="#ffffff",

        linewidth=0.65,

        zorder=0,
    )


    # Coastline

    ax.add_feature(

        cfeature.COASTLINE,

        edgecolor="#ffffff",

        linewidth=0.75,

        alpha=0.85,

        zorder=1,
    )


    # ========================================================
    # GRID
    # ========================================================

    ax.gridlines(

        draw_labels=False,

        linewidth=0.25,

        color="#ffffff",

        alpha=0.25,

        linestyle="-",
    )


    # ========================================================
    # DRAW CYCLONES
    # ========================================================

    for name, original_points in tracks.items():

        if len(original_points) < 2:
            continue


        # ----------------------------------------------------
        # Simplify
        # ----------------------------------------------------

        simplified = (
            simplify_track(

                original_points,

                min_distance=2.5,
            )
        )


        print(

            f"{name}: "

            f"{len(original_points)} observations "

            f"-> "

            f"{len(simplified)} control points"
        )


        # ----------------------------------------------------
        # Smooth route
        # ----------------------------------------------------

        coordinates = (
            build_smooth_track(
                simplified
            )
        )


        if len(coordinates) < 2:
            continue


        # ----------------------------------------------------
        # Intensity
        # ----------------------------------------------------

        intensities = (
            build_intensity_values(

                simplified,

                len(coordinates),
            )
        )


        # ====================================================
        # SUBTLE CONTINUOUS ROUTE
        # ====================================================

        draw_subtle_route(

            ax,

            coordinates,
        )


        # ====================================================
        # SHORT DENSE ARROWS
        # ====================================================

        draw_arrow_field(

            ax,

            coordinates,

            intensities,
        )


    # ========================================================
    # LABELS
    # ========================================================

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

        offset = label_offsets[
            name
        ]


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

            zorder=7,
        )


    # ========================================================
    # TITLE
    # ========================================================

    ax.set_title(

        "Tropical Cyclone Journeys · 2024",

        fontsize=18,

        fontweight="bold",

        pad=16,
    )


    # ========================================================
    # LEGEND
    # ========================================================

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

                linewidth=2.0,

                alpha=0.95,

                label=intensity,
            )
        )


    ax.legend(

        handles=legend_items,

        title="Intensity",

        loc="upper left",

        frameon=True,

        framealpha=0.94,

        facecolor="#f4f5f5",

        edgecolor="#d0d4d5",
    )


    # ========================================================
    # SAVE
    # ========================================================

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


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()