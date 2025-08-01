import cv2, time, logging
from .config import RTSP_URL

log = logging.getLogger("capture")

def capture_worker(stop_event, frame_queue):
    """Worker đọc camera RTSP và đẩy frame vào queue"""
    cap = None

    def connect():
        nonlocal cap
        if cap:
            cap.release()
        cap = cv2.VideoCapture(RTSP_URL)
        if not cap.isOpened():
            log.error(f"Cannot open RTSP {RTSP_URL}, retrying in 5s...")
            return False
        log.info("RTSP opened.")
        return True

    # Kết nối ban đầu
    while not connect():
        if stop_event.is_set():
            return
        time.sleep(5)

    while not stop_event.is_set():
        ret, frame = cap.read()
        if ret:
            if not frame_queue.full():
                frame_queue.put(frame)
        else:
            log.warning("Frame grab failed, reconnecting in 2s...")
            time.sleep(2)
            connect()
