import paho.mqtt.client as mqtt
import json


class MQTTHandler:
    def __init__(self, broker="broker.hivemq.com", port=1883):
        self.client = mqtt.Client()
        self.client.connect(broker, port, 60)

    def send_buzzer(self, cafe_id, table_id, waiting_time):
        topic = f"cafe/{cafe_id}/alert"

        payload = {
            "table": table_id,
            "waiting_time": waiting_time
        }

        self.client.publish(topic, json.dumps(payload))

        print(f"[MQTT] Alert sent to {topic}")