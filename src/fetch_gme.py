"""Download GME MGP hourly price files (anonymous front-end API) and parse NORD into data/gme_nord.csv.

Raw GME data stays local (gitignored): GME terms allow personal, non-commercial use only; source: Gestore dei Mercati Energetici S.p.A.
Usage: fetch_gme.py START_YYYY-MM END_YYYY-MM
"""
import calendar, re, sys, time, zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
import pandas as pd, requests

BASE = "https://gme.mercatoelettrico.org"
PAGE = BASE + "/en-us/Home/Results/Electricity/MGP/Download/Download?valore=Prezzi"
API = BASE + "/DesktopModules/GmeDownload/API/ExcelDownload/downloadzipfile"
ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"


def session():
    s = requests.Session(); s.headers["User-Agent"] = "Mozilla/5.0"
    html = s.get(PAGE, timeout=60).text
    s.headers.update({"RequestVerificationToken": re.search(r'RequestVerificationToken" type="hidden" value="([^"]+)"', html).group(1),
                      "ModuleId": re.search(r'ModuleId":(\d+)', html).group(1), "TabId": re.search(r'TabId":(\d+)', html).group(1)})
    return s


def fetch_month(s, y, m):
    last = calendar.monthrange(y, m)[1]
    p = dict(DataInizio=f"{y}{m:02d}01", DataFine=f"{y}{m:02d}{last}", Date=f"{y}{m:02d}01", Mercato="MGP", Settore="Prezzi", FiltroDate="InizioFine")
    r = s.get(API, params=p, timeout=120)
    if r.status_code != 200 or r.content[:2] != b"PK":
        raise RuntimeError(f"{y}-{m:02d} status={r.status_code} head={r.content[:100]!r}")
    (RAW / f"{y}{m:02d}.zip").write_bytes(r.content)


def parse():
    rows = []
    for zf in sorted(RAW.glob("*.zip")):
        z = zipfile.ZipFile(zf)
        for n in z.namelist():
            if re.fullmatch(r"\d{8}MGPPrezzi\.xml", n):  # hourly file only
                for el in ET.fromstring(z.read(n)).iter("Prezzi"):
                    rows.append((el.findtext("Data"), int(el.findtext("Ora")), float(el.findtext("NORD").replace(",", "."))))
    df = pd.DataFrame(rows, columns=["date", "hour", "nord"])
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
    df = df.sort_values(["date", "hour"]).drop_duplicates(["date", "hour"]).reset_index(drop=True)
    df.to_csv(ROOT / "data" / "gme_nord.csv", index=False)
    return df


if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    lenient = "--lenient" in sys.argv
    y, m = map(int, sys.argv[1].split("-")); ye, me = map(int, sys.argv[2].split("-"))
    s = session()
    while (y, m) <= (ye, me):
        for t in range(4):
            try:
                fetch_month(s, y, m); break
            except Exception as e:
                print("retry", y, m, str(e)[:150], flush=True)
                if t == 3:
                    if lenient: break
                    raise
                time.sleep(10 * (t + 1)); s = session()
        m += 1
        if m == 13: y, m = y + 1, 1
        time.sleep(0.5)
    df = parse()
    print("parsed", len(df), df.date.min().date(), df.date.max().date())
