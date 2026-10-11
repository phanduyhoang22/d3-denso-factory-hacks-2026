import io, zipfile, urllib.request
from pathlib import Path

SOURCES = {
    "ai4i":  "https://archive.ics.uci.edu/static/public/601/ai4i+2020+predictive+maintenance+dataset.zip",
    "secom": "https://archive.ics.uci.edu/static/public/179/secom.zip",
}

base = Path(__file__).parent
for name, url in SOURCES.items():
    out = base / name
    out.mkdir(exist_ok=True)
    print(f"Downloading {name} ...")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    data = urllib.request.urlopen(req).read()
    zipfile.ZipFile(io.BytesIO(data)).extractall(out)
    print("  ->", [p.name for p in out.iterdir()])