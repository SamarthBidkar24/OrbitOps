"""
download.py — Meteor Model Data Downloader (Final Version)
==========================================================
Source: IAU Meteor Data Center (MDC)
Attempts to fetch live data from the MDC PHP interface and parses the HTML table.
Includes a robust hardcoded fallback for 30 major annual showers.

Output:
  iau_meteor_showers.csv
  india_cities.csv (from public mirror)
"""

import os
import io
import math
import requests
import pandas as pd
from pathlib import Path
from bs4 import BeautifulSoup

# ── Paths ─────────────────────────────────────────────────────────────────────
DATA_DIR    = Path(__file__).parent.resolve()
SHOWERS_CSV = DATA_DIR / "iau_meteor_showers.csv"
INDIA_CSV   = DATA_DIR / "india_cities.csv"

# ── Configuration ─────────────────────────────────────────────────────────────
IAU_URL = "https://www.ta3.sk/IAUC22DB/MDC2007/Roje/roje_lista.php?corobic_roje=1&sort_roje=0"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml"
}

# ── Fallback Data ─────────────────────────────────────────────────────────────
FALLBACK_SHOWERS = [
 {"shower_code":"PER","name":"Perseids","ra_radiant":48.2,"dec_radiant":58.1,"solar_long_peak":140.0,"zhr":100,"velocity_kms":59},
 {"shower_code":"GEM","name":"Geminids","ra_radiant":112.3,"dec_radiant":32.5,"solar_long_peak":261.0,"zhr":150,"velocity_kms":35},
 {"shower_code":"LEO","name":"Leonids","ra_radiant":153.5,"dec_radiant":21.6,"solar_long_peak":235.0,"zhr":15,"velocity_kms":71},
 {"shower_code":"ORI","name":"Orionids","ra_radiant":95.0,"dec_radiant":15.8,"solar_long_peak":208.0,"zhr":20,"velocity_kms":66},
 {"shower_code":"ETA","name":"Eta Aquariids","ra_radiant":338.0,"dec_radiant":-1.0,"solar_long_peak":45.5,"zhr":50,"velocity_kms":66},
 {"shower_code":"QUA","name":"Quadrantids","ra_radiant":230.1,"dec_radiant":48.5,"solar_long_peak":283.0,"zhr":120,"velocity_kms":41},
 {"shower_code":"LYR","name":"Lyrids","ra_radiant":271.4,"dec_radiant":33.6,"solar_long_peak":32.3,"zhr":18,"velocity_kms":49},
 {"shower_code":"SDA","name":"South Delta Aquariids","ra_radiant":340.0,"dec_radiant":-16.4,"solar_long_peak":125.0,"zhr":25,"velocity_kms":41},
 {"shower_code":"TAU","name":"Taurids","ra_radiant":52.0,"dec_radiant":14.0,"solar_long_peak":224.0,"zhr":10,"velocity_kms":27},
 {"shower_code":"DRA","name":"Draconids","ra_radiant":262.1,"dec_radiant":54.0,"solar_long_peak":195.0,"zhr":10,"velocity_kms":20},
 {"shower_code":"URS","name":"Ursids","ra_radiant":217.0,"dec_radiant":75.3,"solar_long_peak":270.7,"zhr":10,"velocity_kms":33},
 {"shower_code":"MON","name":"Monocerotids","ra_radiant":100.0,"dec_radiant":8.0,"solar_long_peak":257.7,"zhr":5,"velocity_kms":42},
 {"shower_code":"COM","name":"Coma Berenicids","ra_radiant":175.0,"dec_radiant":25.0,"solar_long_peak":271.0,"zhr":5,"velocity_kms":65},
 {"shower_code":"NOO","name":"Northern Orionids","ra_radiant":88.5,"dec_radiant":23.1,"solar_long_peak":208.0,"zhr":5,"velocity_kms":42},
 {"shower_code":"KAP","name":"Kappa Cygnids","ra_radiant":286.0,"dec_radiant":51.0,"solar_long_peak":145.0,"zhr":5,"velocity_kms":25},
 {"shower_code":"AND","name":"Andromedids","ra_radiant":20.9,"dec_radiant":25.8,"solar_long_peak":235.0,"zhr":5,"velocity_kms":18},
 {"shower_code":"PHO","name":"Phoenicids","ra_radiant":15.0,"dec_radiant":-55.0,"solar_long_peak":244.7,"zhr":5,"velocity_kms":18},
 {"shower_code":"NTA","name":"North Taurids","ra_radiant":58.0,"dec_radiant":22.0,"solar_long_peak":229.0,"zhr":5,"velocity_kms":29},
 {"shower_code":"JAC","name":"July Gamma Draconids","ra_radiant":270.0,"dec_radiant":50.5,"solar_long_peak":105.0,"zhr":5,"velocity_kms":28},
 {"shower_code":"AUR","name":"Aurigids","ra_radiant":84.0,"dec_radiant":42.0,"solar_long_peak":158.6,"zhr":6,"velocity_kms":66},
 {"shower_code":"SPE","name":"September Epsilon Perseids","ra_radiant":48.0,"dec_radiant":39.7,"solar_long_peak":177.0,"zhr":5,"velocity_kms":64},
 {"shower_code":"CAP","name":"Alpha Capricornids","ra_radiant":307.5,"dec_radiant":-10.0,"solar_long_peak":127.0,"zhr":5,"velocity_kms":23},
 {"shower_code":"GDR","name":"Gamma Draconids","ra_radiant":268.0,"dec_radiant":51.0,"solar_long_peak":105.0,"zhr":5,"velocity_kms":28},
 {"shower_code":"LMI","name":"Leonis Minorids","ra_radiant":162.0,"dec_radiant":37.2,"solar_long_peak":209.0,"zhr":5,"velocity_kms":62},
 {"shower_code":"OPH","name":"Ophiuchids","ra_radiant":258.0,"dec_radiant":-20.0,"solar_long_peak":80.0,"zhr":5,"velocity_kms":28},
 {"shower_code":"JBO","name":"June Bootids","ra_radiant":224.0,"dec_radiant":48.0,"solar_long_peak":83.0,"zhr":5,"velocity_kms":18},
 {"shower_code":"PPU","name":"Pi Puppids","ra_radiant":110.0,"dec_radiant":-45.0,"solar_long_peak":26.8,"zhr":5,"velocity_kms":18},
 {"shower_code":"ARC","name":"Alpha Centaurids","ra_radiant":211.0,"dec_radiant":-59.0,"solar_long_peak":319.2,"zhr":6,"velocity_kms":56},
 {"shower_code":"GAN","name":"Gamma Normids","ra_radiant":239.0,"dec_radiant":-50.0,"solar_long_peak":353.3,"zhr":6,"velocity_kms":56},
 {"shower_code":"VEL","name":"Delta Velids","ra_radiant":131.0,"dec_radiant":-52.0,"solar_long_peak":285.0,"zhr":5,"velocity_kms":35}
]

