"""
verify_data.py — OrbitOps Dataset Health Checker
==================================================
Verifies all three downloaded datasets and prints a structured health report.

Usage:
    cd models/
    python verify_data.py

Requires: pandas
"""

import sys
import textwrap
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    sys.exit("[✗] pandas is not installed. Run: pip install pandas")

# ── Root paths ─────────────────────────────────────────────────────────────────
MODELS_DIR = Path(__file__).parent.resolve()

NEO_CSV     = MODELS_DIR / "neo_model"    / "data" / "neo_closeapproach.csv"
SPECTRA_CSV = MODELS_DIR / "spectra_model"/ "data" / "spectra_combined.csv"
METEOR_CSV  = MODELS_DIR / "meteor_model" / "data" / "iau_meteor_showers.csv"
INDIA_CSV   = MODELS_DIR / "meteor_model" / "data" / "india_cities.csv"

# ── ANSI colours (auto-disable on Windows without ANSI support) ────────────────
try:
    import ctypes
    ctypes.windll.kernel32.SetConsoleMode(ctypes.windll.kernel32.GetStdHandle(-11), 7)
except Exception:
    pass

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def ok(msg):  return f"{GREEN}[PASS]{RESET} {msg}"
def fail(msg):return f"{RED}[FAIL]{RESET} {msg}"
def warn(msg):return f"{YELLOW}[WARN]{RESET} {msg}"
def info(msg):return f"{CYAN}[INFO]{RESET} {msg}"

# ── Utility helpers ────────────────────────────────────────────────────────────
def section(title: str) -> None:
    width = 62
    print(f"\n{BOLD}{'═' * width}{RESET}")
    print(f"{BOLD}  {title}{RESET}")
    print(f"{BOLD}{'═' * width}{RESET}")


def subsection(title: str) -> None:
    print(f"\n  {CYAN}── {title} ──{RESET}")


def ascii_bar(label: str, count: int, total: int, width: int = 30) -> str:
    pct   = count / total if total else 0
    filled = int(pct * width)
    bar   = "█" * filled + "░" * (width - filled)
    return f"  {label:<20} {bar}  {count:>6,}  ({pct*100:5.1f}%)"


def check(condition: bool, pass_msg: str, fail_msg: str) -> tuple[bool, str]:
    if condition:
        return True, ok(pass_msg)
    return False, fail(fail_msg)


def load_csv(path: Path, label: str) -> pd.DataFrame | None:
    if not path.exists():
        print(fail(f"{label} not found at:\n    {path}"))
        return None
    try:
        df = pd.read_csv(path, low_memory=False)
        print(info(f"Loaded {label}  ({path.stat().st_size / 1024:.1f} KB)"))
        return df
    except Exception as exc:
        print(fail(f"Could not read {label}: {exc}"))
        return None


# ── Collect results for final summary ─────────────────────────────────────────
RESULTS: dict[str, list[str]] = {}   # dataset → list of issue strings (empty = PASS)


def record(dataset: str, passed: bool, issue: str = "") -> None:
    RESULTS.setdefault(dataset, [])
    if not passed:
        RESULTS[dataset].append(issue)


