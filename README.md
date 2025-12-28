# Pibooth Libcamera Plugin (Pi 5 Support)

This plugin enables the **Raspberry Pi 5 Camera** to work with [Pibooth](https://github.com/pibooth/pibooth) on Debian Bookworm/Trixie.

## Features
* **Smooth 30fps Video Preview** (using `rpicam-vid`)
* **High-Res Capture** (using `rpicam-still`)
* **Instant Preview:** Pre-warms the camera during menu selection to eliminate black screens.
* **Compatibility Fixes:** Solves Wayland and Pillow 10+ (Python 3.11/3.13) crashing issues.

## Requirements
* Raspberry Pi 5
* Raspberry Pi OS Bookworm or Trixie (Tested on Trixie)
* Python 3.11+
* Pibooth >= 2.0.0
* `rpicam-apps` (libcamera)

## Installation

1. **Install system dependencies:**
   ```bash
   sudo apt install rpicam-apps
   ```  

2. **Install the plugin:**
   ```bash
   pip install git+https://github.com/steveharris87/pibooth-libcamera-pi5
   ```
   Restart Pibooth: The plugin is auto-discovered. No config changes needed.

## Notes
Pi 5 Only: This uses the specific hardware video encoders on the Pi 5. It will not work on Pi 3/4.

Wayland Native: Tested under Wayland—no X11 hacks required.

Pre-warming: The camera starts silently while users are choosing their "Number of Photos," ensuring the preview appears instantly.

## License
This plugin is released under the MIT License.
