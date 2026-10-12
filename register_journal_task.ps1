# Jalankan SEKALI dari folder talatee-database (PowerShell biasa, tanpa admin).
$dir = (Get-Location).Path
$bat = Join-Path $dir "journal_dispatch.bat"
if (-not (Test-Path $bat)) { throw "journal_dispatch.bat tidak ada di $dir" }

$action   = New-ScheduledTaskAction -Execute $bat -WorkingDirectory $dir
$every10  = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
              -RepetitionInterval (New-TimeSpan -Minutes 10) -RepetitionDuration (New-TimeSpan -Days 3650)
$atLogon  = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
              -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew `
              -ExecutionTimeLimit (New-TimeSpan -Minutes 20)

Register-ScheduledTask -TaskName "Talatee Journal Dispatch" -Action $action `
  -Trigger @($every10, $atLogon) -Settings $settings -Description "Kirim hook jurnal suara ke Telegram" | Out-Null
Get-ScheduledTask -TaskName "Talatee Journal Dispatch" | Select-Object TaskName, State
