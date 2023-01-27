byte data[5];
byte buff;
int ledPin = 9; 

int get_crc()
{
    byte crc = 0;
    for (int i = 0; i < 5; i++) {
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


void setup() {
  pinMode(11, OUTPUT);  // sets the pin as output
  Serial.begin(9600);
  Serial.println("MOODBOT v0.0.1");
}

void loop() {
    if (Serial.available() >= 6) {
        buff = Serial.read();
        if (buff == 0xff) {
          for (int i = 0; i < 4; i++) {
            data[i] = Serial.read();
          }
          buff = Serial.read();
          for (int i = 0; i < 4; i++) {
                Serial.print(data[i]);
          }
          analogWrite(11, data[0]);
          Serial.print(buff);
          Serial.print(":");
          Serial.println(get_crc());
          Serial.flush();
        }
       
    }
}

