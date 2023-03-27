# Product: MoodBot (Control Unit)
# Author:  Edgars Grankins
# Company: GRCR-Technologies
# Date:    27.03.2023
# Version: 0.5
# License: LGPLv3

import threading
from time import time, sleep
import tkinter as tk
from tkinter.ttk import Label
from gpiozero import Button, MCP3004
import serial
import RPi.GPIO as GPIO
from MFRC522 import MFRC522
from typing import Tuple, Union

DEBUG = False

def get_crc8(data: bytes, poly: int) -> int:
    crc = 0
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ poly
            else:
                crc >>= 1
    return crc & 0xff

# RFID reader
class MFRC522Reader:

    READER = None

    KEY = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]
    BLOCK_ADDRS = [8, 9, 10]

    def __init__(self) -> None:
        self.READER = MFRC522(device=1, pin_rst=11)
        self.id = None
        self.text = None
        self.t = None

    # Continuously read and print the ID of the card
    def run_loop(self) -> None:
        while True:
            if DEBUG:
                print("Hold a tag near the reader")
            self.id, self.text = self.read()
            if DEBUG:
                print(self.id)
            sleep(1)

    # start te run loop in a separate thread
    def run(self) -> None:
        self.t = threading.Thread(target=self.run_loop)
        self.t.daemon = True
        self.t.start()

    # read a card and return the id and text
    def read(self) -> Tuple[int, str]:
        id, text = self.read_no_block()

        while not id:
            id, text = self.read_no_block()

        return id, text

    # attempt to read a card without blocking and return the id and text
    def read_no_block(self) -> Tuple[int, str]:
        (status, TagType) = self.READER.MFRC522_Request(self.READER.PICC_REQIDL)

        if status != self.READER.MI_OK:
            return None, None
        (status, uid) = self.READER.MFRC522_Anticoll()

        if status != self.READER.MI_OK:
            return None, None

        id = self.uid_to_num(uid)
        self.READER.MFRC522_SelectTag(uid)
        status = self.READER.MFRC522_Auth(
            self.READER.PICC_AUTHENT1A, 11, self.KEY, uid)
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

    # convert the uid to a number
    def uid_to_num(self, uid) -> int:
        n = 0

        for i in range(0, 5):
            n = n * 256 + uid[i]

        return n


# Joystick reader
class MCP3004Reader:
    def __init__(self) -> None:
        self.axis_x = MCP3004(channel=0)
        self.axis_y = MCP3004(channel=1)

    def read(self) -> Tuple[float, float]:
        return [self.axis_x.value, self.axis_y.value]

    def close(self) -> None:
        self.axis_x.close()
        self.axis_y.close()


# Button readerS
class ButtonReader:
    def __init__(self) -> None:
        # Define the button
        self.button_led = Button(25)
        self.button_dig_up = Button(24)
        self.button_dig_down = Button(23)
        self.button_dig_cw = Button(27)
        self.button_dig_ccw = Button(22)

    # Read the button
    def read(self)  -> Tuple[bool, bool, bool, bool, bool]:
        return [
            self.button_led.value,
            self.button_dig_up.value,
            self.button_dig_down.value,
            self.button_dig_cw.value,
            self.button_dig_ccw.value
        ]

    # Close the button
    def close(self) -> None:
        self.button_led.close()
        self.button_dig_up.close()
        self.button_dig_down.close()
        self.button_dig_cw.close()
        self.button_dig_ccw.close()

# Robot controller
class RobotController:
    def __init__(self) -> None:
        # Initialize serial connections, RFID and joystick readers,
        # button reader, and used IDs list
        self.rf_serial = self.open_rf_serial()
        self.id_serial = self.open_id_serial()
        self.rfid_reader = MFRC522Reader()
        self.rfid_reader.run()
        self.joystick_reader = MCP3004Reader()
        self.button_reader = ButtonReader()
        self.used_ids = []

    # Open the serial port for the RF module
    def open_rf_serial(self):
        return serial.Serial(port='/dev/ttyUSB0', baudrate=38400, timeout=0.1)

    # Open the serial port for secondary Controller (ID reader)
    def open_id_serial(self):
        return serial.Serial(port='/dev/serial0', baudrate=38400, timeout=0.01)

    # Validate the remote ID and update the used IDs list
    def validate_remote_id(self):
        try:
            remote_id = int(self.id_serial.readline())
            if remote_id in self.used_ids:
                retval = True
            else:
                retval = False
                self.used_ids.append(remote_id)
            self.id_serial.write(str(retval).encode())
        except Exception as err:
            if DEBUG:
                print(err)
            else:
                pass

    # Check the remote ID by sending it to the ID reader
    def check_remote_id(self, rx_msg):
        self.id_serial.write(str(rx_msg).encode())
        try:
            status = self.id_serial.readline() == b'True'
        except Exception:
            status = False
        return status

    # Check if the RFID is in the used IDs list or if it's in the remote ID list
    def check_rfid(self):
        rfid = self.rfid_reader.id

        if rfid in self.used_ids or self.check_remote_id(rfid):
            return True

        self.used_ids.append(rfid)
        return False

    # Handle joystick input and calculate wheel speeds
    def handle_joy(self):
        MAX_PWM = 127
        axis = self.joystick_reader.read()
        buttons = self.button_reader.read()

        if DEBUG:
            print(f'X: {axis[0]-0.5}\nY: {axis[1]-0.5}')
            print(f'data_to_send:{data}')

        l_wheels_spd = 0
        r_wheels_spd = 0

        # Calculate left and right coefficients based on joystick axis input
        l_r_coef = int((axis[0]-0.5)*2*MAX_PWM)*-1\
              if abs(axis[0]-0.5) >= 0.1 else 0
        f_b_coef = int((axis[1]-0.5)*-2*MAX_PWM)*-1\
            if abs(axis[1]-0.5) >= 0.1 else 0

        # Calculate left and right wheel speeds
        l_wheels_spd = (f_b_coef-l_r_coef)*-1
        r_wheels_spd = (f_b_coef+l_r_coef)*-1

        # Limit wheel speeds to MAX_PWM
        l_wheels_spd = min(max(l_wheels_spd, -MAX_PWM), MAX_PWM)
        r_wheels_spd = min(max(r_wheels_spd, -MAX_PWM), MAX_PWM)

        # Create data packet with wheel speeds and button states
        data = [0xFF, abs(l_wheels_spd), abs(r_wheels_spd), 0x00, 0]
        data[3] = (0x00 if l_wheels_spd > 0 else 0x1) | \
            (0x02 if r_wheels_spd > 0 else 0x00)

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

        # Calculate and append CRC
        crc = get_crc8(bytes(data[1:4]), 0X8C)
        data[4] = crc
        return data

    # Send data (wheel speeds and button states) to the robot
    def send_data(self):
        data = self.handle_joy()
        self.rf_serial.write(serial.to_bytes(data))

    # Send stop command to the robot
    def send_stop(self):
        self.rf_serial.write(serial.to_bytes([255, 0, 0, 1, 94]))

    # Get battery level from the robot
    def get_bat_lvl(self):
        rx_msg = self.rf_serial.readline()
        try:
            bat = int(rx_msg.decode('utf-8').split(':')[0])
            if DEBUG:
                print(bat)
            return bat
        except:
            if DEBUG:
                print(rx_msg)
            return None


