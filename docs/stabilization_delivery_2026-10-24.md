# ERGoSIGHT 0.2.0 - Stabilisasi Deteksi

Pembaruan terbaru: [delivery 0.2.1](stabilization_followup_2026-10-24.md).
Catatan installer/clock manual di bawah adalah histori 0.2.0, bukan instruksi
rilis terkini. Gunakan 0.2.1 untuk laporan lengkap dan profil source/installer.

Implementasi dari [audit 24 Oktober 2026](audit_detection_recording_2026-10-24.md).
Dokumen ini membedakan perubahan kode dari validasi perangkat yang masih diperlukan.

## Perubahan yang Sudah Dibuat

- Perangkat memiliki ID persisten, kredensial pairing, dan verifikasi identitas pada
  respons. Alamat `10.55.0.1` tidak lagi dianggap identitas kamera.
- Backend memeriksa akun/pemilik, kamera sesi, run ID, timestamp, dan urutan frame.
  WebSocket perangkat memerlukan Bearer; token login browser dikirim lewat pesan
  autentikasi, bukan query URL yang dapat tercatat di access log.
- Status agent dan kesiapan kamera dipisahkan. Backend memeriksa perangkat setiap
  sekitar tiga detik; UI memperbarui status otomatis. Versi lama ditandai Pairing Required.
- Sesi melewati preparing dan menunggu frame pertama. Kegagalan startup tidak
  dinyatakan running. Kamera yang sedang dipakai sesi lain ditolak.
- Lease edge 25 detik menghentikan inferensi tanpa pembaruan backend. Heartbeat
  aplikasi setiap lima detik mencegah backend yang tertinggal terus menjalankan
  kamera setelah operator menutup aplikasi; batas hilangnya operator 20 detik.
- Kontrol FPS source diterapkan secara eksplisit; queue sebelum inference membuang
  frame lama. Pekerjaan hand/JPEG dipindahkan ke worker dengan antrean satu frame.
  Batch inference menjadi satu. Frame terlalu tua tidak diterbitkan sebagai live.
- Preview mengambil satu frame terbaru per permintaan, tanpa menumpuk request.
  Error kamera tampil sebagai unavailable; demo tidak menjadi fallback otomatis.
- Ring buffer menyimpan maksimal 36 frame beserta pose, run, frame ID, dan waktu
  sumber. Snapshot meminta frame yang tepat; frame kedaluwarsa tidak diganti foto lain.
- Snapshot dan sumber review dipertahankan; inspeksi foto menggantikan recapture
  historis. Worker observed memilih sampel lebih lengkap/berisiko sebelum direview.
- Wrist hilang tetap null. Backend menghitung provisional; final memerlukan frame
  terverifikasi serta semua komponen terukur atau nilai manual eksplisit. Koreksi
  manual disimpan terpisah dalam breakdown review.
- Worker observation dibedakan berdasarkan kamera dan run. Track kandidat harus
  cukup stabil dan memperlihatkan tubuh sebelum menjadi worker observed.
- Re-ID memakai kontinuitas posisi untuk gap singkat, menolak kecocokan ambigu,
  dan menghapus galeri kedaluwarsa. Nomor track bukan identitas manusia terkonfirmasi.
- Timeline utama menyembunyikan entered/left, termasuk rekaman lama. Gap berhenti
  menambah exposure. Interval risiko yang overlap untuk worker terkonfirmasi
  dihitung sekali pada total summary/analytics.
- ACK ingest tidak menunggu snapshot HTTP. Snapshot diproses lewat job tersimpan;
  raw row tidak lagi menyalin seluruh payload semua worker. Frame retry/out-of-order
  tidak menggandakan sampel. Subscriber lambat memiliki timeout.
- Migrasi menambah scope kamera/run dan event key, tanpa menghapus histori.
  Startup membackup database SQLite sebelum migrasi integritas.

## Validasi Lokal

