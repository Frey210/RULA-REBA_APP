# ERGoSIGHT 0.2.0 - Stabilisasi Deteksi

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
- Edge: 18 tes ID persisten, otorisasi, buffer terbatas, frame basi, gap track, dan
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

Deploy SSH otomatis pada sesi ini ditolak peninjauan otomatis dengan keterangan
`blocked by policy`; perintah tidak dijalankan. Raspberry Pi masih memakai versi
sebelumnya. Tidak ada perubahan kernel, EEPROM, atau boot order dalam rilis ini.

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

- Pipeline Hailo pada hardware belum diuji dengan kode rilis ini karena deploy
  diblokir. Validasi kompatibilitas source caps, frame age, dan hand inference
  diperlukan segera setelah deploy manual.
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
