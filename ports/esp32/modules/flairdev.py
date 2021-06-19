
import json
import machine
import os
import sys
import time
import uos
import _thread

from ble_flair import BLE_FLair
from configuration import BLUETOOTH_DEVICE_NAME

import bmx055
import dotstar
import filesystem
import wifi

FILE_SETTINGS = "flair-settings.json"

VALID_FLAIR_MODES = ["ambient", "compass", "rainbow"]
VALID_WIFI_MODES = ["ap", "client"]


UUID_RULER_64            = b"   1   2   3   4   5   6   7   8   9   0   1   2   3   4   5   6"
DEVICE_MAIN_SERVICE_UUID = b"\x88\x88\x88\x88\x88\x88\x88\x88\x88\x88\x88\x88\x88\x88\x88\x88"

CONTROL_SERVICE_UUID     = b"\x00\x00\x00\x00\x00\x00\x8c\xc8\x8c\xc8\x8c\xc8\x8c\xc8\x8c\xc8"

DEVICETYPE_UUID          = b"\x11\x11\x11\x11\x11\x11\x00\x00\x8c\xc8\x8c\xc8\x8c\xc8\x8c\xc8"

FLAIR_MODE_IO_UUID       = b"\x22\x22\x22\x22\x22\x22\x00\x00\x8c\xc8\x8c\xc8\x8c\xc8\x8c\xc8"
WIFI_MODE_IO_UUID        = b"\x33\x33\x33\x33\x33\x33\x00\x00\x8c\xc8\x8c\xc8\x8c\xc8\x8c\xc8"

CONTROL_IO_READ_UUID     = b"\x44\x44\x44\x44\x44\x44\x00\x00\x8c\xc8\x8c\xc8\x8c\xc8\x8c\xc8"
CONTROL_IO_WRITE_UUID    = b"\x55\x55\x55\x55\x55\x55\x00\x00\x8c\xc8\x8c\xc8\x8c\xc8\x8c\xc8"

UUID_RULER_16            = b"1234"

TOKEN_START_OF_MESSAGE = b"----BEGIN----"
TOKEN_END_OF_MESSAGE   = b"----END----"
TOKEN_RESET_OF_MESSAGE = b"----RESET----"

DEFAULT_FLAIR_SETTINGS = {
    "flair" : {
        "mode" : "compass",
        "settings": {
            "ambient": {
                "red": 255,
                "green": 0,
                "blue": 255,
                "intensity": dotstar.BRIGHTNESS_MID
            },
            "compass": {
                "intensity": dotstar.BRIGHTNESS_MID
            },
            "rainbow": {
                "intensity": dotstar.BRIGHTNESS_MID
            }
        }
    }
}

ble_device = None
ble_control_svc = None

dotstar_device = None

flair_settings = None

wifi_mode = None

proto_inbound = []
proto_outbound = []

navigation = None

render_mode_name = None
active_render_mode_name = None


def bytes_cast(in_obj):
    if type(in_obj) == str:
        out_bytes = in_obj.encode('utf-8')
        return out_bytes
    return in_obj

def str_cast(in_obj):
    out_str = None
    if type(in_obj) == bytes:
        out_str = in_obj.decode('utf-8')
    else:
        out_str = str(in_obj)
    return out_str

def process_packet(pack_in):
    global flair_settings

    pack_out = None

    what = pack_in["what"]
    if what == "hello":
        pack_out = { 'success': True, 'message': 'Waah Wah Waaaah' }
    elif what == 'get_flair':
        if "flair" in flair_settings:
            pack_out = { 'success': True, 'settings': flair_settings["flair"]}
        else:
            pack_out = { 'success': False, 'message': 'Unable to get flair settings.' }
    elif what == 'get_wifi':
        if "wifi" in flair_settings:
            pack_out = { 'success': True, 'settings': flair_settings["wifi"]}
        else:
            pack_out = { 'success': False, 'message': 'Unable to get wifi settings.' }
    elif what == 'reset':
        pass
    elif what == 'set_flair':
        new_settings = pack_in["settings"]
        flair_settings["flair"] = new_settings
        settings_save()
    elif what == 'set_wifi':
        new_settings = pack_in["settings"]
        flair_settings["wifi"] = new_settings
        settings_save()
    else:
        err_msg = "Unknown packet what=%r" % what
        print (err_msg)
        pack_out = { 'success': False, 'message': err_msg }

    return pack_out

