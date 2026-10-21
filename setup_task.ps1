$pythonw = "C:\Users\DeLL\AppData\Local\Programs\Python\Python312\pythonw.exe"
$script = "C:\Users\DeLL\pnr-tracker\pnr_tracker.py"
$workdir = "C:\Users\DeLL\pnr-tracker"

$action = New-ScheduledTaskAction -Execute $pythonw -Argument "`"$script`" --once" -WorkingDirectory $workdir
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 30)
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName "PNR_Status_Tracker" -Action $action -Trigger $trigger -Settings $settings -Force
Write-Host "Task PNR_Status_Tracker registered successfully!"
