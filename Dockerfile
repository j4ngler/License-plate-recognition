FROM python:3.7-slim

WORKDIR /opt/app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy source
COPY app ./app
COPY main.py .
COPY model ./model
COPY yolov5 ./yolov5

# cài yolov5 như editable package để torch.hub tìm thấy
RUN pip install --no-cache-dir -e ./yolov5

ENV PYTHONUNBUFFERED=1
CMD ["python", "main.py"]
