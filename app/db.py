"""
Lớp truy cập MySQL đơn giản (mysql-connector-python).
"""

import datetime, mysql.connector
from .config import DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME
import logging

log = logging.getLogger("db")


def _conn():
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        autocommit=True,
    )


def init_schema() -> None:
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS plates (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            plate     VARCHAR(16) NOT NULL,
            ts        DATETIME    NOT NULL,
            img_path  VARCHAR(255) NOT NULL
        )
        """
    )
    cur.close()
    conn.close()
    log.info("Schema checked/created.")

# bổ sung import
from typing import List, Dict

def get_recent_plates(limit: int = 100) -> List[Dict]:
    conn = _conn()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        "SELECT plate, ts, img_path FROM plates ORDER BY ts DESC LIMIT %s",
        (limit,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def save_plate(plate: str, img_path: str, ts: datetime.datetime, vehicle_type: str) -> None:
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO plates (plate, ts, img_path) VALUES (%s, %s, %s)",
        (plate, ts, img_path, vehicle_type),
    )
    cur.close()
    conn.close()
    log.debug("Saved plate %s – %s", plate, img_path, vehice_type)
