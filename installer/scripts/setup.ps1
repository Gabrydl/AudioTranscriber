# AudioTranscriber - setup / repair. Started by AudioTranscriber.exe (built into it), never by hand.
# Everything big (Python packages, Whisper, Ollama + its models) stays on the drive the app folder is on.
# Progress is written to -LogFile; lines starting with ## are read by the setup window.
param(
    [Parameter(Mandatory = $true)][string]$Root,
    [Parameter(Mandatory = $true)][string]$LogFile,
    [Parameter(Mandatory = $true)][string]$Exe
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$Root = (Resolve-Path -LiteralPath $Root).Path.TrimEnd('\')
$Drive = Split-Path -Qualifier $Root
Set-Location -LiteralPath $Root
$Total = 9
$utf8 = New-Object System.Text.UTF8Encoding($false)
$script:lastKey = ""; $script:lastTime = [DateTime]::MinValue
$Esc = [char]27

function Log([string]$t) { [System.IO.File]::AppendAllText($LogFile, $t + "`r`n", $utf8) }
function Step([int]$n, [string]$t) { Log ""; Log "##STEP $n/$Total $t" }
function Ok([string]$t) { Log "    $t" }
function Warn([string]$t) { Log "##WARN $t" }

# Runs a program and copies its output into the log (spinners and repeated progress lines are thinned out).
function Run([string]$exe, [string[]]$a) {
    $old = $ErrorActionPreference; $ErrorActionPreference = "Continue"
    try {
        & $exe @a 2>&1 | ForEach-Object {
            $l = ("$_" -replace "$Esc\[[0-9;?]*[A-Za-z]", "" -replace "`r", "").Trim()
            if (-not $l -or $l -match '^[\s\-\\|/.]*$' -or $l -match '^[▀-▟\s]+$') { return }
            $key = if ($l.Length -gt 22) { $l.Substring(0, 22) } else { $l }
            $now = [DateTime]::Now
            if ($key -eq $script:lastKey -and ($now - $script:lastTime).TotalSeconds -lt 3) { return }
            $script:lastKey = $key; $script:lastTime = $now
            Log "    $l"
        }
    } finally { $ErrorActionPreference = $old }
    return $LASTEXITCODE
}

try {
    Log "AudioTranscriber setup - $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
    Log "Folder: $Root"

    # ------------------------------------------------------------ 1. Windows
    Step 1 "Checking Windows"
    $build = [int](Get-CimInstance Win32_OperatingSystem).BuildNumber
    if ($build -lt 19041) { Warn "Windows build $build is too old for per-app audio capture (needs Windows 10 2004 or newer)." }
    else { Ok "Windows build $build - per-app audio capture supported" }

    # ------------------------------------------------------------ 2. Previous copy
    Step 2 "Looking for a previous copy to reuse"
    $prev = $null
    $om = [Environment]::GetEnvironmentVariable("OLLAMA_MODELS", "User")
    if ($om -and (Test-Path -LiteralPath $om)) {
        $c = (Resolve-Path -LiteralPath (Split-Path -Parent $om)).Path.TrimEnd('\')
        if ($c -ne $Root -and (Test-Path -LiteralPath (Join-Path $c "models"))) { $prev = $c }
    }
    if ($prev) {
        Ok "Found $prev - copying its models, settings and voices instead of downloading them again"
        foreach ($d in @("models", "ollama_models")) {
            if (Test-Path -LiteralPath (Join-Path $prev $d)) {
                $code = Run "robocopy.exe" @((Join-Path $prev $d), (Join-Path $Root $d), "/E", "/XO", "/R:1", "/W:1", "/NFL", "/NDL", "/NJH", "/NJS", "/NP")
                if ($code -ge 8) { Warn "Some files in $d could not be copied - they will be downloaded instead." }
            }
        }
        foreach ($f in @("settings.json", "speakers.json")) {
            $src = Join-Path $prev $f; $dst = Join-Path $Root $f
            if ((Test-Path -LiteralPath $src) -and -not (Test-Path -LiteralPath $dst)) { Copy-Item -LiteralPath $src -Destination $dst }
        }
        if (Test-Path -LiteralPath (Join-Path $Root "ollama_models")) {
            [Environment]::SetEnvironmentVariable("OLLAMA_MODELS", (Join-Path $Root "ollama_models"), "User")
        }
        Ok "Done. The old folder is untouched; you can delete it once the app works from here."
    } else { Ok "None found - everything will be downloaded" }

    # ------------------------------------------------------------ 3. Python
    Step 3 "Looking for Python 3.10 - 3.13"
    function Test-Py($cmd, $extra) {
        try {
            $v = & $cmd @extra -c "import sys, venv, ensurepip; print('%d.%d' % sys.version_info[:2])" 2>$null
            if ($LASTEXITCODE -eq 0 -and "$v" -match '^3\.(1[0-3])$') { return "$v" }
        } catch {}
        return $null
    }
    $vpy = "$Root\.venv\Scripts\python.exe"
    $venvOk = (Test-Path $vpy) -and (Test-Py $vpy @())
    $py = $null; $pyArgs = @()
    if (-not $venvOk) {
        $candidates = @(
            @("$Drive\py311\python.exe", @()), @("$Drive\Python311\python.exe", @()),
            @("py", @("-3.11")), @("py", @("-3.12")), @("py", @("-3.13")), @("py", @("-3.10")),
            @("python", @())
        )
        foreach ($c in $candidates) {
            $v = Test-Py $c[0] $c[1]
            if ($v) { $py = $c[0]; $pyArgs = $c[1]; Ok "Using Python $v ($($c[0]))"; break }
        }
        if (-not $py) {
            if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
                throw "Python 3.11 is needed. Install it from python.org, then run setup again."
            }
            Ok "No suitable Python found - installing Python 3.11 to $Drive\Python311"
            Run "winget" @("install", "-e", "--id", "Python.Python.3.11", "--location", "$Drive\Python311", "--silent",
                           "--accept-package-agreements", "--accept-source-agreements") | Out-Null
            if (Test-Path "$Drive\Python311\python.exe") { $py = "$Drive\Python311\python.exe" }
            else { throw "Python could not be installed. Install Python 3.11 from python.org, then run setup again." }
        }
    } else { Ok "The app's Python environment is working" }

    # ------------------------------------------------------------ 4. venv + packages
    Step 4 "Installing Python packages (about 1.5 - 2 GB)"
    if (-not $venvOk) {
        Ok "Creating the app's private Python environment (.venv)"
        if ((Run $py ($pyArgs + @("-m", "venv", "--clear", "$Root\.venv"))) -ne 0) { throw "The Python environment could not be created." }
    }
    $env:PIP_CACHE_DIR = "$Drive\pip_cache"
    $env:PIP_DISABLE_PIP_VERSION_CHECK = "1"
    Run $vpy @("-m", "pip", "install", "--upgrade", "--progress-bar", "off", "pip", "wheel") | Out-Null
    if ((Run $vpy @("-m", "pip", "install", "--progress-bar", "off", "-r", "$Root\requirements.txt")) -ne 0) {
        throw "Some Python packages could not be installed (see details)."
    }

    # ------------------------------------------------------------ 5. GPU
    Step 5 "Checking the graphics card"
    $hasNvidia = $null -ne (Get-Command nvidia-smi -ErrorAction SilentlyContinue)
    if ($hasNvidia) {
        Ok "NVIDIA GPU found - installing CUDA 12 libraries for Whisper"
        if ((Run $vpy @("-m", "pip", "install", "--progress-bar", "off", "nvidia-cublas-cu12", "nvidia-cudnn-cu12==9.*")) -ne 0) {
            Warn "CUDA libraries could not be installed - the app will fall back to the CPU."
        }
        Run "nvidia-smi" @("--query-gpu=name,memory.total,driver_version", "--format=csv,noheader") | Out-Null
    } else { Warn "No NVIDIA GPU found - choose the 'CPU only' profile in Settings." }

    # ------------------------------------------------------------ 6. Ollama
    Step 6 "Setting up the translator (Ollama + gemma3:4b, about 3.3 GB)"
    $ollamaModels = "$Root\ollama_models"
    $current = [Environment]::GetEnvironmentVariable("OLLAMA_MODELS", "User")
    if (-not $current -or -not (Test-Path -LiteralPath $current)) {
        New-Item -ItemType Directory -Force -Path $ollamaModels | Out-Null
        [Environment]::SetEnvironmentVariable("OLLAMA_MODELS", $ollamaModels, "User")
        $current = $ollamaModels
    }
    $env:OLLAMA_MODELS = $current
    Ok "Translation models folder: $current"

    function Find-Ollama {
        $c = Get-Command ollama -ErrorAction SilentlyContinue
        if ($c) { return $c.Source }
        foreach ($p in @("$Drive\Ollama\ollama.exe", "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe", "$env:ProgramFiles\Ollama\ollama.exe")) {
            if (Test-Path $p) { return $p }
        }
        return $null
    }
    $ollama = Find-Ollama
    if (-not $ollama) {
        Ok "Installing Ollama to $Drive\Ollama"
        if (Get-Command winget -ErrorAction SilentlyContinue) {
            Run "winget" @("install", "-e", "--id", "Ollama.Ollama", "--location", "$Drive\Ollama", "--silent",
                           "--accept-package-agreements", "--accept-source-agreements") | Out-Null
            $ollama = Find-Ollama
        }
        if (-not $ollama) {
            $setup = "$env:TEMP\OllamaSetup.exe"
            Invoke-WebRequest "https://ollama.com/download/OllamaSetup.exe" -OutFile $setup -UseBasicParsing
            Start-Process $setup -ArgumentList "/VERYSILENT", "/NORESTART", "/SUPPRESSMSGBOXES", "/DIR=`"$Drive\Ollama`"" -Wait
            Remove-Item $setup -ErrorAction SilentlyContinue
            $ollama = Find-Ollama
        }
        if (-not $ollama) { throw "Ollama could not be installed. Install it from ollama.com, then run setup again." }
    }
    Ok "Ollama: $ollama"
    Get-Process -Name "ollama*" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    Start-Process -WindowStyle Hidden -FilePath $ollama -ArgumentList "serve"
    $up = $false
    for ($i = 0; $i -lt 30 -and -not $up; $i++) {
        Start-Sleep -Seconds 1
        try { Invoke-WebRequest "http://127.0.0.1:11434/api/tags" -UseBasicParsing -TimeoutSec 2 | Out-Null; $up = $true } catch {}
    }
    if (-not $up) { throw "Ollama did not start." }
    if ((Run $ollama @("pull", "gemma3:4b")) -ne 0) { throw "The translation model could not be downloaded." }

    # ------------------------------------------------------------ 7. Whisper
    Step 7 "Downloading the speech model (Whisper large-v3-turbo, about 1.6 GB)"
    $env:HF_HOME = "$Root\models\hf"
    $env:HF_HUB_DISABLE_PROGRESS_BARS = "1"
    $env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"
    $env:AT_MODELS = "$Root\models"
    if ((Run $vpy @("-c", "import os; from faster_whisper import download_model; download_model('large-v3-turbo', cache_dir=os.environ['AT_MODELS']); print('ok')")) -ne 0) {
        throw "The speech model could not be downloaded."
    }

    # ------------------------------------------------------------ 8. Speaker models
    Step 8 "Downloading the voice recognition models (about 245 MB)"
    $env:AT_SPEAKER = "$Root\models\speaker"
    $code = "import os; from huggingface_hub import hf_hub_download as d; [d('csukuangfj/speaker-embedding-models', f, local_dir=os.environ['AT_SPEAKER']) for f in ('wespeaker_en_voxceleb_resnet293_LM.onnx', 'nemo_en_titanet_large.onnx', 'wespeaker_en_voxceleb_CAM++_LM.onnx')]; print('ok')"
    if ((Run $vpy @("-c", $code)) -ne 0) { throw "The voice recognition models could not be downloaded." }

    # ------------------------------------------------------------ 9. Shortcuts
    Step 9 "Creating shortcuts"
    $ws = New-Object -ComObject WScript.Shell
    foreach ($dir in @([Environment]::GetFolderPath("Desktop"), [Environment]::GetFolderPath("Programs"))) {
        $lnk = $ws.CreateShortcut((Join-Path $dir "AudioTranscriber.lnk"))
        $lnk.TargetPath = $Exe
        $lnk.Arguments = ""
        $lnk.WorkingDirectory = $Root
        $lnk.IconLocation = "$Exe,0"
        $lnk.Description = "Live voice transcription and translation"
        $lnk.Save()
    }
    Ok "Desktop and Start menu shortcuts created"
    $runKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
    if (Get-ItemProperty -Path $runKey -Name "AudioTranscriber" -ErrorAction SilentlyContinue) {
        Set-ItemProperty -Path $runKey -Name "AudioTranscriber" -Value "`"$Exe`" --tray"
    }

    Log ""
    Log "##DONE"
    exit 0
} catch {
    Log ""
    Log "    $($_.InvocationInfo.PositionMessage)"
    Log "##FAIL $($_.Exception.Message)"
    exit 1
}
