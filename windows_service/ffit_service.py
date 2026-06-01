# FFit Thermal Printer Driver — Windows Background Service
# Path: windows_service/ffit_service.py

import os
import sys
import time
import socket
import json
import tempfile
import threading
from PIL import Image
import numpy as np

# Try-imports for Windows-specific libraries
try:
    import win32print
    import fitz  # PyMuPDF
except ImportError:
    # Fallbacks for syntax check on Linux
    win32print = None
    fitz = None

# Settings & Paths
APPDATA = os.environ.get("APPDATA", os.path.expanduser("~"))
CONFIG_DIR = os.path.join(APPDATA, "ffit")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
PORT = 9100
BIND_IP = "127.0.0.1"


def get_config():
    """Reads configuration saved by the Flutter GUI."""
    if not os.path.exists(CONFIG_PATH):
        return {
            "printer_name": "FFit-Thermal",
            "connection_type": "usb",
            "device_path": "ZJ-58",  # Default USB printer name in Windows
            "ip_address": "",
            "port": 9100,
            "com_port": "COM3"
        }
    try:
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading config: {e}")
        return {}


def build_footer() -> bytes:
    """Standard company branding footer."""
    esc = bytearray()
    esc += bytes([0x1B, 0x40])        # INIT
    esc += bytes([0x1B, 0x61, 0x01]) # CENTER
    esc += b"\n"                      # blank line
    esc += b"-" * 32 + b"\n"         # separator
    esc += bytes([0x1B, 0x45, 0x01]) # BOLD ON
    esc += b"Powered by- FFIT.IO\n"
    esc += bytes([0x1B, 0x45, 0x00]) # BOLD OFF
    esc += bytes([0x1B, 0x64, 0x03]) # FEED 3
    esc += bytes([0x1D, 0x56, 0x00]) # CUT
    return bytes(esc)


def crop_whitespace(img, margin=8):
    """Crops side and vertical white margins from printed documents."""
    gray = img.convert('L')
    pixels = np.array(gray)
    h, w = pixels.shape

    # Find non-white rows (vertical)
    row_means = np.mean(pixels, axis=1)
    non_white_rows = np.where(row_means < 254)[0]
    if len(non_white_rows) == 0:
        return img
    first_row = non_white_rows[0]
    last_row = non_white_rows[-1]

    # Find non-white columns (horizontal)
    col_means = np.mean(pixels, axis=0)
    non_white_cols = np.where(col_means < 254)[0]
    if len(non_white_cols) == 0:
        first_col, last_col = 0, w - 1
    else:
        first_col = non_white_cols[0]
        last_col = non_white_cols[-1]

    top = max(0, first_row - margin)
    bottom = min(h, last_row + margin + 1)
    left = max(0, first_col - margin)
    right = min(w, last_col + margin + 1)

    return img.crop((left, top, right, bottom))


def image_to_raster(img, target_width=384) -> bytes:
    """Converts a PIL image to ESC/POS GS v 0 raster bytes."""
    # Resize keeping aspect ratio
    w, h = img.size
    scale = target_width / w
    new_h = int(h * scale)
    resized = img.resize((target_width, new_h), Image.Resampling.LANCZOS)

    # Convert to black and white
    bw = resized.convert('1')
    width_bytes = (target_width + 7) // 8

    # Build ESC/POS GS v 0 command
    raster = bytearray()
    raster += bytes([0x1D, 0x76, 0x30, 0x00])
    raster += bytes([width_bytes & 0xFF, (width_bytes >> 8) & 0xFF])
    raster += bytes([new_h & 0xFF, (new_h >> 8) & 0xFF])

    # Pack bits
    pixels = list(bw.getdata())
    for y in range(new_h):
        for bx in range(width_bytes):
            byte_val = 0
            for bit in range(8):
                x = bx * 8 + bit
                if x < target_width:
                    pixel = pixels[y * target_width + x]
                    if pixel == 0:  # 0 is black in binary mode
                        byte_val |= (0x80 >> bit)
            raster.append(byte_val)

    return bytes(raster)


