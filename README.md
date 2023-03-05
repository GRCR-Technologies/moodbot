# The Moodbot (Digging Robot)

## Image setuping
```sh
sudo apt install git
sudo apt install python3-pip
sudo apt install python3-tk
sudo apt install xserver-xorg -y
sudo apt install xinit -y
sudo apt install x11-xserver-utils -y
pip3 install pyserial
nano .xsession
```
```sh
DISPLAY=:0 xrandr --output HDMI-2 --rotate left

while true
do
    DISPLAY=:0 python3 /home/moonbot/moodbot/py/rpi_cu.py
done
```
```sh
sudo nano .bashrc
```
```sh
startx
```



## RF Protocol

    [START][SPD_R][SPD_L][CTRL][CRC]
    [0xff][0-255][0-255][0-127][0-255]
    START: 0xff
    SPD_L: 0-255
    SPD_R: 0-255
    CTRL: 0-127
    CTRL.0: 0 = SPD_L_BWD ,      1 = SPD_L_FWD   0x01
    CTRL.1: 0 = SPD_R_BWD ,      1 = SPD_R_FWD   0x02
    CTRL.2: 0 = DIG_ROT_OFF ,    1 = DIG_ROT_ON  0x04
    CTRL.3: 0 = DIG_ROT_BWD ,    1 = DIG_ROT_FWD 0x08
    CTRL.4: 0 = DIG_MOVE_OFF ,   1 = DIG_MOVE_ON 0x10
    CTRL.5: 0 = DIG_MOVE_DWN ,   1 = DIG_MOVE_UP 0x20
    CTRL.6: 0 = LED_OFF ,        1 = LED_ON      0x40
    CRC: 0-255







