<#
smoke-test.ps1 — exercise a running pipeline-lab instance end to end.

By default this targets the live Render deployment. Pass -Local to build a
throwaway SQLite-backed server on 127.0.0.1:8000 and test that instead. The
script works against an empty database: it creates its own todo, updates it,
reads it back, then deletes it.

  # Live deployment (default)
  pwsh -File .\scripts\smoke-test.ps1

  # A different instance
  pwsh -File .\scripts\smoke-test.ps1 -BaseUrl "https://example.onrender.com"

  # Local, launches uvicorn itself
  pwsh -File .\scripts\smoke-test.ps1 -Local

Exit code 0 = all checks passed, 1 = something failed.
#>
param(
    [string]$BaseUrl = "https://pipeline-lab.onrender.com",
    [switch]$Local,
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$py = Join-Path $repo ".venv\Scripts\python.exe"
$fails = 0
$proc = $null

function Check($name, $cond) {
    if ($cond) { Write-Host "PASS  $name" -ForegroundColor Green }
    else { Write-Host "FAIL  $name" -ForegroundColor Red; $script:fails++ }
}

function Wait-Health($base) {
    for ($i = 0; $i -lt 40; $i++) {
        try { Invoke-RestMethod "$base/health" -TimeoutSec 2 | Out-Null; return $true }
        catch { Start-Sleep -Milliseconds 500 }
    }
    return $false
}

try {
    if ($Local) {
        if (-not (Test-Path $py)) { $py = "python" }
        $BaseUrl = "http://127.0.0.1:$Port"
        $log = Join-Path $repo ".uvicorn.smoke.log"
        Write-Host "Starting local server on $BaseUrl ..." -ForegroundColor Cyan
        $proc = Start-Process -FilePath $py `
            -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$Port") `
            -WorkingDirectory $repo -PassThru -NoNewWindow `
            -RedirectStandardError $log -RedirectStandardOutput "$log.out"
    }

    $BaseUrl = $BaseUrl.TrimEnd("/")
    Write-Host "Smoke testing $BaseUrl" -ForegroundColor Cyan

    if (-not (Wait-Health $BaseUrl)) {
        Write-Host "FAIL  server never became healthy at $BaseUrl" -ForegroundColor Red
        if ($Local) { Get-Content $log -ErrorAction SilentlyContinue }
        exit 1
    }

    $health = Invoke-RestMethod "$BaseUrl/health"
    Check "GET /health -> status ok" ($health.status -eq "ok")

    $todos = Invoke-RestMethod "$BaseUrl/todos"
    Check "GET /todos -> shape (todos + count)" ($null -ne $todos.todos -and $todos.count -eq $todos.todos.Count)

    try { Invoke-RestMethod "$BaseUrl/todos/999999" | Out-Null; Check "GET /todos/999999 -> 404" $false }
    catch { Check "GET /todos/999999 -> 404" ($_.Exception.Response.StatusCode.value__ -eq 404) }

    $created = Invoke-RestMethod "$BaseUrl/todos" -Method Post -ContentType "application/json" `
        -Body (@{ title = "smoke todo"; done = $false } | ConvertTo-Json)
    Check "POST /todos -> 201 with id" ($null -ne $created.id -and $created.title -eq "smoke todo")

    $fetched = Invoke-RestMethod "$BaseUrl/todos/$($created.id)"
    Check "GET /todos/{id} -> created todo" ($fetched.id -eq $created.id -and $fetched.title -eq "smoke todo")

    $updated = Invoke-RestMethod "$BaseUrl/todos/$($created.id)" -Method Put -ContentType "application/json" `
        -Body (@{ title = "smoke updated"; done = $true } | ConvertTo-Json)
    Check "PUT /todos/{id} -> updated fields" ($updated.title -eq "smoke updated" -and $updated.done -eq $true)

    $refetched = Invoke-RestMethod "$BaseUrl/todos/$($created.id)"
    Check "PUT change persists across GET" ($refetched.title -eq "smoke updated" -and $refetched.done -eq $true)

    try { Invoke-RestMethod "$BaseUrl/todos/999999" -Method Put -ContentType "application/json" -Body '{"title":"ghost"}' | Out-Null; Check "PUT /todos/999999 -> 404" $false }
    catch { Check "PUT /todos/999999 -> 404" ($_.Exception.Response.StatusCode.value__ -eq 404) }

    $deleted = Invoke-WebRequest "$BaseUrl/todos/$($created.id)" -Method Delete -UseBasicParsing
    Check "DELETE /todos/{id} -> 204" ($deleted.StatusCode -eq 204)

    try { Invoke-RestMethod "$BaseUrl/todos/$($created.id)" | Out-Null; Check "GET deleted todo -> 404" $false }
    catch { Check "GET deleted todo -> 404" ($_.Exception.Response.StatusCode.value__ -eq 404) }

    try {
        $metrics = Invoke-WebRequest "$BaseUrl/metrics" -UseBasicParsing
        Check "GET /metrics -> 200 with http_requests_total" ($metrics.StatusCode -eq 200 -and $metrics.Content -match "http_requests_total")
    }
    catch { Check "GET /metrics -> 200 with http_requests_total" $false }
}
finally {
    if ($proc -and -not $proc.HasExited) { Stop-Process -Id $proc.Id -Force }
}

if ($fails -gt 0) { Write-Host "`n$fails check(s) failed" -ForegroundColor Red; exit 1 }
Write-Host "`nAll checks passed" -ForegroundColor Green
exit 0