# ── Fetching Logic ────────────────────────────────────────────────────────────
def fetch_showers():
    print(f"\n[→] Attempting to fetch live data from {IAU_URL}...")
    try:
        resp = requests.get(IAU_URL, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        table = soup.find('table') # Finding the main data table
        
        if not table:
            raise ValueError("No table found on the page.")
            
        rows = table.find_all('tr')
        if len(rows) < 2:
            raise ValueError("Table is empty.")

        # Identify columns
        # Expected header: No, Code, Name, Activity, RA_rad, Dec_rad, dRA, dDec, V_g, r, Zhr, ...
        # Column mapping (0-indexed): Code=1, Name=2, RA_rad=4, Dec_rad=5, SolLon=11, V_g=8, Zhr=10
        records = []
        for i, row in enumerate(rows[1:]):
            cols = row.find_all('td')
            if len(cols) < 12: continue
            
            # Helper to convert radians to degrees
            def to_deg(val_str):
                try:
                    v = float(val_str.replace(',','.'))
                    return round(math.degrees(v), 2)
                except: return None

            def to_float(val_str):
                try: return float(val_str.replace(',','.'))
                except: return None

            records.append({
                "shower_code": cols[1].text.strip(),
                "name": cols[2].text.strip(),
                "ra_radiant": to_deg(cols[4].text.strip()),
                "dec_radiant": to_deg(cols[5].text.strip()),
                "solar_long_peak": to_float(cols[11].text.strip()), # Based on typical PHP layout
                "zhr": to_float(cols[10].text.strip()),
                "velocity_kms": to_float(cols[8].text.strip())
            })
        
        if len(records) > 0:
            df = pd.DataFrame(records)
            df.to_csv(SHOWERS_CSV, index=False)
            print(f"[✓] Live data parsed. Saved {len(df)} showers to {SHOWERS_CSV.name}")
            return True
            
    except Exception as e:
        print(f"[!] Live fetch failed: {e}")
    
    print("[→] Falling back to hardcoded shower list...")
    df = pd.DataFrame(FALLBACK_SHOWERS)
    df.to_csv(SHOWERS_CSV, index=False)
    print(f"[✓] Fallback saved {len(df)} showers to {SHOWERS_CSV.name}")
    return True

def fetch_cities():
    print("\n[→] Fetching India Cities data...")
    # Using the dr5hn mirror as it's the most reliable public CSV
    url = "https://raw.githubusercontent.com/dr5hn/countries-states-cities-database/master/csv/cities.csv"
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text))
        india = df[df['country_name'] == 'India'].copy()
        if len(india) > 0:
            india.to_csv(INDIA_CSV, index=False)
            print(f"[✓] Saved {len(india)} Indian cities to {INDIA_CSV.name}")
            return
    except Exception as e:
        print(f"[!] Cities fetch failed: {e}")
    
    print("[!] Manual download might be needed for cities as described in previous logs.")

if __name__ == "__main__":
    fetch_showers()
    fetch_cities()
    print("\n[Done] All downloads completed.")
