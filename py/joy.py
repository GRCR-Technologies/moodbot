#!/usr/bin/python3
import pygame
import time
import serial


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

MAX_PWM = 127

pygame.init()

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

def calc_speed(axis):
    l_wheels_spd = 0
    r_wheels_spd = 0

    l_r_coef = int(axis[3]*MAX_PWM)
    f_b_coef = int(axis[4]*MAX_PWM)
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
    data[3] = (0x00 if l_wheels_spd > 0 else 0x1) + (0x02 if r_wheels_spd > 0 else 0x00)  
    # data = [0xFF, 100, 100, 0x00, 0]
    crc = get_crc8(bytes(data[1:4]), 0X8C)
    data[4] = crc
    return data


def main():

    with serial.Serial('/dev/tty.usbserial-2130', 38400) as ser:
        print(ser.readline())
        joysticks = {}
        done = False
        axis = None
        buttons = None
        last_time = time.time()
        while not done:
            last_time = time.time()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    done = True
                if event.type == pygame.JOYDEVICEADDED:
                    joy = pygame.joystick.Joystick(event.device_index)
                    joysticks[joy.get_instance_id()] = joy
                    print(f"Joystick {joy.get_instance_id()} connencted")
                if event.type == pygame.JOYDEVICEREMOVED:
                    del joysticks[event.instance_id]
                    print(f"Joystick {event.instance_id} disconnected")
            joystick_count = pygame.joystick.get_count()
            # For each joystick:
        
            for joystick in joysticks.values():
                axis = [joystick.get_axis(x) for x in range(joystick.get_numaxes())]
                buttons = [joystick.get_button(x) for x in range(joystick.get_numbuttons())]
            time.sleep(0.01)
            if axis is not None:
                data = calc_speed(axis)
                print(data)
                ser.write(serial.to_bytes(data))
                print(ser.readline())
            c_time = time.time()-last_time
            print(f'{c_time*1000}ms {1/c_time}Hz')


if __name__ == "__main__":
    main()
    pygame.quit()