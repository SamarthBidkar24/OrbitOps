"""
download.py — Spectra Model Data Downloader
=============================================
Sources:
  SMASS-II MIT Spectra Index  →  spectra_model/data/raw/<id>.tab
                               →  spectra_model/data/spectra_combined.csv

The MIT SMASS page lists links to individual .tab files (two-column: wavelength, reflectance).
Each filename encodes the asteroid designation used as the class label seed.

Usage:
  pip install requests beautifulsoup4 pandas
  python download.py
"""

import re
import time
import requests
import pandas as pd
from pathlib import Path
from bs4 import BeautifulSoup

# ── Paths ─────────────────────────────────────────────────────────────────────
DATA_DIR     = Path(__file__).parent.resolve()
RAW_DIR      = DATA_DIR / "raw"
COMBINED_CSV = DATA_DIR / "spectra_combined.csv"
RAW_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL  = "http://smass.mit.edu"
INDEX_URL = f"{BASE_URL}/minus.html"

# ── Helpers ───────────────────────────────────────────────────────────────────
def human_size(path: Path) -> str:
    size = path.stat().st_size
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def scrub_asteroid_id(filename: str) -> str:
    """
    Derive a clean asteroid designation from the .tab filename.
    SMASS filenames look like: 'aXXXXX.tab' or 'sa001.tab' etc.
    We strip the leading 'a'/'sa' and the extension.
    """
    stem = Path(filename).stem          # e.g. 'a00001'
    label = re.sub(r"^s?a", "", stem)  # strip leading 'a' or 'sa'
    return label if label else stem


def parse_tab_file(content: str, asteroid_id: str) -> pd.DataFrame:
    """
    Parse a two-column SMASS .tab text file into a DataFrame.
    Lines beginning with '#' are comments.
    Columns: wavelength (μm) → we convert to nm, reflectance (normalised).
    """
    rows = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            try:
                wl_um  = float(parts[0])
                refl   = float(parts[1])
                rows.append({
                    "asteroid_id"    : asteroid_id,
                    "wavelength_nm"  : round(wl_um * 1000, 4),   # μm → nm
                    "reflectance"    : refl,
                    "class_label"    : "",   # populated later from taxonomy table
                })
            except ValueError:
                continue
    return pd.DataFrame(rows)


# ── Step 1: Scrape index page for .tab links ───────────────────────────────────
def scrape_smass_index() -> list[dict]:
    print("\n" + "=" * 60)
    print("STEP 1 — Scraping SMASS-II index page")
    print("=" * 60)
    print(f"[→] GET {INDEX_URL}")

    resp = requests.get(INDEX_URL, timeout=60)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.endswith(".tab") and ("/data/" in href or "smass" in href.lower()):
            full_url = href if href.startswith("http") else f"{BASE_URL}/{href.lstrip('/')}"
            asteroid_id = scrub_asteroid_id(href.split("/")[-1])
            links.append({"url": full_url, "asteroid_id": asteroid_id, "filename": href.split("/")[-1]})

    # Deduplicate
    seen = set()
    unique = []
    for lk in links:
        if lk["url"] not in seen:
            seen.add(lk["url"])
            unique.append(lk)

    print(f"[✓] Found {len(unique)} unique spectra links.")
    return unique


# ── Step 2: Download each .tab file ──────────────────────────────────────────
def download_spectra(links: list[dict]) -> list[pd.DataFrame]:
    print("\n" + "=" * 60)
    print("STEP 2 — Downloading individual spectra")
    print("=" * 60)

    frames = []
    failed = []

    for i, lk in enumerate(links, start=1):
        dest = RAW_DIR / lk["filename"]
        prefix = f"[{i:>4}/{len(links)}]"

        if dest.exists():
            print(f"{prefix} [SKIP] {lk['filename']} (already downloaded)")
            content = dest.read_text(encoding="utf-8", errors="replace")
        else:
            try:
                resp = requests.get(lk["url"], timeout=30)
                resp.raise_for_status()
                content = resp.text
                dest.write_text(content, encoding="utf-8")
                print(f"{prefix} [OK]   {lk['filename']}  ({human_size(dest)})")
                time.sleep(0.15)   # be polite to MIT servers
            except Exception as exc:
                print(f"{prefix} [FAIL] {lk['filename']}  → {exc}")
                failed.append(lk["url"])
                continue

        df = parse_tab_file(content, lk["asteroid_id"])
        if not df.empty:
            frames.append(df)

    if failed:
        print(f"\n[!] {len(failed)} files could not be downloaded:")
        for u in failed:
            print(f"    {u}")

    return frames


# ── Step 3: Combine into single CSV ──────────────────────────────────────────
def build_combined_csv(frames: list[pd.DataFrame]) -> None:
    print("\n" + "=" * 60)
    print("STEP 3 — Building combined CSV")
    print("=" * 60)

    if not frames:
        print("[!] No spectra data collected — combined CSV will be empty.")
        pd.DataFrame(columns=["asteroid_id", "wavelength_nm", "reflectance", "class_label"]).to_csv(
            COMBINED_CSV, index=False
        )
        return

    combined = pd.concat(frames, ignore_index=True)

    # Ensure consistent column order
    combined = combined[["asteroid_id", "wavelength_nm", "reflectance", "class_label"]]

    combined.to_csv(COMBINED_CSV, index=False)
    print(f"[✓] Saved → {COMBINED_CSV}")
    print(f"    Size       : {human_size(COMBINED_CSV)}")
    print(f"    Total rows : {len(combined):,}")
    print(f"    Asteroids  : {combined['asteroid_id'].nunique():,}")
    print(f"    Wl range   : {combined['wavelength_nm'].min():.1f} – {combined['wavelength_nm'].max():.1f} nm")


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════╗")
    print("║        Spectra Model — Data Downloader           ║")
    print("╚══════════════════════════════════════════════════╝")
    print(f"Output directory : {DATA_DIR}")
    print(f"Raw spectra dir  : {RAW_DIR}\n")

    try:
        links = scrape_smass_index()
    except Exception as exc:
        print(f"[✗] Failed to scrape index: {exc}")
        links = []

    frames = []
    if links:
        frames = download_spectra(links)

    build_combined_csv(frames)

    print("\n" + "=" * 60)
    print("Done. Summary of data/ directory:")
    all_files = sorted(DATA_DIR.rglob("*"))
    for f in all_files:
        if f.is_file():
            rel = f.relative_to(DATA_DIR)
            print(f"  • {str(rel):<40} {human_size(f)}")
    print("=" * 60)
