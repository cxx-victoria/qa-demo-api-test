# ============================================================
#  One-click runner for the Hurl interface test suite
#  Location: D:\qa-projects\01-hurl-lab\run.ps1
#
#  Prerequisite: the service under test must be running first,
#  in ANOTHER PowerShell window:
#      cd D:\qa-projects\00-demo-api
#      .\.venv\Scripts\Activate.ps1
#      uvicorn app:app --port 8000
#
#  WHY THIS FILE IS ASCII-ONLY (important, do not "fix" it):
#  Windows PowerShell 5.1 reads a .ps1 file as ANSI/GBK when the file
#  has no BOM. Non-ASCII text then gets garbled, and a lead byte can
#  swallow the closing quote of a string, producing a confusing parse
#  error such as "MissingEndCurlyBrace".
#  Keeping the script ASCII-only makes it work on every Windows
#  PowerShell version regardless of code page. Chinese explanations
#  live in the .md docs instead.
# ============================================================

$ErrorActionPreference = 'Stop'
# PowerShell 7.3+ can turn a native command's non-zero exit code into a
# terminating error. hurl exits non-zero whenever a case fails (which is
# expected here), so make sure that behaviour is off.
$PSNativeCommandUseErrorActionPreference = $false

$Base      = 'http://127.0.0.1:8000'
$ReportDir = 'reports'

# ---------- 0) health check: is the service under test up? ----------
Write-Host "`n===== 0. Checking the service under test ($Base) =====" -ForegroundColor Cyan
$up = $false
try {
    $probe = Invoke-WebRequest -Uri "$Base/tasks" -TimeoutSec 5 -UseBasicParsing
    if ($probe.StatusCode -eq 200) { $up = $true }
} catch {
    $up = $false
}

if (-not $up) {
    Write-Host "FAILED: cannot reach $Base/tasks" -ForegroundColor Red
    Write-Host ""
    Write-Host "The service under test is NOT running." -ForegroundColor Yellow
    Write-Host "Start it first in ANOTHER window and leave that window open:" -ForegroundColor Yellow
    Write-Host "    cd D:\qa-projects\00-demo-api"
    Write-Host "    .\.venv\Scripts\Activate.ps1"
    Write-Host "    uvicorn app:app --port 8000"
    Write-Host ""
    Write-Host "Then run this script again in THIS window." -ForegroundColor Yellow
    exit 1
}
Write-Host "OK: service is up." -ForegroundColor Green

# ---------- 1) locate hurl ----------
$Hurl = $env:HURL_EXE
if (-not $Hurl -or -not (Get-Command $Hurl -ErrorAction SilentlyContinue)) {
    if (Get-Command hurl -ErrorAction SilentlyContinue) {
        $Hurl = 'hurl'
    } else {
        Write-Host "hurl not found. Install it with:  winget install hurl" -ForegroundColor Yellow
        Write-Host 'Or point to the exe:  $env:HURL_EXE = "C:\Program Files\hurl\hurl.exe"' -ForegroundColor Yellow
        exit 1
    }
}
Write-Host ("hurl  : {0}" -f (Get-Command $Hurl).Source) -ForegroundColor DarkGray

# ---------- 2) helper: run a group of case files ----------
function Invoke-Cases {
    param([string]$Title, [string]$Pattern)
    Write-Host "`n===== $Title =====" -ForegroundColor Cyan
    # The @(...) matters: when a pattern matches exactly one file, PowerShell
    # returns a bare string, and "@string" would expand it character by character.
    $files = @(Get-ChildItem $Pattern | ForEach-Object { $_.FullName })
    if ($files.Count -eq 0) {
        Write-Host ("No case file matched: {0}" -f $Pattern) -ForegroundColor Yellow
        return
    }
    & $Hurl --test @files
}

Invoke-Cases "1. smoke test (expect all PASS)"     "cases\00_smoke.hurl"
Invoke-Cases "2. business flow (expect all PASS)"  "cases\10_flow_login_create_query.hurl"
Invoke-Cases "3. error case (expect PASS)"         "cases\20_boundary_login_fail.hurl"
Invoke-Cases "4. defect repro (4 expected FAILs)"  "cases\3*_defect_*.hurl"

# ---------- 3) full suite + reports + timing ----------
Write-Host "`n===== 5. Full suite + reports =====" -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path $ReportDir | Out-Null

# Reports must be idempotent: hurl APPENDS a new <testsuite> to an existing
# junit.xml instead of overwriting it, so delete the old one first.
Remove-Item "$ReportDir\junit.xml" -Force -ErrorAction SilentlyContinue

$all = @(Get-ChildItem 'cases\*.hurl' | ForEach-Object { $_.FullName })
Write-Host ("case files: {0}" -f $all.Count) -ForegroundColor DarkGray

$sw = [System.Diagnostics.Stopwatch]::StartNew()
& $Hurl --test --report-junit "$ReportDir\junit.xml" --report-html "$ReportDir\html" @all
$code = $LASTEXITCODE
$sw.Stop()

Write-Host ""
Write-Host "====================== SUMMARY ======================" -ForegroundColor Green
Write-Host ("case files run  : {0}" -f $all.Count)
Write-Host ("total elapsed   : {0:N2} s" -f $sw.Elapsed.TotalSeconds) -ForegroundColor Yellow
Write-Host ("hurl exit code  : {0}   (0 = all PASS; non-zero = some FAIL, expected here)" -f $code)
Write-Host ("reports         : {0}\junit.xml  and  {0}\html\index.html" -f $ReportDir)
Write-Host ""
Write-Host ">>> This elapsed time is the number for your resume. <<<" -ForegroundColor Yellow
