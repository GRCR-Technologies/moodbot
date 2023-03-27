// Product: MoodBot (Robot)
// Author:  Edgars Grankins
// Company: GRCR-Technologies
// Date:    27.03.2023
// Version: 0.5
// License: LGPLv3

#include <SoftwareSerial.h>

SoftwareSerial swSerial(10, 11); // RX, TX

// [START][SPD_R][SPD_L][CTRL][CRC]
// [0xff][0-255][0-255][0-127][0-255]
// START: 0xff
// SPD_L: 0-255
// SPD_R: 0-255
// CTRL: 0-127
// CTRL.0: 0 = SPD_L_BWD ,      1 = SPD_L_FWD   0x01
// CTRL.1: 0 = SPD_R_BWD ,      1 = SPD_R_FWD   0x02
// CTRL.2: 0 = DIG_ROT_OFF ,    1 = DIG_ROT_ON  0x04
// CTRL.3: 0 = DIG_ROT_BWD ,    1 = DIG_ROT_FWD 0x08
// CTRL.4: 0 = DIG_MOVE_OFF ,   1 = DIG_MOVE_ON 0x10
// CTRL.5: 0 = DIG_MOVE_DWN ,   1 = DIG_MOVE_UP 0x20
// CTRL.6: 0 = LED_OFF ,        1 = LED_ON      0x40
// CRC: 0-255

// Constants and pin assignments
#define L_WHL_PWM_PIN 3
#define L_WHL_DIR_PIN 2
#define L_WHL_DIR_MAP 0x01

#define R_WHL_PWM_PIN 9
#define R_WHL_DIR_PIN 4
#define R_WHL_DIR_MAP 0x02

#define DIG_ROT_PWM_PIN 6
#define DIG_ROT_ON_MAP 0x04
#define DIG_ROT_DIR_PIN 7
#define DIG_ROT_DIR_MAP 0x08
#define DIG_ROT_PWM_MAX 127

#define DIG_MOVE_PWM_PIN 5
#define DIG_MOVE_ON_MAP 0x10
#define DIG_MOVE_DIR_PIN 8
#define DIG_MOVE_DIR_MAP 0x20
#define DIG_MOVE_PWM_MAX 200

#define LED 12
#define LED_MAP 0x40

byte data[3];
byte buff;

// Calculate CRC
int get_crc() {
    byte crc = 0;
    for (int i = 0; i < 3; i++) {
        crc ^= data[i];
        for (int j = 0; j < 8; j++) {
            if (crc & 0x01) {
                crc = (crc >> 1) ^ 0x8C;
            } else {
                crc >>= 1;
            }
        }
    }
    return crc;
}

// Handle left and right wheels
void handle_wheels() {
    digitalWrite(L_WHL_DIR_PIN, data[2] & L_WHL_DIR_MAP);
    analogWrite(L_WHL_PWM_PIN, data[0]);

    digitalWrite(R_WHL_DIR_PIN, data[2] & R_WHL_DIR_MAP);
    analogWrite(R_WHL_PWM_PIN, data[1]);
}

// Handle dig rotation
void handle_dig_rot() {
    if (data[2] & DIG_ROT_ON_MAP) {
        // dig rotation direction
        digitalWrite(DIG_ROT_DIR_PIN, data[2] & DIG_ROT_DIR_MAP);
        // dig rotation on/off
        analogWrite(DIG_ROT_PWM_PIN, DIG_ROT_PWM_MAX);
    } else {
        analogWrite(DIG_ROT_PWM_PIN, 0);
    }
}

// Handle dig movement
void handle_dig_move() {
    if (data[2] & DIG_MOVE_ON_MAP) {
        // Dig direction
        digitalWrite(DIG_MOVE_DIR_PIN, data[2] & DIG_MOVE_DIR_MAP);
        // Dig on/off
        analogWrite(DIG_MOVE_PWM_PIN, DIG_MOVE_PWM_MAX);
    } else {
        analogWrite(DIG_MOVE_PWM_PIN, 0);
    }
}

// Handle LED
void handle_led() {
    digitalWrite(LED, data[2] & LED_MAP);
}

void setup() {
    pinMode(R_WHL_PWM_PIN, OUTPUT);
    pinMode(R_WHL_DIR_PIN, OUTPUT);
    pinMode(L_WHL_PWM_PIN, OUTPUT);
    pinMode(L_WHL_DIR_PIN, OUTPUT);
    pinMode(DIG_ROT_PWM_PIN, OUTPUT);
    pinMode(DIG_ROT_DIR_PIN, OUTPUT);
    pinMode(DIG_MOVE_PWM_PIN, OUTPUT);
    pinMode(DIG_MOVE_DIR_PIN, OUTPUT);
    pinMode(LED, OUTPUT);

    swSerial.begin(38400);
    swSerial.println("MOODBOT v0.5.0");
}

void loop() {
    if (swSerial.available() >= 5) {
        buff = swSerial.read();
        if (buff == 0xff) {
            for (int i = 0; i < 3; i++) {
                data[i] = swSerial.read();
            }
            buff = swSerial.read();
            if (buff == get_crc()) {
                swSerial.println(String(analogRead(A0)) + ":OK");
                handle_wheels();
                handle_dig_rot();
                handle_dig_move();
                handle_led();
            } else {
                swSerial.println(String(analogRead(A0)) + ":ERR");
            }
        }
    }
}