def process_pdf(pdf_bytes) -> bytes:
    """Converts PDF pages into auto-cropped, auto-scaled ESC/POS raster stream."""
    if not fitz:
        print("Error: PyMuPDF (fitz) is not installed.")
        return b""

    stream = bytearray()
    stream += bytes([0x1B, 0x40])  # INIT printer

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page in doc:
            # Render page at 150 DPI
            pix = page.get_pixmap(dpi=150)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # Crop margins
            cropped = crop_whitespace(img)

            # Convert to ESC/POS raster
            raster = image_to_raster(cropped)
            stream += raster

        # Append company footer
        stream += build_footer()
    except Exception as e:
        print(f"Error processing PDF: {e}")

    return bytes(stream)


def send_to_device(data_bytes):
    """Routes ESC/POS stream to the configured target device."""
    config = get_config()
    conn_type = config.get("connection_type", "usb").lower()

    if conn_type == "usb":
        # Windows Direct spooler raw writing
        device_name = config.get("device_path", "ZJ-58")
        try:
            hPrinter = win32print.OpenPrinter(device_name)
            try:
                hJob = win32print.StartDocPrinter(hPrinter, 1, ("FFit Print Job", None, "RAW"))
                win32print.StartPagePrinter(hPrinter)
                win32print.WritePrinter(hPrinter, data_bytes)
                win32print.EndPagePrinter(hPrinter)
                win32print.EndDocPrinter(hPrinter)
                print(f"Sent job to USB printer: {device_name}")
            finally:
                win32print.ClosePrinter(hPrinter)
        except Exception as e:
            print(f"Error writing to USB printer '{device_name}': {e}")

    elif conn_type == "network":
        # Raw TCP connection
        ip = config.get("ip_address", "")
        port = int(config.get("port", 9100))
        if not ip:
            print("Error: Network printer IP is empty.")
            return
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect((ip, port))
            s.sendall(data_bytes)
            s.close()
            print(f"Sent job to network printer: {ip}:{port}")
        except Exception as e:
            print(f"Error writing to network printer: {e}")

    elif conn_type == "bluetooth":
        # COM Port stream
        com = config.get("com_port", "COM3")
        try:
            import serial
            ser = serial.Serial(com, 9600, timeout=5)
            ser.write(data_bytes)
            ser.close()
            print(f"Sent job to Bluetooth COM port: {com}")
        except Exception as e:
            print(f"Error writing to Bluetooth COM port '{com}': {e}")


def handle_client(conn, addr):
    """Processes incoming data stream from a print connection."""
    print(f"Connected by {addr}")
    job_data = bytearray()
    
    # Read raw print stream
    while True:
        data = conn.recv(8192)
        if not data:
            break
        job_data.extend(data)
    conn.close()

    if not job_data:
        return

    # Check for PDF header signature
    if job_data.startswith(b"%PDF-"):
        print("Detected PDF print stream. Processing vector pages...")
        processed_data = process_pdf(bytes(job_data))
    else:
        print("Detected raw ESC/POS stream. Appending footer and forwarding...")
        processed_data = bytes(job_data) + build_footer()

    send_to_device(processed_data)


def main():
    # Make sure appdata config folder exists
    os.makedirs(CONFIG_DIR, exist_ok=True)

    print(f"Starting FFit Windows print server on {BIND_IP}:{PORT}...")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        s.bind((BIND_IP, PORT))
        s.listen(5)
    except Exception as e:
        print(f"Failed to bind to {BIND_IP}:{PORT}. Is another print server running? Error: {e}")
        sys.exit(1)

    while True:
        try:
            conn, addr = s.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr))
            t.daemon = True
            t.start()
        except KeyboardInterrupt:
            print("\nShutting down print server.")
            break
        except Exception as e:
            print(f"Socket accept error: {e}")


if __name__ == "__main__":
    main()
