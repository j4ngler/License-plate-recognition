import datetime, os, logging, queue
import function.helper as helper
import function.utils_rotate as utils_rotate
from .utils import save_image, ensure_dir
from .config import IMG_DIR
import torch, re, cv2
from .mqtt_client import publish_plate

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
            x1, y1, x2, y2 = map(int, plate[:4])
            crop_img = frame[y1:y2, x1:x2]
            if crop_img.size > 0:
                try:
                    ocr_queue.put((crop_img.copy(), (x1, y1)), timeout=1)
                except queue.Full:
                    pass

            # Vẽ khung detect để debug (nếu cần)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)

        # Show preview
        cv2.imshow("Detect", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            stop_event.set()
            break

        frame_queue.task_done()

def ocr_worker(stop_event, ocr_queue):
    """Worker OCR biển số (chỉ lưu 1 ảnh mới nhất khi cùng biển số)"""
    last_plate = None
    same_count = 0
    MAX_COUNT = 3  # detect tối đa 3 ảnh liên tiếp trước khi lưu

    while not stop_event.is_set():
        try:
            crop_img, _ = ocr_queue.get(timeout=1)
        except queue.Empty:
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
            # Nếu là biển số mới → reset counter
            if lp != last_plate:
                last_plate = lp
                same_count = 1
            else:
                same_count += 1

            # Chỉ lưu khi đủ 3 lần hoặc khi biển số mới xuất hiện
            if same_count >= MAX_COUNT:
                ts = datetime.datetime.now()
                day_dir = os.path.join(IMG_DIR, ts.strftime("%Y-%m-%d"))
                ensure_dir(day_dir)
                img_path = save_image(crop_img, day_dir, f"{ts.strftime('%H%M%S')}_{lp}.jpg")
                log.info(f"[{ts}] OCR: {lp} -> saved {img_path}")
                
                 # Gửi MQTT qua hàm có sẵn
                publish_plate(lp, ts.isoformat())
                log.info(f"[MQTT] Sent: {lp}")

                same_count = 0  # reset để tránh lưu liên tục