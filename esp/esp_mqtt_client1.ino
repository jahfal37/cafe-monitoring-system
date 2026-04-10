#include <WiFi.h>
#include <PubSubClient.h>

const char* ssid = "Kost buk wati";
const char* password = "adek0708";

const char* mqtt_server = "192.168.100.99"; // IP Raspberry Pi

WiFiClient espClient;
PubSubClient client(espClient);

#define BUZZER 15

void setup_wifi() {

  delay(10);
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi connected");
}

void buzzer_alert() {

  Serial.println("Buzzer ON for 10 seconds");

  unsigned long startTime = millis();

  while (millis() - startTime < 10000) {

    digitalWrite(BUZZER, HIGH);
    delay(500);

    digitalWrite(BUZZER, LOW);
    delay(500);
  }

}

void callback(char* topic, byte* message, unsigned int length) {

  String msg;

  for (int i = 0; i < length; i++) {
    msg += (char)message[i];
  }

  Serial.print("Message received: ");
  Serial.println(msg);

  if (msg == "10") {
    buzzer_alert();
  }

}

void reconnect() {

  while (!client.connected()) {

    Serial.print("Connecting MQTT...");

    if (client.connect("ESP32_client")) {

      Serial.println("connected");
      client.subscribe("cafe/waiting_time");

    } else {

      Serial.print("failed, rc=");
      Serial.println(client.state());
      delay(2000);

    }
  }
}

void setup() {

  pinMode(BUZZER, OUTPUT);
  Serial.begin(115200);

  setup_wifi();

  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);
}

void loop() {

  if (!client.connected()) {
    reconnect();
  }

  client.loop();
}