- Backend: 37 tes auth/pairing, lifecycle, deduplikasi, urutan frame, pemisahan kamera,
  data hilang, koreksi manual, bukti immutable, PDF privat, exposure overlap,
  serta hilangnya operator.
- Edge: 19 tes ID persisten, otorisasi, buffer terbatas, frame basi, gap track, dan
  dua identitas dengan penampilan ambigu.
- Desktop: TypeScript/Vite build, ESLint, serta Playwright pada lebar 1440 dan
  1120 piksel. Review tanpa data lengkap tidak dapat difinalkan, foto dapat
  diperbesar, status kamera offline terbaca, dan tidak ada overflow horizontal.
- Database: migrasi fresh SQLite dan salinan database lokal diverifikasi; jumlah
  rekaman dipertahankan dan integrity_check OK. Database asli tidak diubah saat tes.
- Paket: backend hasil PyInstaller diuji terpisah; isi kode paket dibandingkan
  dengan source. Installer dibangun, tetapi belum diuji instalasi pada laptop baru.

## Jika Pairing Versi Baru Gagal

Pemeriksaan langsung pada CAM_02 di `http://10.55.0.1:8765/pairing/info`
menunjukkan agent lama: `device_id` belum tersedia, meskipun `paired` bernilai
true. Status paired tersebut milik agent lama, bukan bukti bahwa kontrak 0.2.0
sudah aktif. Backend baru sengaja menolak agent tanpa identitas persisten.

Solusi: deploy agent seperti langkah berikut, lalu Scan LAN dan pairing ulang.
Jangan menghapus kamera, histori, atau state pairing. Aplikasi kini membedakan
agent kedaluwarsa, kredensial pemilik, kode kedaluwarsa, jaringan, dan format
pairing yang tidak cocok. Pairing tidak melewati keamanan untuk mendukung agent lama.

## Deploy Raspberry Pi Secara Manual

Percobaan awal deploy SSH otomatis ditolak peninjauan otomatis dengan keterangan
`blocked by policy`; perintah tersebut tidak dijalankan. Pengguna kemudian berhasil
deploy manual CAM_02 melalui git bundle sampai `9cb9950`. Langkah berikut tetap
menjadi panduan untuk perangkat lain. Tidak ada perubahan kernel, EEPROM, atau
boot order dalam rilis ini.

1. Stop sesi aktif dari aplikasi lama. Tutup aplikasi sebelum mengganti backend.
2. Masuk ke Pi yang benar. Untuk kabel langsung:

   ```text
   ssh admin@10.55.0.1
   ```

3. Jalankan perintah berikut di terminal Pi. Backup menyimpan kredensial lokal;
   jangan upload folder backup ke GitHub.

   ```bash
   cd /home/admin/RULA-REBA_Detection_HailoAI
   umask 077
   backup="$HOME/ergosight-backup-$(date +%Y%m%d-%H%M%S)"
   mkdir -p "$backup"
   cp .env data/edge_state.json "$backup/"
   sudo systemctl stop ergoquipt-edge-agent
   git pull --ff-only
   sudo systemctl start ergoquipt-edge-agent
   systemctl is-active ergoquipt-edge-agent
   curl -fsS http://127.0.0.1:8765/pairing/info
   ```

   Jika `git pull` gagal karena perubahan lokal, simpan perubahan tersebut dahulu.
   Jangan memakai `git reset --hard`. Service dapat dinyalakan kembali dengan
   `sudo systemctl start ergoquipt-edge-agent`.

   Hasil terakhir harus memiliki `cam_id: CAM_02` dan `device_id` berupa UUID.
   Jika `device_id` belum ada, jangan pairing dahulu: cek folder service dengan
   `systemctl cat ergoquipt-edge-agent` dan log menggunakan
   `journalctl -u ergoquipt-edge-agent -n 50 --no-pager`.

