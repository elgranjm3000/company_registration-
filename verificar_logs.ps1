# Script de PowerShell para buscar productos modificados en los logs
Get-ChildItem "logs\sync_*.txt" |
    Select-String -Pattern "MODIFICADO" -Context 0,2 |
    Select-Object -Last 100