# ══════════════════════════════════════════════════════════════════════════════
# 1. NEO DATA CHECK
# ══════════════════════════════════════════════════════════════════════════════
def check_neo() -> None:
    section("1 · NEO — Close-Approach Data")
    ds = "NEO"
    df = load_csv(NEO_CSV, "neo_closeapproach.csv")
    if df is None:
        record(ds, False, "File missing")
        return

    df.columns = [c.strip() for c in df.columns]

    # ── Overview ──────────────────────────────────────────────────────────────
    subsection("Overview")
    print(f"  Rows    : {len(df):,}")
    print(f"  Columns : {list(df.columns)}")

    # Date range — CNEOS uses 'cd' (close-date) column
    date_col = next((c for c in df.columns if c.lower() in ("cd", "date", "close_date", "time")), None)
    if date_col:
        dates = pd.to_datetime(df[date_col], errors="coerce").dropna()
        if not dates.empty:
            print(f"  Date range : {dates.min().date()}  →  {dates.max().date()}")
        else:
            print(warn("  Date column found but could not parse dates."))
    else:
        print(warn("  No recognisable date column found for range check."))

    # ── Null checks ───────────────────────────────────────────────────────────
    subsection("Null Value Checks")
    required_cols = ["dist", "v_rel", "h", "cd"]
    for col in required_cols:
        # Try case-insensitive match
        match = next((c for c in df.columns if c.lower() == col.lower()), None)
        if match is None:
            msg = f"Column '{col}' missing from dataset"
            print(fail(msg))
            record(ds, False, msg)
        else:
            nulls = df[match].isna().sum()
            p, m = check(nulls == 0,
                         f"'{match}' has no nulls",
                         f"'{match}' has {nulls:,} null value(s)")
            print(f"  {m}")
            record(ds, p, m.replace(GREEN, "").replace(RED, "").replace(RESET, ""))

    # ── Distance range check ──────────────────────────────────────────────────
    subsection("Distance Range Check  (0.00001 – 0.06 AU)")
    dist_col = next((c for c in df.columns if c.lower() == "dist"), None)
    if dist_col:
        dist = pd.to_numeric(df[dist_col], errors="coerce").dropna()
        out_of_range = ((dist < 0.00001) | (dist > 0.06)).sum()
        p, m = check(out_of_range == 0,
                     f"All {len(dist):,} 'dist' values in [0.00001, 0.06] AU",
                     f"{out_of_range:,} 'dist' values outside [0.00001, 0.06] AU")
        print(f"  {m}")
        if not dist.empty:
            print(f"  dist min={dist.min():.6f}  max={dist.max():.6f}  mean={dist.mean():.6f} AU")
        record(ds, p, m.replace(GREEN, "").replace(RED, "").replace(RESET, ""))
    else:
        msg = "Column 'dist' not found — skipping range check"
        print(warn(f"  {msg}"))
        record(ds, False, msg)

    # ── Sample rows ───────────────────────────────────────────────────────────
    subsection("Sample Rows (first 3)")
    print(textwrap.indent(df.head(3).to_string(index=False), "  "))


