import json
import logging
import paho.mqtt.client as mqtt
from typing import Optional
from .config import MQTT_HOST, MQTT_PORT, MQTT_TOPIC, MQTT_USER, MQTT_PASS

log = logging.getLogger("mqtt")
_client: Optional[mqtt.Client] = None  # dùng Optional thay vì `|`

def _ensure_client() -> mqtt.Client:
    global _client
    if _client is not None:
        return _client

    _client = mqtt.Client()
    if MQTT_USER:
        _client.username_pw_set(MQTT_USER, MQTT_PASS)
    _client.connect(MQTT_HOST, MQTT_PORT)
    log.info("Connected to MQTT %s:%s as %s", MQTT_HOST, MQTT_PORT, MQTT_USER or "<anonymous>")
    return _client

def publish_plate(plate: str, ts_iso: str) -> None:
    payload = json.dumps({"plate": plate, "timestamp": ts_iso})
    _ensure_client().publish(MQTT_TOPIC, payload)
    log.debug("MQTT ▶ %s – %s", MQTT_TOPIC, payload)
