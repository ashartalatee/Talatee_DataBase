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
#   - minio_data\         (seluruh isi bucket talatee-raw, file mentah)
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

Write-Host "=== Backup Postgres (pg_dump lewat Docker) ===" -ForegroundColor Cyan
docker exec talatee-database-postgres-1 pg_dump -U talatee -d talatee_platform --clean --if-exists `
    | Out-File -FilePath "$backupDir\postgres_dump.sql" -Encoding utf8

if ($LASTEXITCODE -ne 0) {
    Write-Host "GAGAL backup Postgres. Pastikan docker compose up -d sudah jalan." -ForegroundColor Red
    exit 1
}
Write-Host "  OK -> $backupDir\postgres_dump.sql" -ForegroundColor Green

Write-Host "=== Backup MinIO (copy volume Docker) ===" -ForegroundColor Cyan
# Copy langsung dari volume Docker MinIO ke folder backup lewat container sementara.
docker run --rm `
    -v talatee-database_minio_data:/source:ro `
    -v "${PWD}\${backupDir}:/backup" `
    alpine sh -c "cp -r /source /backup/minio_data"

if ($LASTEXITCODE -ne 0) {
    Write-Host "GAGAL backup MinIO." -ForegroundColor Red
    exit 1
}
Write-Host "  OK -> $backupDir\minio_data\" -ForegroundColor Green

Write-Host ""
Write-Host "=== BACKUP SELESAI ===" -ForegroundColor Green
Write-Host "Folder: $backupDir"
Write-Host ""
Write-Host "LANGKAH SELANJUTNYA (WAJIB, backup ini belum aman kalau cuma di laptop ini):" -ForegroundColor Yellow
Write-Host "  1. Copy folder '$backupDir' ke Google Drive / hardisk eksternal / cloud storage"
Write-Host "  2. JANGAN taruh folder ini di dalam repo git (sudah bukan urusan git)"
Write-Host "  3. Catat juga isi .env dan .env.local secara TERPISAH di tempat aman"
Write-Host "     (password manager, catatan terenkripsi) -- JANGAN digabung folder backup ini"
