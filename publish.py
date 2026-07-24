from pathlib import Path
from datetime import datetime, timezone
import html
import shutil
import subprocess

BASE = Path("/mnt/beegfs/arthur.duarte/COMET/sinotica")
FIGURES = BASE / "figures"
WEB = BASE / "web"
IMAGES = WEB / "images"

def run(command):
    return subprocess.run(command, check=True, text=True)

def main():
    cycles = sorted(p for p in FIGURES.iterdir() if p.is_dir() and (p / ".completed").exists())
    if not cycles:
        raise RuntimeError("No completed forecast cycle was found.")

    cycle = cycles[-1]
    shutil.rmtree(IMAGES, ignore_errors=True)
    IMAGES.mkdir(parents=True)

    cards = []
    for source in sorted(cycle.rglob("*.png")):
        relative = source.relative_to(cycle)
        destination = IMAGES / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

        title = relative.parent.name.replace("_", " ").title()
        cards.append(f'<article><h2>{html.escape(title)}</h2><a href="images/{relative.as_posix()}" target="_blank"><img src="images/{relative.as_posix()}" loading="lazy"></a></article>')

    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ECMWF IFS Synoptic Forecast</title>
<style>
body{{margin:0;background:#f4f4f4;color:#222;font-family:Arial,sans-serif}}
header{{padding:22px 5%;background:#fff;border-bottom:3px solid #a50000}}
header h1{{margin:0 0 7px;font-size:25px}}
header p{{margin:3px 0}}
main{{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:18px;padding:20px 3%}}
article{{background:#fff;padding:12px;box-shadow:0 1px 5px #bbb}}
article h2{{margin:0 0 10px;font-size:16px}}
img{{display:block;width:100%;height:auto}}
footer{{padding:18px;text-align:center;background:#fff;border-top:1px solid #ccc}}
@media(max-width:600px){{main{{grid-template-columns:1fr;padding:10px}}}}
</style>
</head>
<body>
<header>
<h1>ECMWF IFS Synoptic Forecast</h1>
<p><b>Forecast cycle:</b> {cycle.name} UTC</p>
<p><b>Last website update:</b> {updated}</p>
</header>
<main>
{''.join(cards)}
</main>
<footer>Automatically generated synoptic products</footer>
</body>
</html>"""

    (WEB / "index.html").write_text(page, encoding="utf-8")

    run(["git", "-C", str(WEB), "add", "-A"])
    changed = subprocess.run(["git", "-C", str(WEB), "diff", "--cached", "--quiet"]).returncode

    if changed == 0:
        print("Website already up to date.")
        return

    run(["git", "-C", str(WEB), "commit", "-m", f"Update forecast cycle {cycle.name}"])
    run(["git", "-C", str(WEB), "push", "origin", "main"])
    print(f"Website published for cycle {cycle.name}.")

if __name__ == "__main__":
    main()