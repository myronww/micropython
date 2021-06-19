
import json
import machine
import os
import sys
import time
import uos


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
flair_mode = None

wifi_mode = None

proto_inbound = []
proto_outbound = []

navigation = None

active_flair_mode = None


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

def set_flair_mode(mode):
    global flair_mode
    global active_flair_mode

    flair_settings["mode"] = mode
    settings_save()
    flair_mode = mode
    active_flair_mode = None
    return

def settings_load():
    global flair_mode
    global flair_settings

    if flair_settings is None:
        if filesystem.exists(FILE_SETTINGS):
            with open(FILE_SETTINGS, 'r') as sf:
                flair_settings = json.load(sf)
        else:
            flair_settings = DEFAULT_FLAIR_SETTINGS
            settings_save()

    flair_mode = flair_settings["flair"]["mode"]

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
    global flair_mode
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

    flair_mode = flair_settings["flair"]["mode"]
    time.sleep(.5)

    dotstar_device.push_buffer(dotstar.BLUE_BUFFER)
    flairsvc = BLE_FLair(BLUETOOTH_DEVICE_NAME)
    flairsvc.set_receive_callback(process_message)

    time.sleep(.5)

    dotstar_device.push_buffer(dotstar.GRN_BUFFER)

    time.sleep(.5)
    return

def load_flair_mode_settings(mode):
    print("loading flair settings")

    if mode not in flair_settings["flair"]["settings"]:
        flair_settings["flair"]["settings"][mode] = DEFAULT_FLAIR_SETTINGS["flair"]["settings"][mode]
        settings_save()

    settings = flair_settings["flair"]["settings"][mode]

    return settings

class FlairStateAmbient:
    def __init__(self):
        settings = load_flair_mode_settings("ambient")
        self.red = settings["red"]
        self.green = settings["green"]
        self.blue = settings["blue"]
        self.intensity = settings["intensity"]
        self.delay = .1
        return

    def pulse(self):
        dotstar_device.fill_color(self.red, self.green, self.blue, self.intensity)
        return

class FlairStateCompass:
    def __init__(self):
        settings = load_flair_mode_settings("compass")
        self.direction = int(navigation.mag_read_heading())
        self.intensity = settings["intensity"]
        self.delay = .1
        return

    def pulse(self):
        self.direction = int(navigation.mag_read_heading())
        dotstar_device.fill_direction(self.direction)
        return

class FlairStateRainbow:
    def __init__(self):
        settings = load_flair_mode_settings("rainbow")
        self.direction = 0
        self.intensity = settings["intensity"]
        self.delay = .1
        return

    def pulse(self):
        dotstar_device.fill_direction(self.direction)
        self.direction = (self.direction + 1) % 360
        return

mode_to_state_lookup = {
    "ambient": FlairStateAmbient,
    "compass": FlairStateCompass,
    "rainbow": FlairStateRainbow
}

def loop():

    global active_flair_mode

    if flair_mode is None:
        raise Exception("Error cannot start the flair loop while flair_mode is None.")

    flair_state = None
    pulse_delay = .1

    mark_now = time.time()
    mark_next = mark_now + 5

    while True:
        current_mode = active_flair_mode

        # Active mode gets set to None if a settings change occurs
        # for the active mode, which will trigger a state update
        if flair_mode != current_mode:
            print ("Switching modes... cur=%r new=%r" % (current_mode, flair_mode))
            try:
                # Switch mode
                fstate_class = mode_to_state_lookup[flair_mode]
                flair_state = fstate_class()
                pulse_delay = flair_state.delay
            except Exception as xcpt:
                sys.print_exception(xcpt)

            active_flair_mode = flair_mode
            current_mode = flair_mode

        if flair_state is not None:
            if current_mode == "ambient" or current_mode == "compass" or current_mode == "rainbow":
                if mark_now > mark_next:
                    print("Pulsing %r..." % current_mode)
                    mark_next = mark_now + 5
                flair_state.pulse()
            else:
                print("Unknown flair mode %r" % current_mode)
        else:
            print("Error flair_state was None.")

        time.sleep(pulse_delay)
        mark_now = time.time()

    return
