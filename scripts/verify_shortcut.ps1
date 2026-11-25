$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut("C:\Users\beckpalmx\Desktop\Smart iOS Optimizer.lnk")
Write-Host "Shortcut Target:" $sc.TargetPath
Write-Host "Shortcut Icon:" $sc.IconLocation
Write-Host "Shortcut WorkDir:" $sc.WorkingDirectory
