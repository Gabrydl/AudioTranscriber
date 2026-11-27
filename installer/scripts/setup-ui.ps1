# AudioTranscriber - setup window. Started by AudioTranscriber.exe (built into it).
# Exit code 0 = installed and the user chose to open the app; 1 = cancelled / failed.
param(
    [Parameter(Mandatory = $true)][string]$Root,
    [Parameter(Mandatory = $true)][string]$Exe,
    [Parameter(Mandatory = $true)][string]$SetupScript,
    [switch]$Repair
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
Add-Type -TypeDefinition @"
using System; using System.Runtime.InteropServices;
public static class AtNative {
    [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
    [DllImport("dwmapi.dll")] public static extern int DwmSetWindowAttribute(IntPtr h, int a, ref int v, int s);
}
"@
try { [AtNative]::SetProcessDPIAware() | Out-Null } catch {}
[System.Windows.Forms.Application]::EnableVisualStyles()

$Root = $Root.TrimEnd('\', '.')
if ($Root -match '^[A-Za-z]:$') { $Root += '\' }
$LogFile = Join-Path $Root "setup.log"

# ---------------------------------------------------------------- look (same palette as the app)
$C = @{
    Bg = [Drawing.ColorTranslator]::FromHtml("#0e0e0f"); Surf = [Drawing.ColorTranslator]::FromHtml("#161618")
    Surf2 = [Drawing.ColorTranslator]::FromHtml("#1e1e21"); Border = [Drawing.ColorTranslator]::FromHtml("#2a2a2e")
    Text = [Drawing.ColorTranslator]::FromHtml("#ececee"); Muted = [Drawing.ColorTranslator]::FromHtml("#9a9aa1")
    Dim = [Drawing.ColorTranslator]::FromHtml("#64646b"); Violet = [Drawing.ColorTranslator]::FromHtml("#8b5cf6")
    Cyan = [Drawing.ColorTranslator]::FromHtml("#06b6d4"); Red = [Drawing.ColorTranslator]::FromHtml("#f87171")
    Amber = [Drawing.ColorTranslator]::FromHtml("#fbbf24")
}
$g0 = [Drawing.Graphics]::FromHwnd([IntPtr]::Zero); $K = $g0.DpiX / 96.0; $g0.Dispose()
function S([double]$v) { [int][Math]::Round($v * $K) }
function Font([double]$pt, [string]$style = "Regular", [string]$fam = "Segoe UI") {
    New-Object Drawing.Font($fam, [single]$pt, [Drawing.FontStyle]$style)
}
function Label($text, $x, $y, $w, $h, $font, $color) {
    $l = New-Object Windows.Forms.Label
    $l.Text = $text; $l.Location = New-Object Drawing.Point((S $x), (S $y)); $l.Size = New-Object Drawing.Size((S $w), (S $h))
    $l.Font = $font; $l.ForeColor = $color; $l.BackColor = [Drawing.Color]::Transparent
    $form.Controls.Add($l); $l
}
function RoundPath([Drawing.Rectangle]$r, [int]$rad) {
    $p = New-Object Drawing.Drawing2D.GraphicsPath; $d = $rad * 2
    if ($d -le 0 -or $r.Width -le $d -or $r.Height -lt $d) { $p.AddRectangle($r); return $p }
    $p.AddArc($r.X, $r.Y, $d, $d, 180, 90); $p.AddArc($r.Right - $d - 1, $r.Y, $d, $d, 270, 90)
    $p.AddArc($r.Right - $d - 1, $r.Bottom - $d - 1, $d, $d, 0, 90); $p.AddArc($r.X, $r.Bottom - $d - 1, $d, $d, 90, 90)
    $p.CloseFigure(); $p
}
# Buttons are painted by hand: gradient for the main action, dark for the secondary one.
function Button($text, $x, $y, $w, $primary) {
    $b = New-Object Windows.Forms.Label
    $b.Text = $text; $b.Location = New-Object Drawing.Point((S $x), (S $y)); $b.Size = New-Object Drawing.Size((S $w), (S 38))
    $b.Font = Font 10 "Bold"; $b.Cursor = [Windows.Forms.Cursors]::Hand; $b.BackColor = $C.Bg
    $b.Tag = @{ Primary = $primary; Hover = $false }
    $b.add_MouseEnter({ $this.Tag.Hover = $true; $this.Invalidate() })
    $b.add_MouseLeave({ $this.Tag.Hover = $false; $this.Invalidate() })
    $b.add_Paint({
        param($s, $e)
        $g = $e.Graphics; $g.SmoothingMode = "AntiAlias"; $g.TextRenderingHint = "ClearTypeGridFit"
        $r = New-Object Drawing.Rectangle(0, 0, $s.Width, $s.Height)
        $g.Clear($C.Bg)
        $path = RoundPath $r (S 10)
        if (-not $s.Enabled) {
            $br = New-Object Drawing.SolidBrush($C.Surf2); $g.FillPath($br, $path); $fg = $C.Dim
        } elseif ($s.Tag.Primary) {
            $a = if ($s.Tag.Hover) { [Drawing.ColorTranslator]::FromHtml("#9d74ff") } else { $C.Violet }
            $z = if ($s.Tag.Hover) { [Drawing.ColorTranslator]::FromHtml("#22d3ee") } else { $C.Cyan }
            $br = New-Object Drawing.Drawing2D.LinearGradientBrush($r, $a, $z, [single]20); $g.FillPath($br, $path); $fg = [Drawing.Color]::White
        } else {
            $c = if ($s.Tag.Hover) { [Drawing.ColorTranslator]::FromHtml("#26262a") } else { $C.Surf2 }
            $br = New-Object Drawing.SolidBrush($c); $g.FillPath($br, $path)
            $pen = New-Object Drawing.Pen($C.Border); $g.DrawPath($pen, $path); $pen.Dispose(); $fg = $C.Text
        }
        $br.Dispose(); $path.Dispose()
        [Windows.Forms.TextRenderer]::DrawText($g, $s.Text, $s.Font, $r, $fg,
            [Windows.Forms.TextFormatFlags]"HorizontalCenter, VerticalCenter, SingleLine")
    })
    $b.add_EnabledChanged({ $this.Invalidate() })
    $b.add_TextChanged({ $this.Invalidate() })
    $form.Controls.Add($b); $b
}

# ---------------------------------------------------------------- window
$form = New-Object Windows.Forms.Form
$form.Text = if ($Repair) { "AudioTranscriber - Repair" } else { "AudioTranscriber - Setup" }
$form.ClientSize = New-Object Drawing.Size((S 600), (S 300))
$form.FormBorderStyle = "FixedSingle"; $form.MaximizeBox = $false
$form.StartPosition = "CenterScreen"; $form.BackColor = $C.Bg; $form.ForeColor = $C.Text
$form.Font = Font 9.5
try { $form.Icon = [Drawing.Icon]::ExtractAssociatedIcon($Exe) } catch {}
$form.add_HandleCreated({ $v = 1; try { [AtNative]::DwmSetWindowAttribute($form.Handle, 20, [ref]$v, 4) | Out-Null } catch {} })

$title = Label "AudioTranscriber" 28 22 540 34 (Font 17 "Regular" "Segoe UI Semibold") $C.Text
$sub = Label "Live voice transcription and translation - runs 100% on this PC" 30 58 540 20 (Font 9.5) $C.Muted
$intro = if ($Repair) {
    "Repair checks every component and downloads only what is missing or broken. Your settings, voices and models are kept."
} else {
    "One-time setup. It downloads about 8 GB (Python packages, speech, voice and translation models) to drive $((Split-Path -Qualifier $Root)) and takes 10-20 minutes. You can keep using your PC meanwhile."
}
$info = Label $intro 30 94 540 44 (Font 9.5) $C.Text
$step = Label "" 30 152 420 22 (Font 10 "Bold") $C.Text
$time = Label "" 450 152 120 22 (Font 9) $C.Dim
$time.TextAlign = "MiddleRight"

# progress bar (painted)
$bar = New-Object Windows.Forms.Panel
$bar.Location = New-Object Drawing.Point((S 30), (S 180)); $bar.Size = New-Object Drawing.Size((S 540), (S 6))
$bar.BackColor = $C.Bg; $bar.Tag = @{ Value = 0.0; Pulse = 0.0; Busy = $false }
$bar.add_Paint({
    param($s, $e)
    $g = $e.Graphics; $g.SmoothingMode = "AntiAlias"
    $r = New-Object Drawing.Rectangle(0, 0, $s.Width, $s.Height)
    $p = RoundPath $r ([int]($s.Height / 2)); $br = New-Object Drawing.SolidBrush($C.Surf2); $g.FillPath($br, $p); $br.Dispose(); $p.Dispose()
    $w = [int]($s.Width * [Math]::Min(1.0, $s.Tag.Value))
    if ($w -ge $s.Height) {
        $fr = New-Object Drawing.Rectangle(0, 0, $w, $s.Height); $p = RoundPath $fr ([int]($s.Height / 2))
        $br = New-Object Drawing.Drawing2D.LinearGradientBrush((New-Object Drawing.Rectangle(0, 0, $s.Width, $s.Height)), $C.Violet, $C.Cyan, [single]0)
        $g.FillPath($br, $p); $br.Dispose(); $p.Dispose()
    }
    if ($s.Tag.Busy) {   # soft light moving along the bar while a long step runs
        $x = [int](($s.Width + 160) * $s.Tag.Pulse) - 80
        $pr = New-Object Drawing.Rectangle($x, 0, 80, $s.Height)
        $br = New-Object Drawing.Drawing2D.LinearGradientBrush($pr, [Drawing.Color]::FromArgb(0, 255, 255, 255), [Drawing.Color]::FromArgb(70, 255, 255, 255), [single]0)
        $br.SetSigmaBellShape(0.5); $g.FillRectangle($br, $pr); $br.Dispose()
    }
})
$form.Controls.Add($bar)

$detailsLink = New-Object Windows.Forms.LinkLabel
$detailsLink.Text = "Show details"; $detailsLink.Location = New-Object Drawing.Point((S 28), (S 200)); $detailsLink.AutoSize = $true
$detailsLink.LinkColor = $C.Muted; $detailsLink.ActiveLinkColor = $C.Text; $detailsLink.LinkBehavior = "HoverUnderline"
$detailsLink.BackColor = [Drawing.Color]::Transparent; $detailsLink.Font = Font 9
$form.Controls.Add($detailsLink)

$log = New-Object Windows.Forms.TextBox
$log.Multiline = $true; $log.ReadOnly = $true; $log.ScrollBars = "Vertical"; $log.WordWrap = $true
$log.BorderStyle = "None"; $log.BackColor = $C.Surf; $log.ForeColor = $C.Muted; $log.Font = Font 8.5 "Regular" "Consolas"
$log.Location = New-Object Drawing.Point((S 30), (S 228)); $log.Size = New-Object Drawing.Size((S 540), (S 190)); $log.Visible = $false
$form.Controls.Add($log)

$secondary = Button "Cancel" 330 238 110 $false
$primary = Button $(if ($Repair) { "Repair" } else { "Install" }) 450 238 120 $true

function Set-Details([bool]$show) {
    $log.Visible = $show
    $detailsLink.Text = if ($show) { "Hide details" } else { "Show details" }
    $h = if ($show) { 490 } else { 300 }
    $form.ClientSize = New-Object Drawing.Size((S 600), (S $h))
    $y = if ($show) { 428 } else { 238 }
    $primary.Top = S $y; $secondary.Top = S $y
}
$detailsLink.add_LinkClicked({ Set-Details (-not $log.Visible) })

# ---------------------------------------------------------------- state
$script:proc = $null; $script:pos = 0L; $script:partial = ""; $script:state = "idle"
$script:started = $null; $script:result = 1
$step.Text = if ($Repair) { "Ready to repair" } else { "Ready to install" }

function Append([string]$t) {
    if ($log.TextLength -gt 400000) { $log.Text = $log.Text.Substring(200000) }
    $log.AppendText($t + "`r`n")
}

function Finish([bool]$ok, [string]$msg) {
    $timer.Stop(); $bar.Tag.Busy = $false
    $secondary.Enabled = $true
    if ($ok) {
        $script:state = "done"; $bar.Tag.Value = 1.0
        $step.Text = if ($Repair) { "Repair complete" } else { "Setup complete" }; $step.ForeColor = $C.Text
        $info.Text = "AudioTranscriber is ready. Shortcuts are on your desktop and in the Start menu."
        $primary.Text = "Open AudioTranscriber"; $primary.Width = S 190; $primary.Left = S 380; $primary.Enabled = $true
        $secondary.Text = "Close"; $secondary.Left = S 260
    } else {
        $script:state = "failed"
        $step.Text = "Setup did not finish"; $step.ForeColor = $C.Red
        $info.Text = "$msg`nNothing is lost: press Retry and setup continues from where it stopped. Full log: setup.log"
        $primary.Text = "Retry"; $primary.Enabled = $true
        $secondary.Text = "Close"
        Set-Details $true
    }
    $bar.Invalidate()
}

function Pump {
    if (-not (Test-Path -LiteralPath $LogFile)) { return }
    try {
        $fs = New-Object IO.FileStream($LogFile, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]"ReadWrite, Delete")
        try {
            if ($fs.Length -lt $script:pos) { $script:pos = 0L }
            [void]$fs.Seek($script:pos, [IO.SeekOrigin]::Begin)
            $buf = New-Object byte[] ($fs.Length - $script:pos)
            $n = $fs.Read($buf, 0, $buf.Length); $script:pos += $n
        } finally { $fs.Dispose() }
    } catch { return }
    if ($n -le 0) { return }
    $text = $script:partial + [Text.Encoding]::UTF8.GetString($buf, 0, $n)
    $lines = $text -split "`r?`n"
    $script:partial = $lines[-1]
    if ($lines.Count -lt 2) { return }
    foreach ($l in $lines[0..($lines.Count - 2)]) {
        if ($l -match '^##STEP (\d+)/(\d+) (.*)$') {
            $step.Text = $Matches[3]; $bar.Tag.Value = ([double]$Matches[1] - 1) / [double]$Matches[2]
            Append ""; Append ("> " + $Matches[3])
        } elseif ($l -match '^##WARN (.*)$') {
            Append ("! " + $Matches[1])
        } elseif ($l -eq '##DONE') {
            Finish $true ""
        } elseif ($l -match '^##FAIL (.*)$') {
            Append ("x " + $Matches[1]); Finish $false $Matches[1]
        } elseif ($l -notmatch '^AudioTranscriber setup - ') {
            Append $l
        }
    }
}

$timer = New-Object Windows.Forms.Timer
$timer.Interval = 250
$timer.add_Tick({
    Pump
    if ($script:state -ne "running") { return }
    $bar.Tag.Pulse = ($bar.Tag.Pulse + 0.018) % 1.0; $bar.Invalidate()
    $el = (Get-Date) - $script:started
    $time.Text = "{0}:{1:00} elapsed" -f [int][Math]::Floor($el.TotalMinutes), $el.Seconds
    if ($script:proc.HasExited) {
        Start-Sleep -Milliseconds 300; Pump
        if ($script:state -eq "running") { Finish $false "Setup stopped unexpectedly (code $($script:proc.ExitCode))." }
    }
})

function Start-Setup {
    $script:state = "running"; $script:pos = 0L; $script:partial = ""; $script:started = Get-Date
    try { if (Test-Path -LiteralPath $LogFile) { Remove-Item -LiteralPath $LogFile -Force } } catch {}
    $log.Clear(); $step.ForeColor = $C.Text; $step.Text = "Starting..."
    $info.Text = $intro
    $primary.Text = if ($Repair) { "Repairing..." } else { "Installing..." }; $primary.Enabled = $false
    $secondary.Text = "Cancel"; $secondary.Enabled = $true
    $bar.Tag.Busy = $true; $bar.Tag.Value = 0.0
    $r = $Root.TrimEnd('\'); if ($r -match ':$') { $r += '\.' }
    $psi = New-Object Diagnostics.ProcessStartInfo
    $psi.FileName = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
    $psi.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$SetupScript`" -Root `"$r`" -LogFile `"$LogFile`" -Exe `"$Exe`""
    $psi.UseShellExecute = $false; $psi.CreateNoWindow = $true; $psi.WorkingDirectory = $Root
    try { $script:proc = [Diagnostics.Process]::Start($psi) }
    catch { Finish $false "Setup could not start: $($_.Exception.Message)"; return }
    $timer.Start()
}

function Stop-Setup {
    if ($script:proc -and -not $script:proc.HasExited) {
        Start-Process -FilePath "taskkill.exe" -ArgumentList "/PID $($script:proc.Id) /T /F" -WindowStyle Hidden -Wait
    }
}

function Confirm-Cancel {
    $a = [Windows.Forms.MessageBox]::Show($form, "Stop setup now? You can finish it later by opening AudioTranscriber again.",
        "AudioTranscriber", "YesNo", "Question")
    return $a -eq "Yes"
}

$primary.add_Click({
    if (-not $this.Enabled) { return }
    switch ($script:state) {
        "done" { $script:result = 0; $form.Close() }
        default { Start-Setup }
    }
})
$secondary.add_Click({
    if (-not $this.Enabled) { return }
    if ($script:state -eq "running") {
        if (Confirm-Cancel) { $timer.Stop(); Stop-Setup; $script:state = "cancelled"; $form.Close() }
    } else { $form.Close() }
})
$form.add_FormClosing({
    param($s, $e)
    if ($script:state -eq "running") {
        if (Confirm-Cancel) { $timer.Stop(); Stop-Setup; $script:state = "cancelled" } else { $e.Cancel = $true }
    }
})
$form.add_Shown({ $form.Activate() })

[void]$form.ShowDialog()
$form.Dispose()
exit $script:result
