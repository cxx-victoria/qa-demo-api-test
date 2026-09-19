# 一键执行：在本目录（hurl-lab）下运行   .\run.ps1
# 前提：被测服务已在 127.0.0.1:8000 运行

# ---------- 1) 找到 hurl ----------
$Hurl = $env:HURL_EXE
if (-not $Hurl -or -not (Get-Command $Hurl -ErrorAction SilentlyContinue)) {
    if (Get-Command hurl -ErrorAction SilentlyContinue) {
        $Hurl = "hurl"
    } else {
        Write-Host "找不到 hurl。请先执行：winget install hurl" -ForegroundColor Yellow
        Write-Host "或设置环境变量 HURL_EXE 指向 hurl.exe 的完整路径，例如：" -ForegroundColor Yellow
        Write-Host '  $env:HURL_EXE = "D:\tools\hurl\hurl.exe"' -ForegroundColor Yellow
        exit 1
    }
}

# ---------- 2) 小工具：按文件列表跑（PowerShell 不会给 hurl 展开通配符，所以要自己列） ----------
function Invoke-Cases {
    param([string]$Title, [string]$Pattern)
    Write-Host "`n===== $Title =====" -ForegroundColor Cyan
    # 注意 @(...)：只匹配到 1 个文件时 PowerShell 返回的是单个字符串，
    # 直接 @字符串 会被按"字符"逐个展开（C、:、\ ...），必须强制成数组。
    $files = @(Get-ChildItem $Pattern | ForEach-Object { $_.FullName })
    if (-not $files) { Write-Host "没找到匹配 $Pattern 的用例" -ForegroundColor Yellow; return }
    & $Hurl --test @files
}

Invoke-Cases "1. 冒烟测试（应该全部通过）"        "cases\00_smoke.hurl"
Invoke-Cases "2. 业务流测试（应该全部通过）"      "cases\10_flow_login_create_query.hurl"
Invoke-Cases "3. 异常用例：错误密码（应该通过）"  "cases\20_boundary_login_fail.hurl"
Invoke-Cases "4. 找缺陷：4 条预期失败，失败=发现 bug" "cases\3*_defect_*.hurl"

# ---------- 3) 出报告 ----------
Write-Host "`n===== 5. 生成测试报告 =====" -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path reports | Out-Null
$all = @(Get-ChildItem cases\*.hurl | ForEach-Object { $_.FullName })
& $Hurl --test --report-junit reports\junit.xml --report-html reports\html @all
Write-Host "报告已生成，用浏览器打开：reports\html\index.html" -ForegroundColor Green
