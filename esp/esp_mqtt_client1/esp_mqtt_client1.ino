#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

const char* ssid = "Buya Danzel";
const char* password = "priasigma";

const char* mqtt_server = "10.198.49.53";

WiFiClient espClient;
PubSubClient client(espClient);

#define BUZZER 22
#define LED 25

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
// ALERT (BUZZER + LED)
// =========================
void alert_signal() {
  Serial.println("ALERT TRIGGERED!");

  for (int i = 0; i < 10; i++) {
    digitalWrite(BUZZER, HIGH);
    digitalWrite(LED, HIGH);
    delay(300);

    digitalWrite(BUZZER, LOW);
    digitalWrite(LED, LOW);
    delay(300);
  }
}

// =========================
// CALLBACK MQTT
// =========================
void callback(char* topic, byte* message, unsigned int length) {

  String payload;
  for (int i = 0; i < length; i++) {
    payload += (char)message[i];
  }

  Serial.println(payload);

  StaticJsonDocument<200> doc;

  if (deserializeJson(doc, payload)) {
    Serial.println("JSON parse error");
    return;
  }

  int table = doc["table"];
  int waiting_time = doc["waiting_time"];

  Serial.printf("Table: %d | Waiting: %d\n", table, waiting_time);

  // =========================
  // LOGIC
  // =========================
  if (waiting_time >= 10) {
    alert_signal();
  } else {
    digitalWrite(LED, LOW);  // pastikan mati 
  }
}

// =========================
// MQTT RECONNECT
// =========================
void reconnect() {
  while (!client.connected()) {

    Serial.print("Connecting MQTT...");

    if (client.connect("ESP32_client")) {

      Serial.println("connected");
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
  pinMode(LED, OUTPUT);

  digitalWrite(BUZZER, LOW);
  digitalWrite(LED, LOW);

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