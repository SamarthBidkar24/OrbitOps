"""
download.py — NEO Model Data Downloader
========================================
Sources:
  1. NASA CNEOS Close-Approach Data API  →  neo_closeapproach.csv
  2. MPC NEO Extended List (gzip JSON)   →  mpc_neo.json

Usage:
  python download.py
"""

import os
import gzip
import json
import shutil
import requests
import pandas as pd
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).parent.resolve()
NEO_CSV   = DATA_DIR / "neo_closeapproach.csv"
MPC_JSON  = DATA_DIR / "mpc_neo.json"

# ── Helpers ───────────────────────────────────────────────────────────────────
def human_size(path: Path) -> str:
    size = path.stat().st_size
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def download_stream(url: str, dest: Path, label: str) -> None:
    """Stream-download *url* to *dest* with a progress counter."""
    print(f"\n[→] {label}")
    print(f"    URL : {url}")
    resp = requests.get(url, stream=True, timeout=120)
    resp.raise_for_status()
    total = int(resp.headers.get("content-length", 0))
    downloaded = 0
    with open(dest, "wb") as fh:
        for chunk in resp.iter_content(chunk_size=65_536):
            if chunk:
                fh.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded / total * 100
                    print(f"\r    {pct:5.1f}%  ({downloaded:,} / {total:,} bytes)", end="", flush=True)
    print()  # newline after progress


# ── 1. NASA CNEOS Close-Approach Data ─────────────────────────────────────────
def fetch_nasa_cad() -> None:
    URL = (
        "https://ssd-api.jpl.nasa.gov/cad.api"
        "?dist-max=0.05&date-min=2020-01-01&fullname=true"
    )
    print("\n" + "=" * 60)
    print("STEP 1 — NASA CNEOS Close-Approach Data")
    print("=" * 60)

    print(f"[→] Requesting: {URL}")
    resp = requests.get(URL, timeout=120)
    resp.raise_for_status()
    payload = resp.json()

    fields = payload["fields"]
    data   = payload["data"]
    count  = payload.get("count", len(data))
    print(f"[✓] Received {count} close-approach records.")

    df = pd.DataFrame(data, columns=fields)
    df.to_csv(NEO_CSV, index=False)
    print(f"[✓] Saved → {NEO_CSV}")
    print(f"    Size : {human_size(NEO_CSV)}")
    print(f"    Rows : {len(df):,}   Columns : {list(df.columns)}")


# ── 2. MPC NEO Extended List ──────────────────────────────────────────────────
def fetch_mpc_neo() -> None:
    URL    = "https://www.minorplanetcenter.net/Extended_Files/nea_extended.json.gz"
    GZ_TMP = DATA_DIR / "mpc_neo_raw.json.gz"

    print("\n" + "=" * 60)
    print("STEP 2 — MPC NEO Extended List (gzip JSON)")
    print("=" * 60)

    download_stream(URL, GZ_TMP, "Downloading MPC gzip archive …")

    print(f"[→] Decompressing {GZ_TMP.name} …")
    with gzip.open(GZ_TMP, "rb") as gz_in, open(MPC_JSON, "wb") as json_out:
        shutil.copyfileobj(gz_in, json_out)
    GZ_TMP.unlink(missing_ok=True)

    # Quick validation
    with open(MPC_JSON, "r", encoding="utf-8") as fh:
        records = json.load(fh)
    record_count = len(records) if isinstance(records, list) else "N/A"

    print(f"[✓] Saved → {MPC_JSON}")
    print(f"    Size    : {human_size(MPC_JSON)}")
    print(f"    Records : {record_count:,}" if isinstance(record_count, int) else f"    Records : {record_count}")


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════╗")
    print("║           NEO Model — Data Downloader            ║")
    print("╚══════════════════════════════════════════════════╝")
    print(f"Output directory: {DATA_DIR}\n")

    try:
        fetch_nasa_cad()
    except Exception as exc:
        print(f"[✗] NASA CAD fetch failed: {exc}")

    try:
        fetch_mpc_neo()
    except Exception as exc:
        print(f"[✗] MPC NEO fetch failed: {exc}")

    print("\n" + "=" * 60)
    print("Done. Files in data/:")
    for f in DATA_DIR.iterdir():
        if f.is_file() and f.suffix in (".csv", ".json"):
            print(f"  • {f.name:<30} {human_size(f)}")
    print("=" * 60)
