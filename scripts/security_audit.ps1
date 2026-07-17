# Stride — dependency vulnerability audit. Run from the repo root; wire into CI later.
#   powershell -File scripts/security_audit.ps1

Write-Host "== Python dependencies (pip-audit via uvx) ==" -ForegroundColor Cyan
uvx pip-audit --skip-editable --path (Resolve-Path ".venv\Lib\site-packages" -ErrorAction SilentlyContinue) 2>$null
if ($LASTEXITCODE -ne 0) {
  # fallback: audit the resolved requirements of the workspace
  uv export --no-emit-workspace --format requirements.txt | uvx pip-audit -r -
}

Write-Host "`n== Web dependencies (npm audit) ==" -ForegroundColor Cyan
npm audit --prefix apps/web --audit-level=moderate

Write-Host "`nReview any findings above; pin or upgrade affected packages." -ForegroundColor Cyan