# ══════════════════════════════════════════════════════════════════════════════
# 2. SPECTRA DATA CHECK
# ══════════════════════════════════════════════════════════════════════════════
def check_spectra() -> None:
    section("2 · SPECTRA — Combined Spectra Dataset")
    ds = "SPECTRA"
    df = load_csv(SPECTRA_CSV, "spectra_combined.csv")
    if df is None:
        record(ds, False, "File missing")
        return

    df.columns = [c.strip().lower() for c in df.columns]

    # ── Overview ──────────────────────────────────────────────────────────────
    subsection("Overview")
    print(f"  Total rows        : {len(df):,}")
    asteroid_col = next((c for c in df.columns if "asteroid" in c or c == "id"), "asteroid_id")
    if asteroid_col in df.columns:
        print(f"  Unique asteroids  : {df[asteroid_col].nunique():,}")
    label_col = next((c for c in df.columns if "class" in c or "label" in c), None)
    if label_col and label_col in df.columns:
        vc = df[label_col].value_counts()
        print(f"  Unique class labels ({len(vc)}): {list(vc.index[:10])}" +
              (" …" if len(vc) > 10 else ""))

    # ── Wavelength range check ────────────────────────────────────────────────
    subsection("Wavelength Range Check  (400 – 2500 nm)")
    wl_col = next((c for c in df.columns if "wavelength" in c or "wl" in c), None)
    if wl_col:
        wl = pd.to_numeric(df[wl_col], errors="coerce").dropna()
        bad_wl = ((wl < 400) | (wl > 2500)).sum()
        p, m = check(bad_wl == 0,
                     f"All {len(wl):,} wavelength values in [400, 2500] nm",
                     f"{bad_wl:,} wavelength values outside [400, 2500] nm")
        print(f"  {m}")
        print(f"  wavelength min={wl.min():.1f}  max={wl.max():.1f}  mean={wl.mean():.1f} nm")
        record(ds, p, m.replace(GREEN, "").replace(RED, "").replace(RESET, ""))
    else:
        msg = "wavelength_nm column not found"
        print(warn(f"  {msg}"))
        record(ds, False, msg)

    # ── Reflectance check ─────────────────────────────────────────────────────
    subsection("Reflectance Check  (> 0 and < 5.0)")
    refl_col = next((c for c in df.columns if "reflectance" in c or "refl" in c), None)
    if refl_col:
        refl = pd.to_numeric(df[refl_col], errors="coerce").dropna()
        bad_refl = ((refl <= 0) | (refl >= 5.0)).sum()
        p, m = check(bad_refl == 0,
                     f"All {len(refl):,} reflectance values in (0, 5.0)",
                     f"{bad_refl:,} reflectance values out of range (≤0 or ≥5.0)")
        print(f"  {m}")
        print(f"  reflectance min={refl.min():.4f}  max={refl.max():.4f}  mean={refl.mean():.4f}")
        record(ds, p, m.replace(GREEN, "").replace(RED, "").replace(RESET, ""))
    else:
        msg = "reflectance column not found"
        print(warn(f"  {msg}"))
        record(ds, False, msg)

    # ── ASCII class distribution ───────────────────────────────────────────────
    if label_col and label_col in df.columns:
        subsection("Class Distribution (ASCII bar chart)")
        vc = df[label_col].value_counts()
        total = len(df)
        display = vc.head(20)   # cap at 20 labels for readability
        for lbl, cnt in display.items():
            key = str(lbl) if str(lbl).strip() else "(unlabelled)"
            print(ascii_bar(key, cnt, total))
        if len(vc) > 20:
            print(f"  ... and {len(vc) - 20} more classes not shown")


