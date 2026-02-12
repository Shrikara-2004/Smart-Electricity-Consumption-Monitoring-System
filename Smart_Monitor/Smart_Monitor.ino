#include <WiFi.h>
#include <HTTPClient.h>
#include <PZEM004Tv30.h>

const char* ssid = "Shri’s iPhone";
const char* password = "123456789";
const char* flaskServerURL = "http://192.168.0.107:5001/api/esp32/data";  // Change IP

#define PZEM_RX_PIN 16
#define PZEM_TX_PIN 17
PZEM004Tv30 pzem(Serial2, PZEM_RX_PIN, PZEM_TX_PIN);

float voltage, current, power, energy, frequency, pf;

void setup() {
  Serial.begin(115200);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n✅ WiFi connected!");
  Serial.println("IP: " + WiFi.localIP().toString());
}

void loop() {
  voltage = pzem.voltage();
  current = pzem.current();
  power = pzem.power();
  energy = pzem.energy();
  frequency = pzem.frequency();
  pf = pzem.pf();

  if (!isnan(voltage)) {
    HTTPClient http;
    http.begin(flaskServerURL);
    http.addHeader("Content-Type", "application/json");

    String json = "{\"voltage\":" + String(voltage, 2) + 
                  ",\"current\":" + String(current, 3) + 
                  ",\"power\":" + String(power, 2) + 
                  ",\"energy\":" + String(energy, 3) + 
                  ",\"frequency\":" + String(frequency, 1) + 
                  ",\"pf\":" + String(pf, 2) + "}";

    int code = http.POST(json);
    Serial.println(code > 0 ? "✅ Sent" : "❌ Failed");
    http.end();
  }

  delay(2000);
}
