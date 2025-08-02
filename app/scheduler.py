import threading, time, logging, queue, traceback
from .capture import capture_worker
from .detector import detect_worker, ocr_worker
from .db import init_schema
from .utils import cleanup_old
from .config import IMG_DIR, KEEP_DAYS

log = logging.getLogger("scheduler")
log.setLevel(logging.INFO)

frame_queue = queue.Queue(maxsize=10)   # Frame từ camera
plate_queue = queue.Queue(maxsize=20)
ocr_queue = queue.Queue(maxsize=30)    # Crop biển số từ detect

stop_event = threading.Event()

def _cleanup_loop():
    """Dọn ảnh cũ"""
    log.info("[Scheduler] Cleanup loop START.")
    while not stop_event.is_set():
        cleanup_old(IMG_DIR, KEEP_DAYS)
        time.sleep(3600 * 12)

def save_worker():
    while not stop_event.is_set():
        try:
            target(**args)
        except:
            log.error(f"[Worker Crash] {target.__name__}: {e}")
            log.error(traceback.format_exc())
            time.sleep(1)

def run():
    init_schema()

    # Start threads
    threading.Thread(target=capture_worker, args=(stop_event, frame_queue), daemon=True).start()
    threading.Thread(target=detect_worker, args=(stop_event, frame_queue, ocr_queue), daemon=True).start()
    threading.Thread(target=ocr_worker, args=(stop_event, ocr_queue), daemon=True).start()
    threading.Thread(target=_cleanup_loop, daemon=True).start()

    log.info("Backend AI READY – press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_event.set()
        log.info("Stopping backend...")
