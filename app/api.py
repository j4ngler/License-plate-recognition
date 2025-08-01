from fastapi import FastAPI, Response
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import threading, cv2, io, asyncio, time

from .scheduler import run
from .scheduler import frame_queue
from .db import get_recent_plates
from .config import IMG_DIR

app = FastAPI(title="LP Backend API")

# 1. Mount folder static/ cho index.html, CSS, JS
app.mount("/static", StaticFiles(directory="static"), name="static")
# 2. Mount folder ảnh lưu plate
app.mount("/data", StaticFiles(directory=IMG_DIR), name="data")

# 3. Chạy scheduler khi startup
@app.on_event("startup")
def startup_event():
    run()

# 4. Trang index (giao diện)
@app.get("/", response_class=HTMLResponse)
async def index():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

# 5. API lấy JSON lịch sử
@app.get("/api/plates")
async def api_plates(limit: int = 50):
    rows = get_recent_plates(limit)
    # convert datetime → isoformat
    for r in rows:
        r["ts"] = r["ts"].isoformat()
        # path tới URL
        r["img_url"] = r["img_path"].replace(IMG_DIR, "/data")
    return rows

# 6. MJPEG live‑stream
def mjpeg_generator():
    for frame in frames():
        ret, jpeg = cv2.imencode(".jpg", frame)
        if not ret:
            continue
        chunk = (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" +
            jpeg.tobytes() +
            b"\r\n"
        )
        yield chunk
        # điều chỉnh fps stream (nếu cần)
        time.sleep(0.03)

@app.get("/stream")
def stream():
    return StreamingResponse(
        mjpeg_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )
