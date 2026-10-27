<#
Chuẩn bị môi trường chạy app trên Windows: thư mục .venv có đủ thư viện trong requirements.txt.

Máy chưa có Python 3.10+ (64-bit) thì tự tải Python bản portable chính thức (gói "python" trên NuGet của Microsoft)
vào thư mục .python của app: không cần quyền admin, không cài vào hệ thống, không đổi PATH. Xoá thư mục app là sạch.
Lần sau chỉ kiểm tra nhanh; requirements.txt đổi (bản app mới) thì tự cài thêm thư viện.

Gọi từ run.bat / agent.bat:
    powershell -NoProfile -ExecutionPolicy Bypass -File tools\setup.ps1 [-ForcePortable]
-ForcePortable: bỏ qua Python có sẵn trên máy (dùng để test).
#>
param([switch]$ForcePortable)

$ErrorActionPreference = 'Continue'   # lệnh ngoài (python, pip) kiểm tra bằng $LASTEXITCODE
$ProgressPreference = 'SilentlyContinue'   # thanh tiến trình làm Invoke-WebRequest chậm hẳn trên PowerShell 5.1

$App = Split-Path -Parent $PSScriptRoot
$PyVersion = '3.13.17'
$PyUrl = "https://api.nuget.org/v3-flatcontainer/python/$PyVersion/python.$PyVersion.nupkg"
$PySha256 = 'DCE409744B088F94C6E37BA41F8100C384C27E029E843237364C602D30D475E5'   # khớp SHA512 NuGet công bố cho gói này
$VenvDir = Join-Path $App '.venv'
$VenvPy = Join-Path $VenvDir 'Scripts\python.exe'
$PortableDir = Join-Path $App '.python'
$PortablePy = Join-Path $PortableDir 'tools\python.exe'
$Requirements = Join-Path $App 'requirements.txt'
$Stamp = Join-Path $VenvDir 'l2m-requirements.sha256'

function Say([string]$text) { Write-Host "[L2M Ops] $text" }

function Test-Python([string]$exe) {
    # Python 3.10+ 64-bit chạy được? (bỏ qua "python.exe" giả của Microsoft Store: nó không in gì)
    if (-not $exe -or -not (Test-Path $exe)) { return $false }
    $out = & $exe -c "import sys, struct; print(sys.version_info >= (3, 10) and struct.calcsize('P') == 8)" 2>$null
    return ($LASTEXITCODE -eq 0 -and "$out".Trim() -eq 'True')
}

function Find-Python {
    if (Test-Python $PortablePy) { return $PortablePy }
    if ($ForcePortable) { return $null }
    $candidates = @()
    $launcher = Get-Command py -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($launcher) {
        $exe = & $launcher.Source -3 -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $exe) { $candidates += "$exe".Trim() }
    }
    foreach ($cmd in Get-Command python, python3 -CommandType Application -All -ErrorAction SilentlyContinue) {
        if ($cmd.Source -notmatch '\\WindowsApps\\') { $candidates += $cmd.Source }
    }
    foreach ($exe in $candidates) {
        if (Test-Python $exe) { return $exe }
    }
    return $null
}

function Install-PortablePython {
    Say "Chua co Python 3.10+ tren may: tai Python $PyVersion ban portable (~15 MB, chi nam trong thu muc app)..."
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    if ([Net.WebRequest]::DefaultWebProxy) {   # proxy công ty cần đăng nhập Windows
        [Net.WebRequest]::DefaultWebProxy.Credentials = [Net.CredentialCache]::DefaultNetworkCredentials
    }
    $zip = Join-Path $env:TEMP "l2m-python-$PyVersion.zip"
    Invoke-WebRequest -Uri $PyUrl -OutFile $zip -UseBasicParsing -ErrorAction Stop
    $hash = (Get-FileHash $zip -Algorithm SHA256).Hash
    if ($hash -ne $PySha256) {
        Remove-Item $zip -Force -ErrorAction SilentlyContinue
        throw "File Python tai ve khong dung (SHA256 $hash). Thu lai sau hoac bao admin."
    }
    if (Test-Path $PortableDir) { Remove-Item $PortableDir -Recurse -Force -ErrorAction Stop }
    New-Item -ItemType Directory -Path $PortableDir | Out-Null
    Say "Giai nen Python..."
    $tar = Get-Command tar.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($tar) { & $tar.Source -xf $zip -C $PortableDir }   # nhanh hơn Expand-Archive nhiều
    if (-not $tar -or $LASTEXITCODE -ne 0) { Expand-Archive -Path $zip -DestinationPath $PortableDir -Force -ErrorAction Stop }
    Remove-Item $zip -Force -ErrorAction SilentlyContinue
    if (-not (Test-Python $PortablePy)) { throw "Khong chay duoc Python vua tai ($PortablePy)." }
    return $PortablePy
}

function Test-Edge {
    $paths = @("${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
               "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
               "$env:LOCALAPPDATA\Microsoft\Edge\Application\msedge.exe")
    return [bool]($paths | Where-Object { $_ -and (Test-Path $_) })
}

try {
    $reqHash = (Get-FileHash $Requirements -Algorithm SHA256 -ErrorAction Stop).Hash
    if ((Test-Path $VenvPy) -and (Test-Path $Stamp) -and ((Get-Content $Stamp -Raw).Trim() -eq $reqHash)) {
        & $VenvPy -c "pass" 2>$null
        if ($LASTEXITCODE -eq 0) { exit 0 }   # đã sẵn sàng
    }
    if (Test-Path $VenvPy) {
        & $VenvPy -c "pass" 2>$null
        if ($LASTEXITCODE -ne 0) {   # vd Python tạo ra .venv đã bị gỡ khỏi máy
            Say "Moi truong .venv cu khong chay duoc nua: tao lai."
            Remove-Item $VenvDir -Recurse -Force -ErrorAction Stop
        }
    }
    if (-not (Test-Path $VenvPy)) {
        $python = Find-Python
        if (-not $python) { $python = Install-PortablePython }
        Say "Tao moi truong Python cho app (.venv) tu $python ..."
        & $python -m venv $VenvDir
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path $VenvPy)) { throw "Khong tao duoc .venv." }
    }
    Say "Cai thu vien cho app (lan dau mat vai phut)..."
    & $VenvPy -m pip install --disable-pip-version-check --upgrade pip
    & $VenvPy -m pip install --disable-pip-version-check -r $Requirements
    if ($LASTEXITCODE -ne 0) { throw "Cai thu vien that bai. Kiem tra mang Internet (can vao duoc pypi.org) roi chay lai." }
    Set-Content -Path $Stamp -Value $reqHash -Encoding ascii
    if (-not (Test-Edge)) { Say "Canh bao: khong thay Microsoft Edge. Thao tac NC tool / MyTool can Edge." }
    Say "Cai dat xong."
    exit 0
} catch {
    Write-Host "[L2M Ops] Cai dat that bai: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
