# AudioTranscriber - points shortcuts, "Start with Windows" and the Ollama models folder at this install.
# Run hidden by AudioTranscriber.exe once per location (and whenever old .bat launchers are found).
param(
    [Parameter(Mandatory = $true)][string]$Root,
    [Parameter(Mandatory = $true)][string]$Exe
)
$ErrorActionPreference = "SilentlyContinue"
$Root = $Root.TrimEnd('\', '.')
if ($Root -match '^[A-Za-z]:$') { $Root += '\' }

# Shortcuts: refresh any AudioTranscriber shortcut on the desktop, add one to the Start menu.
$ws = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath("Desktop")
$programs = [Environment]::GetFolderPath("Programs")
$targets = @(Join-Path $programs "AudioTranscriber.lnk")
$targets += Get-ChildItem -LiteralPath $desktop -Filter "*.lnk" | Where-Object {
    $l = $ws.CreateShortcut($_.FullName)
    $_.BaseName -like "AudioTranscriber*" -or $l.Arguments -like "*AudioTranscriber*main.py*" -or $l.TargetPath -like "*AudioTranscriber*"
} | ForEach-Object { $_.FullName }
if (-not (Test-Path (Join-Path $desktop "AudioTranscriber.lnk")) -and $targets.Count -eq 1) {
    $targets += Join-Path $desktop "AudioTranscriber.lnk"
}
foreach ($t in ($targets | Select-Object -Unique)) {
    $lnk = $ws.CreateShortcut($t)
    $lnk.TargetPath = $Exe
    $lnk.Arguments = ""
    $lnk.WorkingDirectory = $Root
    $lnk.IconLocation = "$Exe,0"
    $lnk.Description = "Live voice transcription and translation"
    $lnk.Save()
}

# Start with Windows: keep it on if it was on, but start through the exe.
$runKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
if (Get-ItemProperty -Path $runKey -Name "AudioTranscriber") {
    Set-ItemProperty -Path $runKey -Name "AudioTranscriber" -Value "`"$Exe`" --tray"
}

# Ollama models: if the saved folder no longer exists (folder renamed or moved), use the one next to the app.
$models = Join-Path $Root "ollama_models"
$current = [Environment]::GetEnvironmentVariable("OLLAMA_MODELS", "User")
if ((Test-Path -LiteralPath $models) -and (-not $current -or -not (Test-Path -LiteralPath $current))) {
    [Environment]::SetEnvironmentVariable("OLLAMA_MODELS", $models, "User")
    # a running Ollama still looks in the old folder; the app restarts it with the right one when needed
    Get-Process -Name "ollama" | Stop-Process -Force
}
exit 0
