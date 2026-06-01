# Skill Log: Receipt Margin Cropping & Scaling (Preventing Tiny Text)

This document details the algorithm and logic developed to resolve the "tiny text / side-space" issue when printing from Google Chrome and system applications to 58mm thermal printers.

---

## 🔍 The Root Cause
When printing from Google Chrome, the print engine often treats the receipt as a standard A4 page or adds thick default margins. 
* **The Problem**: A 58mm thermal receipt is rendered in the middle of a wide A4 canvas. When scaled down directly to 58mm, the content becomes tiny, unreadable, and surrounded by large white spaces.
* **The Solution**: Detect where the receipt content actually is, strip the surrounding white margins, and scale the remaining contents to fill the entire 384px print width.

---

## 🛠️ The Standard Deviation Cropping Algorithm

To crop margins dynamically without hardcoding values, we inspect pixel density across columns (horizontal) and rows (vertical).

```python
import numpy as np
from PIL import Image

def crop_whitespace(image_path_or_obj, margin=8):
    # 1. Load image and convert to grayscale
    img = Image.open(image_path_or_obj).convert('L')
    pixels = np.array(img)
    h, w = pixels.shape

    # 2. Find vertical margins (top & bottom rows)
    # Check which rows contain non-white pixels (luminance < 250)
    row_means = np.mean(pixels, axis=1)
    non_white_rows = np.where(row_means < 254)[0]
    
    if len(non_white_rows) == 0:
        return img # Empty image
        
    first_row = non_white_rows[0]
    last_row = non_white_rows[-1]

    # 3. Find horizontal margins (left & right columns)
    # Check which columns contain non-white pixels (luminance < 250)
    col_means = np.mean(pixels, axis=0)
    non_white_cols = np.where(col_means < 254)[0]
    
    if len(non_white_cols) == 0:
        first_col, last_col = 0, w - 1
    else:
        first_col = non_white_cols[0]
        last_col = non_white_cols[-1]

    # 4. Apply safety margins
    top    = max(0, first_row - margin)
    bottom = min(h, last_row + margin + 1)
    left   = max(0, first_col - margin)
    right  = min(w, last_col + margin + 1)

    # 5. Crop and return
    return img.crop((left, top, right, bottom))
```

---

## 📈 Auto-Zoom & Scaling to 58mm

Once the margins are cropped, we scale the image to the exact print width:
* **Target Width**: **`384px`** (standard printable width of 58mm thermal heads).
* **Maintain Aspect Ratio**: Resize height proportionally.
* **Esc/POS Format**: Convert to `GS v 0` raster data using direct bit-packing (8 pixels per byte).

This ensures the receipt stretches fully across the 58mm paper, resulting in maximum font size and clarity.
