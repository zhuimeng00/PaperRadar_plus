# encoding: utf-8
param([string]$TaskName = "PaperRadar_Daily_0800")
schtasks /Delete /TN $TaskName /F
Write-Host "已删除计划任务：$TaskName"
