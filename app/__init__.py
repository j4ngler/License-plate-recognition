"""
Package backend AI – license plate recognition & notification service.
Khởi tạo logging mặc định, có thể sửa tùy nhu cầu.
"""
import logging, os, sys

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
    stream=sys.stdout,
)
