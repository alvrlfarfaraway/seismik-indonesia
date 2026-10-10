"""Unduh katalog gempa USGS (FDSN event API) untuk wilayah Indonesia."""
import io
from pathlib import Path

import pandas as pd
import requests

URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
OUT = Path(__file__).resolve().parent.parent / "data" / "raw" / "usgs_2015_2026.csv"
START_YEAR, END_YEAR = 2015, 2026
END_DATE = "2026-10-01"


def fetch_year(year: int) -> pd.DataFrame:
    params = {
        "format": "csv",
        "minmagnitude": 4.5,
        "starttime": f"{year}-01-01",
        "endtime": END_DATE if year == END_YEAR else f"{year + 1}-01-01",
        "minlatitude": -11,
        "maxlatitude": 6,
        "minlongitude": 95,
        "maxlongitude": 141,
        "orderby": "time-asc",
    }
    r = requests.get(URL, params=params, timeout=120)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    print(f"{year}: {len(df)} baris")
    return df


def main() -> None:
    frames = [fetch_year(y) for y in range(START_YEAR, END_YEAR + 1)]
    df = pd.concat(frames, ignore_index=True).drop_duplicates(subset="id")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)

    t = pd.to_datetime(df["time"])
    print(f"Jumlah baris : {len(df)}")
    print(f"Rentang waktu: {t.min()} sampai {t.max()}")
    print(f"Rentang mag. : {df['mag'].min()} sampai {df['mag'].max()}")


if __name__ == "__main__":
    main()
