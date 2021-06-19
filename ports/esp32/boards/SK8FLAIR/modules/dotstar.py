# ===================================================================================================
#          Name: dotstar.py 
#        Author: Myron W Walker
#   Description: Can be used with the WiPy and micropython to drive the DotStar LEDS.
# 
#    Copyright
# ====================================================================================================

import micropython
import sys
import time

micropython.alloc_emergency_exception_buf(2048)

from machine import Pin, SPI

DARK_BUFFER = b"\xff\x00\x00\x00"
BLUE_BUFFER = b"\xff\xff\x00\x00"
GRN_BUFFER = b"\xff\x00\xff\x00"
RED_BUFFER = b"\xff\x00\x00\xff"
WHT_BUFFER = b"\xff\xff\xff\xff"

CLOCK_PIN = 14
DATA_OUT_PIN = 13
DATA_IN_PIN = 12

BRIGHTNESS_MIN = 0
BRIGHTNESS_MAX = 31
BRIGHTNESS_MID = 15
BRIGHTNESS_MODULO = 32

COLOR_MIN = 0
COLOR_MAX = 255
COLOR_MODULO = 256

DEGREES_MODULO = 360
DEGREES_THIRD = 120

PIXEL_LEADER = 0b11100000

SHADE_MIN = 0
SHADE_MAX = 255
SHADE_MODULO = 256


class DotStarDevice:
    """
        The strip expects the colors to be sent in BGR order.  They are sent in a buffer
        with as a set of 4 bytes per pixel ( 0xFF/B/G/R )
    """
    LED_START = 0b11100000  # Three "1" bits, followed by 5 brightness bits

    START_FRAME = [0x00, 0x00, 0x00, 0x00]

    def __init__(self, led_count, data_pin=DATA_OUT_PIN, clock_pin=CLOCK_PIN, data_in_unused=DATA_IN_PIN, baudrate=80000000):
        self._data_pin = Pin(data_pin, mode=Pin.OUT)
        self._clock_pin = Pin(clock_pin, mode=Pin.OUT)
        self._unused_pin = Pin(data_in_unused, mode=Pin.IN)

        self._buss = SPI(1, 10000000, sck=self._clock_pin, mosi=self._data_pin, miso=self._unused_pin)
        
        self._led_count = led_count

        
        self._start_frame = [0x00, 0x00, 0x00, 0x00]
        self._start_frame_index = 0
    
        self._data_frame_off = [0xFF, 0x00, 0x00, 0x00] * led_count
        self._flush_frame = [0xFF, 0xFF, 0xFF, 0xFF] * led_count

        self._render_buffer = bytearray(self._start_frame + self._data_frame_off + self._flush_frame)
        
        self._led_buffer_len = (self._led_count * 4)
        self._data_frame_index = 4
        self._data_frame_stop = self._data_frame_index + self._led_buffer_len

        return

    def fill_direction(self, degrees, shade=SHADE_MAX, brightness=BRIGHTNESS_MID):
        degrees = degrees % DEGREES_MODULO

        red = 0
        green = 0
        blue = 0

        pct_fr = float(degrees % DEGREES_THIRD) / float(DEGREES_THIRD)
        inv_fr = 1 - pct_fr

        if degrees > 240:
            blue = int(COLOR_MAX * inv_fr)
            red = int(COLOR_MAX * pct_fr)
        elif degrees == 240:
            blue = COLOR_MAX
        elif degrees > 120:
            green = int(COLOR_MAX * inv_fr)
            blue = int(COLOR_MAX * pct_fr)
        elif degrees == 120:
            green = COLOR_MAX
        elif degrees > 0:
            red = int(COLOR_MAX * inv_fr)
            green = int(COLOR_MAX * pct_fr)
        else:
            red = COLOR_MAX

        self.fill_color(red, green, blue, brightness=brightness)

        return

    def fill_color(self, red, green, blue, brightness=BRIGHTNESS_MID):

        red = red % COLOR_MODULO
        green = green % COLOR_MODULO
        blue = blue % COLOR_MODULO
        brightness = brightness % BRIGHTNESS_MODULO

        pixel_bytes = bytes((PIXEL_LEADER | brightness, blue, green, red))

        self._fill_render_buffer(pixel_bytes)

        self.update()

        return

    def push_buffer(self, buffer):

        self._fill_render_buffer(buffer)

        self.update()

        return

    def update(self):
        self._buss.write(self._render_buffer)
        return

    def _fill_render_buffer(self, src_pixel_buffer):
    	srclen = len(src_pixel_buffer)
        sindex = 0
        for pindex in range(self._data_frame_index, self._data_frame_stop):
            self._render_buffer[pindex] = src_pixel_buffer[sindex % srclen]
            sindex += 1
        return


def run_patterns():

    from bmx055 import BMX055

    imu = BMX055()
    imu.init()

    ds = DotStarDevice(14)

    ds.push_buffer(DARK_BUFFER)
    time.sleep(1)
    ds.push_buffer(WHT_BUFFER)
    time.sleep(1)
    ds.push_buffer(BLUE_BUFFER)
    time.sleep(1)
    ds.push_buffer(RED_BUFFER)
    time.sleep(1)
    ds.push_buffer(GRN_BUFFER)
    time.sleep(1)

    while True:
        try:
            while(True):
                direction = imu.mag_read_heading()
                ds.fill_direction(direction)
                time.sleep(.005)

        except Exception as e:
            sys.print_exception(e)
