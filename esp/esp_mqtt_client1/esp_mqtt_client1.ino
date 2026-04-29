#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

const char* ssid = "asistenaja";
const char* password = "digidawpalingcool";

const char* mqtt_server = "192.168.0.145";

WiFiClient espClient;
PubSubClient client(espClient);

#define BUZZER 22

// =========================
// WIFI
// =========================
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

  Serial.println("\nWiFi connected");
}

// =========================
// BUZZER (NON BLOCKING STYLE SEDERHANA)
// =========================
void buzzer_alert() {
  Serial.println("BUZZER TRIGGERED!");

  for (int i = 0; i < 10; i++) {
    digitalWrite(BUZZER, HIGH);
    delay(300);
    digitalWrite(BUZZER, LOW);
    delay(300);
  }
}

// =========================
// CALLBACK MQTT (JSON PARSE)
// =========================
void callback(char* topic, byte* message, unsigned int length) {

  Serial.print("Message arrived: ");

  String payload;
  for (int i = 0; i < length; i++) {
    payload += (char)message[i];
  }

  Serial.println(payload);

  // =========================
  // PARSE JSON
  // =========================
  StaticJsonDocument<200> doc;

  DeserializationError error = deserializeJson(doc, payload);

  if (error) {
    Serial.print("JSON parse failed: ");
    Serial.println(error.c_str());
    return;
  }

  int table = doc["table"];
  int waiting_time = doc["waiting_time"];

  Serial.print("Table: ");
  Serial.println(table);

  Serial.print("Waiting Time: ");
  Serial.println(waiting_time);

  // =========================
  // LOGIC BUZZER
  // =========================
  if (waiting_time >= 10) {
    buzzer_alert();
  }
}

// =========================
// RECONNECT MQTT
// =========================
void reconnect() {
  while (!client.connected()) {

    Serial.print("Connecting MQTT...");

    if (client.connect("ESP32_client")) {

      Serial.println("connected");

      // topic baru (JSON)
      client.subscribe("cafe/cafe1/alert");

    } else {

      Serial.print("failed, rc=");
      Serial.println(client.state());
      delay(2000);
    }
  }
}

// =========================
// SETUP
// =========================
void setup() {
  pinMode(BUZZER, OUTPUT);
  digitalWrite(BUZZER, HIGH);
  delay(500);
  digitalWrite(BUZZER, LOW);

  Serial.begin(115200);
  setup_wifi();
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);
}

// =========================
// LOOP
// =========================
void loop() {

  if (!client.connected()) {
    reconnect();
  }

  client.loop();
}