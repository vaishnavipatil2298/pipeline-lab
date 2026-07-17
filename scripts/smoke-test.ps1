<#
smoke.ps1 — launch pipeline-lab and drive every endpoint, then tear down.

This is the agent-facing driver for the run-pipeline-lab skill. It:
  1. Starts uvicorn (app.main:app) as a child process on 127.0.0.1:8000
  2. Polls /health until the server is ready (or times out)
  3. Exercises GET /health, GET /todos, GET /todos/{id} (hit + 404),
     POST /todos, and PUT /todos/{id} (update + 404)
  4. Asserts each response and prints a PASS/FAIL line
  5. Always kills the server it started

Run from the repo root:
    .\.venv\Scripts\python.exe -m pytest -q   # (tests, optional)
    pwsh -File .claude\skills\run-pipeline-lab\smoke.ps1

Exit code 0 = all checks passed, 1 = something failed (or server never came up).
#>
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
$py   = Join-Path $repo ".venv\Scripts\python.exe"
$base = "http://127.0.0.1:8000"
$fails = 0

function Check($name, $cond) {
    if ($cond) { Write-Host "PASS  $name" -ForegroundColor Green }
    else       { Write-Host "FAIL  $name" -ForegroundColor Red; $script:fails++ }
}

# 1. Launch uvicorn as a child process, logging to a file.
$log = Join-Path $repo ".uvicorn.smoke.log"
$proc = Start-Process -FilePath $py `
    -ArgumentList @("-m","uvicorn","app.main:app","--host","127.0.0.1","--port","8000") `
    -WorkingDirectory $repo -PassThru -RedirectStandardError $log -RedirectStandardOutput "$log.out" -NoNewWindow

try {
    # 2. Wait for /health to answer.
    $ready = $false
    for ($i = 0; $i -lt 40; $i++) {
        try { Invoke-RestMethod "$base/health" -TimeoutSec 2 | Out-Null; $ready = $true; break }
        catch { Start-Sleep -Milliseconds 500 }
    }
    if (-not $ready) {
        Write-Host "FAIL  server never came up" -ForegroundColor Red
        Get-Content $log -ErrorAction SilentlyContinue
        exit 1
    }

    # 3. Drive the endpoints.
    $health = Invoke-RestMethod "$base/health"
    Check "GET /health -> status ok" ($health.status -eq "ok")

    $todos = Invoke-RestMethod "$base/todos"
    Check "GET /todos -> count matches list" ($todos.count -eq $todos.todos.Count -and $todos.count -ge 1)

    $one = Invoke-RestMethod "$base/todos/1"
    Check "GET /todos/1 -> id 1" ($one.id -eq 1)

    try { Invoke-RestMethod "$base/todos/9999" | Out-Null; Check "GET /todos/9999 -> 404" $false }
    catch { Check "GET /todos/9999 -> 404" ($_.Exception.Response.StatusCode.value__ -eq 404) }

    $created = Invoke-RestMethod "$base/todos" -Method Post -ContentType "application/json" `
        -Body (@{ title = "smoke todo"; done = $false } | ConvertTo-Json)
    Check "POST /todos -> 201 with id" ($null -ne $created.id -and $created.title -eq "smoke todo")

    $updated = Invoke-RestMethod "$base/todos/$($created.id)" -Method Put -ContentType "application/json" `
        -Body (@{ title = "smoke updated"; done = $true } | ConvertTo-Json)
    Check "PUT /todos/{id} -> updated fields" ($updated.title -eq "smoke updated" -and $updated.done -eq $true)

    $refetched = Invoke-RestMethod "$base/todos/$($created.id)"
    Check "PUT change persists across GET" ($refetched.title -eq "smoke updated" -and $refetched.done -eq $true)

    try { Invoke-RestMethod "$base/todos/9999" -Method Put -ContentType "application/json" -Body '{"title":"ghost"}' | Out-Null; Check "PUT /todos/9999 -> 404" $false }
    catch { Check "PUT /todos/9999 -> 404" ($_.Exception.Response.StatusCode.value__ -eq 404) }
}
finally {
    # 4. Always kill the server we started.
    if ($proc -and -not $proc.HasExited) { Stop-Process -Id $proc.Id -Force }
}

if ($fails -gt 0) { Write-Host "`n$fails check(s) failed" -ForegroundColor Red; exit 1 }
Write-Host "`nAll checks passed" -ForegroundColor Green
exit 0
