# -*- coding: utf-8 -*-
"""
Pibooth Plugin: Libcamera CLI Wrapper for Raspberry Pi 5
Target OS: Debian 12 (Bookworm/Trixie) with Wayland
Features: 
  - Dynamic Preview Sizing (Matches capture aspect ratio)
  - Pre-warming (Starts camera during menu selection for instant preview)
  - Pillow 10+ Compatibility
"""

import time
import subprocess
import os
import signal
import io
import threading
import pygame
from PIL import Image, ImageFont, ImageDraw

# Pibooth imports
from pibooth.utils import PoolingTimer, LOGGER
from pibooth.language import get_translated_text
from pibooth.camera.base import BaseCamera
from pibooth.pictures import sizing
import pibooth

__version__ = "5.7.0-PREWARM"

# --- CONSTANTS ---
TARGET_PREVIEW_WIDTH = 720 
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


# --- PILLOW 10+ COMPATIBILITY PATCHES ---
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS

if not hasattr(ImageFont.FreeTypeFont, 'getsize'):
    def getsize(self, text):
        left, top, right, bottom = self.getbbox(text)
        return (right - left), (bottom - top)
    ImageFont.FreeTypeFont.getsize = getsize

if not hasattr(ImageDraw.ImageDraw, 'textsize'):
    def textsize(self, text, font=None, *args, **kwargs):
        if font is None: font = ImageFont.load_default()
        return font.getsize(text)
    ImageDraw.ImageDraw.textsize = textsize
# --------------------------------------


