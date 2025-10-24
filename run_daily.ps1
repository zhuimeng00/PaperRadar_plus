# PaperRadar daily runner (UTF-8 logging; WinPS 5.1 compatible)
param(
  [int]$SinceDays = 2,
  [switch]$OpenDigest = $true
)

$ErrorActionPreference = "Stop"

# --- Project & Python ---
$ProjectDir = $PSScriptRoot
if (-not (Test-Path $ProjectDir)) { throw "Project directory not found: $ProjectDir" }
Set-Location $ProjectDir

$Py = Join-Path $ProjectDir ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) {
  if (Get-Command py.exe -ErrorAction SilentlyContinue)      { $Py = "py.exe" }
  elseif (Get-Command python.exe -ErrorAction SilentlyContinue) { $Py = "python.exe" }
  else { throw "Python not found. Create venv and install deps first." }
}

# --- Log (force UTF-8; ensure BOM so VS Code/Notepad auto-detect) ---
$LogDir = Join-Path $ProjectDir "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$today = Get-Date -Format "yyyy-MM-dd"
$LogFile = Join-Path $LogDir ("run_" + $today + ".log")

# 先写一个 UTF-8（带 BOM）的头行，后续都以 UTF-8 追加
$CmdShow = "PaperRadar --run --since_days $SinceDays"
$now = Get-Date
$Header = "[{0:yyyy-MM-dd HH:mm:ss}{1}] RUN: {2}" -f $now, $now.ToString("zzz"), $CmdShow
if (Test-Path $LogFile) {
  # 已有当日日志：空一行后追加抬头（UTF-8）
  "`r`n$Header" | Add-Content -Path $LogFile -Encoding utf8
} else {
  # 首次生成当天日志：创建 UTF-8（带 BOM）文件
  $Header | Out-File -FilePath $LogFile -Encoding utf8
}
Write-Host $Header

# 控制台输出也切到 UTF-8
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$OutputEncoding = $utf8NoBom
[Console]::OutputEncoding = $utf8NoBom

# --- Run python (WinPS 5.1 用 Arguments；强制子进程走 UTF-8) ---
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName               = $Py
$psi.Arguments              = "`"$ProjectDir\paper_radar_plus.py`" --since_days $SinceDays"
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError  = $true
$psi.UseShellExecute        = $false
$psi.CreateNoWindow         = $true

# 让 .NET 以 UTF-8 解码子进程输出
$psi.StandardOutputEncoding = [System.Text.Encoding]::UTF8
$psi.StandardErrorEncoding  = [System.Text.Encoding]::UTF8
# 让 Python 强制 UTF-8 输出
$psi.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8"
$psi.EnvironmentVariables["PYTHONUTF8"]       = "1"

$proc = New-Object System.Diagnostics.Process
$proc.StartInfo = $psi
$null = $proc.Start()

# 交替读取 stdout/stderr，手动 tee 到控制台 + UTF-8 日志（追加）
$stdOut = $proc.StandardOutput
$stdErr = $proc.StandardError
while(-not $proc.HasExited -or -not $stdOut.EndOfStream -or -not $stdErr.EndOfStream) {
  if(-not $stdOut.EndOfStream) {
    $line = $stdOut.ReadLine()
    if($null -ne $line) { Write-Host $line; $line | Out-File -FilePath $LogFile -Append -Encoding utf8 }
  }
  if(-not $stdErr.EndOfStream) {
    $eline = $stdErr.ReadLine()
    if($null -ne $eline) { Write-Host $eline; $eline | Out-File -FilePath $LogFile -Append -Encoding utf8 }
  }
  Start-Sleep -Milliseconds 10
}
$ExitCode = $proc.ExitCode

# --- Summary / popup / open digest ---
$digest = Join-Path (Join-Path $ProjectDir "digests") ($today + ".md")
if (Test-Path $digest) { $msg = "Digest generated: " + $digest } else { $msg = "No digest. See log: " + $LogFile }
try { $wshell = New-Object -ComObject Wscript.Shell; $wshell.Popup($msg, 8, "PaperRadar", 64) | Out-Null } catch {}

if ($OpenDigest -and (Test-Path $digest)) {
  try {
    if (Get-Command code -ErrorAction SilentlyContinue)      { & code --reuse-window "$digest" }
    elseif (Get-Command typora.exe -ErrorAction SilentlyContinue) { & typora.exe "$digest" }
    elseif (Get-Command notepad.exe -ErrorAction SilentlyContinue){ & notepad.exe "$digest" }
    else { Invoke-Item "$digest" }
  } catch {}
}

exit $ExitCode
