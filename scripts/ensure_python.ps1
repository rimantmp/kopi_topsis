param(
    [Parameter(Mandatory = $true)]
    [string]$OutputFile,
    [int]$MinimumMajor = 3,
    [int]$MinimumMinor = 12
)

$ErrorActionPreference = "Stop"

function Test-CompatiblePython {
    param([string]$Executable)
    if (-not $Executable -or -not (Test-Path -LiteralPath $Executable -PathType Leaf)) {
        return $false
    }
    try {
        $result = & $Executable -c "import sys; print('OK' if (sys.version_info.major, sys.version_info.minor) >= ($MinimumMajor, $MinimumMinor) and sys.version_info.major < 4 else 'NO')" 2>$null
        return ($LASTEXITCODE -eq 0 -and $result -eq "OK")
    } catch {
        return $false
    }
}

function Get-PythonCandidates {
    $paths = [System.Collections.Generic.List[string]]::new()
    $command = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($command) { $paths.Add($command.Source) }

    $launcher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($launcher) {
        try {
            $launcherPath = & $launcher.Source -3.12 -c "import sys; print(sys.executable)" 2>$null
            if ($LASTEXITCODE -eq 0 -and $launcherPath) { $paths.Add($launcherPath.Trim()) }
        } catch {}
    }

    $knownPaths = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"),
        (Join-Path $env:ProgramFiles "Python312\python.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Python312\python.exe")
    )
    foreach ($path in $knownPaths) {
        if ($path) { $paths.Add($path) }
    }
    return $paths | Select-Object -Unique
}

function Find-CompatiblePython {
    foreach ($candidate in Get-PythonCandidates) {
        if (Test-CompatiblePython $candidate) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }
    return $null
}

$python = Find-CompatiblePython
if (-not $python) {
    Write-Host "[INFO] Python $MinimumMajor.$MinimumMinor atau lebih baru belum tersedia."
    $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
    if (-not $winget) {
        throw "winget tidak ditemukan. Instal App Installer dari Microsoft Store atau pasang Python $MinimumMajor.$MinimumMinor secara manual."
    }

    Write-Host "[INFO] Menginstal Python 3.12 secara otomatis melalui winget ..."
    & $winget.Source install --id Python.Python.3.12 --exact --source winget --scope user --accept-package-agreements --accept-source-agreements --silent
    if ($LASTEXITCODE -ne 0) {
        throw "Instalasi Python melalui winget gagal dengan exit code $LASTEXITCODE."
    }
    $python = Find-CompatiblePython
}

if (-not $python) {
    throw "Python selesai diinstal tetapi executable belum ditemukan. Tutup terminal, buka kembali, lalu jalankan install.bat."
}

$version = & $python -c "import platform; print(platform.python_version())"
Write-Host "[OK] Python $version kompatibel: $python"
Set-Content -LiteralPath $OutputFile -Value $python -Encoding ASCII
