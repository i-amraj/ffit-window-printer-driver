# FFit Thermal Printer Driver — Windows Installer Script
# Path: installer/install.ps1

$ErrorActionPreference = "Stop"

# Colors for output
function Write-ColorHost($text, $color) {
    Write-Host $text -ForegroundColor $color
}

Write-ColorHost "====================================================" "Cyan"
Write-ColorHost "     FFit Thermal Printer Driver — Windows Setup    " "Cyan"
Write-ColorHost "====================================================" "Cyan"

# 1. Admin privilege check
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-ColorHost "Please run this installer as Administrator." "Red"
    Write-ColorHost "Relaunching PowerShell as Admin..." "Yellow"
    Start-Process powershell -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

# 2. Setup directories
$InstallDir = "C:\Program Files\FFit Printer"
$ConfigDir = "$env:APPDATA\ffit"
$ConfigPath = "$ConfigDir\config.json"
$TempDir = "$env:TEMP\ffit_setup"

Write-ColorHost "[1/5] Creating folders..." "Yellow"
if (-not (Test-Path $InstallDir)) { New-Item -ItemType Directory -Path $InstallDir | Out-Null }
if (-not (Test-Path $ConfigDir)) { New-Item -ItemType Directory -Path $ConfigDir | Out-Null }
if (Test-Path $TempDir) { Remove-Item -Recurse -Force $TempDir | Out-Null }
New-Item -ItemType Directory -Path $TempDir | Out-Null

# 3. Create default configuration if not present
if (-not (Test-Path $ConfigPath)) {
    $defaultConfig = @{
        printer_name = "FFit-Thermal"
        connection_type = "usb"
        device_path = "ZJ-58"
        ip_address = ""
        port = 9100
        com_port = "COM3"
    }
    $defaultConfig | ConvertTo-Json | Out-File -FilePath $ConfigPath -Encoding utf8
}

# 4. Download compiled release packages
Write-ColorHost "[2/5] Downloading Windows binaries from GitHub..." "Yellow"
$zipUrl = "https://raw.githubusercontent.com/i-amraj/ffit-linux-printer-driver/main/ffit-printer-windows-x64.zip"
$zipPath = "$TempDir\release.zip"

Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath -UseBasicParsing

# Extract files
Write-ColorHost "[3/5] Extracting packages..." "Yellow"
Expand-Archive -Path $zipPath -DestinationPath "$TempDir\extracted" -Force

# 5. Install binaries
Write-ColorHost "[4/5] Copying application files..." "Yellow"

# Kill running instances of application or service to overwrite safely
Stop-Process -Name "ffit_printer_ubuntu" -ErrorAction SilentlyContinue
Stop-Process -Name "ffit_service" -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

Copy-Item -Path "$TempDir\extracted\bundle\*" -Destination $InstallDir -Recurse -Force
Copy-Item -Path "$TempDir\extracted\ffit_service.exe" -Destination "$InstallDir\ffit_service.exe" -Force
Copy-Item -Path "$TempDir\extracted\icon.png" -Destination "$InstallDir\icon.png" -Force

# Rename executable to match application name on Windows
if (Test-Path "$InstallDir\ffit_printer_ubuntu.exe") {
    Rename-Item -Path "$InstallDir\ffit_printer_ubuntu.exe" -NewName "ffit-printer.exe" -Force -ErrorAction SilentlyContinue
}

# 6. Configure Task Scheduler for background service (Runs silently at logon)
Write-ColorHost "[5/5] Configuring background services..." "Yellow"

# Unregister old task if exists
Unregister-ScheduledTask -TaskName "FFitPrintService" -Confirm:$false -ErrorAction SilentlyContinue

$Action = New-ScheduledTaskAction -Execute "$InstallDir\ffit_service.exe"
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName "FFitPrintService" -Action $Action -Trigger $Trigger -Settings $Settings -Description "FFit Port 9100 Background Print Service" | Out-Null

# Start background service immediately
Start-Process -FilePath "$InstallDir\ffit_service.exe" -WindowStyle Hidden

# 7. Create shortcuts (Desktop and Start Menu)
$WshShell = New-Object -ComObject WScript.Shell
$DesktopPath = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::CommonDesktopDirectory)
$StartMenuPath = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::CommonPrograms)

# Desktop shortcut
$Shortcut = $WshShell.CreateShortcut("$DesktopPath\FFit Printer.lnk")
$Shortcut.TargetPath = "$InstallDir\ffit-printer.exe"
$Shortcut.WorkingDirectory = $InstallDir
$Shortcut.IconLocation = "$InstallDir\icon.png"
$Shortcut.Save()

# Start menu shortcut
$Shortcut = $WshShell.CreateShortcut("$StartMenuPath\FFit Printer.lnk")
$Shortcut.TargetPath = "$InstallDir\ffit-printer.exe"
$Shortcut.WorkingDirectory = $InstallDir
$Shortcut.IconLocation = "$InstallDir\icon.png"
$Shortcut.Save()

# Cleanup
Remove-Item -Recurse -Force $TempDir | Out-Null

Write-ColorHost "====================================================" "Green"
Write-ColorHost "        ✅ Setup Complete Successfully!            " "Green"
Write-ColorHost "====================================================" "Green"
Write-ColorHost "Next Steps:" "Cyan"
Write-ColorHost "  1. Launch 'FFit Printer' from your Desktop or Start Menu." "NC"
Write-ColorHost "  2. Configure your printer interface." "NC"
Write-ColorHost "  3. Go to Control Panel -> Add Printer -> Add standard TCP/IP port pointing to 127.0.0.1." "NC"
Write-ColorHost "  4. Print with size locked receipts!" "NC"
Write-ColorHost "====================================================" "Green"

# Launch app directly
Start-Process -FilePath "$InstallDir\ffit-printer.exe"
