from pathlib import Path
from datetime import datetime, timezone
import json
import re
import shutil
import subprocess

BASE = Path("/mnt/beegfs/arthur.duarte/COMET/sinotica")
FIGURES = BASE / "figures"
WEB = BASE / "web"
IMAGES = WEB / "images"
PUBLISHED_CYCLE = WEB / ".published_cycle"

PRODUCT_LABELS = {
    "fig01_mslp_thickness_precipitation": "MSLP + 1000–500 hPa Thickness + 6-h Precipitation",
    "fig02_total_cloud_cover": "Total Cloud Cover",
    "fig03_geopotential_wind_850": "850-hPa Geopotential Height + Wind",
    "fig04_near_surface_fields": "Near-Surface Fields",
    "fig05_thetae_geopotential_advection": "850-hPa Theta-e + Geopotential Height + Temperature Advection",
    "fig06_mucape_cin_mslp": "MUCAPE + CIN + MSLP",
    "fig07_specific_humidity_wind_850": "850-hPa Specific Humidity + Wind",
    "fig08_total_column_water_vapor": "Total Column Water Vapor",
    "fig08_total_column_water": "Total Column Water Vapor",
}

FRAME_PATTERN = re.compile(r"_(\d{8})_(\d{4})_f(\d{3})$")


def run(command):
    return subprocess.run(command, check=True, text=True)


