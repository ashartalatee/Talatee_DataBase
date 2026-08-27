# scripts/restore.ps1
#
# Restore data Talatee (Postgres + MinIO) dari folder backup hasil backup.ps1.
# Dipakai saat setup di LAPTOP BARU, setelah docker compose up -d pertama kali
# jalan (supaya volume Docker-nya sudah ada, biar bisa ditulisi).
#
# Jalankan dari root project talatee-data-platform:
#     .\scripts\restore.ps1 -BackupFolder "C:\path\ke\talatee-backup-2026-08-26_1000"

param(
    [Parameter(Mandatory=$true)]
    [string]$BackupFolder
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $BackupFolder)) {
    Write-Host "Folder backup tidak ditemukan: $BackupFolder" -ForegroundColor Red
    exit 1
}

$dumpFile = Join-Path $BackupFolder "postgres_dump.sql"
$minioDataFolder = Join-Path $BackupFolder "minio_data"

if (-not (Test-Path $dumpFile)) {
    Write-Host "File postgres_dump.sql tidak ditemukan di $BackupFolder" -ForegroundColor Red
    exit 1
}

Write-Host "=== Pastikan container Postgres & MinIO jalan (docker compose up -d) ===" -ForegroundColor Cyan
docker compose up -d
Start-Sleep -Seconds 5

Write-Host "=== Restore Postgres ===" -ForegroundColor Cyan
Get-Content $dumpFile | docker exec -i talatee-database-postgres-1 psql -U talatee -d talatee_platform

if ($LASTEXITCODE -ne 0) {
    Write-Host "GAGAL restore Postgres." -ForegroundColor Red
    exit 1
}
Write-Host "  OK - data Postgres ter-restore." -ForegroundColor Green

Write-Host "=== Restore MinIO ===" -ForegroundColor Cyan
docker run --rm `
    -v talatee-database_minio_data:/dest `
    -v "${minioDataFolder}:/source:ro" `
    alpine sh -c "cp -r /source/. /dest/"

if ($LASTEXITCODE -ne 0) {
    Write-Host "GAGAL restore MinIO." -ForegroundColor Red
    exit 1
}
Write-Host "  OK - data MinIO ter-restore." -ForegroundColor Green

Write-Host ""
Write-Host "=== RESTORE SELESAI ===" -ForegroundColor Green
Write-Host "Restart backend (uvicorn app.main:app --reload) lalu cek dashboard untuk verifikasi."
