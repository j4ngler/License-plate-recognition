from app.scheduler import run

if __name__ == "__main__":
    import uvicorn
    # chạy FastAPI app in-process, scheduler đã start trong @startup_event
    uvicorn.run(
        "app.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,         # chỉ dev, khi deploy bỏ reload
        log_level="info"
    )