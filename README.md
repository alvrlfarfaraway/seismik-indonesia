# Analisis Seismisitas Indonesia

## Tujuan

Menganalisis pola kegempaan di wilayah Indonesia menggunakan katalog gempa terbuka
dari USGS (FDSN event API) untuk memahami distribusi ruang dan waktu gempa serta
karakteristik statistiknya. Proyek ini adalah analisis statistik, bukan prediksi gempa.

## Struktur Proyek

```
seismik-indonesia/
├── data/
│   ├── raw/          # data mentah hasil unduhan (tidak dilacak git)
│   └── processed/    # data bersih/hasil olahan (tidak dilacak git)
├── src/              # modul Python (pengambilan data, pembersihan, analisis)
├── notebooks/        # eksplorasi dan visualisasi
├── requirements.txt
└── README.md
```

## Rencana Tiga Tahap

### Tahap 1 - Pengambilan & Pembersihan Data
- Mengunduh katalog gempa untuk wilayah Indonesia melalui API.
- Membersihkan data: menghapus duplikat, menangani nilai hilang, menyeragamkan
  format waktu, magnitudo, dan kedalaman.
- Menyimpan hasil ke `data/processed/`.

### Tahap 2 - Analisis Eksploratif
- Statistik deskriptif magnitudo dan kedalaman.
- Peta sebaran episenter dan tren jumlah gempa per waktu.
- Perbandingan antarwilayah tektonik (mis. Sumatra, Jawa, Sulawesi, Maluku, Papua).

### Tahap 3 - Analisis Statistik Seismisitas
- Estimasi nilai-b Gutenberg-Richter dengan maximum likelihood (Aki-Utsu).
- Interval kepercayaan nilai-b dengan bootstrap.
- Penentuan magnitudo kelengkapan (Mc) katalog.
- Validasi Monte Carlo terhadap estimator.
- Ringkasan temuan dan keterbatasan analisis.

## Memulai

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

## Status

Tahap awal: kerangka proyek sudah disiapkan, analisis belum ditulis.
