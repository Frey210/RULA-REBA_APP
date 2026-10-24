# ERGoSIGHT 0.2.1 - Delivery Lanjutan

Melanjutkan [delivery stabilisasi](stabilization_delivery_2026-10-24.md).
Status implementasi tidak sama dengan kelulusan seluruh gate perangkat.

## Selesai Di Kode

- Start kamera berjalan paralel (maksimal empat permintaan start bersamaan).
  Kamera yang sudah siap mendapat pembaruan lease selama menunggu kamera lain.
  Kegagalan salah satu kamera membatalkan start dan menghentikan kamera sesi.
  SQLAlchemy session/model tidak dipakai lintas thread HTTP.
- Start terautentikasi membawa waktu UTC backend. Worker Pi menggunakan anchor
  tersebut ditambah selisih monotonic untuk timestamp capture; jam OS Pi tidak
  diubah dan tidak memerlukan internet. Provenance `clock_source` disimpan.
  Validasi frame basi backend tetap 30 detik. Ini bukan sinkronisasi lintas kamera
  yang telah dikalibrasi: ada ketidakpastian satu arah jaringan. Jam laptop harus
  benar; perubahan besar jam laptop memerlukan sesi baru.
- Source dapat memakai profil installer secara eksplisit melalui
  `npm.cmd run electron:installed-profile`. Database, media, dan JWT secret tetap
  satu profil. Launcher menolak backend yang berbeda versi/profil pada port 8000;
  tidak menghapus pairing untuk mengatasi konflik tersebut.
- Devices menyediakan Diagnostics: ZIP dengan versi/runtime, ukuran database,
  ruang kosong disk, jumlah rekaman, UUID perangkat, freshness online dan health
  ringkas. Tidak berisi akun, password, token, foto, path profil, atau raw log.
- Penghapusan sesi eksplisit juga menghapus file PDF/ZIP terkait. Jalur media
  harus berada di media root; penghapusan tidak boleh menyentuh file luar profil.
  Retensi raw otomatis tetap nonaktif agar review/data historis tidak berubah.

## Laporan Lengkap

Reports > Generate Report menghasilkan PDF dan ZIP pada direktori UUID baru.
Regenerasi tidak menimpa hasil sebelumnya. Penulisan file sementara dan publikasi
status ready dilakukan setelah kedua artefak selesai; kegagalan menghapus hanya
file generasi baru. Tidak ada migrasi schema atau penghapusan histori.

PDF berisi identitas sesi/operator, versi, catatan dan waktu UTC detik, identitas
kamera/UUID, worker registry dan scope kamera/run/track, status konfirmasi,
durasi observasi/risiko serta rata-rata/peak provisional per track, seluruh event
observed/risiko, seluruh assessment provisional/reviewed, parameter manual,
komponen skor, catatan review, pengukuran sumber, kualitas pose, dan foto.
Total risiko lintas track worker terkonfirmasi memakai gabungan interval overlap.
Jumlah worker di metadata laporan adalah jumlah track sesi, bukan jaminan jumlah
manusia unik; identitas yang belum dikonfirmasi tetap terpisah.

Batas tersembunyi 12 event/20 review dihapus. Timeline entered/left tetap tidak
ditampilkan. Sudut hilang tidak diubah menjadi nol. Foto registrasi hanya menjadi
referensi identitas, bukan bukti penilaian postur. Foto tidak siap, hilang, rusak,
di luar media root atau checksum berbeda dicatat sebagai tidak tersedia. Foto
legacy tidak dinyatakan terverifikasi. Tidak mengambil gambar kamera saat ini
untuk mengganti bukti historis.

ZIP berisi PDF yang sama, semua foto asli yang tersedia, `detections.csv`,
`workers.csv`, `events.csv`, `assessments.csv`, dan `manifest.json` dengan checksum,
sumber frame/run/waktu, hubungan event/detection, serta alasan foto tidak ikut.
Sampel CSV ditulis bertahap; raw payload/credential perangkat tidak diekspor.
Teks CSV yang dapat menjadi formula spreadsheet dinetralkan. File unduhan hanya
bisa diakses akun pemilik. Paket laporan memuat data pribadi; setelah diekspor,
perlindungan dan pembagiannya menjadi tanggung jawab pemegang file.

## Verifikasi

- Backend: 48 tes lulus, termasuk dua kamera dengan barrier startup paralel,
  lease gagal/rollback, 25 review dan lebih dari 12 event, catatan panjang/markup,
  checksum foto, akses owner, generasi immutable, kegagalan disk, dan hapus PDF/ZIP.
  Foto registrasi juga diuji agar berlabel referensi identitas, bukan bukti postur.
  Tabel derajat dibatasi ke sepuluh komponen terukur; skor twist legacy tidak
  ditampilkan sebagai sudut. Hitungan worker di UI Reports diberi label tracks.