4. Jalankan aplikasi dari source terbaru:

   ```powershell
   cd D:\Aerasea\RULA-REBA_APP\desktop
   npm.cmd run electron
   ```

   Jika memakai installer, pasang build terbaru dari
   `desktop/installer/reliability-0.2.0-pairing/ERGoSIGHT-Setup-0.2.0.exe`. Installer 0.1.0
   tidak mendukung kontrak perangkat baru. Jangan menghapus `%APPDATA%\ERGoSIGHT`.

5. Login, buka Devices, Scan LAN, Create pairing code, lalu Pair pada perangkat
   yang dimaksud. Pairing ulang satu kali diperlukan untuk perangkat versi lama.
   Tunggu Device Online dan Camera Ready sebelum memulai sesi.
6. Ulangi untuk CAM_03 saat perangkat tersebut tersambung. Dua Pi pada satu LAN
   bersama harus memakai DHCP router/AP; dua server direct-LAN `10.55.0.1` tidak
   boleh disambungkan bersamaan ke switch yang sama.

State pairing tidak boleh dihapus sebagai langkah troubleshooting rutin. Jika
perangkat sebelumnya dipair ke laptop/backend lain yang masih menyimpan kredensial,
gunakan backend pemilik untuk transfer. Reset kepemilikan memerlukan prosedur
eksplisit; tidak disediakan bypass autentikasi otomatis.

## Gate yang Masih Terbuka

### Preview Auto dan Tes Gerakan

Perhatikan profil backend saat menguji source: default launcher development memakai
`backend/dev_server.sqlite3`, sedangkan installer memakai
`%APPDATA%/ergosight-desktop/ergosight.sqlite3`. Keduanya tidak berbagi akun maupun
kredensial pairing. Untuk tes source dengan perangkat yang sudah dipair installer,
backend harus memakai database, `.jwt-secret`, dan media dari profil installer yang
sama melalui `ERGOQUIPT_DATABASE_URL`, `JWT_SECRET_KEY`, dan `MEDIA_ROOT`. Jangan
menghapus state Pi atau mencoba pairing ke database development kosong. Setelah
berganti profil backend, reload Electron dan login kembali dengan akun profil itu.

Pada pemeriksaan setelah peralihan profil, CAM_02 terverifikasi online dan
`camera_available: true`; inferensi masih idle sebelum pengguna memulai sesi.

Perubahan desktop berikutnya menjadikan Auto sebagai default preview. Laju polling
diperkirakan dari respons jaringan dan pengulangan byte gambar, bukan FPS nominal
kamera. Batas Auto 4-12 request/detik sebelum memperhitungkan jaringan yang lambat.
Hanya satu request aktif per preview; durasi request sudah dihitung dalam interval.
Gambar identik tidak dirender ulang. Indikator FPS menghitung frame berbeda yang
diterima preview, bukan FPS inferensi atau jaminan refresh layar.

Ikon Preview settings membuka batas manual 4/8/12 atau Auto. Pengaturan ini tidak
mengubah kamera, pose inference, maupun frekuensi pencatatan. Tidak perlu deploy
ulang Pi untuk perubahan ini. Installer 0.2.0 pada folder pairing di atas dibuat
sebelum perubahan Auto; gunakan source terbaru untuk pengujian ini.

Untuk tes aktual, buka Live Assessment, pilih CAM_02, tunggu Camera Ready, lalu
mulai sesi. Berdiri dengan tubuh terlihat penuh; gerakkan tangan dan badan,
kemudian berhenti mendadak untuk membandingkan gerakan dan preview. Ulangi setelah
5-10 menit, lalu Stop dan periksa sumber snapshot di Session Review. Catat FPS
preview serta apakah delay bertambah; jangan gunakan hasil ini sebagai validasi
akurasi skor ergonomi. Mulai dengan satu worker dan satu kamera.

### Validasi Hardware

#### Workspace Multi-Kamera

Live Assessment sekarang memakai toolbar sesi ringkas dan camera wall di dalam
viewport desktop. Maksimal empat preview tampil bersamaan, otomatis satu atau dua
kolom sesuai jumlah kamera. Kamera kelima dan seterusnya berada pada halaman
berikutnya; ikon focus memperbesar satu kamera dan dapat dikembalikan ke grid.
Gambar memakai object-fit contain agar rasio sumber dipertahankan tanpa crop.