def process_message(flairsvc):

    msg_in = flairsvc.read()

    print(b"Processing Message:\n%s" % msg_in)

    parts_out = []
    try:
        pack_in = json.loads(msg_in)
        pack_out = process_packet(pack_in)

        msg_out = bytes_cast(json.dumps(pack_out))

        flairsvc.write(msg_out)

    except Exception as xcpt:
        err_msg = str(xcpt)
        print(err_msg)

    return

def set_render_mode(mode):
    global render_mode_name
    global active_render_mode_name

    flair_settings["mode"] = mode
    settings_save()
    render_mode_name = mode
    return

def settings_load():
    global render_mode_name
    global flair_settings

    if flair_settings is None:
        if filesystem.exists(FILE_SETTINGS):
            with open(FILE_SETTINGS, 'r') as sf:
                flair_settings = json.load(sf)
        else:
            flair_settings = DEFAULT_FLAIR_SETTINGS
            settings_save()

    render_mode_name = flair_settings["flair"]["mode"]

    return

def settings_save():
    global flair_settings

    if flair_settings is not None:
        settings_content = json.dumps(flair_settings)
        with open(FILE_SETTINGS, 'w') as sf:
            sf.write(settings_content)

    return

flairsvc = None

def initialize():

    global BLUETOOTH_DEVICE_NAME

    global dotstar_device
    global flair_settings
    global render_mode_name
    global wifi_mode
    global navigation

    global flairsvc

    # Initialize the DotStar first so we can use it to indicate
    # the status of the boot process.
    dotstar_device = dotstar.DotStarDevice(14)

    dotstar_device.push_buffer(dotstar.DARK_BUFFER)

    navigation = bmx055.BMX055()
    navigation.init()
    time.sleep(.5)

    dotstar_device.push_buffer(dotstar.RED_BUFFER)

    settings_load()
    time.sleep(.5)

    dotstar_device.push_buffer(dotstar.WHT_BUFFER)
    
    wifi.initialize()

    render_mode_name = flair_settings["flair"]["mode"]
    time.sleep(.5)

    dotstar_device.push_buffer(dotstar.BLUE_BUFFER)
    flairsvc = BLE_FLair(BLUETOOTH_DEVICE_NAME)
    flairsvc.set_receive_callback(process_message)

    time.sleep(.5)

    dotstar_device.push_buffer(dotstar.GRN_BUFFER)

    time.sleep(.5)
    return

def load_render_mode_settings(mode):
    print("loading flair settings")

    if mode not in flair_settings["flair"]["settings"]:
        flair_settings["flair"]["settings"][mode] = DEFAULT_FLAIR_SETTINGS["flair"]["settings"][mode]
        settings_save()

    settings = flair_settings["flair"]["settings"][mode]

    return settings


FALL_THRESHOLD = 40

class RenderOverride:
    NONE = 0
    FALL = 1

