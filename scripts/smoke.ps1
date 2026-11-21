# Поднимает port-forward к gateway, запускает smoke-тест и закрывает port-forward.
# Нужны Python и pytest (python -m pip install -r cars-service/requirements.txt).
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path reports)) { New-Item -ItemType Directory reports | Out-Null }

$pf = Start-Process kubectl -ArgumentList "port-forward -n car-accounting svc/gateway 8082:80" `
      -PassThru -WindowStyle Hidden
try {
    $ok = $false
    foreach ($i in 1..30) {
        try { Invoke-WebRequest -UseBasicParsing http://localhost:8082/healthz | Out-Null; $ok = $true; break }
        catch { Start-Sleep -Seconds 1 }
    }
    if (-not $ok) { throw "gateway is not reachable on localhost:8082" }

    # сколько реплик каждого сервиса ожидаем увидеть в балансировке (берём меньшее)
    $counts = foreach ($d in "cars-service", "owners-service") {
        $n = kubectl get deployment $d -n car-accounting -o jsonpath="{.status.readyReplicas}"
        if ($n) { [int]$n } else { 1 }
    }
    $replicas = ($counts | Measure-Object -Minimum).Minimum

    $env:BASE_URL = "http://localhost:8082"
    $env:EXPECT_REPLICAS = $replicas
    python -m pytest smoke_tests --junitxml=reports/results.xml
    $code = $LASTEXITCODE
}
finally {
    Stop-Process -Id $pf.Id -Force -ErrorAction SilentlyContinue
}
exit $code
