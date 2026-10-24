# Preview Camera 0.2.3

## Perubahan

Live Assessment sebelumnya membatasi camera wall ke kamera sesi terpilih,
termasuk sesi review pending. Operator tidak bisa mengecek kamera paired lain
tanpa berganti/membuat sesi.

Selector Preview camera sekarang tersedia sebelum sesi dan setelah Stop:

- Kamera tertentu: memakai nama kustom serta technical camera ID.
- All paired cameras: wall seluruh kamera paired dengan paging empat preview.
- Session cameras: kembali ke kamera sesi tersimpan. Tanpa sesi, default memakai
  seluruh kamera paired.

Perubahan pilihan hanya lokal di renderer. Tidak ada request create/start sesi,
perubahan camera_node_ids sesi, pairing, atau konfigurasi Pi. Preview lama di-
unmount sehingga polling/request aktif dibatalkan. Kamera offline tetap bisa
dipilih, tetapi tidak dipoll; UI menampilkan Device offline.

Preparing/running/stopping memakai kamera sesi dan menyembunyikan selector idle.
Kesiapan Start dihitung dari kamera sesi, bukan kamera yang dipreview. Assignment
worker dinonaktifkan untuk kamera di luar scope sesi terpilih. Pergantian pilihan
membersihkan focus, paging dan panel inspector agar tidak tertinggal pada kamera
sebelumnya. Pemilihan sesi lain mengembalikan mode Session cameras.

## Verifikasi

- `desktop/tests/idlePreview.browser.js`: pergantian CAM_02/CAM_03, tidak ada sesi,
  sesi stopped, semua paired/kamera sesi, offline tanpa polling, polling kamera
  lama berhenti, tidak ada write/start akibat preview, dan running wall tetap
  sesuai kamera sesi. Tidak ada perubahan readiness Start akibat pilihan preview.
- Viewport 1120x720 dan 1440x900 diperiksa tanpa overflow halaman; screenshot
  idle diperiksa. Tidak menggunakan kamera pengguna untuk tes browser sintetis.
- Regresi workspace 1/2/4/6 kamera, assignment, focus, paging serta start/stop lulus.
- 50 tes backend dan 10 tes logika desktop/profil lulus; ESLint dan build lulus.
  Detector mekanis UI tidak melaporkan temuan.
- Backend paket diuji pada profil smoke terpisah: migrasi/auth, PDF, Excel, ZIP dan
  diagnostik. Versi backend/desktop diselaraskan ke 0.2.3; skor tidak diubah.

## Penggunaan

Installer: `desktop/installer/preview-0.2.3/ERGoSIGHT-Setup-0.2.3.exe`.
Ukuran 135506614 byte; SHA-256
`D87DDC18F7A554585AD3633B3BBF9EDD498AED60B60226D16BE0186D218C947D`.
Isi ASAR dan executable backend cocok dengan hasil build source terakhir.
Tutup aplikasi versi lama, pasang installer, lalu buka Live Assessment dan pilih
Preview camera. Untuk mulai merekam kamera berbeda, buat New session dan pilih
kamera pada dialog sesi; preview saja tidak mengganti target rekaman.

Tidak perlu deploy ulang Pi. Database/pairing tetap memakai profil yang sama.
Uji dua Pi fisik aktif bersamaan dan instalasi pada laptop bersih belum dilakukan.
Installer tidak ditandatangani digital; Windows dapat menampilkan peringatan.
