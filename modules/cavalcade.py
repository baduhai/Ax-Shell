import os
import struct
import threading
import subprocess
import re
import ctypes
import signal

from gi.repository import GLib, Gtk, Gdk
from loguru import logger
from math import pi

from fabric.widgets.overlay import Overlay

import configparser

def get_bars(file_path):
    config = configparser.ConfigParser()
    config.read(file_path)
    return int(config['general']['bars'])

CAVA_CONFIG = os.path.expanduser("~/.config/Ax-Shell/config/cavalcade/cava.ini")

bars = get_bars(CAVA_CONFIG)

def set_death_signal():
    """
    Set the death signal of the child process to SIGTERM so that if the parent
    process is killed, the child (cava) is automatically terminated.
    """
    libc = ctypes.CDLL("libc.so.6")
    PR_SET_PDEATHSIG = 1
    libc.prctl(PR_SET_PDEATHSIG, signal.SIGTERM)

class Cava:
    """
    CAVA wrapper.
    Launch cava process with certain settings and read output.
    """
    NONE = 0
    RUNNING = 1
    RESTARTING = 2
    CLOSING = 3

    def __init__(self, mainapp):
        self.bars = bars
        self.path = "/tmp/cava.fifo"

        self.cava_config_file = os.path.expanduser("~/.config/Ax-Shell/config/cavalcade/cava.ini")
        self.data_handler = mainapp.draw.update
        self.command = ["cava", "-p", self.cava_config_file]
        self.state = self.NONE

        self.env = dict(os.environ)
        self.env["LC_ALL"] = "en_US.UTF-8"  # not sure if it's necessary

        is_16bit = True
        self.byte_type, self.byte_size, self.byte_norm = ("H", 2, 65535) if is_16bit else ("B", 1, 255)

        if not os.path.exists(self.path):
            os.mkfifo(self.path)

    def _run_process(self):
        logger.debug("Launching cava process...")
        try:
            self.process = subprocess.Popen(
                self.command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=self.env,
                preexec_fn=set_death_signal  # Ensure cava gets killed when the parent dies.
            )
            logger.debug("cava successfully launched!")
            self.state = self.RUNNING
        except Exception:
            logger.exception("Fail to launch cava")

    def _start_reader_thread(self):
        logger.debug("Activate cava stream handler")
        self.thread = threading.Thread(target=self._read_output)
        self.thread.daemon = True
        self.thread.start()

    def _read_output(self):
        fifo = open(self.path, "rb")
        chunk = self.byte_size * self.bars  # number of bytes for given format
        fmt = self.byte_type * self.bars  # pack of given format
        while True:
            data = fifo.read(chunk)
            if len(data) < chunk:
                break
            sample = [i / self.byte_norm for i in struct.unpack(fmt, data)]
            GLib.idle_add(self.data_handler, sample)
        fifo.close()
        GLib.idle_add(self._on_stop)

    def _on_stop(self):
        logger.debug("Cava stream handler deactivated")
        if self.state == self.RESTARTING:
            if not self.thread.isAlive():
                self.start()
            else:
                logger.error("Can't restart cava, old handler still alive")
        elif self.state == self.RUNNING:
            self.state = self.NONE
            logger.error("Cava process was unexpectedly terminated.")
            # self.restart()  # May cause infinity loop, need more check

    def start(self):
        """Launch cava"""
        self._start_reader_thread()
        self._run_process()

    def restart(self):
        """Restart cava process"""
        if self.state == self.RUNNING:
            logger.debug("Restarting cava process (normal mode) ...")
            self.state = self.RESTARTING
            if self.process.poll() is None:
                self.process.kill()
        elif self.state == self.NONE:
            logger.warning("Restarting cava process (after crash) ...")
            self.start()

    def close(self):
        """Stop cava process"""
        self.state = self.CLOSING
        if self.process.poll() is None:
            self.process.kill()
        os.remove(self.path)

class AttributeDict(dict):
    """Dictionary with keys as attributes. Does nothing but easy reading"""
    def __getattr__(self, attr):
        return self.get(attr,3)

    def __setattr__(self, attr, value):
        self[attr] = value

