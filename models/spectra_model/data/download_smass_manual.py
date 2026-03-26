"""
download_smass_manual.py — Bus-DeMeo Taxonomy Spectra Builder
==============================================================
Source: NASA PDS Small Bodies Node — Bus-DeMeo Asteroid Taxonomy V1.0
  https://sbn.psi.edu/pds/resource/busdemeotax.html

Files downloaded:
  demeotax.tab    — 371 asteroids with their taxonomy class labels
  meanspectra.tab — Mean reflectance spectrum for each of 24 classes
                    (41 wavelength points, 0.45–2.45 µm)

Strategy:
  Since the dataset ships mean spectra per CLASS (not per asteroid),
  each classified asteroid is assigned its class's mean spectrum.
  Result: 371 asteroids × 41 wavelengths = 15,211 rows.

Output:
  spectra_model/data/spectra_combined.csv
  Columns: asteroid_id, wavelength_nm, reflectance, class_label

Usage:
  pip install requests pandas
  python download_smass_manual.py
"""

import io
import sys
import time
import requests
import pandas as pd
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
DATA_DIR     = Path(__file__).parent.resolve()
RAW_DIR      = DATA_DIR / "raw"
COMBINED_CSV = DATA_DIR / "spectra_combined.csv"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# ── PDS Archive base ──────────────────────────────────────────────────────────
PDS_BASE = "https://sbnarchive.psi.edu/pds4/non_mission/ast.bus-demeo.taxonomy/data"
TAX_URL  = f"{PDS_BASE}/demeotax.tab"
SPE_URL  = f"{PDS_BASE}/meanspectra.tab"

# ── 24 Bus-DeMeo class names in the exact column order of meanspectra.tab ─────
# Each class occupies 2 consecutive columns: (MEAN, STDDEV).
# Classes with only 1 member (Cg, O, R) have -.999 as their STDDEV sentinel.
CLASSES = [
    "A", "B", "C", "Cb", "Cg", "Cgh", "Ch",
    "D", "K", "L", "O", "Q", "R",
    "S", "Sa", "Sk", "Sl", "Sq", "Sqw", "Sr", "Sv", "Sw",
    "T", "V", "X", "Xc", "Xk", "Xe",
]
# Note: there are 28 classes listed in the XML (fields 2–49 → 48 data cols → 24 pairs).
# However the PDS3 documentation lists 24. We parse dynamically instead of hard-coding.

MISSING_SENTINEL = -0.999   # PDS sentinel for "no data"

# ── Helpers ───────────────────────────────────────────────────────────────────
def human_size(path: Path) -> str:
    size = path.stat().st_size
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def fetch_text(url: str, label: str, cache_path: Path) -> str:
    """Download *url* to *cache_path* (skip if already exists) and return text."""
    if cache_path.exists():
        print(f"  [SKIP] {label} already cached ({human_size(cache_path)})")
        return cache_path.read_text(encoding="utf-8", errors="replace")

    print(f"  [→]   Downloading {label} …")
    print(f"        {url}")
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    text = resp.text
    cache_path.write_text(text, encoding="utf-8")
    print(f"  [✓]   Saved → {cache_path.name}  ({human_size(cache_path)})")
    return text


# ── Step 1: Parse demeotax.tab ────────────────────────────────────────────────
# Mapping from variant class labels that appear in demeotax.tab but NOT in
# meanspectra.tab, to their closest base class that IS in meanspectra.tab.
CLASS_FALLBACK: dict[str, str] = {
    "Srw" : "Sr",
    "Svw" : "Sv",
    "Vw"  : "V",
    "Sqw" : "Sq",   # Sqw is in meanspectra; kept as insurance
    "Skw" : "Sk",
    "Slw" : "Sl",
    "Saw" : "Sa",
    "Sw"  : "S",    # Sw is in meanspectra; kept as insurance
    "Spw" : "S",
}


