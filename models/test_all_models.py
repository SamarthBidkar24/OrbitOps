import importlib.util
import sys
import json
from pathlib import Path
from datetime import datetime

# ── Module Loader ─────────────────────────────────────────────────────────────
def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    module_dir = str(Path(path).parent)
    if module_dir not in sys.path:
        sys.path.append(module_dir)
    spec.loader.exec_module(mod)
    return mod

BASE = Path(__file__).parent.resolve()

print("\n" + "="*45)
print("INTEGRATED MODEL PIPELINE VALIDATION")
print("="*45)

failed = False

try:
    neo = load_module("neo_predict", BASE / "neo_model/src/predict.py")
    spectra = load_module("spectra_predict", BASE / "spectra_model/src/predict.py")
    meteor = load_module("meteor_predict", BASE / "meteor_model/src/predict.py")
except Exception as e:
    print(f"✘ LOAD FAIL: {e}")
    sys.exit(1)

# TEST 1: NEO Predict
try:
    res_neo = neo.predict_neo("2025-08-12", 0)
    assert "top_neos" in res_neo
    print("✓ TEST 1 PASS — NEO returns valid dict")
except Exception as e:
    print(f"✘ TEST 1 FAIL: {e}")
    failed = True

# TEST 2: NEO Features
try:
    assert len(res_neo["top_neos"]) >= 1
    assert "orbital_elements" in res_neo["top_neos"][0]
    print("✓ TEST 2 PASS — NEO orbital elements present")
except Exception as e:
    print(f"✘ TEST 2 FAIL: {e}")
    failed = True

# TEST 3: Spectra
try:
    res_spec = spectra.classify_spectrum([500, 1000], [1.0, 1.2])
    assert "predicted_class" in res_spec
    print("✓ TEST 3 PASS — Spectra returns valid dict")
except Exception as e:
    print(f"✘ TEST 3 FAIL: {e}")
    failed = True

# TEST 4: Spectra profile
try:
    assert len(res_spec["spectral_profile"]["wavelengths"]) == 41
    print("✓ TEST 4 PASS — Spectra profile is complete (41 pts)")
except Exception as e:
    print(f"✘ TEST 4 FAIL: {e}")
    failed = True

# TEST 5: Meteor tonight
try:
    # Use "Mumbai" as it's definitely in India cities list
    res_met = meteor.get_tonight_showers("Mumbai")
    assert "active_showers" in res_met
    print("✓ TEST 5 PASS — Meteor tonight returns valid dict")
except Exception as e:
    print(f"✘ TEST 5 FAIL: {e}")
    failed = True

# TEST 6: Meteor Calendar
try:
    now = datetime.now()
    res_cal = meteor.get_month_calendar("Pune", now.year, now.month)
    assert len(res_cal) > 0
    print("✓ TEST 6 PASS — Meteor calendar is non-empty")
except Exception as e:
    print(f"✘ TEST 6 FAIL: {e}")
    failed = True

# TEST 7: Dark Spots (Testing "Bengaluru" specifically as it's the expected city name in data)
try:
    res_spots = meteor.get_dark_spots("Bengaluru")
    assert len(res_spots) >= 1
    assert "bortle_class" in res_spots[0]
    print("✓ TEST 7 PASS — Dark spots returns valid list")
except Exception as e:
    print(f"✘ TEST 7 FAIL: {e}")
    failed = True

# TEST 8: JSON
try:
    json.dumps(res_neo)
    json.dumps(res_spec)
    json.dumps(res_met)
    json.dumps(res_cal)
    json.dumps(res_spots)
    print("✓ TEST 8 PASS — All outputs JSON serializable")
except Exception as e:
    print(f"✘ TEST 8 FAIL: {e}")
    failed = True

print("\n" + "="*45)
if not failed:
    print("FINAL STATUS: ALL TESTS PASSED")
else:
    print("FINAL STATUS: VALIDATION FAILED")
print("="*45)

if failed:
    sys.exit(1)
