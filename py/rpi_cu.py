# Product: MoodBot
# Author:  Edgars Grankins
# Company: GRCR-Technologies  
# Date:    08.04.2023

from gpiozero import Button, MCP3004
from time import time, sleep
import serial 
import RPi.GPIO as GPIO
from  MFRC522 import MFRC522
import threading
# importing tkinter for gui
import tkinter as tk
from tkinter.ttk import Label

DEBUG = False

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
            if DEBUG: print("Hold a tag near the reader")
            self.id, self.text = self.read()
            if DEBUG: print(self.id)
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
        self.id_serial = self.open_id_serial()
        self.timeout = True
        self.start_time = time()
        self.rate = 1000
        self.init_gui()
        self.used_ids = []
        
    
    def init_gui(self):
        self.cnt = 0
        self.cnt_sts = False
        self.timer = Label(
            self.window,
            text="00:00",
            font=("Arial", 160),
            foreground="white",
            relief="solid",
            background="black")
        self.msg = Label(
            self.window, text="Noskenējiet karti!",
            font=("Arial", 64), 
            foreground="white",
            relief="solid",
            background="black")
        self.msg.place(x=10, y=200)
        self.bat = Label(
            self.window,
            text="0%",
            font=("Arial", 48),
            foreground="white",
            relief="solid",
            background="black")
        self.bat.place(x=610,)

    def mission_complete(self):
        self.msg.config(text="  Misija pabeigta!")
        self.window.after(3000, self.waiting_msg)

    def waiting_msg(self):
        self.msg.config(text="Noskenējiet karti!")
    
    def start_countdown(self):
        if not self.timeout:
            return
        self.msg.place_forget()
        self.timer.place(x=85, y=120)
        self.cnt = self.GAME_TIMEOUT
        self.timeout = False
        self.window.after(1000, self.countdown)
    
    def countdown(self):
        self.timer.config(
            text=f'{int((self.cnt-(self.cnt%60))/60):02d}:{self.cnt%60:02d}')
        self.cnt -= 1

        if self.cnt < 0:
            self.timeout = True
            self.timer.place_forget()
            self.msg.place(x=10, y=200)
            self.mission_complete()
        else:
            self.window.after(1000, self.countdown)


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

    def validate_remote_id(self):
        try:
            remote_id = int(self.id_serial.readline())
            if remote_id in self.used_ids:
                retval = True
            else:
                retval = False
                self.used_ids.append(remote_id)
            self.id_serial.write(str(retval).encode())
        except Exception as e:
            if DEBUG: 
                print(e)
            else: 
                pass

    def check_remote_id(self, rx_msg):
        self.id_serial.write(str(rx_msg).encode())
        try:
            status = (self.id_serial.readline() == b'True')
        except Exception:
            status = False
        return status 

    # TODO: Implement RFID list check
    def check_rfid(self, rfid):

        if rfid in self.used_ids or self.check_remote_id(rfid):
            return True
        self.used_ids.append(rfid)
        return False

    # TODO: Implement battery level check
    def handle_bat_lvl(self, rx_msg):
        try:
            bat = int(rx_msg.decode('utf-8').split(':')[0])
            if DEBUG: print(bat)
        except:
            if DEBUG: print(rx_msg)
            return

        self.bat.config(text=f'{int((bat-723)/2.5)}%')

        if bat < 801:
            self.bat.config(foreground="red")
        else:
            self.bat.config(foreground="white")
        


    def open_rf_serial(self):
        return serial.Serial(port='/dev/ttyUSB0', baudrate=38400, timeout=0.1)

    def open_id_serial(self):
        return serial.Serial(port='/dev/serial0', baudrate=38400, timeout=0.01)

    def check_id_status(self):
        if self.rfid_reader.id is not None:
            if not self.check_rfid(self.rfid_reader.id):
                if DEBUG: print(f'RFID: {self.rfid_reader.id}')
                self.start_countdown()
                self.rate = 50
            else:
                self.rfid_reader.id = None
                self.mission_complete()

        else:
            if DEBUG: print("Activete with Access Key!")
            self.rf_serial.write(serial.to_bytes([255, 0, 0, 1, 94]))
            rx_msg = self.rf_serial.readline()
            self.handle_bat_lvl(rx_msg)


    def run_rf_communication(self):
        try:
            now = time()
            if DEBUG: print(now-self.start_time)
            self.rfid_reader.id = None

            axis = self.joystick_reader.read()
            buttons = self.button_reader.read()
            data = self.handle_joy(axis, buttons)
       
            self.rf_serial.write(serial.to_bytes(data))
            rx_msg = self.rf_serial.readline()
            self.handle_bat_lvl(rx_msg)

            if DEBUG:
                print(f'X: {axis[0]-0.5}\nY: {axis[1]-0.5}')
                print(f'data_to_send:{data}')

            if self.timeout:
                print("Disarm: Timeout!")
                self.rf_serial.write(serial.to_bytes([255, 0, 0, 1, 94]))
                rx_msg = self.rf_serial.readline()
                self.handle_bat_lvl(rx_msg)
                self.rate = 1000
        except Exception as err:
            if DEBUG: 
                print(err)
            else:
                pass
            #TODO: remove card from used cards list if failed

    def run_loop(self):
        self.validate_remote_id()
        if self.timeout:
            self.rate = 1000
            self.check_id_status()
        else:
            self.rate = 50
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
        window.title("Moodbot v0.4.0")
        window.geometry("800x480") 
        window.configure(bg='black')

        # creating object
        app = App(window)
        window.after(app.rate, app.run_loop)
        window.mainloop()
    except KeyboardInterrupt:
        print("Cleaning up!")
        window.destroy()
        GPIO.cleanup()
        exit()