# ══════════════════════════════════════════════════════════════════════════════
# 3. METEOR SHOWER CHECK
# ══════════════════════════════════════════════════════════════════════════════
def check_meteor() -> None:
    section("3 · METEOR — IAU MDC Shower Working List")
    ds = "METEOR"
    df = load_csv(METEOR_CSV, "iau_meteor_showers.csv")
    if df is None:
        record(ds, False, "File missing")
        return

    df.columns = [c.strip().lower() for c in df.columns]

    # ── Overview ──────────────────────────────────────────────────────────────
    subsection("Overview")
    print(f"  Rows    : {len(df):,}")
    print(f"  Columns : {list(df.columns)}")

    # ── RA radiant check ──────────────────────────────────────────────────────
    subsection("RA Radiant Check  (0 – 360°)")
    ra_col = next((c for c in df.columns if "ra" in c and "radiant" in c or c == "ra_radiant"), None)
    if not ra_col:
        ra_col = next((c for c in df.columns if c.startswith("ra")), None)
    if ra_col:
        ra = pd.to_numeric(df[ra_col], errors="coerce").dropna()
        bad_ra = ((ra < 0) | (ra > 360)).sum()
        p, m = check(bad_ra == 0,
                     f"All {len(ra):,} RA values in [0, 360]°",
                     f"{bad_ra:,} RA values outside [0, 360]°")
        print(f"  {m}")
        print(f"  RA min={ra.min():.2f}°  max={ra.max():.2f}°")
        record(ds, p, m.replace(GREEN, "").replace(RED, "").replace(RESET, ""))
    else:
        msg = "ra_radiant column not found"
        print(warn(f"  {msg}"))
        record(ds, False, msg)

    # ── Dec radiant check ─────────────────────────────────────────────────────
    subsection("Dec Radiant Check  (-90 – 90°)")
    dec_col = next((c for c in df.columns if "dec" in c and "radiant" in c or c == "dec_radiant"), None)
    if not dec_col:
        dec_col = next((c for c in df.columns if c.startswith("dec")), None)
    if dec_col:
        dec = pd.to_numeric(df[dec_col], errors="coerce").dropna()
        bad_dec = ((dec < -90) | (dec > 90)).sum()
        p, m = check(bad_dec == 0,
                     f"All {len(dec):,} Dec values in [-90, 90]°",
                     f"{bad_dec:,} Dec values outside [-90, 90]°")
        print(f"  {m}")
        print(f"  Dec min={dec.min():.2f}°  max={dec.max():.2f}°")
        record(ds, p, m.replace(GREEN, "").replace(RED, "").replace(RESET, ""))
    else:
        msg = "dec_radiant column not found"
        print(warn(f"  {msg}"))
        record(ds, False, msg)

    # ── Velocity check ────────────────────────────────────────────────────────
    subsection("Velocity Check  (11 – 73 km/s  physical limits)")
    vel_col = next((c for c in df.columns if "velocity" in c or "vg" in c or "vel" in c), None)
    if vel_col:
        vel = pd.to_numeric(df[vel_col], errors="coerce").dropna()
        bad_vel = ((vel < 11) | (vel > 73)).sum()
        p, m = check(bad_vel == 0,
                     f"All {len(vel):,} velocity values in [11, 73] km/s",
                     f"{bad_vel:,} velocity values outside physical range [11, 73] km/s")
        print(f"  {m}")
        if not vel.empty:
            print(f"  velocity min={vel.min():.1f}  max={vel.max():.1f}  mean={vel.mean():.1f} km/s")
        record(ds, p, m.replace(GREEN, "").replace(RED, "").replace(RESET, ""))
    else:
        msg = "velocity_kms column not found"
        print(warn(f"  {msg}"))
        record(ds, False, msg)

    # ── Top 10 by ZHR ─────────────────────────────────────────────────────────
    subsection("Top 10 Showers by ZHR")
    zhr_col = next((c for c in df.columns if "zhr" in c), None)
    name_col = next((c for c in df.columns if "name" in c), None)
    if zhr_col:
        df[zhr_col] = pd.to_numeric(df[zhr_col], errors="coerce")
        top10 = df.nlargest(10, zhr_col)
        cols_to_show = [c for c in [name_col, "shower_code", zhr_col, vel_col] if c and c in df.columns]
        print(textwrap.indent(top10[cols_to_show].to_string(index=False), "  "))
    else:
        print(warn("  ZHR column not found — skipping top-10 list."))


