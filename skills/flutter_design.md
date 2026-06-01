# Skill Log: Premium UI Design & Layout Constraints

This document logs the design system, typography, and constraints implemented in the **FFit Printer** Flutter application.

---

## 🎨 Premium Design System

The application layout uses rich aesthetics to create a state-of-the-art impression:

* **Theme & Colors**:
  - Dark Mode background using curated deep slates and blues (`0xFF0B0F19`, `0xFF111827`).
  - Sleek teal and cyan accent colors (`0xFF0EA5E9`, `0xFF06B6D4`) instead of standard default blues.
  - Harmonies built using precise HSL-based values.
* **Glassmorphism**:
  - Cards and containers use semi-transparent white/gray overlays (`Colors.white.withOpacity(0.05)`).
  - Subtle borders with thin light outlines (`Colors.white.withOpacity(0.1)`).
  - Background blurs (`BackdropFilter` with `ImageFilter.blur(sigmaX: 10, sigmaY: 10)`) to create depth.
* **Typography**:
  - Use of modern Google Fonts (`Outfit` or `Inter`) for headers and receipts.
  - Bold accents for primary info, keeping regular text highly readable on dark backdrops.

---

## 📐 Layout Constraints (Locked to 58mm)

To ensure the driver remains highly robust and avoids sizing issues:
* **All 80mm / other size options are strictly removed** from the UI.
* The model returns a hardcoded **384px** width and **58mm** paper size configurations.
* This eliminates user configuration errors and guarantees that the rasterizer always outputs 384px images.

---

## 🧩 Reusable Flutter Widgets

* **`StepCard`**: Card for step-by-step installation instructions.
* **`StatusBadge`**: Animated status indicator showing connection states (Connecting, Connected, Disconnected).
* **`ActionButton`**: A sleek glassmorphic button with micro-animations and hover transitions.
* **`PrinterTile`**: Displays printer info with customized icons depending on connection channel (USB, Bluetooth, Network).