class Spectrum:
    """Spectrum drawing"""
    def __init__(self):
        self.silence_value = 0
        self.audio_sample = []
        self.color = None

        self.area = Gtk.DrawingArea()
        self.area.connect("draw", self.redraw)
        self.area.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)

        self.sizes = AttributeDict()
        self.sizes.area = AttributeDict()
        self.sizes.bar = AttributeDict()

        self.silence = 10
        self.max_height = 12

        self.area.connect("configure-event", self.size_update)
        self.color_update()

    def is_silence(self, value):
        """Check if volume level critically low during last iterations"""
        self.silence_value = 0 if value > 0 else self.silence_value + 1
        return self.silence_value > self.silence

    def update(self, data):
        """Audio data processing"""
        self.color_update()
        self.audio_sample = data
        if not self.is_silence(self.audio_sample[0]):
            self.area.queue_draw()
        elif self.silence_value == (self.silence + 1):
            self.audio_sample = [0] * self.sizes.number
            self.area.queue_draw()

    # noinspection PyUnusedLocal
    def redraw(self, widget, cr):
        """Draw spectrum graph"""
        cr.set_source_rgba(*self.color)
        # cr.set_source_rgba(170/255, 170/255, 1, 1)

        dx = 3

        center_y = self.sizes.area.height / 2  # Centro vertical del área de dibujo
        for i, value in enumerate(self.audio_sample):

            # width = self.sizes.bar.width + int(i < self.sizes.wcpi)
            width = self.sizes.area.width / self.sizes.number - self.sizes.padding
            radius = width / 2
            height = max(self.sizes.bar.height * min(value, 1), self.sizes.zero) / 2
            if height == self.sizes.zero / 2 + 1:
                height *= 0.5

            height = min(height, self.max_height)

            # Dibujar rectángulo
            cr.rectangle(dx, center_y - height, width, height * 2)
            cr.arc(dx + radius, center_y - height, radius, 0, 2 * pi)
            cr.arc(dx + radius, center_y + height, radius, 0, 2 * pi)

            cr.close_path()
            # cr.rectangle(0, center_y, self.sizes.area.width, 20)

            dx += width + self.sizes.padding
        cr.fill()

    # noinspection PyUnusedLocal
    def size_update(self, *args):
        """Update drawing geometry"""
        self.sizes.number = bars
        self.sizes.padding = 2.5
        self.sizes.zero = 0

        self.sizes.area.width = self.area.get_allocated_width()
        self.sizes.area.height = self.area.get_allocated_height() - 2

        tw = self.sizes.area.width - self.sizes.padding * (self.sizes.number - 1)
        self.sizes.bar.width = max(int(tw / self.sizes.number), 1)
        self.sizes.bar.height = self.sizes.area.height
        # self.sizes.wcpi = tw % self.sizes.number  # width correction point index

    def color_update(self):
        """Set drawing color according current settings by reading primary color from CSS"""
        color = "#a5c8ff"  # default value
        try:
            with open(os.path.expanduser("~/.config/Ax-Shell/styles/colors.css"), "r") as f:
                content = f.read()
                m = re.search(r"--primary:\s*(#[0-9a-fA-F]{6})", content)
                if m:
                    color = m.group(1)
        except Exception as e:
            logger.error("Failed to read primary color: {}".format(e))
        red = int(color[1:3], 16) / 255
        green = int(color[3:5], 16) / 255
        blue = int(color[5:7], 16) / 255
        self.color = Gdk.RGBA(red=red, green=green, blue=blue, alpha=1.0)

class SpectrumRender():
    def __init__(self, mode=None, **kwargs):
        super().__init__(**kwargs)
        self.mode = mode

        self.draw = Spectrum()
        self.cava = Cava(self)
        self.cava.start()

    def get_spectrum_box(self):
        # Get the spectrum box
        box = Overlay(name="cavalcade", h_align='center', v_align='center')
        box.set_size_request(180, 40)
        box.add_overlay(self.draw.area)
        return box