class RenderModeOverrides:
    def __init__(self):
        self._override = RenderOverride.NONE
        self._fall_detect_begin = None
        self._fall_detect_last = None
        self._up_detected_begin = None
        self._fall_color_state = 0
        return

    def check_for_override(self):
        _, _, mag_z, _ = navigation.mag_read_axis_data()

        now = time.time()
        if self._override == RenderOverride.NONE:
            if self._fall_detect_begin is None:
                if mag_z > FALL_THRESHOLD:
                    self._fall_detect_begin = now
            else:
                self._fall_detect_last = now
                if mag_z > FALL_THRESHOLD:
                    if (self._fall_detect_last - self._fall_detect_begin) > 4:
                        self._override = RenderOverride.FALL
                else:
                    self._override = RenderOverride.NONE
                    self._fall_detect_begin = None
                    self._fall_detect_last = None
                    self._up_detected_begin = None
        elif self._override == RenderOverride.FALL:
            if self._fall_detect_last is None:
                self._fall_detect_last = now
            else:
                if mag_z < FALL_THRESHOLD:
                    if self._up_detected_begin is None:
                        self._up_detected_begin = now
                    elif (now - self._up_detected_begin) > 2:
                        self._override = RenderOverride.NONE
                        self._fall_detect_begin = None
                        self._fall_detect_last = None
                        self._up_detected_begin = None
                elif mag_z > FALL_THRESHOLD:
                    self._fall_detect_last = now
                    self._up_detected_begin = None
        else:
            self._override = RenderOverride.NONE
            self._fall_detect_begin = None
            self._fall_detect_last = None
            self._up_detected_begin = None

        return self._override

    def pulse(self):

        if self._override == RenderOverride.FALL:
            if (self._fall_color_state % 20) == 0:
                dotstar_device.push_buffer(dotstar.WHT_BUFFER)
            elif (self._fall_color_state % 20) == 10:
                dotstar_device.push_buffer(dotstar.RED_BUFFER)
            self._fall_color_state = (self._fall_color_state + 1) % 20

        return

class RenderModeAmbient(RenderModeOverrides):
    def __init__(self):
        RenderModeOverrides.__init__(self)
        settings = load_render_mode_settings("ambient")
        self.red = settings["red"]
        self.green = settings["green"]
        self.blue = settings["blue"]
        self.intensity = settings["intensity"]
        self.delay = .1
        return

    def pulse(self):
        global dotstar_device

        if self.check_for_override() == RenderOverride.NONE:
            dotstar_device.fill_color(self.red, self.green, self.blue, self.intensity)
        else:
            RenderModeOverrides.pulse(self)

        return

class RenderModeCompass(RenderModeOverrides):
    def __init__(self):
        RenderModeOverrides.__init__(self)
        settings = load_render_mode_settings("compass")
        self.direction = int(navigation.mag_read_heading())
        self.intensity = settings["intensity"]
        self.delay = .1
        return

    def pulse(self):
        global dotstar_device
        global navigation

        if self.check_for_override() == RenderOverride.NONE:
            self.direction = int(navigation.mag_read_heading(cache=True))
            dotstar_device.fill_direction(self.direction)
        else:
            RenderModeOverrides.pulse(self)

        return

class RenderModeRainbow(RenderModeOverrides):
    def __init__(self):
        RenderModeOverrides.__init__(self)
        settings = load_render_mode_settings("rainbow")
        self.direction = 0
        self.intensity = settings["intensity"]
        self.delay = .1
        return

    def pulse(self):
        global dotstar_device

        if self.check_for_override() == RenderOverride.NONE:
            dotstar_device.fill_direction(self.direction)
            self.direction = (self.direction + 1) % 360
        else:
            RenderModeOverrides.pulse(self)

        return

mode_to_state_lookup = {
    "ambient": RenderModeAmbient,
    "compass": RenderModeCompass,
    "rainbow": RenderModeRainbow
}


render_timer = None

renderer = None
render_pulse_delay = .05

render_show_pulse_count = 5

def render_loop():
    global render_mode_name
    global active_render_mode_name
    global renderer
    global render_show_pulse_count

    while True:
        # Active mode gets set to None if a settings change occurs
        # for the active mode, which will trigger a state update
        if active_render_mode_name is None or active_render_mode_name != render_mode_name:
            print ("Switching modes... cur=%r new=%r" % (active_render_mode_name, render_mode_name))
            try:
                # Switch mode
                rmode_class = mode_to_state_lookup[render_mode_name]
                renderer = rmode_class()
                pulse_delay = renderer.delay
            except Exception as xcpt:
                sys.print_exception(xcpt)

            active_render_mode_name = render_mode_name

        if renderer is not None:
            if active_render_mode_name in ["ambient", "compass", "rainbow"]:
                if render_show_pulse_count > 0:
                    print("Pulsing %s..." % active_render_mode_name)
                    render_show_pulse_count -= 1
                renderer.pulse()
            else:
                print("Unknown render mode %r" % active_render_mode_name)
        else:
            print("Error renderer was None.")
        
        time.sleep(render_pulse_delay)

    return