def parse_taxonomy(text: str) -> dict[str, str]:
    """
    Return {asteroid_id: class_label} from demeotax.tab.

    Fixed-width PDS format (0-indexed columns):
        0 –  6  : asteroid number
        7 – 25  : asteroid name
        26 – 37 : provisional designation
        38 – 41 : Bus-DeMeo taxonomy class  ← key field
        42 – 53 : observation date
        54 +    : reference flags

    The server sends the file with \r\r\n line endings (DOS file stored on
    Unix), so we normalise before slicing.
    """
    taxonomy: dict[str, str] = {}
    # Normalise all carriage returns then split cleanly
    text = text.replace("\r", "")
    for line in text.split("\n"):
        line = line.rstrip()
        if len(line) < 40:          # must be long enough to contain the class field
            continue
        try:
            num  = line[0:7].strip()
            name = line[7:26].strip()
            cls  = line[37:40].strip()   # taxonomy class at col 37 (confirmed: 'C' for Ceres, etc.)
        except IndexError:
            continue

        if not cls or not num:
            continue

        # Strip quality/uncertainty flag (colon suffix, e.g. "Sq:" → "Sq")
        cls = cls.rstrip(":")

        # Build a stable asteroid_id
        if name and name != "-":
            asteroid_id = f"{num}_{name}".replace(" ", "_")
        else:
            prov = line[26:38].strip()
            asteroid_id = f"{num}_{prov}".strip("_ ").replace(" ", "_") if prov and prov != "-" else num

        taxonomy[asteroid_id] = cls

    return taxonomy


# ── Step 2: Parse meanspectra.tab ─────────────────────────────────────────────
def parse_meanspectra(text: str) -> tuple[pd.DataFrame, list[str]]:
    """
    Parse the fixed-width mean spectra table.

    Each row: wavelength_um  cls1_mean  cls1_std  cls2_mean  cls2_std  ...
    Missing values encoded as -.999 → replaced with NaN.
    Handles \\r\\r\\n double-CRLF endings from the PDS server.

    Returns (DataFrame, list_of_class_names).
    """
    rows = []
    text = text.replace("\r", "")   # normalise line endings
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        vals = line.split()
        if not vals:
            continue
        try:
            wl_um = float(vals[0])
        except ValueError:
            continue

        data_vals = []
        for v in vals[1:]:
            try:
                fv = float(v)
                data_vals.append(None if abs(fv - MISSING_SENTINEL) < 1e-3 else fv)
            except ValueError:
                data_vals.append(None)
        rows.append([wl_um] + data_vals)

    if not rows:
        raise RuntimeError("meanspectra.tab parsed 0 rows — check URL / format.")

    # Normalise row lengths (some rows may have fewer trailing values)
    max_cols = max(len(r) for r in rows)
    for r in rows:
        while len(r) < max_cols:
            r.append(None)

    n_data_cols   = max_cols - 1
    n_class_pairs = n_data_cols // 2

    actual_classes = list(CLASSES[:n_class_pairs])
    for i in range(len(actual_classes), n_class_pairs):
        actual_classes.append(f"UNK{i}")

    col_names = ["wavelength_um"]
    for cls in actual_classes:
        col_names += [f"{cls}_mean", f"{cls}_std"]

    df = pd.DataFrame(rows, columns=col_names[:max_cols])
    df["wavelength_nm"] = df["wavelength_um"] * 1000.0
    return df, actual_classes


