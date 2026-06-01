# FFit Windows Printer Driver (58mm Thermal Only)

A premium, driverless desktop integration for 58mm thermal printers on Windows (10/11), featuring automated vertical and horizontal margin cropping for perfect text size and clarity.

*Developed with ❤️ by Raj — Premium ESC/POS Printing Solutions*

---

## 📐 Architecture Overview

Unlike traditional Windows GDI drivers that rasterize receipts as standard sheets (shrinking fonts and adding wide margins), **FFit Printer** uses a local Port 9100 interceptor:

```
Chrome / App (Print Page) ──> Windows Spooler (Redirected to 127.0.0.1:9100)
                                                 │
                                                 ▼
USB / Bluetooth COM ◄── [win32print RAW] ◄── FFit Windows Service (PIL Auto-Crop & Resize)
```

1. **Local TCP Interceptor**: Runs a background print server listening on `127.0.0.1:9100`.
2. **Auto-Margin Cropper**: Inspects incoming print jobs, crops all white margin borders, and scales the text container to the exact **384px** printable width of the thermal head.
3. **RAW Spooler Bypass**: Sends clean ESC/POS bytes directly to the printer device.

---

## 🚀 One-Command Installation

To install the Flutter GUI, register the background print service, and set up desktop shortcuts automatically, open **PowerShell (as Administrator)** and paste this command:

```powershell
iwr -useb https://raw.githubusercontent.com/i-amraj/ffit-windows-printer-driver/main/installer/install.ps1 | iex
```

*(Note: Replace `ffit-windows-printer-driver` with your exact Windows repository name on GitHub)*

---

## 📋 Folder Structure

* `ffit_printer_windows/`: Flutter desktop GUI app for managing configurations.
* `windows_service/`: Python background TCP server that processes vector PDFs and communicates with hardware interfaces.
* `installer/`: PowerShell script for automated remote installation.
