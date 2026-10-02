import json
import logging
import time
from queue import Queue, Empty
from threading import Thread, Event
import paho.mqtt.client as mqtt

from analytics.live.openf1.auth import OpenF1AuthService

logger = logging.getLogger(__name__)

class OpenF1Transport:
    def __init__(self, auth_service: OpenF1AuthService):
        self.auth_service = auth_service
        self.broker = "mqtt.openf1.org"
        self.port = 8883
        self.message_queue = Queue()
        self.running = Event()
        self.client = None
        self.thread = None

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("Connected to OpenF1 MQTT Broker.")
            # Subscribe to relevant topics for a session (using wildcards or specific topics)
            # Typically topics are v1/sessions, v1/laps, etc.
            client.subscribe("v1/#")
        else:
            logger.error(f"Failed to connect to OpenF1 MQTT Broker, return code {rc}")

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
            self.message_queue.put((msg.topic, payload))
        except Exception as e:
            logger.warning(f"Failed to decode message from {msg.topic}: {e}")

    def on_disconnect(self, client, userdata, rc):
        logger.warning(f"Disconnected from OpenF1 MQTT Broker (rc: {rc})")
        if rc != 0 and self.running.is_set():
            logger.info("Attempting automatic reconnect...")

    def _mqtt_loop(self):
        while self.running.is_set():
            try:
                token = self.auth_service.get_token()
                self.client = mqtt.Client(transport="websockets")
                # Using token as password (OpenF1 convention)
                self.client.username_pw_set(username="token", password=token)
                self.client.on_connect = self.on_connect
                self.client.on_message = self.on_message
                self.client.on_disconnect = self.on_disconnect
                
                # Websocket endpoint is typically on port 8084 as per docs, or standard MQTTS on 8883
                # We'll use 8084 websockets.
                self.client.connect("mqtt.openf1.org", 8084, 60)
                self.client.loop_forever()
            except Exception as e:
                logger.error(f"MQTT connection error: {e}")
                time.sleep(5) # Exponential backoff would be better, but simple retry for now

    def start(self):
        self.running.set()
        self.thread = Thread(target=self._mqtt_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running.clear()
        if self.client:
            self.client.disconnect()
        if self.thread:
            self.thread.join(timeout=2)

    def get_messages(self, timeout=1.0):
        messages = []
        while True:
            try:
                msg = self.message_queue.get(timeout=timeout if not messages else 0.1)
                messages.append(msg)
            except Empty:
                break
        return messages
