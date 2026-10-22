$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python ortamı oluşturulamadı.' }
}
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
& $python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Bağımlılıklar kurulamadı.' }
& $python -m unittest -q test_copier test_ui
if ($LASTEXITCODE -ne 0) { throw 'Testler başarısız.' }
& $python -m PyInstaller --noconfirm --onefile --windowed --collect-all customtkinter --add-data 'assets;assets' --add-data 'THIRD_PARTY_NOTICES.md;.' --add-data 'LICENSE;.' --icon assets/app.ico --name Sunucu-Kopyalama_v1.0.0 app.py
if ($LASTEXITCODE -ne 0) { throw 'EXE derlenemedi.' }
$exe = Join-Path $PSScriptRoot 'dist\Sunucu-Kopyalama_v1.0.0.exe'
$report = Join-Path $PSScriptRoot 'build\release-self-check.json'
$process = Start-Process -FilePath $exe -ArgumentList @('--self-check', '--report', $report) -WindowStyle Hidden -Wait -PassThru
if ($process.ExitCode -ne 0) { throw 'Paketlenmiş uygulama kontrolü başarısız.' }
Get-FileHash -LiteralPath $exe -Algorithm SHA256
