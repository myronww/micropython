

from micropython import const

import bluetooth

from ble_advertising import advertising_payload

_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)
_IRQ_GATTS_READ_REQUEST = const(4)

DEVICE_MAIN_SERVICE_UUID = bluetooth.UUID("88888888-8888-8888-8888-888888888888")

CONTROL_SERVICE_UUID =     bluetooth.UUID("00000000-0000-8c8c-8c8c-8c8c8c8c8c8c")

DEVICETYPE_UUID =          bluetooth.UUID("11111111-1111-8c8c-8c8c-8c8c8c8c8c8c")

FLAIR_MODE_IO_UUID =       bluetooth.UUID("22222222-2222-8c8c-8c8c-8c8c8c8c8c8c")
WIFI_MODE_IO_UUID =        bluetooth.UUID("33333333-3333-8c8c-8c8c-8c8c8c8c8c8c")

CONTROL_IO_READ_UUID =     bluetooth.UUID("44444444-4444-8c8c-8c8c-8c8c8c8c8c8c")
CONTROL_IO_WRITE_UUID =    bluetooth.UUID("55555555-5555-8c8c-8c8c-8c8c8c8c8c8c")

ATTR_DEV_TYPE = (
    DEVICETYPE_UUID,
    bluetooth.FLAG_READ
)

ATTR_UART_TX = (
    CONTROL_IO_WRITE_UUID,
    bluetooth.FLAG_READ | bluetooth.FLAG_NOTIFY
)

ATTR_UART_RX = (
    CONTROL_IO_READ_UUID,
    bluetooth.FLAG_WRITE
)

_CONTROL_SERVICE = (
    CONTROL_SERVICE_UUID,
    (ATTR_DEV_TYPE, ATTR_UART_TX, ATTR_UART_RX),
)

# org.bluetooth.characteristic.gap.appearance.xml
_ADV_APPEARANCE_GENERIC_COMPUTER = const(128)

class BLE_FLair:
    def __init__(self, name, rxbuf_len=1024):
        self._name = name
        self._rxbuf_len = rxbuf_len
        
        self._ble = None
    
        self._dt_handle = None
        self._rx_handle = None
        self._tx_handle = None

        bluetooth.BLE()
        self._ble.active(True)
        self._ble.irq(self._irq)

        ((self._dt_handle, self._tx_handle, self._rx_handle),) = self._ble.gatts_register_services((_CONTROL_SERVICE,))

        # Increase the size of the rx buffer and enable append mode.
        self._ble.gatts_set_buffer(self._rx_handle, rxbuf_len, True)

        self._connections = set()
        
        self._rx_buffer = bytearray()

        self._rcv_callback = None

        # Optionally add services=[_UART_UUID], but this is likely to make the payload too large.
        self._payload = advertising_payload(name=name, appearance=_ADV_APPEARANCE_GENERIC_COMPUTER)
        self._advertise()

        return

    def set_receive_callback(self, rcv_callback):
        self._rcv_callback = rcv_callback

    def _irq(self, event, data):
        # Track connections so we can send notifications.
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, _, _ = data
            self._connections.add(conn_handle)

        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _ = data
            if conn_handle in self._connections:
                self._connections.remove(conn_handle)
            # Start advertising again to allow a new connection.
            self._advertise()

        elif event == _IRQ_GATTS_WRITE:
            conn_handle, value_handle = data
            if conn_handle in self._connections and value_handle == self._rx_handle:
                self._rx_buffer += self._ble.gatts_read(self._rx_handle)
                if self._rcv_callback:
                    self._rcv_callback(self)

        elif event == _IRQ_GATTS_READ_REQUEST:
            conn_handle, value_handle = data
            if conn_handle in self._connections and value_handle == self._dt_handle:
                self._ble.gatts_write(self._dt_handle, b"flair-skate")

        return

    def any(self):
        return len(self._rx_buffer)

    def read(self, sz=None):
        if not sz:
            sz = len(self._rx_buffer)
        result = self._rx_buffer[0:sz]
        self._rx_buffer = self._rx_buffer[sz:]
        return result

    def write(self, data):
        for conn_handle in self._connections:
            self._ble.gatts_notify(conn_handle, self._tx_handle, data)

    def close(self):
        for conn_handle in self._connections:
            self._ble.gap_disconnect(conn_handle)
        self._connections.clear()

    def _advertise(self, interval_us=500000):
        self._ble.gap_advertise(interval_us, adv_data=self._payload)
