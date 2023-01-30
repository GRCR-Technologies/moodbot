#!/usr/bin/python3
import pygame
import time

pygame.init()


def calc_speed(axis):
    l_wheels_spd = 0
    r_wheels_spd = 0

    l_r_coef = int(axis[3]*256)
    f_b_coef = int(axis[4]*256)
    l_wheels_spd = f_b_coef-l_r_coef
    r_wheels_spd = f_b_coef+l_r_coef
    return l_wheels_spd, r_wheels_spd


def main():
    joysticks = {}
    done = False
    axis = None
    buttons = None
    while not done:
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
        time.sleep(0.1)
        if axis is not None:
            print(calc_speed(axis))


if __name__ == "__main__":
    main()
    pygame.quit()