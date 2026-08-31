# scripts/backup.ps1
#
# Backup SELURUH data Talatee (Postgres + MinIO) ke satu folder, supaya bisa
# dipindah ke laptop lain atau disimpan di Google Drive/hardisk eksternal.
#
# Jalankan dari root project talatee-data-platform (folder ini, sejajar
# dengan docker-compose.yml):
#     .\scripts\backup.ps1
#
# Hasilnya: folder baru talatee-backup-YYYY-MM-DD_HHmm\ berisi:
#   - postgres_dump.sql   (seluruh isi database, lewat pg_dump)
#   - minio_data.tar.gz   (seluruh isi bucket talatee-raw, dikompres jadi 1 file)
#
# CATATAN PENTING:
# 1. minio_data di-kompres jadi 1 file (bukan folder mentah berisi ratusan
#    file kecil) karena file internal MinIO (misal xl.meta) sering GAGAL
#    diupload lewat browser ke Google Drive/cloud storage lain.
# 2. Dipakai `tar` (bukan `cp` biasa) dengan folder `.minio.sys/tmp`
#    dikecualikan + `--ignore-failed-read` — soalnya MinIO tetap AKTIF JALAN
#    saat backup berlangsung, jadi file sementara di situ bisa muncul/hilang
#    sendiri di tengah proses (bukan data penting, aman diabaikan).
#
# PENTING: backup ini TIDAK termasuk kode (itu urusan git/GitHub) dan TIDAK
# termasuk file .env/.env.local (itu harus disalin manual & disimpan aman
# terpisah, jangan taruh di folder backup yang sama supaya tidak ke-upload
# ke Drive/tempat lain tanpa sengaja).

$ErrorActionPreference = "Stop"

$timestamp = Get-Date -Format "yyyy-MM-dd_HHmm"
$backupDir = "talatee-backup-$timestamp"

Write-Host "=== Membuat folder backup: $backupDir ===" -ForegroundColor Cyan
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

Write-Host "=== Menunggu Postgres siap menerima koneksi ===" -ForegroundColor Cyan
$maxRetries = 15
$ready = $false
for ($i = 1; $i -le $maxRetries; $i++) {
    docker exec talatee-database-postgres-1 pg_isready -U talatee 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $ready = $true
        break
    }
    Write-Host "  belum siap, coba lagi ($i/$maxRetries)..."
    Start-Sleep -Seconds 2
}
if (-not $ready) {
    Write-Host "GAGAL: Postgres tidak siap setelah $maxRetries kali percobaan." -ForegroundColor Red
    exit 1
}
Write-Host "  Postgres siap." -ForegroundColor Green

Write-Host "=== Backup Postgres (pg_dump lewat Docker) ===" -ForegroundColor Cyan
docker exec talatee-database-postgres-1 pg_dump -U talatee -d talatee_platform --clean --if-exists `
    | Out-File -FilePath "$backupDir\postgres_dump.sql" -Encoding utf8

if ($LASTEXITCODE -ne 0) {
    Write-Host "GAGAL backup Postgres. Pastikan docker compose up -d sudah jalan." -ForegroundColor Red
    exit 1
}
Write-Host "  OK -> $backupDir\postgres_dump.sql" -ForegroundColor Green

Write-Host "=== Backup MinIO (tar volume Docker jadi 1 file, tahan file sementara) ===" -ForegroundColor Cyan
docker run --rm `
    -v talatee-database_minio_data:/source:ro `
    -v "${PWD}\${backupDir}:/backup" `
    alpine sh -c "apk add --no-cache tar >/dev/null 2>&1; tar --exclude='.minio.sys/tmp' --ignore-failed-read -czf /backup/minio_data.tar.gz -C /source ."

if ($LASTEXITCODE -ne 0) {
    Write-Host "GAGAL backup MinIO." -ForegroundColor Red
    exit 1
}
Write-Host "  OK -> $backupDir\minio_data.tar.gz" -ForegroundColor Green

Write-Host ""
Write-Host "=== BACKUP SELESAI ===" -ForegroundColor Green
Write-Host "Folder: $backupDir"
Write-Host "Isi: postgres_dump.sql + minio_data.tar.gz (cuma 2 file, gampang diupload)"
Write-Host ""
Write-Host "LANGKAH SELANJUTNYA (WAJIB, backup ini belum aman kalau cuma di laptop ini):" -ForegroundColor Yellow
Write-Host "  1. Copy folder '$backupDir' ke Google Drive / hardisk eksternal / cloud storage"
Write-Host "  2. JANGAN taruh folder ini di dalam repo git (sudah bukan urusan git)"
Write-Host "  3. Catat juga isi .env dan .env.local secara TERPISAH di tempat aman"
Write-Host "     (password manager, catatan terenkripsi) -- JANGAN digabung folder backup ini"
