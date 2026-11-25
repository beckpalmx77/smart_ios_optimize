$WshShell = New-Object -ComObject WScript.Shell
$DesktopPath = [System.Environment]::GetFolderPath('Desktop')
$ShortcutPath = Join-Path -Path $DesktopPath -ChildPath "Smart iOS Optimizer.lnk"

$BaseDir = Split-Path -Parent $PSScriptRoot
$TargetPath = Join-Path -Path $BaseDir -ChildPath "dist\SmartIOSOptimizer\SmartIOSOptimizer.exe"
$WorkingDir = Join-Path -Path $BaseDir -ChildPath "dist\SmartIOSOptimizer"
$IconPath = Join-Path -Path $BaseDir -ChildPath "assets\app_icon.ico"

$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $TargetPath
$Shortcut.WorkingDirectory = $WorkingDir
$Shortcut.IconLocation = "$IconPath,0"
$Shortcut.Description = "Smart iOS Optimizer - Deep Clean & Optimization Tool"
$Shortcut.Save()

Write-Host "Desktop Shortcut created successfully at: $ShortcutPath"
Write-Host "Target: $TargetPath"
Write-Host "Icon: $IconPath"