Start session dan Stop session tetap mengendalikan seluruh sesi/kamera terpilih,
bukan satu kamera secara terpisah. New session membuka pemilihan kamera serta
catatan; kamera offline/tidak siap tidak dapat dipilih. Video hanya menghentikan
permintaan preview. Pergantian halaman/focus tidak menghentikan inferensi atau
pencatatan kamera sesi yang tidak sedang ditampilkan.

Ikon worker di tiap kartu membuka panel samping. Kamera dan worker dapat dipilih
langsung tanpa scroll halaman. Daftar worker memiliki scroll lokal; Measurements
dibuka hanya ketika diperlukan. Assignment memperlihatkan proses penyimpanan dan
error yang bisa dicoba ulang, tanpa mengubah identitas pada kamera lain. Panel
tidak menutupi toolbar Stop session. Ukuran kamera hanya berubah saat operator
membuka panel, memilih focus, mengganti halaman, atau mengubah ukuran jendela;
kemunculan/hilangnya deteksi tidak mengubah grid.

Regresi browser mencakup 1/2/4 kamera, paging enam kamera, viewport 1120x720 dan
1440x900, source gagal/pulih, start/stop, kamera offline, assignment gagal/pulih,
ID lokal yang sama lintas kamera, serta pemilihan track langsung. Tes memakai
endpoint dan gambar sintetis, bukan bukti kapasitas empat Pi fisik. Installer lama
belum memuat workspace ini; gunakan source terbaru. Uji multi-Pi fisik dan sesi
panjang tetap merupakan gate terpisah.

#### Ukuran Preview Stabil

Grid preview diperbaiki agar isi Detection Insights tidak mengubah lebar/tinggi
kamera. Preview tetap 16:9; panel data memakai lebar kolom terbatas dan scroll
internal. Grid sudut menyesuaikan ruang panel, tanpa memperbesar preview.

Regresi browser `desktop/tests/livePreviewLayout.browser.js` mereproduksi bug lama
(lebar 623.5 menjadi 922 px ketika worker muncul). Setelah perbaikan, ukuran dan
posisi preview tetap pada transisi 0/1/6/0 worker di viewport 1440, 1280, dan 1120
px, termasuk pergantian ukuran gambar sumber. Tidak ada overlap atau overflow
horizontal. Jalankan dengan Vite pada 5173 dan
`playwright-cli.cmd run-code --filename=desktop/tests/livePreviewLayout.browser.js`
setelah membuka browser Playwright. Tes memakai data sintetis tanpa mengubah sesi
atau database pengguna. Installer lama belum memuat perbaikan CSS ini.

#### Detection Insights Tanpa Kedipan

Kartu worker tidak lagi dihapus ketika pose kosong atau melewati batas freshness
dua detik. Panel menyimpan maksimal 32 snapshot worker terakhir per kamera/run,
mempertahankan urutan kartu serta key berdasarkan worker, bukan nomor tracking.
Setelah dua detik tanpa pembaruan, kartu berstatus Last seen / not live. Koneksi
putus dan sesi tidak aktif juga tidak boleh menampilkan status Live. Data lama
tetap terpisah dari hitungan orang aktif, overlay, dan perhitungan exposure.

Cache dibersihkan saat sesi berganti dan dibatasi ke run kamera yang sesuai;
pengguna tidak melihat pose sesi/perangkat lain sebagai data aktif. Sembilan tes
logika preview/insights mencakup gap, perubahan tracking, scope, urutan data, batas
retensi, dan freshness. Regresi browser juga memeriksa kartu DOM tetap sama saat
worker menghilang serta panel tetap ada ketika koneksi putus. Ini perbaikan UI,
bukan peningkatan akurasi detektor/Re-ID. Installer lama belum memuat perubahan ini.

#### Uji Sesi Aktual CAM_02

