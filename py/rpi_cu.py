from gpiozero import Button, MCP3004
from time import time, sleep
import serial 
import RPi.GPIO as GPIO
from  MFRC522 import MFRC522
import threading
# importing tkinter for gui
import tkinter as tk
from tkinter.ttk import Label


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

# RFID reader
class MFRC522Reader:

    READER = None
    
    KEY = [0xFF,0xFF,0xFF,0xFF,0xFF,0xFF]
    BLOCK_ADDRS = [8, 9, 10]
    
    def __init__(self):
        self.READER = MFRC522(device=1, pin_rst=11)
        self.id = None
        self.text = None
        self.t = None

    def run_loop(self):
        while True:
            print("Hold a tag near the reader")
            self.id, self.text = self.read()
            print(self.id)
            sleep(1)

    def run(self):
        self.t = threading.Thread(target=self.run_loop)  
        self.t.daemon = True
        self.t.start() 

    
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
        self.button_led.close()
        self.button_dig_up.close()
        self.button_dig_down.close()
        self.button_dig_cw.close()
        self.button_dig_ccw.close()

class App:
    GAME_TIMEOUT = 10 # 360=3min
    DEBUG = True

    def __init__(self, window):
        self.window: tk.Tk = window
        self.rfid_reader = MFRC522Reader()
        self.rfid_reader.run()
        self.joystick_reader = MCP3004Reader()
        self.button_reader = ButtonReader()
        self.timeout = True
        self.rf_serial = self.open_rf_serial()
        self.id_serial = None
        self.timeout = True
        self.start_time = time()
        self.rate = 1000

    def handle_joy(self, axis, buttons):
        MAX_PWM = 127

        l_wheels_spd = 0
        r_wheels_spd = 0
        if abs(axis[0]-0.5) < 0.1:
            l_r_coef = 0
        else:
            l_r_coef = int((axis[0]-0.5)*2*MAX_PWM)
        
        if  abs(axis[1]-0.5) < 0.1:
            f_b_coef = 0
        else:
            f_b_coef = int((axis[1]-0.5)*-2*MAX_PWM)
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
        if buttons[0]:
            data[3] |= 0x40

        crc = get_crc8(bytes(data[1:4]), 0X8C)
        data[4] = crc
        return data

    # TODO: Implement RFID list check
    def check_rfid(self, rfid):
        return True

    # TODO: Implement battery level check
    def handle_bat_lvl(self, rx_msg):
        print(rx_msg)


    def open_rf_serial(self):
        return serial.Serial(port='/dev/ttyUSB0', baudrate=38400, timeout=1)

    def check_id_status(self):
        if self.rfid_reader.id is not None:
            if self.check_rfid(self.rfid_reader.id):
                print(f'RFID: {self.rfid_reader.id}')
                self.timeout = False
                self.start_time = time()
                self.rate = 50
        else:
            print("Activete with Access Key!")
            self.rf_serial.write(serial.to_bytes([255, 0, 0, 1, 94]))
            rx_msg = self.rf_serial.readline()
            self.handle_bat_lvl(rx_msg)


    def run_rf_communication(self):
        try:
            now = time()
            print(now-self.start_time)
            self.rfid_reader.id = None

            axis = self.joystick_reader.read()
            buttons = self.button_reader.read()
            data = self.handle_joy(axis, buttons)
       
            self.rf_serial.write(serial.to_bytes(data))
            rx_msg = self.rf_serial.readline()
            self.handle_bat_lvl(rx_msg)

            if self.DEBUG:
                print(f'X: {axis[0]-0.5}\nY: {axis[1]-0.5}')
                print(f'data_to_send:{data}')

            if self.start_time + self.GAME_TIMEOUT < now:
                print("Disarm: Timeout!")
                self.rf_serial.write(serial.to_bytes([255, 0, 0, 1, 94]))
                rx_msg = self.rf_serial.readline()
                self.handle_bat_lvl(rx_msg)
                self.timeout = True
                self.rate = 1000
        except Exception as err:
            print(err)
            #TODO: remove card from used cards list if failed

    def run_loop(self):
        if self.timeout:
            self.check_id_status()
        else:
            self.run_rf_communication()
        self.window.after(self.rate, self.run_loop)
    
    def close(self):
        self.joystick_reader.close()
        self.button_reader.close()
        self.rf_serial.close()
            


if __name__ == '__main__':
    try:
        # creating window
        window = tk.Tk()
        
        # setting attribute
        #Owindow.attributes('-fullscreen', True)
        window.title("Moodbot v0.1.0")
        window.geometry("800x480") 
        window.configure(bg='black')

        # creating object
        app = App(window)
        window.after(app.rate, app.run_loop)
        window.mainloop()
    except KeyboardInterrupt:
        print("Cleaning up!")
        GPIO.cleanup()
        exit()