- Edge: 21 tes lulus; clock tetap maju menggunakan monotonic ketika jam OS salah
  atau meloncat; fallback lama tetap diberi label device_clock.
- Desktop: 10 tes logika/profil; lint serta TypeScript/Vite build lulus.
- Playwright: workspace 1/2/4/6 kamera sintetis, assignment/focus/paging dan
  start-stop. Reports pada 1120x720 dan 1440x900: PDF/ZIP, diagnostik, filter sesi
  preparing/running/stopping, pemulihan download gagal, dan autentikasi request.
- PDF stres berisi 25 review dengan catatan panjang dirender ke gambar halaman;
  pemeriksaan batas teks tidak menemukan overflow dan contact sheet diperiksa.
- Paket backend: migrasi SQLite baru, register/login, PDF (font/logo), ZIP dan
  diagnostik berhasil di profil smoke terpisah pada port 8010.
- CAM_02 dideploy ke `fbd2b4e` melalui bundle karena Pi tidak memiliki internet.
  Backup `.env` dan state pairing disimpan privat di home Pi. Service aktif;
  kernel, EEPROM, paket Hailo, dan kredensial pairing tidak diubah.
- Uji aktual `SESSION_20261024_008`: pipeline berjalan lima menit, 144 sampel
  status ready, frame age 88-341 ms, 809 header frame terautentikasi diterima.
  Seluruh header memakai backend_session_clock; selisih waktu capture ke ingest
  98-1847 ms. Stop berhasil, proses inference tidak berjalan lagi. Ini bukan
  latency layar, uji memory leak 60 menit, atau validasi worker/ergonomi.
- Laporan format baru untuk `SESSION_20261024_007` dibuat dari data lokal aktual:
  lima foto ikut, tidak ada foto omitted. PDF/ZIP tersedia melalui Reports tanpa
  mengubah laporan generasi sebelumnya. Data/foto privat tidak masuk Git.

## Artefak Dan Penggunaan

- Installer: `desktop/installer/stabilization-0.2.1/ERGoSIGHT-Setup-0.2.1.exe`.
  Ukuran 135008606 byte; SHA-256
  `186B2796AACECD4E5D9C849DEB855718CE641227411628B8E1EEE4BE9101B009`.
  Status Authenticode `NotSigned`. Isi ASAR (HTML/CSS/JS, logo, main/preload dan
  helper profil) serta executable backend dibandingkan byte-for-byte dengan
  hasil build source terakhir; font/logo laporan ikut dalam resource backend.
- Source default tetap memakai DB development terpisah. Untuk perangkat yang
  sudah dipair installer, gunakan perintah installed-profile setelah menutup
  backend/aplikasi lain. Reload/login kembali jika token akses telah kedaluwarsa.
- Stop sesi, selesaikan review sesuai kebutuhan, buka Reports, pilih sesi,
  Generate Report, lalu PDF atau ZIP + Photos. Laporan lama tidak berubah;
  generate ulang agar mendapatkan format 0.2.1.
- Sesi diagnostik lima menit tetap tersimpan untuk audit. Boleh dihapus lewat
  History jika tidak diperlukan; tidak dihapus otomatis.

## Gate Yang Belum Bisa Ditutup

- CAM_03 belum tersedia. Dua Pi pada LAN bersama memerlukan DHCP/IP berbeda;
  jangan gunakan dua server direct-LAN 10.55.0.1 bersamaan pada switch yang sama.
- Uji minimal 60 menit dengan 1-3 worker, pengukuran memory/latency layar,
  occlusion, pakaian serupa, dan pemulihan kabel putus perlu dijalankan aktual.
- Soft Re-ID tidak menjamin orang yang kembali setelah TTL 10 detik mendapat
  nomor yang sama; konfirmasi worker registry tetap diperlukan. Trained body
  Re-ID dan identitas otomatis lintas kamera bukan kemampuan rilis ini.
- Validasi sudut/skor terhadap penilaian ergonomi referensi belum dilakukan.
  Satu kamera 2D tidak dapat menjamin semua sudut/twist teramati.
- Installer/upgrade pada laptop bersih kedua belum diuji. Biner tidak ditandatangani
  dengan sertifikat code-signing; Windows dapat menampilkan peringatan.
- Kebijakan retensi destruktif otomatis ditunda sampai ukuran dan kebutuhan
  penyimpanan terukur. Jangan menghapus Detection begitu saja: sumber review,
  backfill, dan ekspor detail masih menggunakannya. Saat ini tersedia penghapusan
  sesi eksplisit dan diagnostik ukuran DB/ruang kosong, bukan auto-purge.

Rilis ini menutup pekerjaan software di atas, bukan klaim siap produksi penuh
atau kelulusan gate fisik yang masih terbuka.
