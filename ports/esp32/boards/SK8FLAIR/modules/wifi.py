
import json
import time
import network

import filesystem

from configuration import WIRELESS_SSID, WIRELESS_PASSWORD

FILE_SETTINGS = "network-settings.json"

DEFAULT_CONNECTION_TIMEOUT = 30

sta_wlan = None
ap_wlan = None

def dump_wireless_info():
    global sta_wlan
    global ap_wlan

    if sta_wlan is not None:
        active = sta_wlan.isconnected()
        if active:
            print("STA: (connected)")
            for item in ap_wlan.ifconfig():
                print("    %r" % item)
        else:
            print("STA: (disconnected)")

    if ap_wlan is not None:
        active = ap_wlan.active()
        if active:
            print("AP: (active)")
            print("    SSID: %s" % ap_wlan.config("essid"))
            print("    authmode: %s" % ap_wlan.config("authmode"))
            print("    channel: %s" % ap_wlan.config("channel"))
            print("    mac: %s" % ap_wlan.config("mac"))
            print("    visible: %r" %  (not ap_wlan.config("hidden")))
        else:
            print("AP: (not-active)")
    else:
        print("AP: (not-active)")

    return

def initialize():
    global sta_wlan
    global ap_wlan

    if filesystem.exists(FILE_SETTINGS):
        with open(FILE_SETTINGS, 'r') as sf:
            flair_settings = json.load(sf)
            if 'networks' in flair_settings:
                known_networks = flair_settings['networks']

                known_network_lookup = {}
                ssid_list = []
                for nxt_net in known_networks:
                    ssid = nxt_net["ssid"]
                    known_network_lookup[ssid] = nxt_net
                    ssid_list.append(ssid)

                sta_wlan = network.WLAN(network.STA_IF)
                found_networks = sta_wlan.scan()
                for nxt_fnd in found_networks:
                    print("Found network SSID=%s " % nxt_fnd.ssid)
                    if nxt_fnd.ssid in ssid_list:
                        known_ntwk = known_network_lookup[nxt_fnd.ssid]
                        if "password" in known_ntwk:
                            print("Attempting to connect to network SSID=%s " % nxt_fnd.ssid)
                            passwd = known_ntwk["password"]
                            sta_wlan.connect(nxt_fnd.ssid, auth=(nxt_fnd.sec, passwd), timeout=5000)
                        else:
                            sta_wlan.connect(nxt_fnd.ssid, timeout=5000)

                        now = time.time()
                        end = now + DEFAULT_CONNECTION_TIMEOUT
                        while not sta_wlan.isconnected():
                            now = time.time()
                            if now > end:
                                break
                                time.sleep(5)

    if sta_wlan is None or (sta_wlan is not None and not sta_wlan.isconnected()):
        ap_wlan = network.WLAN(network.AP_IF)
        ap_wlan.config(essid=WIRELESS_SSID, password=WIRELESS_PASSWORD)
        ap_wlan.config(max_clients=10)
        ap_wlan.active(True)

    dump_wireless_info()

    return
