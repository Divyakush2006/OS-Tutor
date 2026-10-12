# OS Tutor - start the full local stack and open the chat UI.
#
#   powershell -ExecutionPolicy Bypass -File serve\start_tutor.ps1
#
#   llama-server  :8081  base Qwen3-4B (Q8_0 GGUF) + ostutor v3.0 LoRA, CUDA
#   gateway       :8090  trained system prompts, greedy decoding, 16k ceiling, loop guard
#   Open WebUI    :3000  the chat frontend (opens in your browser)
#
# Stop everything with serve\stop_tutor.ps1. Logs are in serve\logs.
$ErrorActionPreference = "Stop"
$Root  = Split-Path -Parent $PSScriptRoot
$Serve = Join-Path $Root "serve"
$Logs  = Join-Path $Serve "logs"; New-Item -ItemType Directory -Force $Logs | Out-Null
$Py    = Join-Path $Serve ".venv-webui\Scripts\python.exe"
$Server = Join-Path $Serve "llama.cpp\bin\llama-server.exe"
$Base  = Join-Path $Root "models\gguf\qwen3-4b-instruct-2507-Q8_0.gguf"
$Lora  = Join-Path $Root "models\gguf\ostutor-v3-lora-f16.gguf"

foreach ($f in @($Py, $Server, $Base, $Lora)) {
    if (-not (Test-Path $f)) { throw "missing: $f  (see serve\README.md, setup)" }
}

# The model needs about 6.5 GB of the 8 GB GPU. Refuse to start on a busy GPU
# (for example while tools/run_eval.py is running) instead of failing half-way.
$used = [int](& nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits)
if ($used -gt 1500) {
    throw "GPU already has $used MiB in use - stop the other GPU job first (an evaluation?)."
}

function Wait-Http($url, $name, $seconds) {
    for ($i = 0; $i -lt $seconds; $i++) {
        try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 $url | Out-Null; Write-Host "  $name ready"; return }
        catch { Start-Sleep 1 }
    }
    throw "$name did not come up in $seconds s - see $Logs"
}

Write-Host "[1/3] model server (llama.cpp, CUDA)"
# -c 20480: 16,384-token answers plus the question. KV cache in q8_0 (needs flash
# attention) halves its memory, so the whole stack fits the 8 GB GPU.
Start-Process -WindowStyle Hidden -FilePath $Server -ArgumentList @(
    "-m", "`"$Base`"", "--lora", "`"$Lora`"",
    "-ngl", "99", "-c", "20480", "-np", "1",
    "-fa", "on", "-ctk", "q8_0", "-ctv", "q8_0",
    "--jinja", "--host", "127.0.0.1", "--port", "8081",
    "--alias", "ostutor") `
    -RedirectStandardOutput "$Logs\llama-server.out.log" -RedirectStandardError "$Logs\llama-server.log"
Wait-Http "http://127.0.0.1:8081/health" "model server" 180

Write-Host "[2/3] tutor gateway"
Start-Process -WindowStyle Hidden -FilePath $Py -ArgumentList "`"$Serve\gateway.py`"" `
    -RedirectStandardOutput "$Logs\gateway.out.log" -RedirectStandardError "$Logs\gateway.log"
Wait-Http "http://127.0.0.1:8090/v1/models" "gateway" 60

Write-Host "[3/3] Open WebUI (first start takes a minute or two)"
$env:DATA_DIR = Join-Path $Serve "webui-data"
$env:WEBUI_NAME = "OS Tutor"
$env:WEBUI_AUTH = "False"                       # single-user, localhost only
$env:ENABLE_OLLAMA_API = "False"
$env:OPENAI_API_BASE_URL = "http://127.0.0.1:8090/v1"
$env:OPENAI_API_KEY = "local"
$env:DEFAULT_MODELS = "ostutor"          # auto mode: routes per question
# Background "task" generations (titles, tags, follow-ups, autocomplete) would run
# on the same GPU and delay answers - off.
$env:ENABLE_TITLE_GENERATION = "False"
$env:ENABLE_TAGS_GENERATION = "False"
$env:ENABLE_FOLLOW_UP_GENERATION = "False"
$env:ENABLE_AUTOCOMPLETE_GENERATION = "False"
$env:ENABLE_RETRIEVAL_QUERY_GENERATION = "False"
$env:ENABLE_SEARCH_QUERY_GENERATION = "False"
$env:ENABLE_WEB_SEARCH = "False"
$env:ANONYMIZED_TELEMETRY = "False"; $env:SCARF_NO_ANALYTICS = "true"; $env:DO_NOT_TRACK = "true"
$WebUI = Join-Path $Serve ".venv-webui\Scripts\open-webui.exe"
Start-Process -WindowStyle Hidden -FilePath $WebUI -ArgumentList @("serve", "--host", "127.0.0.1", "--port", "3000") `
    -RedirectStandardOutput "$Logs\webui.out.log" -RedirectStandardError "$Logs\webui.log"
Wait-Http "http://127.0.0.1:3000/health" "Open WebUI" 300

Start-Process "http://localhost:3000"
Write-Host "`nOS Tutor is running at http://localhost:3000"
Write-Host "Models: ostutor (auto) | ostutor-solve | ostutor-analyze | ostutor-explain | ostutor-tutor | ostutor-shell"