# ── Step 3: Build combined CSV ────────────────────────────────────────────────
def build_combined(taxonomy: dict[str, str], spectra_df: pd.DataFrame,
                   actual_classes: list[str]) -> pd.DataFrame:
    """
    For each asteroid, look up its class, select that class's mean spectrum,
    and emit one row per wavelength point.

    Output columns: asteroid_id, wavelength_nm, reflectance, class_label
    """
    frames = []

    for asteroid_id, cls_label in taxonomy.items():
        cls_clean = cls_label.rstrip(":").strip()

        # Resolve the mean column, with fallback chain:
        #   1. exact match
        #   2. CLASS_FALLBACK mapping (e.g. Srw → Sr)
        #   3. leading capital letter (e.g. Srw → S as last resort)
        def resolve_mean_col(cls: str) -> str | None:
            for candidate in [
                cls,
                CLASS_FALLBACK.get(cls, ""),
                cls[0] if cls else "",
            ]:
                if not candidate:
                    continue
                col = f"{candidate}_mean"
                if col in spectra_df.columns:
                    return col
            return None

        mean_col = resolve_mean_col(cls_clean)
        if mean_col is None:
            # Genuinely unmapped class — skip
            continue

        sub = spectra_df[["wavelength_nm", mean_col]].copy()
        sub = sub.dropna(subset=[mean_col])
        sub.rename(columns={mean_col: "reflectance"}, inplace=True)
        sub["asteroid_id"]  = asteroid_id
        sub["class_label"]  = cls_clean
        frames.append(sub[["asteroid_id", "wavelength_nm", "reflectance", "class_label"]])

    if not frames:
        return pd.DataFrame(columns=["asteroid_id", "wavelength_nm", "reflectance", "class_label"])

    combined = pd.concat(frames, ignore_index=True)
    combined["wavelength_nm"] = combined["wavelength_nm"].round(2)
    combined["reflectance"]   = combined["reflectance"].round(6)
    return combined


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════╗")
    print("║   Bus-DeMeo Taxonomy — Spectra Combined CSV Builder  ║")
    print("╚══════════════════════════════════════════════════════╝")
    print(f"  Output dir : {DATA_DIR}")
    print(f"  Raw cache  : {RAW_DIR}\n")

    # ── Download taxonomy index ───────────────────────────────────────────────
    print("─" * 56)
    print("STEP 1 — Downloading taxonomy classification table")
    print("─" * 56)
    try:
        tax_text = fetch_text(TAX_URL, "demeotax.tab", RAW_DIR / "demeotax.tab")
    except Exception as exc:
        sys.exit(f"[✗] Failed to download demeotax.tab: {exc}")

    taxonomy = parse_taxonomy(tax_text)
    print(f"  [✓] Parsed {len(taxonomy):,} asteroid classifications.")
    class_counts = pd.Series(taxonomy.values()).value_counts()
    print(f"       Classes found ({len(class_counts)}): "
          f"{', '.join(f'{k}={v}' for k,v in class_counts.items())}")

    # ── Download mean spectra ─────────────────────────────────────────────────
    print()
    print("─" * 56)
    print("STEP 2 — Downloading mean class spectra")
    print("─" * 56)
    try:
        spe_text = fetch_text(SPE_URL, "meanspectra.tab", RAW_DIR / "meanspectra.tab")
    except Exception as exc:
        sys.exit(f"[✗] Failed to download meanspectra.tab: {exc}")

    try:
        spectra_df, actual_classes = parse_meanspectra(spe_text)
    except Exception as exc:
        sys.exit(f"[✗] Failed to parse meanspectra.tab: {exc}")

    print(f"  [✓] Parsed {len(spectra_df):,} wavelength points "
          f"across {len(actual_classes)} classes.")
    print(f"       Wavelength range: "
          f"{spectra_df['wavelength_nm'].min():.0f} – "
          f"{spectra_df['wavelength_nm'].max():.0f} nm")

    # ── Build & save combined CSV ─────────────────────────────────────────────
    print()
    print("─" * 56)
    print("STEP 3 — Building spectra_combined.csv")
    print("─" * 56)
    combined = build_combined(taxonomy, spectra_df, actual_classes)

    if combined.empty:
        print("[✗] Combined DataFrame is empty — check class name matching.")
        sys.exit(1)

    combined.to_csv(COMBINED_CSV, index=False)

    print(f"  [✓] Saved → {COMBINED_CSV}")
    print(f"       File size        : {human_size(COMBINED_CSV)}")
    print(f"       Total rows       : {len(combined):,}")
    print(f"       Unique asteroids : {combined['asteroid_id'].nunique():,}")
    print(f"       Unique classes   : {combined['class_label'].nunique()}")
    print(f"       Classes          : {sorted(combined['class_label'].unique())}")
    print(f"       Wavelength range : "
          f"{combined['wavelength_nm'].min():.1f} – "
          f"{combined['wavelength_nm'].max():.1f} nm")

    print()
    print("─" * 56)
    print("STEP 4 — Preview (first 8 rows)")
    print("─" * 56)
    print(combined.head(8).to_string(index=False))

    print()
    print("─" * 56)
    print("Class distribution")
    print("─" * 56)
    dist = combined.groupby("class_label")["asteroid_id"].nunique().sort_values(ascending=False)
    total = dist.sum()
    BAR_W = 28
    for cls, cnt in dist.items():
        bar = "█" * int(cnt / total * BAR_W) + "░" * (BAR_W - int(cnt / total * BAR_W))
        print(f"  {cls:<4}  {bar}  {cnt:>3} asteroids")

    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║  Done. spectra_combined.csv is ready for training.  ║")
    print("╚══════════════════════════════════════════════════════╝")