class App:
    GAME_TIMEOUT = 120  # Timeout for the game in seconds, 120=2min
    ID_TIMEOUT = 28800    # Timeout for the ID in seconds, 28800=8h
    DEBUG = True       # Debug flag for printing debug information

    def __init__(self, window):
        self.window: tk.Tk = window
        self.robot_controller = RobotController()
        self.init_gui()

    # Initialize the graphical user interface
    def init_gui(self):
        self.rate = 1000
        self.boot_time = time()
        self.start_time = time()
        self.timeout = True
        self.cnt = 0
        self.cnt_sts = False
        # Create and configure timer label
        self.timer = Label(
            self.window,
            text="00:00",
            font=("Arial", 160),
            foreground="white",
            relief="solid",
            background="black")
        # Create and configure message label
        self.msg = Label(
            self.window, text="Noskenējiet karti!",
            font=("Arial", 64),
            foreground="white",
            relief="solid",
            background="black")
        self.msg.place(x=10, y=200)
        # Create and configure battery label
        self.bat = Label(
            self.window,
            text="0%",
            font=("Arial", 48),
            foreground="white",
            relief="solid",
            background="black")
        self.bat.place(x=610,)

    # Show "Mission complete" message in LV
    def mission_complete(self):
        self.msg.config(text="  Misija pabeigta!")
        self.window.after(3000, self.waiting_msg)

    # Show "Scan your card" message in LV
    def waiting_msg(self):
        self.msg.config(text="Noskenējiet karti!")

    # Start the countdown for the game
    def start_countdown(self):
        if not self.timeout:
            return
        self.msg.place_forget()
        self.timer.place(x=85, y=120)
        self.cnt = self.GAME_TIMEOUT
        self.timeout = False
        self.window.after(1000, self.countdown)

    # Update the countdown timer
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

    # Update battery level label
    def handle_bat_lvl(self):
        batlvl = self.robot_controller.get_bat_lvl()

        if batlvl is not None:
            self.bat.config(text=f'{int((batlvl-723)/2.5)}%')

        if batlvl < 801:
            self.bat.config(foreground="red")
        else:
            self.bat.config(foreground="white")

    # Check RFID status and start the countdown if a valid ID is found
    def check_id_status(self):
        if self.robot_controller.rfid_reader.id is not None:
            if not self.robot_controller.check_rfid():
                if DEBUG:
                    print(f'RFID: {self.robot_controller.rfid_reader.id}')
                self.start_countdown()
                self.rate = 50
            else:
                self.robot_controller.rfid_reader.id = None
                self.mission_complete()
        else:
            if DEBUG:
                print("Activate with Access Key!")
            self.robot_controller.send_stop()
            self.handle_bat_lvl()

    # Run the communication with the robot and update battery level
    def run_rf_communication(self):
        try:
            now = time()
            if DEBUG:
                print(now-self.start_time)
            self.robot_controller.rfid_reader.id = None
            self.robot_controller.send_data()
            self.handle_bat_lvl()

            if self.timeout:
                print("Disarm: Timeout!")
                self.robot_controller.send_stop()
                self.handle_bat_lvl()
                self.rate = 1000
        except Exception as err:
            if DEBUG:
                print(err)
            else:
                pass

    # Check for ID timeout and clear used IDs if necessary
    def check_id_timeout(self):
        if time() - self.boot_time > self.ID_TIMEOUT:
            self.robot_controller.used_ids = []
            self.boot_time = time()

    # Main loop of the application
    def run_loop(self):
        self.robot_controller.validate_remote_id()
        if self.timeout:
            self.rate = 1000
            self.check_id_status()
            self.check_id_timeout()
        else:
            self.rate = 50
            self.run_rf_communication()
        self.window.after(self.rate, self.run_loop)

    # Clean up resources when closing the application
    def close(self):
        self.robot_controller.joystick_reader.close()
        self.robot_controller.button_reader.close()
        self.robot_controller.rf_serial.close()


if __name__ == '__main__':
    try:
        # creating window
        window = tk.Tk()

        # setting attribute
        window.title("Moodbot v0.5.0")
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
