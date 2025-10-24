# encoding: utf-8
param(
  [string]$TaskName = "PaperRadar_Daily_0800",
  [string]$ProjectDir = "D:\PaperRader\PaperRadar_plus",
  [string]$Time = "08:00",
  [int]$SinceDays = 2
)
$ErrorActionPreference = "Stop"
$Runner = Join-Path $PSScriptRoot "run_daily.ps1"
if (-not (Test-Path $Runner)) { throw "未找到 run_daily.ps1：$Runner" }
$psCmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$Runner`" -SinceDays $SinceDays"
schtasks /Create /TN $TaskName /TR "$psCmd" /SC DAILY /ST $Time /IT /F | Out-Null
Write-Host "计划任务已创建：$TaskName  每天 $Time 运行"
Write-Host "测试运行一次：schtasks /Run /TN $TaskName"
Write-Host "查看日志：$ProjectDir\logs\run_YYYY-MM-DD.log"