- Sesi `SESSION_20261024_004` berhasil menjalankan pipeline. Awalnya ingest ditolak:
  jam Pi berada pada 27 September, laptop 24 Oktober, dan NTP Pi belum sinkron.
  Jam UTC Pi dikoreksi dari laptop melalui SSH terverifikasi; validasi stale frame
  backend tetap aktif. Setelah koreksi, deteksi mulai tersimpan.
- Dua belas sampel selama sekitar 22 detik tetap running/ready. Umur frame sumber
  133-371 ms tanpa tren meningkat; RSS proses sekitar 235 MiB. Ini bukan uji leak
  durasi panjang atau pengukuran latency layar.
- Pengguna melaporkan Preview Auto sekitar 4 FPS saat berada di depan kamera,
  video terus berjalan dan mengikuti gerakan, bukan memutar gerakan lama.
- `REID_0002` stabil selama jendela sampel, tetapi kemudian muncul ID 3/4/5.
  Interval antar deteksi ID berbeda sekitar 13-26 detik, sedangkan konfigurasi
  perangkat `EDGE_REID_TTL_SECONDS=10`. Pengguna mengonfirmasi sempat keluar kamera;
  perubahan tersebut konsisten dengan batas retensi ini, bukan bukti ID berubah
  ketika pekerja terus terlihat. Re-identifikasi setelah jeda panjang belum lulus.
- Snapshot sesi berstatus ready. Review visual dan akurasi sudut tetap perlu diuji.
- Bagian sesi sebelum koreksi jam tidak diterima backend; jangan menganggap
  durasi tersebut sebagai exposure tercatat. Koreksi jam manual belum menyelesaikan
  sinkronisasi otomatis untuk perangkat LAN tanpa internet; ini menjadi gate MVP
  sebelum operasi tanpa bantuan IT.

- Deploy manual CAM_02 sampai commit `9cb9950` sudah dikonfirmasi melalui output
  pengguna. Pemeriksaan LAN mengonfirmasi device_id tersedia dan kontrol tanpa
  kredensial ditolak 403.
- Startup pertama menemukan `ModuleNotFoundError: pydantic_settings` pada
  environment Hailo. Commit edge `dc15a51` memisahkan writer frame dari settings
  agent; path data diberikan eksplisit oleh worker. Update sudah dideploy langsung
  ke CAM_02, tanpa mengubah paket Hailo, kernel, EEPROM, atau pairing.
- Uji diagnostik start/stop pada Pi berhasil: frame pertama ready, empat sampel
  berikutnya running/ready, frame age 148/156/248/339 ms, dan proses berhasil
  dihentikan. Ini umur frame sumber, bukan pengukuran latency layar. Probe memakai
  run diagnostik terpisah, bukan assessment pengguna. Uji sesi aktual, kualitas
  pose/hand, dan kestabilan durasi panjang masih diperlukan.
- Uji 60 menit dan target latency audit belum terbukti. Jalankan satu kamera dahulu,
  1-3 worker, kemudian dua Pi. Catat apakah frame age dan pemakaian memori stabil.
- Belum ada klaim akurasi identitas otomatis untuk semua occlusion, pakaian serupa,
  atau perpindahan lintas kamera. Konfirmasi worker registry tetap diperlukan.
- Validasi sudut dan skor terhadap penilaian ergonomi referensi tetap merupakan
  gate terpisah; 2D dan komponen twist memiliki keterbatasan observasi.
- Retensi raw data otomatis tidak diaktifkan agar rekaman pengguna tidak terhapus
  diam-diam. Ukuran database perlu diukur pada uji sesi panjang sebelum kebijakan
  retensi ditetapkan.
- Bukti lama tanpa frame provenance tetap legacy; gambar yang sudah tertimpa tidak
  dapat dipulihkan dengan mengambil gambar kamera saat ini.

Rilis ini memperbaiki jalur software, tetapi belum dinyatakan lulus gate hardware
atau siap produksi penuh sebelum pengujian di atas diselesaikan.
