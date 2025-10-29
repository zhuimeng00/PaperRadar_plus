# PaperRadar daily runner · UTF-8 (no BOM) log + fixed working dir
param(
  [int]$SinceDays = 5,
  [switch]$OpenDigest = $true
)

$ErrorActionPreference = "Stop"

# --- Paths ---
$ProjectDir = "D:\PaperRader\PaperRadar_plus"   # ← 如路径变化请改这里
if (-not (Test-Path $ProjectDir)) { throw "Project directory not found: $ProjectDir" }

$Py = Join-Path $ProjectDir ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) {
  if (Get-Command py.exe -ErrorAction SilentlyContinue)      { $Py = "py.exe" }
  elseif (Get-Command python.exe -ErrorAction SilentlyContinue) { $Py = "python.exe" }
  else { throw "Python not found. Create venv first." }
}

$Config = Join-Path $ProjectDir "config.yaml"   # 绝对路径传给 python
$DigestDir = Join-Path $ProjectDir "digests"

# --- Log (UTF-8 no BOM, append) ---
$LogDir = Join-Path $ProjectDir "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$today = Get-Date -Format "yyyy-MM-dd"
$LogFile = Join-Path $LogDir ("run_" + $today + ".log")
$utf8 = New-Object System.Text.UTF8Encoding($false)
$sw = New-Object System.IO.StreamWriter($LogFile, $true, $utf8)

function Write-Log([string]$line) {
  $sw.WriteLine($line); $sw.Flush()
}

# 头部（本地时区）
$cmdShow = "PaperRadar --run --config `"$Config`" --since_days $SinceDays"
$header  = "[{0:yyyy-MM-dd HH:mm:ssK}] RUN: {1}" -f (Get-Date), $cmdShow
Write-Host $header
Write-Log  $header

# --- Spawn python with fixed WorkingDirectory ---
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $Py
$psi.WorkingDirectory = $ProjectDir         # ← 关键：修正子进程 CWD
$psi.Arguments = "`"$ProjectDir\paper_radar_plus.py`" --config `"$Config`" --since_days $SinceDays"
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError  = $true
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true

$proc = New-Object System.Diagnostics.Process
$proc.StartInfo = $psi
$null = $proc.Start()

$stdout = $proc.StandardOutput
$stderr = $proc.StandardError

while(-not $proc.HasExited -or -not $stdout.EndOfStream -or -not $stderr.EndOfStream){
  if(-not $stdout.EndOfStream){ $l = $stdout.ReadLine(); if($null -ne $l){ Write-Host $l; Write-Log $l } }
  if(-not $stderr.EndOfStream){ $e = $stderr.ReadLine(); if($null -ne $e){ Write-Host $e; Write-Log $e } }
  Start-Sleep -Milliseconds 10
}
$exit = $proc.ExitCode

# --- Popup / open digest ---
$digest = Join-Path $DigestDir ($today + ".md")
$msg = if (Test-Path $digest) { "Digest generated: $digest" } else { "No digest. See log: $LogFile" }
try { (New-Object -ComObject Wscript.Shell).Popup($msg, 8, "PaperRadar", 64) | Out-Null } catch {}

if ($OpenDigest -and (Test-Path $digest)) {
  try {
    if (Get-Command code -ErrorAction SilentlyContinue) { & code --reuse-window "$digest" }
    elseif (Get-Command typora.exe -ErrorAction SilentlyContinue) { & typora.exe "$digest" }
    elseif (Get-Command notepad.exe -ErrorAction SilentlyContinue) { & notepad.exe "$digest" }
    else { Invoke-Item "$digest" }
  } catch {}
}

$sw.Dispose()
exit $exit
