# Report Exports 0.2.2

## Perbaikan

- PDF tidak lagi mencetak seluruh dictionary/UUID sebagai paragraf panjang.
  Ringkasan sesi, worker/kamera, event, assessment, foto, dan referensi teknis
  mempunyai bagian terpisah. Heading memakai leading eksplisit; sel dibungkus,
  label/angka disejajarkan, tabel dapat berlanjut ke halaman berikutnya.
- Foto utama event hanya dipilih jika detection ID sama dengan sumber pengukuran.
  Foto frame lain tidak dipakai sebagai pengganti. Semua foto tersedia tetap ada
  di lampiran dan ZIP. Angka wrist twist legacy bukan sudut terukur.
- Excel memakai openpyxl sebagai dependency backend. Sheet: Summary, Workers,
  Events, Assessments, Review Details, Measurements, Photos, References.
  Tabel memiliki filter/freeze pane, format tanggal UTC dan angka, lebar kolom,
  row height serta area cetak. Foto memakai thumbnail tertanam; original tetap
  utuh dalam ZIP. Setiap dua foto diberi batas halaman cetak.
- Measurements berisi frame sumber representatif event/foto, bukan seluruh frame
  sesi. Semua raw samples tersedia pada detections.csv dalam ZIP. Review notes
  panjang dibagi menjadi bagian yang dapat dibaca, tanpa membuang isi.
- Nilai nol tetap numerik; pengukuran hilang tetap kosong di Excel dan ditandai
  unavailable di PDF. User text ditulis sebagai string, bukan formula Excel.
- PDF, Excel dan ZIP merupakan satu generasi immutable. ZIP juga memuat workbook
  serta checksum Excel. File sementara dibersihkan saat gagal; laporan generasi
  lama, bukti sumber, dan pairing tidak diubah. Hapus sesi juga menghapus Excel.
- Endpoint Excel memakai autentikasi pemilik dan pembatasan media root seperti
  PDF/ZIP. Path file privat tidak diberikan ke renderer.

## Menemukan Unduhan

1. Buka Reports dan pilih sesi yang sudah berhenti.
2. Klik Generate Report. Tidak perlu kembali ke halaman lain.
3. Download PDF, Download Excel, Download ZIP muncul tepat di bawah kontrol
   generate, juga pada baris laporan. ZIP memuat PDF, Excel, foto asli, CSV dan
   manifest. Ketiganya memakai request Bearer; token tidak dimasukkan ke URL.
4. Jika laporan lama belum memiliki ZIP/Excel, tombol tetap terlihat tetapi
   nonaktif dengan petunjuk Generate Report. Tidak membuat ZIP dari data mutakhir
   lalu menyatakannya sebagai arsip lama. Generate menghasilkan report ID baru.

## Verifikasi

- 50 tes backend lulus: akses owner, Excel privat, checksum/isi ZIP, formula
  injection, nilai nol versus kosong, foto registrasi, hapus artefak, kegagalan
  penulisan, dan foto event harus sama frame dengan pengukuran.
- 10 tes logika desktop/profil lulus. TypeScript/Vite build dan ESLint lulus.
  Pemeriksaan mekanis UI Impeccable tidak melaporkan temuan pada file yang diubah.
- Playwright pada 1120x720 dan 1440x900 memeriksa tombol unduh, laporan legacy,
  generate, PDF/Excel/ZIP, autentikasi request dan pemulihan download gagal.
- PDF aktual sesi 007: sembilan halaman, lima foto, tidak ditemukan teks keluar
  area cetak atau kata bertumpuk; contact sheet dan layout halaman diperiksa.
  PDF stres dengan 25 review/catatan panjang tetap berhasil dirender tanpa
  overflow, tidak dibatasi jumlah event atau review.
- Workbook aktual dan workbook stres dibuka read-only pada Excel lokal lalu
  dirender menjadi PDF tanpa prompt repair. Summary, Review Details, Photos
  diperiksa; lima foto aktual tercetak pada tiga halaman setelah page break.
- Build backend PyInstaller diuji pada DB smoke terpisah: register/login, PDF,
  Excel, ZIP serta diagnostik. Tidak memakai DB akun pengguna untuk smoke test.

## Delivery

Installer baru: `desktop/installer/reports-0.2.2/ERGoSIGHT-Setup-0.2.2.exe`.
Ukuran 135506061 byte; SHA-256
`2328A4B4C396496574F226A0351611E25807EB242675538640123DA004F50F8B`.
Isi ASAR dan executable backend dibandingkan dengan hasil build source terakhir;
font/logo laporan ikut di resource paket. Authenticode: `NotSigned`.
Source juga dapat dijalankan dengan `npm.cmd run electron:installed-profile`
setelah menutup backend/aplikasi versi lama. Backend dan desktop sama-sama 0.2.2;
format manifest laporan menjadi 2. Data sesi dan secret profil tetap dipertahankan.

Tidak perlu deploy ulang Pi untuk perubahan laporan ini. Installer belum diuji
upgrade pada laptop bersih kedua dan tidak memakai sertifikat code-signing.
Raw data tidak dihapus otomatis. Validasi ergonomi, multi-Pi dan sesi satu jam
tetap mengikuti gate stabilisasi sebelumnya, tidak ditutup oleh pengujian laporan.