class LibcameraRpiCamera(BaseCamera):
    def __init__(self, camera_proxy=None):
        super(LibcameraRpiCamera, self).__init__(camera_proxy)
        self._preview_process = None
        self._overlay_text = None
        self._window = None
        self.preview_flip = False
        
        self.running = False
        self.latest_frame_bytes = None
        self.reader_thread = None
        
        self.preview_width = 640
        self.preview_height = 480

        try:
            self.font = ImageFont.truetype(FONT_PATH, 100)
        except IOError:
            self.font = ImageFont.load_default()

    def _specific_initialization(self):
        """Calculate the correct preview aspect ratio."""
        if self.resolution:
            rw, rh = self.resolution
            ratio = rw / rh
            self.preview_width = TARGET_PREVIEW_WIDTH
            self.preview_height = int(TARGET_PREVIEW_WIDTH / ratio)
            if self.preview_height % 2 != 0:
                self.preview_height += 1
            LOGGER.info(f"Config: {rw}x{rh}. Preview: {self.preview_width}x{self.preview_height}")

    def _read_video_stream(self):
        """Reads MJPEG stream from rpicam-vid."""
        cmd = ["rpicam-vid", "-t", "0", "--codec", "mjpeg", "-n", 
               "--width", str(self.preview_width), 
               "--height", str(self.preview_height), 
               "--framerate", "30", 
               "--inline", "-o", "-"]

        LOGGER.info(f"Starting preview: {' '.join(cmd)}")
        
        try:
            self._preview_process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0
            )
            
            buffer = b""
            while self.running:
                chunk = self._preview_process.stdout.read(32768)
                if not chunk: break
                buffer += chunk
                
                while True:
                    a = buffer.find(b'\xff\xd8')
                    b = buffer.find(b'\xff\xd9')
                    
                    if a != -1 and b != -1:
                        if a < b:
                            self.latest_frame_bytes = buffer[a:b+2]
                            buffer = buffer[b+2:]
                        else:
                            buffer = buffer[a:]
                    else:
                        break
                        
                if len(buffer) > 500000: buffer = b""
                    
        except Exception as e:
            LOGGER.error(f"Preview stream crashed: {e}")
        finally:
            self.running = False

    def _start_preview_process(self):
        if self.running: return
        self.running = True
        self.reader_thread = threading.Thread(target=self._read_video_stream, daemon=True)
        self.reader_thread.start()

    def _stop_preview_process(self):
        self.running = False
        if self._preview_process:
            LOGGER.info("Stopping preview...")
            try:
                self._preview_process.terminate()
                self._preview_process.wait(timeout=0.5)
            except:
                try: os.kill(self._preview_process.pid, signal.SIGKILL)
                except: pass
            self._preview_process = None

    def _get_preview_image(self):
        if self.latest_frame_bytes:
            try:
                image_stream = io.BytesIO(self.latest_frame_bytes)
                image = Image.open(image_stream)
                
                if self.preview_flip:
                    image = image.transpose(Image.FLIP_LEFT_RIGHT)

                if self._overlay_text:
                    draw = ImageDraw.Draw(image)
                    try:
                        left, top, right, bottom = self.font.getbbox(self._overlay_text)
                        text_w, text_h = right - left, bottom - top
                    except:
                        text_w, text_h = draw.textsize(self._overlay_text, font=self.font)

                    w, h = image.size
                    x, y = (w - text_w) / 2, (h - text_h) / 2
                    
                    draw.text((x+4, y+4), self._overlay_text, font=self.font, fill=(0,0,0))
                    draw.text((x, y), self._overlay_text, font=self.font, fill=(255,255,255))
                
                return image
            except Exception:
                pass
        
        return Image.new('RGB', (self.preview_width, self.preview_height), (0, 0, 0))

    def _post_process_capture(self, capture_data):
        image = Image.open(capture_data)
        if self.resolution:
            width, height = image.size
            cropped = sizing.new_size_by_croping_ratio((width, height), self.resolution)
            image = image.crop(cropped)
            image = image.resize(self.resolution, Image.ANTIALIAS)
        if self.capture_flip:
            image = image.transpose(Image.FLIP_LEFT_RIGHT)
        return image

    def preview(self, window, flip=True):
        self._window = window
        self.preview_flip = flip
        self._start_preview_process()
        self._window.show_image(self._get_preview_image())

    def preview_countdown(self, timeout, alpha=80):
        timeout = int(timeout)
        timer = PoolingTimer(timeout)
        while not timer.is_timeout():
            remaining = int(timer.remaining() + 1)
            if self._overlay_text != str(remaining):
                self._overlay_text = str(remaining)

            updated_rect = self._window.show_image(self._get_preview_image())
            pygame.event.pump()
            if updated_rect: pygame.display.update(updated_rect)

        self._overlay_text = get_translated_text('smile')
        self._window.show_image(self._get_preview_image())
        pygame.event.pump()
        pygame.display.flip()

    def preview_wait(self, timeout, alpha=80):
        timer = PoolingTimer(timeout)
        while not timer.is_timeout():
            updated_rect = self._window.show_image(self._get_preview_image())
            pygame.event.pump()
            if updated_rect: pygame.display.update(updated_rect)

    def stop_preview(self):
        self._overlay_text = None
        self._stop_preview_process()
        self._window = None

    def capture(self, effect=None):
        self._stop_preview_process()
        time.sleep(0.05) 

        target = getattr(self, 'last_picture_file', os.path.join(os.getcwd(), f"cap_{int(time.time())}.jpg"))
        cmd = ["rpicam-still", "-o", str(target), "-n", "-t", "1", "--immediate",
               "--width", str(self.resolution[0]), "--height", str(self.resolution[1])]
        
        try:
            subprocess.run(cmd, check=True)
            with open(target, 'rb') as f:
                data = io.BytesIO(f.read())
                data.seek(0)
                self._captures.append(data) 
        except Exception as e:
            LOGGER.error(f"Capture failed: {e}")
            img = Image.new('RGB', self.resolution, (0, 0, 0))
            buf = io.BytesIO()
            img.save(buf, format='JPEG')
            buf.seek(0)
            self._captures.append(buf)

        self._overlay_text = None

    def quit(self):
        self._stop_preview_process()
    
    def __del__(self):
        self._stop_preview_process()

# --- HOOKS ---
@pibooth.hookimpl
def pibooth_setup_camera(cfg):
    return LibcameraRpiCamera()

@pibooth.hookimpl
def pibooth_cleanup(app):
    if hasattr(app.camera, 'quit'):
        app.camera.quit()

@pibooth.hookimpl
def state_chosen_enter(app):
    # Pre-warm the camera while the "Chosen" screen is displayed
    LOGGER.info("Pre-warming camera...")
    app.camera._start_preview_process()