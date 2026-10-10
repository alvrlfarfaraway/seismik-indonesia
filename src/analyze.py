"""Analisis katalog USGS: pembersihan, Mc, nilai-b, validasi Monte Carlo."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "usgs_2015_2026.csv"
OUT_CSV = ROOT / "data" / "processed" / "events.csv"
OUT_JSON = ROOT / "web" / "data" / "results.json"

DM = 0.1
LOG10E = np.log10(np.e)
N_BOOT = 2000
SEED = 42

# Wilayah laut yang berada di dalam perairan Indonesia.
LAUT_INDONESIA = {"Banda Sea", "Molucca Sea", "Flores Sea", "Savu Sea",
                  "Java Sea", "Arafura Sea", "Celebes Sea"}


def wilayah(place):
    """Ambil nama negara/wilayah dari bagian setelah koma terakhir."""
    return place.rsplit(",", 1)[-1].strip() if "," in place else place.strip()


def bersihkan(df):
    df = df.copy()
    df["wilayah"] = df["place"].astype(str).map(wilayah)
    masuk = (df["wilayah"] == "Indonesia") | df["wilayah"].isin(LAUT_INDONESIA)
    masuk &= df["mag"].notna() & (df["type"] == "earthquake")
    dibuang = df[~masuk]
    print(f"Baris awal: {len(df)}, dipertahankan: {masuk.sum()}, dibuang: {len(dibuang)}")
    print("Dibuang per wilayah:")
    print(dibuang["wilayah"].value_counts().to_string())
    print("Contoh baris dibuang:")
    contoh = dibuang.groupby("wilayah").head(1)[["place", "latitude", "longitude", "mag"]]
    print(contoh.to_string(index=False))
    bersih = df[masuk].drop(columns="wilayah").reset_index(drop=True)
    return bersih, dibuang


def mc_maxcurv(mag, koreksi=0.2):
    r = np.round(np.asarray(mag) / DM).astype(int)
    hitung = np.bincount(r - r.min())
    modus = (r.min() + hitung.argmax()) * DM
    return round(modus + koreksi, 1), round(modus, 1)


def b_aki(mag, mc):
    m = np.asarray(mag)
    m = m[m >= mc - 1e-9]
    return LOG10E / (m.mean() - (mc - DM / 2)), len(m)


def b_boot(mag, mc, rng, n_boot=N_BOOT):
    m = np.asarray(mag)
    m = m[m >= mc - 1e-9]
    n = len(m)
    if n < 2:
        return None
    idx = rng.integers(0, n, size=(n_boot, n))
    bs = LOG10E / (m[idx].mean(axis=1) - (mc - DM / 2))
    return np.percentile(bs, [2.5, 97.5])


def ringkas_b(mag, mc, rng):
    b, n = b_aki(mag, mc)
    ci = b_boot(mag, mc, rng)
    return {"b": float(b), "n": int(n), "se": float(b / np.sqrt(n)),
            "ci_low": None if ci is None else float(ci[0]),
            "ci_high": None if ci is None else float(ci[1])}


def monte_carlo(mc, rng, b_true=1.0, ukuran=(100, 500, 2000), ulangan=2000, n_boot=1000):
    beta = b_true * np.log(10)
    hasil = []
    for n in ukuran:
        bs = np.empty(ulangan)
        cov_boot = cov_wald = 0
        for i in range(ulangan):
            # Eksponensial terpotong di Mc - dM/2, lalu dibulatkan ke 0,1
            x = mc - DM / 2 + rng.exponential(1 / beta, n)
            m = np.round(x / DM) * DM
            b = LOG10E / (m.mean() - (mc - DM / 2))
            bs[i] = b
            # Bootstrap lewat multinomial pada nilai magnitudo diskret
            nilai, cnt = np.unique(m, return_counts=True)
            rata = rng.multinomial(n, cnt / n, size=n_boot) @ nilai / n
            bb = LOG10E / (rata - (mc - DM / 2))
            lo, hi = np.percentile(bb, [2.5, 97.5])
            cov_boot += lo <= b_true <= hi
            se = b / np.sqrt(n)
            cov_wald += (b - 1.96 * se) <= b_true <= (b + 1.96 * se)
        hasil.append({"N": n, "ulangan": ulangan, "b_benar": b_true,
                      "rata_b": float(bs.mean()),
                      "bias": float(bs.mean() - b_true),
                      "rmse": float(np.sqrt(np.mean((bs - b_true) ** 2))),
                      "cakupan_bootstrap": cov_boot / ulangan,
                      "cakupan_wald": cov_wald / ulangan})
        print(f"  MC N={n}: bias={hasil[-1]['bias']:+.4f} RMSE={hasil[-1]['rmse']:.4f} "
              f"cakupan boot={cov_boot/ulangan:.3f} wald={cov_wald/ulangan:.3f}")
    return hasil


def main():
    rng = np.random.default_rng(SEED)
    df = pd.read_csv(RAW)
    ev, _ = bersihkan(df)
    ev["time"] = pd.to_datetime(ev["time"], utc=True)
    ev["year"] = ev["time"].dt.year
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    ev.to_csv(OUT_CSV, index=False)

    mag = ev["mag"].round(1).to_numpy()
    mc, mc_modus = mc_maxcurv(mag)
    glob = ringkas_b(mag, mc, rng)

    per_tahun = []
    for y, g in ev.groupby("year"):
        r = ringkas_b(g["mag"].round(1).to_numpy(), mc, rng)
        r.update({"tahun": int(y), "n_total": int(len(g))})
        per_tahun.append(r)

    print("Monte Carlo:")
    mcres = monte_carlo(mc, rng)

    bins = np.round(np.arange(mag.min(), mag.max() + DM, DM), 1)
    cnt = np.array([(mag >= x - 1e-9).sum() for x in bins])
    cnt_inc = np.array([((mag > x - DM / 2) & (mag < x + DM / 2)).sum() for x in bins])
    fm = []
    for x, c, ci in zip(bins, cnt, cnt_inc):
        fm.append({"m": float(x), "n_tiap_bin": int(ci), "n_kumulatif": int(c)})
    a = float(np.log10(glob["n"]) + glob["b"] * (mc - DM / 2))

    besar = ev[ev["mag"] >= 5.0]
    titik = [{"lat": float(r.latitude), "lon": float(r.longitude), "mag": float(r.mag),
              "depth": float(r.depth), "time": r.time.strftime("%Y-%m-%dT%H:%M:%SZ"),
              "place": r.place} for r in besar.itertuples()]

    hasil = {
        "n_awal": int(len(df)), "n_bersih": int(len(ev)),
        "rentang_waktu": [ev["time"].min().isoformat(), ev["time"].max().isoformat()],
        "metode": {"mc": "maximum curvature (modus histogram 0,1) + 0,2",
                   "b": "Aki-Utsu dengan koreksi pembulatan dM/2, M >= Mc",
                   "bootstrap": N_BOOT, "seed": SEED},
        "kejadian_per_tahun": {int(k): int(v) for k, v in ev["year"].value_counts().sort_index().items()},
        "histogram_magnitudo": [{"m": float(x), "n": int(c)} for x, c in zip(bins, cnt_inc)],
        "frekuensi_magnitudo": fm,
        "mc": {"modus": mc_modus, "mc": mc},
        "b_global": glob, "a_value": a,
        "b_per_tahun": per_tahun,
        "monte_carlo": mcres,
        "lokasi_m5": titik,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(hasil, ensure_ascii=False, indent=1), encoding="utf-8")

    print("\n=== RINGKASAN ===")
    print(f"Kejadian bersih: {len(ev)} ({hasil['rentang_waktu'][0][:10]} s.d. {hasil['rentang_waktu'][1][:10]})")
    print(f"Mc: modus {mc_modus} + 0,2 = {mc}")
    print(f"b = {glob['b']:.3f}, SE = {glob['se']:.3f}, CI95 bootstrap = [{glob['ci_low']:.3f}, {glob['ci_high']:.3f}], n(M>=Mc) = {glob['n']}")
    print("b per tahun:")
    for r in per_tahun:
        print(f"  {r['tahun']}: b={r['b']:.3f} [{r['ci_low']:.3f}, {r['ci_high']:.3f}] n={r['n']}")
    print(f"Kejadian M>=5,0: {len(titik)}")
    print(f"Tersimpan: {OUT_CSV.relative_to(ROOT)}, {OUT_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
