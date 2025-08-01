"""
Đọc cấu hình từ biến môi trường, cung cấp hằng số cho toàn hệ thống.
"""

import os

# Camera & xử lý
RTSP_URL          = os.getenv("RTSP_URL", "rtsp://admin:UIZCHI@192.168.100.98:554/cam/realmonitor?channel=1&subtype=1")
DETECT_EVERY_SEC  = int(os.getenv("DETECT_EVERY_SEC", "5"))

# Lưu ảnh
IMG_DIR           = os.getenv("IMG_DIR", "D:\\Intern\\license-plate-recognition\\app\\data")
KEEP_DAYS         = int(os.getenv("KEEP_DAYS", "15"))

# MQTT
MQTT_HOST  = os.getenv("MQTT_HOST", "123.30.140.221")
MQTT_PORT  = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER  = os.getenv("MQTT_USER", "iotuser")
MQTT_PASS  = os.getenv("MQTT_PASS", "ecomes")
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "ai/license_plate")

# MySQL  (XAMPP)
DB_HOST = os.getenv("DB_HOST", "localhost")  # container → máy host
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "")          # XAMPP mặc định rỗng
DB_NAME = os.getenv("DB_NAME", "license_plate")

