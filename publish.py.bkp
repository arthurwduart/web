from pathlib import Path
from datetime import datetime, timezone
import html
import shutil
import subprocess

BASE = Path("/mnt/beegfs/arthur.duarte/COMET/sinotica")
FIGURES = BASE / "figures"
WEB = BASE / "web"
IMAGES = WEB / "images"
PUBLISHED_CYCLE = WEB / ".published_cycle"

def run(command):
    return subprocess.run(command, check=True, text=True)

def git_status():
    result = subprocess.run(["git", "-C", str(WEB), "status", "--porcelain"], check=True, capture_output=True, text=True)
    return result.stdout.strip()

def pending_commits():
    result = subprocess.run(["git", "-C", str(WEB), "rev-list", "--count", "@{u}..HEAD"], capture_output=True, text=True)
    if result.returncode != 0:
        return 0
    return int(result.stdout.strip() or 0)

def main():
    if not FIGURES.exists():
        raise FileNotFoundError(f"Figures directory not found: {FIGURES}")

    if not (WEB / ".git").exists():
        raise RuntimeError(f"The website directory is not a Git repository: {WEB}")

    cycles = sorted(path for path in FIGURES.iterdir() if path.is_dir() and (path / ".completed").exists())

    if not cycles:
        raise RuntimeError("No completed forecast cycle was found.")

    cycle = cycles[-1]
    published_cycle = PUBLISHED_CYCLE.read_text(encoding="utf-8").strip() if PUBLISHED_CYCLE.exists() else ""

    if published_cycle == cycle.name and not git_status():
        if pending_commits() > 0:
            print(f"Pending commit found for cycle {cycle.name}. Retrying GitHub push...")
            run(["git", "-C", str(WEB), "push", "origin", "main"])
            print(f"Website published for cycle {cycle.name}.")
        else:
            print(f"Cycle {cycle.name} is already published.")
        return

    figure_files = sorted(cycle.rglob("*.png"))

    if not figure_files:
        raise RuntimeError(f"No PNG figures were found for cycle {cycle.name}.")

    shutil.rmtree(IMAGES, ignore_errors=True)
    IMAGES.mkdir(parents=True, exist_ok=True)

    cards = []

    for source in figure_files:
        relative = source.relative_to(cycle)
        destination = IMAGES / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

        product = relative.parent.name.replace("_", " ").title()
        image_path = f"images/{relative.as_posix()}"

        cards.append(
            f"""
            <article class="card">
                <h2>{html.escape(product)}</h2>
                <a href="{image_path}" target="_blank" rel="noopener noreferrer">
                    <img src="{image_path}" alt="{html.escape(product)}" loading="lazy">
                </a>
            </article>
            """
        )

    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="Automatically generated ECMWF IFS synoptic forecast maps.">
<title>ECMWF IFS Synoptic Forecast</title>

<style>
* {{
    box-sizing: border-box;
}}

body {{
    margin: 0;
    background: #f3f4f6;
    color: #202124;
    font-family: Arial, Helvetica, sans-serif;
}}

header {{
    padding: 22px 4%;
    background: white;
    border-bottom: 3px solid #a50000;
    box-shadow: 0 1px 5px rgba(0, 0, 0, 0.12);
}}

header h1 {{
    margin: 0 0 8px;
    font-size: 26px;
}}

header p {{
    margin: 4px 0;
    font-size: 15px;
}}

main {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
    gap: 20px;
    padding: 22px 3%;
}}

.card {{
    overflow: hidden;
    background: white;
    border-radius: 5px;
    box-shadow: 0 1px 6px rgba(0, 0, 0, 0.18);
}}

.card h2 {{
    margin: 0;
    padding: 12px 14px;
    border-bottom: 1px solid #dddddd;
    font-size: 16px;
}}

.card a {{
    display: block;
}}

.card img {{
    display: block;
    width: 100%;
    height: auto;
    transition: opacity 0.2s ease;
}}

.card img:hover {{
    opacity: 0.92;
}}

footer {{
    padding: 18px;
    background: white;
    border-top: 1px solid #cccccc;
    text-align: center;
    font-size: 13px;
}}

@media (max-width: 600px) {{
    header {{
        padding: 18px;
    }}

    header h1 {{
        font-size: 21px;
    }}

    main {{
        grid-template-columns: 1fr;
        padding: 12px;
    }}
}}
</style>
</head>

<body>
<header>
    <h1>ECMWF IFS Synoptic Forecast</h1>
    <p><strong>Forecast cycle:</strong> {cycle.name} UTC</p>
    <p><strong>Last website update:</strong> {updated}</p>
    <p><strong>Forecast range:</strong> +006 to +072 hours</p>
</header>

<main>
{''.join(cards)}
</main>

<footer>
    Automatically generated synoptic products based on ECMWF IFS forecasts.
</footer>
</body>
</html>
"""

    (WEB / "index.html").write_text(page, encoding="utf-8")
    PUBLISHED_CYCLE.write_text(cycle.name + "\n", encoding="utf-8")

    run(["git", "-C", str(WEB), "add", "-A"])

    changed = subprocess.run(["git", "-C", str(WEB), "diff", "--cached", "--quiet"]).returncode

    if changed == 0:
        print(f"Cycle {cycle.name} is already published.")
        return

    run(["git", "-C", str(WEB), "commit", "-m", f"Update forecast cycle {cycle.name}"])
    run(["git", "-C", str(WEB), "push", "origin", "main"])

    print(f"Website published for cycle {cycle.name}.")

if __name__ == "__main__":
    main()