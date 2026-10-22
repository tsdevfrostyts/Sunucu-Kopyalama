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
& $python -m PyInstaller --noconfirm --clean --onefile --windowed --noupx --add-data 'assets;assets' --add-data 'THIRD_PARTY_NOTICES.md;.' --add-data 'LICENSE;.' --icon assets/app.ico --version-file version_info.txt --name Sunucu-Kopyalama_v1.0.1 app.py
if ($LASTEXITCODE -ne 0) { throw 'EXE derlenemedi.' }
$exe = Join-Path $PSScriptRoot 'dist\Sunucu-Kopyalama_v1.0.1.exe'
$info = [System.Diagnostics.FileVersionInfo]::GetVersionInfo($exe)
if ($info.ProductName -ne 'Sunucu Kopyalama' -or $info.FileVersion -ne '1.0.1.0' -or $info.ProductVersion -ne '1.0.1.0' -or $info.CompanyName -ne 'DevFrosty' -or [string]::IsNullOrWhiteSpace($info.FileDescription) -or [string]::IsNullOrWhiteSpace($info.LegalCopyright) -or [string]::IsNullOrWhiteSpace($info.Language)) {
    throw 'EXE sürüm bilgileri eksik veya yanlış.'
}
$report = Join-Path $PSScriptRoot 'build\release-self-check.json'
$process = Start-Process -FilePath $exe -ArgumentList @('--self-check', '--report', ('"{0}"' -f $report)) -WindowStyle Hidden -Wait -PassThru
if ($process.ExitCode -ne 0) { throw 'Paketlenmiş uygulama kontrolü başarısız.' }
Write-Output "Hazır: $exe"
