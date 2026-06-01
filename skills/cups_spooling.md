# Skill Log: Spooler Queues & Service Permissions (Linux CUPS vs. Windows Spooler)

This document captures the critical learnings and troubleshooting steps resolved regarding printer queue management, driver registration, and permission systems.

---

## 🐧 Linux CUPS Key Learnings

### 1. CUPS Backend Execution Context
* **Problem**: CUPS executes backends (like `/usr/lib/cups/backend/ffit`) under the system user **`lp`** (UID 7, GID 7).
* **Resolution**: The `lp` user does NOT have access to normal user home directories (e.g. `/home/ubuntu_16gb/`). 
* **Key Guideline**: Any temporary files, spool directories, or configuration stores accessed by the backend script MUST be in a globally readable/writable path like `/tmp/` or `/etc/ffit/` with `777` or `755` permissions.

### 2. PPD File Pipeline & PDF Vectors
* **Problem**: Standard CUPS filters (`rastertozj`) often corrupt raw PDF data sent from Chrome (producing garbage outputs or off-center alignment).
* **Resolution**: Bypass raster filters in the PPD file by defining the filter target directly as a PDF:
  ```ppd
  *cupsFilter: "application/pdf 0 -"
  ```
  This delivers clean PDF vectors directly to the custom python engine, bypassing corrupting filters.

### 3. CUPS Service Caching
* **Problem**: Direct modifications to `/usr/share/ppd/` files or backend scripts do not take effect immediately due to memory caching by the CUPS daemon.
* **Resolution**: Always reload the CUPS service after applying updates to drivers, PPDs, or permissions:
  ```bash
  systemctl restart cups
  ```

---

## 🪟 Windows Spooler Adaptations

When replicating this on Windows, keep the following guidelines in mind to prevent similar errors:

### 1. Spooler Account Permissions
* **System Context**: The Windows Spooler service runs under the `Local System` account.
* **Guideline**: If the printer backend writes configurations, it must write to a directory accessible to all users (such as `C:\ProgramData\ffit\`) instead of user-specific paths like `C:\Users\username\AppData\`.

### 2. Raw Printing Spool Bypass
* **Problem**: Standard Windows GDI print drivers try to rasterize or format documents, which ruins ESC/POS raw formatting and produces garbage outputs on thermal printers.
* **Guideline**: To send clean ESC/POS raw command bytes to a USB printer, use `win32print`'s raw spooling mode:
  ```python
  import win32print
  hPrinter = win32print.OpenPrinter("ZJ-58")
  try:
      hJob = win32print.StartDocPrinter(hPrinter, 1, ("FFit Doc", None, "RAW"))
      win32print.StartPagePrinter(hPrinter)
      win32print.WritePrinter(hPrinter, escpos_bytes)
      win32print.EndPagePrinter(hPrinter)
      win32print.EndDocPrinter(hPrinter)
  finally:
      win32print.ClosePrinter(hPrinter)
  ```