# ══════════════════════════════════════════════════════════════════════════════
# 4. INDIA CITIES CHECK
# ══════════════════════════════════════════════════════════════════════════════
def check_india_cities() -> None:
    section("4 · INDIA CITIES — Geographic Dataset")
    ds = "INDIA_CITIES"
    df = load_csv(INDIA_CSV, "india_cities.csv")
    if df is None:
        record(ds, False, "File missing")
        return

    df.columns = [c.strip().lower() for c in df.columns]

    # ── Overview ──────────────────────────────────────────────────────────────
    subsection("Overview")
    print(f"  Total cities : {len(df):,}")
    print(f"  Columns      : {list(df.columns)}")

    # Resolve lat/lon column names flexibly
    lat_col = next((c for c in df.columns if c in ("lat", "latitude")), None)
    lon_col = next((c for c in df.columns if c in ("lng", "lon", "long", "longitude")), None)

    # ── Lat check ─────────────────────────────────────────────────────────────
    subsection("Latitude Check  (6° – 38° N — India bounds)")
    if lat_col:
        lat = pd.to_numeric(df[lat_col], errors="coerce").dropna()
        bad_lat = ((lat < 6) | (lat > 38)).sum()
        p, m = check(bad_lat == 0,
                     f"All {len(lat):,} latitude values in [6, 38]°N",
                     f"{bad_lat:,} latitude values outside India bounds [6, 38]°N")
        print(f"  {m}")
        print(f"  lat min={lat.min():.4f}°  max={lat.max():.4f}°")
        record(ds, p, m.replace(GREEN, "").replace(RED, "").replace(RESET, ""))
    else:
        msg = "Latitude column not found"
        print(warn(f"  {msg}"))
        record(ds, False, msg)

    # ── Lon check ─────────────────────────────────────────────────────────────
    subsection("Longitude Check  (68° – 98° E — India bounds)")
    if lon_col:
        lon = pd.to_numeric(df[lon_col], errors="coerce").dropna()
        bad_lon = ((lon < 68) | (lon > 98)).sum()
        p, m = check(bad_lon == 0,
                     f"All {len(lon):,} longitude values in [68, 98]°E",
                     f"{bad_lon:,} longitude values outside India bounds [68, 98]°E")
        print(f"  {m}")
        print(f"  lon min={lon.min():.4f}°  max={lon.max():.4f}°")
        record(ds, p, m.replace(GREEN, "").replace(RED, "").replace(RESET, ""))
    else:
        msg = "Longitude column not found"
        print(warn(f"  {msg}"))
        record(ds, False, msg)

    # ── Top 5 cities ──────────────────────────────────────────────────────────
    subsection("Sample Cities (first 5 rows shown)")
    city_col  = next((c for c in df.columns if "city" in c or "name" in c), None)
    pop_col   = next((c for c in df.columns if "pop" in c), None)

    if pop_col:
        df[pop_col] = pd.to_numeric(df[pop_col], errors="coerce")
        top5 = df.nlargest(5, pop_col)
    else:
        top5 = df.head(5)

    cols_to_show = [c for c in [city_col, lat_col, lon_col, pop_col] if c and c in df.columns]
    if cols_to_show:
        print(textwrap.indent(top5[cols_to_show].to_string(index=False), "  "))
    else:
        print(textwrap.indent(top5.to_string(index=False), "  "))


# ══════════════════════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
def print_summary() -> None:
    width = 62
    print(f"\n{BOLD}{'═' * width}{RESET}")
    print(f"{BOLD}  FINAL HEALTH REPORT SUMMARY{RESET}")
    print(f"{BOLD}{'═' * width}{RESET}\n")

    dataset_labels = {
        "NEO"          : "NEO Close-Approach Data      (neo_closeapproach.csv)",
        "SPECTRA"      : "Spectra Dataset              (spectra_combined.csv) ",
        "METEOR"       : "Meteor Shower Working List   (iau_meteor_showers.csv)",
        "INDIA_CITIES" : "India Cities Dataset         (india_cities.csv)     ",
    }

    all_pass = True
    for key, label in dataset_labels.items():
        issues = RESULTS.get(key, [])
        if not issues:
            print(f"  {GREEN}● PASS{RESET}  {label}")
        else:
            all_pass = False
            print(f"  {RED}● FAIL{RESET}  {label}")
            for issue in issues:
                clean = (issue
                         .replace(GREEN, "").replace(RED, "")
                         .replace(YELLOW, "").replace(CYAN, "")
                         .replace(BOLD, "").replace(RESET, ""))
                print(f"          {RED}↳{RESET} {clean}")

    print()
    if all_pass:
        print(f"  {BOLD}{GREEN}✔  All datasets passed every check.{RESET}")
    else:
        failed = [k for k, v in RESULTS.items() if v]
        print(f"  {BOLD}{RED}✘  {len(failed)} dataset(s) have issues that need attention.{RESET}")

    print(f"{BOLD}{'═' * width}{RESET}\n")


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print(f"\n{BOLD}{'╔' + '═'*60 + '╗'}{RESET}")
    print(f"{BOLD}{'║':1}{'OrbitOps — Dataset Health Checker':^60}{'║':1}{RESET}")
    print(f"{BOLD}{'╚' + '═'*60 + '╝'}{RESET}")
    print(f"  Models root: {MODELS_DIR}\n")

    check_neo()
    check_spectra()
    check_meteor()
    check_india_cities()
    print_summary()