def pending_commits():
    result = subprocess.run(
        ["git", "-C", str(WEB), "rev-list", "--count", "@{u}..HEAD"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return 0
    return int(result.stdout.strip() or 0)


def frame_metadata(source):
    match = FRAME_PATTERN.search(source.stem)

    if not match:
        raise ValueError(f"Unexpected figure filename: {source.name}")

    date_text, time_text, hour_text = match.groups()

    valid = datetime.strptime(
        date_text + time_text,
        "%Y%m%d%H%M"
    ).replace(tzinfo=timezone.utc)

    return int(hour_text), valid.strftime("%Y-%m-%d %H:%M UTC")


def main():

    # ========================================================
    # CHECK DIRECTORIES
    # ========================================================

    if not FIGURES.exists():
        raise FileNotFoundError(f"Figures directory not found: {FIGURES}")

    if not (WEB / ".git").exists():
        raise RuntimeError(
            f"The website directory is not a Git repository: {WEB}"
        )

    # ========================================================
    # FIND LATEST COMPLETED CYCLE
    # ========================================================

    cycles = sorted(
        path
        for path in FIGURES.iterdir()
        if path.is_dir() and (path / ".completed").exists()
    )

    if not cycles:
        raise RuntimeError("No completed forecast cycle was found.")

    cycle = cycles[-1]

    figure_files = sorted(cycle.rglob("*.png"))

    if not figure_files:
        raise RuntimeError(
            f"No PNG figures were found for cycle {cycle.name}."
        )

    print(f"Preparing website for cycle {cycle.name}...")
    print(f"Figures found: {len(figure_files)}")

    # ========================================================
    # CLEAN CURRENT WEBSITE IMAGES
    # ========================================================

    shutil.rmtree(IMAGES, ignore_errors=True)
    IMAGES.mkdir(parents=True, exist_ok=True)

    # ========================================================
    # BUILD PRODUCT CATALOG
    # ========================================================

    products = {}

    for source in figure_files:

        relative = source.relative_to(cycle)

        destination = IMAGES / relative
        destination.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy2(source, destination)

        product_key = relative.parent.as_posix()

        product_label = PRODUCT_LABELS.get(
            product_key,
            product_key.replace("_", " ").title(),
        )

        hour, valid = frame_metadata(source)

        image_path = f"images/{relative.as_posix()}"

        products.setdefault(
            product_key,
            {
                "label": product_label,
                "frames": [],
            },
        )

        products[product_key]["frames"].append(
            {
                "hour": hour,
                "valid": valid,
                "path": image_path,
            }
        )

    # Ordenar produtos
    products = dict(sorted(products.items()))

    # Ordenar tempos dentro de cada produto
    for product in products.values():
        product["frames"].sort(
            key=lambda frame: frame["hour"]
        )

    # ========================================================
    # FORECAST RANGE
    # ========================================================

    all_hours = sorted(
        {
            frame["hour"]
            for product in products.values()
            for frame in product["frames"]
        }
    )

    min_hour = min(all_hours)
    max_hour = max(all_hours)

    # ========================================================
    # CONVERT PRODUCT DATA TO JAVASCRIPT
    # ========================================================

    products_json = json.dumps(
        products,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    updated = datetime.now(
        timezone.utc
    ).strftime("%Y-%m-%d %H:%M UTC")

    # ========================================================
    # HTML PAGE
    # ========================================================

    page = """<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<meta
    name="description"
    content="Automatically generated ECMWF IFS synoptic forecast maps."
>

<title>ECMWF IFS Synoptic Forecast</title>

<style>

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    background: #f3f4f6;
    color: #202124;
    font-family: Arial, Helvetica, sans-serif;
}

/* ==========================================================
HEADER
========================================================== */

header {
    padding: 18px 4%;
    background: white;
    border-bottom: 3px solid #a50000;
    box-shadow: 0 1px 5px rgba(0, 0, 0, 0.12);
}

header h1 {
    margin: 0 0 8px;
    font-size: 25px;
}

header p {
    margin: 4px 0;
    font-size: 14px;
}

/* ==========================================================
MAIN VIEWER
========================================================== */

.viewer {
    width: min(1200px, 96%);
    margin: 20px auto;
}

/* ==========================================================
CONTROLS
========================================================== */

.controls {
    display: grid;
    grid-template-columns: minmax(280px, 1fr) auto auto;
    gap: 10px;
    align-items: center;

    padding: 14px;

    background: white;

    border-radius: 6px;

    box-shadow:
        0 1px 5px rgba(0, 0, 0, 0.15);
}

select,
button {

    min-height: 40px;

    padding: 8px 12px;

    border: 1px solid #b8b8b8;

    border-radius: 4px;

    background: white;

    color: #202124;

    font-size: 15px;
}

select {
    width: 100%;
}

button {
    cursor: pointer;
}

button:hover {
    background: #eeeeee;
}

button:disabled {
    cursor: default;
    opacity: 0.45;
}

/* ==========================================================
STATUS
========================================================== */

.status {

    display: grid;

    grid-template-columns: 1fr auto;

    gap: 10px;

    align-items: end;

    margin: 14px 0 8px;
}

.product-title {
    font-size: 18px;
    font-weight: 700;
}

.time-info {
    margin-top: 4px;
    font-size: 14px;
}

.forecast-hour {
    color: #a50000;
    font-weight: 700;
}

.frame-counter {
    color: #5f6368;
    font-size: 14px;
    white-space: nowrap;
}

/* ==========================================================
IMAGE
========================================================== */

.image-container {

    position: relative;

    overflow: hidden;

    background: white;

    border-radius: 6px;

    box-shadow:
        0 1px 6px rgba(0, 0, 0, 0.18);
}

.image-container a {
    display: block;
}

.image-container img {

    display: block;

    width: 100%;

    max-height: 78vh;

    object-fit: contain;

    background: white;
}

/* ==========================================================
TIMELINE
========================================================== */

.timeline {

    margin-top: 15px;

    padding: 14px;

    background: white;

    border-radius: 6px;

    box-shadow:
        0 1px 5px rgba(0, 0, 0, 0.15);
}

.timeline input[type="range"] {

    width: 100%;

    cursor: pointer;
}

.timeline-labels {

    display: flex;

    justify-content: space-between;

    margin-top: 4px;

    color: #5f6368;

    font-size: 13px;
}

.play-controls {

    display: flex;

    justify-content: center;

    gap: 10px;

    margin-top: 12px;
}

.keyboard-help {

    margin-top: 8px;

    color: #5f6368;

    text-align: center;

    font-size: 12px;
}

/* ==========================================================
FOOTER
========================================================== */

footer {

    margin-top: 20px;

    padding: 18px;

    background: white;

    border-top: 1px solid #cccccc;

    text-align: center;

    font-size: 13px;
}

/* ==========================================================
MOBILE
========================================================== */

@media (max-width: 700px) {

    header {
        padding: 16px;
    }

    header h1 {
        font-size: 21px;
    }

    .viewer {
        width: 96%;
        margin-top: 12px;
    }

    .controls {
        grid-template-columns: 1fr 1fr;
    }

    .controls select {
        grid-column: 1 / -1;
    }

    .status {
        grid-template-columns: 1fr;
    }

    .frame-counter {
        white-space: normal;
    }
}

</style>

</head>

<body>

<!-- ========================================================
HEADER
======================================================== -->

<header>

<h1>
ECMWF IFS Synoptic Forecast
</h1>

<p>
<strong>Forecast cycle:</strong>
__CYCLE__ UTC
</p>

<p>
<strong>Last website update:</strong>
__UPDATED__
</p>

<p>
<strong>Forecast range:</strong>
+__MIN_HOUR__ to +__MAX_HOUR__ hours
</p>

</header>

<!-- ========================================================
VIEWER
======================================================== -->

<main class="viewer">

<section
    class="controls"
    aria-label="Forecast controls"
>

<select
    id="productSelect"
    aria-label="Forecast product"
>
</select>

<button
    id="previousButton"
    type="button"
>
◀ Previous
</button>

<button
    id="nextButton"
    type="button"
>
Next ▶
</button>

</section>

<!-- ========================================================
STATUS
======================================================== -->

<section
    class="status"
    aria-live="polite"
>

<div>

<div
    id="productTitle"
    class="product-title"
>
</div>

<div class="time-info">

<span
    id="forecastHour"
    class="forecast-hour"
>
</span>

<span> · </span>

<span id="validTime"></span>

</div>

</div>

<div
    id="frameCounter"
    class="frame-counter"
>
</div>

</section>

<!-- ========================================================
IMAGE
======================================================== -->

<section class="image-container">

<a
    id="imageLink"
    target="_blank"
    rel="noopener noreferrer"
>

<img
    id="forecastImage"
    alt="ECMWF IFS forecast map"
>

</a>

</section>

<!-- ========================================================
TIMELINE
======================================================== -->

<section class="timeline">

<input
    id="timeSlider"
    type="range"
    min="0"
    max="0"
    value="0"
    step="1"
    aria-label="Forecast time"
>

<div class="timeline-labels">

<span id="firstHour"></span>

<span id="lastHour"></span>

</div>

<div class="play-controls">

<button
    id="playButton"
    type="button"
>
▶ Play
</button>

</div>

<div class="keyboard-help">
Keyboard: ← previous · → next · Space play/pause
</div>

</section>

</main>

<footer>
Automatically generated synoptic products based on ECMWF IFS forecasts.
</footer>

<!-- ========================================================
JAVASCRIPT
======================================================== -->

<script>

const products = __PRODUCTS_JSON__;

const productSelect =
    document.getElementById("productSelect");

const forecastImage =
    document.getElementById("forecastImage");

const imageLink =
    document.getElementById("imageLink");

const productTitle =
    document.getElementById("productTitle");

const forecastHour =
    document.getElementById("forecastHour");

const validTime =
    document.getElementById("validTime");

const frameCounter =
    document.getElementById("frameCounter");

const timeSlider =
    document.getElementById("timeSlider");

const firstHour =
    document.getElementById("firstHour");

const lastHour =
    document.getElementById("lastHour");

const previousButton =
    document.getElementById("previousButton");

const nextButton =
    document.getElementById("nextButton");

const playButton =
    document.getElementById("playButton");


const productKeys =
    Object.keys(products);


let currentProduct =
    productKeys[0];

let currentIndex = 0;

let animation = null;


/* ==========================================================
CREATE PRODUCT MENU
========================================================== */

productKeys.forEach(key => {

    const option =
        document.createElement("option");

    option.value = key;

    option.textContent =
        products[key].label;

    productSelect.appendChild(option);

});


/* ==========================================================
GET CURRENT FRAMES
========================================================== */

function getFrames() {

    return products[currentProduct].frames;

}


/* ==========================================================
INDEX CONTROL
========================================================== */

function normalizeIndex() {

    const frames = getFrames();

    if (currentIndex < 0) {

        currentIndex =
            frames.length - 1;

    }

    if (currentIndex >= frames.length) {

        currentIndex = 0;

    }

}


/* ==========================================================
PRELOAD PREVIOUS AND NEXT IMAGE
========================================================== */

function preloadAdjacent() {

    const frames = getFrames();

    if (frames.length < 2) {
        return;
    }

    const next =
        frames[
            (currentIndex + 1)
            % frames.length
        ];

    const previous =
        frames[
            (
                currentIndex
                - 1
                + frames.length
            )
            % frames.length
        ];

    const nextImage =
        new Image();

    nextImage.src =
        next.path;

    const previousImage =
        new Image();

    previousImage.src =
        previous.path;

}


/* ==========================================================
UPDATE VIEWER
========================================================== */

function updateViewer() {

    normalizeIndex();

    const frames =
        getFrames();

    const frame =
        frames[currentIndex];

    const label =
        products[currentProduct].label;

    const paddedHour =
        String(frame.hour)
        .padStart(3, "0");


    forecastImage.src =
        frame.path;

    forecastImage.alt =
        `${label} - forecast hour +${paddedHour} h`;

    imageLink.href =
        frame.path;


    productTitle.textContent =
        label;


    forecastHour.textContent =
        `Forecast hour: +${paddedHour} h`;


    validTime.textContent =
        `Valid at: ${frame.valid}`;


    frameCounter.textContent =
        `Frame ${currentIndex + 1} of ${frames.length}`;


    timeSlider.max =
        Math.max(
            frames.length - 1,
            0
        );


    timeSlider.value =
        currentIndex;


    firstHour.textContent =
        `+${String(frames[0].hour).padStart(3, "0")} h`;


    lastHour.textContent =
        `+${String(
            frames[frames.length - 1].hour
        ).padStart(3, "0")} h`;


    preloadAdjacent();

}


/* ==========================================================
TIME NAVIGATION
========================================================== */

function nextFrame() {

    currentIndex += 1;

    updateViewer();

}


function previousFrame() {

    currentIndex -= 1;

    updateViewer();

}


/* ==========================================================
ANIMATION
========================================================== */

function stopAnimation() {

    if (animation !== null) {

        clearInterval(animation);

        animation = null;

    }

    playButton.textContent =
        "▶ Play";

}


function startAnimation() {

    if (animation !== null) {
        return;
    }

    animation =
        setInterval(
            nextFrame,
            900
        );

    playButton.textContent =
        "❚❚ Pause";

}


/* ==========================================================
FIND SAME TIME WHEN CHANGING PRODUCT
========================================================== */

function findNearestHourIndex(
    frames,
    targetHour
) {

    let bestIndex = 0;

    let bestDifference =
        Infinity;


    frames.forEach(
        (frame, index) => {

            const difference =
                Math.abs(
                    frame.hour
                    - targetHour
                );

            if (
                difference
                < bestDifference
            ) {

                bestDifference =
                    difference;

                bestIndex =
                    index;

            }

        }
    );


    return bestIndex;

}


/* ==========================================================
PRODUCT CHANGE
========================================================== */

productSelect.addEventListener(
    "change",
    () => {

        const oldFrames =
            getFrames();

        const oldHour =
            oldFrames[currentIndex]?.hour
            ?? 0;


        currentProduct =
            productSelect.value;


        currentIndex =
            findNearestHourIndex(
                getFrames(),
                oldHour
            );


        stopAnimation();

        updateViewer();

    }
);


/* ==========================================================
BUTTONS
========================================================== */

previousButton.addEventListener(
    "click",
    () => {

        stopAnimation();

        previousFrame();

    }
);


nextButton.addEventListener(
    "click",
    () => {

        stopAnimation();

        nextFrame();

    }
);


/* ==========================================================
SLIDER
========================================================== */

timeSlider.addEventListener(
    "input",
    () => {

        stopAnimation();

        currentIndex =
            Number(
                timeSlider.value
            );

        updateViewer();

    }
);


/* ==========================================================
PLAY / PAUSE
========================================================== */

playButton.addEventListener(
    "click",
    () => {

        if (animation === null) {

            startAnimation();

        } else {

            stopAnimation();

        }

    }
);


/* ==========================================================
KEYBOARD
========================================================== */

document.addEventListener(
    "keydown",
    event => {

        const activeTag =
            document.activeElement?.tagName;


        if (
            activeTag === "SELECT"
            || activeTag === "INPUT"
        ) {

            return;

        }


        if (
            event.key === "ArrowRight"
        ) {

            event.preventDefault();

            stopAnimation();

            nextFrame();

        }


        if (
            event.key === "ArrowLeft"
        ) {

            event.preventDefault();

            stopAnimation();

            previousFrame();

        }


        if (
            event.code === "Space"
        ) {

            event.preventDefault();


            if (
                animation === null
            ) {

                startAnimation();

            } else {

                stopAnimation();

            }

        }

    }
);


/* ==========================================================
INITIALIZE
========================================================== */

updateViewer();

</script>

</body>

</html>
"""

    # ========================================================
    # INSERT DYNAMIC VALUES
    # ========================================================

    page = (
        page
        .replace(
            "__CYCLE__",
            cycle.name,
        )
        .replace(
            "__UPDATED__",
            updated,
        )
        .replace(
            "__MIN_HOUR__",
            f"{min_hour:03d}",
        )
        .replace(
            "__MAX_HOUR__",
            f"{max_hour:03d}",
        )
        .replace(
            "__PRODUCTS_JSON__",
            products_json,
        )
    )

    # ========================================================
    # WRITE WEBSITE
    # ========================================================

    (WEB / "index.html").write_text(
        page,
        encoding="utf-8",
    )

    PUBLISHED_CYCLE.write_text(
        cycle.name + "\n",
        encoding="utf-8",
    )

    # Disable Jekyll processing
    (WEB / ".nojekyll").touch(
        exist_ok=True
    )

    # ========================================================
    # GIT
    # ========================================================

    run(
        [
            "git",
            "-C",
            str(WEB),
            "add",
            "-A",
        ]
    )

    changed = subprocess.run(
        [
            "git",
            "-C",
            str(WEB),
            "diff",
            "--cached",
            "--quiet",
        ]
    ).returncode

    # ========================================================
    # NOTHING CHANGED
    # ========================================================

    if changed == 0:

        if pending_commits() > 0:

            print(
                f"Pending commit found for cycle "
                f"{cycle.name}. Retrying GitHub push..."
            )

            run(
                [
                    "git",
                    "-C",
                    str(WEB),
                    "push",
                    "origin",
                    "main",
                ]
            )

            print(
                f"Website published for cycle "
                f"{cycle.name}."
            )

        else:

            print(
                f"Cycle {cycle.name} is already "
                f"published and unchanged."
            )

        return

    # ========================================================
    # COMMIT
    # ========================================================

    run(
        [
            "git",
            "-C",
            str(WEB),
            "commit",
            "-m",
            f"Update forecast cycle {cycle.name}",
        ]
    )

    # ========================================================
    # PUSH
    # ========================================================

    run(
        [
            "git",
            "-C",
            str(WEB),
            "push",
            "origin",
            "main",
        ]
    )

    print(
        f"Website published for cycle "
        f"{cycle.name}."
    )


if __name__ == "__main__":
    main()