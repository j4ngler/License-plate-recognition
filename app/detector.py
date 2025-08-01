import datetime, os, logging
import function.helper as helper
import function.utils_rotate as utils_rotate
from .utils import save_image, ensure_dir
from .config import IMG_DIR
import torch, re

log = logging.getLogger("detector")

# Load models 1 lần
yolo_LP_detect = torch.hub.load('yolov5', 'custom', path='model/LP_detector_nano_61.pt', source='local')
yolo_LP_detect.conf = 0.4
yolo_license_plate = torch.hub.load('yolov5', 'custom', path='model/LP_ocr_nano_62.pt', source='local')
yolo_license_plate.conf = 0.5

PLATE_PATTERN = re.compile(r'^\d{2}[A-Z]-?\d{4,5}$')

def detect_worker(stop_event, frame_queue, ocr_queue):
    """Worker detect biển số, crop và đẩy vào ocr_queue"""
    while not stop_event.is_set():
        try:
            frame = frame_queue.get(timeout=1)
        except:
            continue

        try:
            det = yolo_LP_detect(frame, size=640)
            list_plates = det.pandas().xyxy[0].values.tolist()
        except Exception as e:
            log.error(f"[DETECT] Lỗi detect: {e}")
            continue

        for plate in list_plates:
            try:
                x1, y1, x2, y2 = map(int, plate[:4])
                crop_img = frame[y1:y2, x1:x2]
                if not ocr_queue.full():
                    ocr_queue.put(crop_img)
            except Exception as e:
                log.warning(f"[DETECT] Crop lỗi: {e}")
                continue


def ocr_worker(stop_event, ocr_queue):
    """Worker OCR biển số"""
    while not stop_event.is_set():
        try:
            crop_img = ocr_queue.get(timeout=1)
        except:
            continue

        lp = ""
        for cc in range(2):
            for ct in range(2):
                rotated = utils_rotate.deskew(crop_img, cc, ct)
                lp = helper.read_plate(yolo_license_plate, rotated)
                if lp != "unknown":
                    break
            if lp != "unknown":
                break

        if lp != "unknown":
            ts = datetime.datetime.now()
            day_dir = os.path.join(IMG_DIR, ts.strftime("%Y-%m-%d"))
            ensure_dir(day_dir)
            img_path = save_image(crop_img, day_dir, f"{ts.strftime('%H%M%S')}_{lp}.jpg")
            log.info(f"[{ts}] OCR: {lp} -> saved {img_path}")
