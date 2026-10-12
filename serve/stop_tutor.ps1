# Stop the OS Tutor stack started by serve\start_tutor.ps1 (and free the GPU).
$Serve = $PSScriptRoot
Get-Process llama-server -ErrorAction SilentlyContinue | Stop-Process -Force
Get-CimInstance Win32_Process |
    Where-Object { $_.CommandLine -and $_.CommandLine -like "*$Serve*" -and
                   ($_.CommandLine -like "*gateway.py*" -or $_.CommandLine -like "*open-webui*") } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Write-Host "OS Tutor stopped."
