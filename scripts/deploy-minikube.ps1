<#
deploy-minikube.ps1 — build the app image, load it into minikube, and deploy.

Steps:
  1. Start the minikube cluster if it isn't running.
  2. Build pipeline-lab:local with the repo Dockerfile.
  3. Load the image into minikube's image store (docker driver can't see the
     host daemon directly).
  4. Apply the k8s/ manifests (app + Postgres + PVC).
  5. Wait for both rollouts and print the access command.

Run from the repo root:
    pwsh -File .\scripts\deploy-minikube.ps1

Requires: Docker Desktop (running), minikube, kubectl, and the minikube
context selected (`kubectl config use-context minikube`).
#>
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $repo

function Have($cmd) { return [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }
foreach ($c in @("docker", "minikube", "kubectl")) {
    if (-not (Have $c)) { throw "$c is required but was not found on PATH." }
}

Write-Host "==> Ensuring minikube is running" -ForegroundColor Cyan
$status = (minikube status --format "{{.Host}}" 2>$null)
if ($status -ne "Running") {
    minikube start --driver=docker --cpus=2 --memory=2200mb
}

Write-Host "==> Building pipeline-lab:local" -ForegroundColor Cyan
docker build -t pipeline-lab:local .

Write-Host "==> Loading image into minikube" -ForegroundColor Cyan
minikube image load pipeline-lab:local

# Postgres is normally pulled by the cluster. Load it from the local daemon when
# present so environments with a restricted registry still work offline.
if ((docker images -q postgres:16-alpine)) {
    Write-Host "==> Loading postgres:16-alpine into minikube" -ForegroundColor Cyan
    minikube image load postgres:16-alpine
}

Write-Host "==> Applying k8s/ manifests" -ForegroundColor Cyan
kubectl apply -k k8s

Write-Host "==> Waiting for rollouts" -ForegroundColor Cyan
kubectl -n pipeline-lab rollout status deployment/postgres --timeout=180s
kubectl -n pipeline-lab rollout status deployment/pipeline-lab --timeout=180s

Write-Host ""
Write-Host "Deployed. Access the app with:" -ForegroundColor Green
Write-Host "    kubectl -n pipeline-lab port-forward svc/pipeline-lab 8080:80"
Write-Host "    curl http://127.0.0.1:8080/health"
Write-Host "or, on the docker driver, expose the NodePort directly:"
Write-Host "    minikube service pipeline-lab -n pipeline-lab"
