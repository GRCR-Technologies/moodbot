from gpiozero import Button, MCP3004
from time import time, sleep
import serial
import RPi.GPIO as GPIO
from  MFRC522 import MFRC522
import threading

# RFID reader
class MFRC522Reader:

    READER = None
    
    KEY = [0xFF,0xFF,0xFF,0xFF,0xFF,0xFF]
    BLOCK_ADDRS = [8, 9, 10]
    
    def __init__(self):
        self.READER = MFRC522(device=1, pin_rst=11)
        self.id = None
        self.text = None

    def run_loop(self):
        while True:
            print("Hold a tag near the reader")
            self.id, self.text = self.read()
            sleep(1)

    def run(self):
        t = threading.Thread(target=self.run_loop)  
        t.daemon = True
        t.start()

    
    def read(self):
        id, text = self.read_no_block()
        while not id:
            id, text = self.read_no_block()
        return id, text
    
    def read_no_block(self):
        (status, TagType) = self.READER.MFRC522_Request(self.READER.PICC_REQIDL)
        if status != self.READER.MI_OK:
            return None, None
        (status, uid) = self.READER.MFRC522_Anticoll()
        if status != self.READER.MI_OK:
            return None, None
        id = self.uid_to_num(uid)
        self.READER.MFRC522_SelectTag(uid)
        status = self.READER.MFRC522_Auth(self.READER.PICC_AUTHENT1A, 11, self.KEY, uid)
        data = []
        text_read = ''
        if status == self.READER.MI_OK:
            for block_num in self.BLOCK_ADDRS:
                block = self.READER.MFRC522_Read(block_num) 
                if block:
                    data += block
            if data:
                text_read = ''.join(chr(i) for i in data)
        self.READER.MFRC522_StopCrypto1()
        return id, text_read
        
    def uid_to_num(self, uid):
        n = 0
        for i in range(0, 5):
            n = n * 256 + uid[i]
        return n


# Joystick reader
class MCP3004Reader:
    def __init__(self):
        self.axis_x = MCP3004(channel=0)
        self.axis_y = MCP3004(channel=1)

    def read(self):
        return [self.axis_x.value, self.axis_y.value]

    def close(self):
        self.axis_x.close()
        self.axis_y.close()


class ButtonReader:
    def __init__(self):
        # Define the button
        self.button_led = Button(25)
        self.button_dig_up = Button(24)
        self.button_dig_down = Button(23)
        self.button_dig_cw = Button(27)
        self.button_dig_ccw = Button(22)

    def read(self):
        return [
            self.button_led.value,
            self.button_dig_up.value,
            self.button_dig_down.value,
            self.button_dig_cw.value,
            self.button_dig_ccw.value
        ]

    def close(self):
        self.button.close()


# // [START][SPD_R][SPD_L][CTRL][CRC]
# // [0xff][0-255][0-255][0-127][0-255]
# // START: 0xff
# // SPD_L: 0-255
# // SPD_R: 0-255
# // CTRL: 0-127
# // CTRL.0: 0 = SPD_L_BWD ,      1 = SPD_L_FWD   0x01
# // CTRL.1: 0 = SPD_R_BWD ,      1 = SPD_R_FWD   0x02
# // CTRL.2: 0 = DIG_ROT_OFF ,    1 = DIG_ROT_ON  0x04
# // CTRL.3: 0 = DIG_ROT_BWD ,    1 = DIG_ROT_FWD 0x08
# // CTRL.4: 0 = DIG_MOVE_OFF ,   1 = DIG_MOVE_ON 0x10
# // CTRL.5: 0 = DIG_MOVE_DWN ,   1 = DIG_MOVE_UP 0x20
# // CTRL.6: 0 = LED_OFF ,        1 = LED_ON      0x40
# // CRC: 0-255

def get_crc8( data: bytes, poly: int) -> int:
        crc = 0
        for b in data:
            crc ^= b
            for i in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ poly
                else:
                    crc >>= 1
        return crc & 0xff

def handle_joy(axis, buttons):
    MAX_PWM = 127

    l_wheels_spd = 0
    r_wheels_spd = 0

    l_r_coef = int(axis[0]*MAX_PWM)
    f_b_coef = int(axis[1]*MAX_PWM)
    l_wheels_spd = (f_b_coef-l_r_coef)*-1
    r_wheels_spd = (f_b_coef+l_r_coef)*-1
    if l_wheels_spd > MAX_PWM:
        l_wheels_spd = MAX_PWM
    if l_wheels_spd < -MAX_PWM:
        l_wheels_spd = -MAX_PWM
    if r_wheels_spd > MAX_PWM:
        r_wheels_spd = MAX_PWM
    if r_wheels_spd < -MAX_PWM:
        r_wheels_spd = -MAX_PWM
    
    data = [0xFF, abs(l_wheels_spd), abs(r_wheels_spd), 0x00, 0]
    data[3] = (0x00 if l_wheels_spd > 0 else 0x1) | (0x02 if r_wheels_spd > 0 else 0x00)

    # Digger movement
    if buttons[1] or buttons[2]:
        data[3] |= 0x10 
        if buttons[1]:
            data[3] |= 0x20

    # Digger rotation
    if buttons[3] or buttons[4]:
        data[3] |= 0x04
        if buttons[3]:
            data[3] |= 0x08
    # LED
    if buttons[5]:
        data[3] |= 0x40

    crc = get_crc8(bytes(data[1:4]), 0X8C)
    data[4] = crc
    return data

# TODO: Implement RFID list check
def check_rfid(rfid):
    return True

# TODO: Implement battery level check
def handle_bat_lvl(rx_msg):
    print(rx_msg)


rfid_reader = MFRC522Reader()
rfid_reader.run()
joystick_reader = MCP3004Reader()
button_reader = ButtonReader()
timeout = True

try:
    with serial.Serial(port='/dev/ttyUSB0', baudrate=38400, timeout=1) as ser:  
        while True:
            try:
                rx_msg = ser.readline()
                handle_bat_lvl(ser)
            except Exception:
                pass

            while timeout:
                if rfid_reader is not None:
                    if check_rfid(rfid_reader.id):
                        print(f'RFID: {rfid_reader.id}')
                        timeout = False
                try:
                    rx_msg = ser.readline()
                    handle_bat_lvl(ser)
                except Exception:
                    pass
                sleep(0.5)


            start_time = time()

            while not timeout:
                axis = joystick_reader.read()
                buttons = button_reader.read()
                data = handle_joy(axis, buttons)
                try:
                    ser.write(serial.to_bytes(data))
                    rx_msg = ser.readline()
                    handle_bat_lvl(ser)
                except Exception:
                    pass

                print(f'X: {axis[0]}\nY: {axis[1]}')
                print(f'LED: {buttons[0]}\n\
                        DIG_UP: {buttons[1]}\n\
                        DIG_DOWN: {buttons[2]}\n\
                        DIG_CW: {buttons[3]}\n\
                        DIG_CCW: {buttons[4]}')
                print(f'data_to_send:{data}')

                if start_time + 60 < time():
                    timeout = True
                    print("Timeout")

                sleep(0.1)
except KeyboardInterrupt:
    GPIO.cleanup()
    raise


