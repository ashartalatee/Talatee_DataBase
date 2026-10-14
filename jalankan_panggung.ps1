# Menyalakan server Panggung dengan aman: database LOKAL talatee_panggung + MinIO LOKAL (bukan cloud).
# Pemakaian dari root repo:   .\jalankan_panggung.ps1
# Kalau skrip diblokir:        Unblock-File .\jalankan_panggung.ps1
#                              (atau)  powershell -ExecutionPolicy Bypass -File .\jalankan_panggung.ps1
# Skrip memakai Python milik venv sendiri (venv tidak perlu diaktifkan dulu).
# Kredensial MinIO lokal dibaca dari container-nya saat dijalankan: tidak ditulis di skrip dan tidak ditampilkan.
# Skrip BERHENTI (server tidak menyala) kalau konfigurasi yang terbaca aplikasi bukan lokal.

$py = 'python'
if (Test-Path '.\venv\Scripts\python.exe') { $py = (Resolve-Path '.\venv\Scripts\python.exe').Path }

# 1) Kredensial MinIO lokal, dibaca dari container.
$minioEnv = docker inspect talatee-database-minio-1 --format '{{range .Config.Env}}{{println .}}{{end}}' 2>$null
$user = $null
$pass = $null
foreach ($line in $minioEnv) {
    if ($line -like 'MINIO_ROOT_USER=*')     { $user = $line.Substring('MINIO_ROOT_USER='.Length) }
    if ($line -like 'MINIO_ROOT_PASSWORD=*') { $pass = $line.Substring('MINIO_ROOT_PASSWORD='.Length) }
    if (-not $user -and $line -like 'MINIO_ACCESS_KEY=*') { $user = $line.Substring('MINIO_ACCESS_KEY='.Length) }
    if (-not $pass -and $line -like 'MINIO_SECRET_KEY=*') { $pass = $line.Substring('MINIO_SECRET_KEY='.Length) }
}
if (-not $user -or -not $pass) {
    Write-Host 'BERHENTI: kredensial MinIO lokal tidak ditemukan di container talatee-database-minio-1 (container mati, atau diatur lewat cara lain).' -ForegroundColor Red
    exit 1
}

# 2) Konfigurasi Panggung (menimpa .env hanya untuk proses ini).
$env:DATABASE_URL = 'postgresql://talatee:talatee@localhost:5434/talatee_panggung'
$env:MINIO_ENDPOINT = 'localhost:9000'
$env:MINIO_ACCESS_KEY = $user
$env:MINIO_SECRET_KEY = $pass
$env:MINIO_SECURE = 'false'
$env:MINIO_BUCKET = 'talatee-panggung'

# 3) Pengaman: periksa apa yang benar-benar terbaca aplikasi.
$guardPy = "from app.config import settings; from sqlalchemy.engine.url import make_url; u = make_url(settings.database_url); print(u.host + '|' + str(u.database) + '|' + settings.minio_endpoint + '|' + settings.minio_bucket)"
$cek = & $py -c $guardPy
$p = "$cek".Trim() -split '\|'
if ($p.Count -ne 4 -or $p[0] -ne 'localhost' -or $p[1] -ne 'talatee_panggung' -or $p[2] -ne 'localhost:9000' -or $p[3] -ne 'talatee-panggung') {
    Write-Host "BERHENTI: konfigurasi tidak aman atau tidak terbaca: $cek" -ForegroundColor Red
    exit 1
}

# 4) Pastikan bucket Panggung ada di MinIO lokal.
$bucketPy = "import os; from minio import Minio; c = Minio(os.environ['MINIO_ENDPOINT'], os.environ['MINIO_ACCESS_KEY'], os.environ['MINIO_SECRET_KEY'], secure=False); b = os.environ['MINIO_BUCKET']; c.bucket_exists(b) or c.make_bucket(b)"
$out = & $py -c $bucketPy 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host 'BERHENTI: tidak bisa memakai MinIO lokal (localhost:9000). Pesan terakhir:' -ForegroundColor Red
    Write-Host (("$out" -split "`n" | Select-Object -Last 1))
    exit 1
}

Write-Host "Panggung: database $($p[1]), MinIO $($p[2]) / bucket $($p[3])" -ForegroundColor Green
& $py -m uvicorn app.main:app --reload
