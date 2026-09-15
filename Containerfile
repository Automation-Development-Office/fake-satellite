FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY seed ./seed

RUN mkdir -p /data

ENV FAKE_SATELLITE_DB=/data/satellite.db
ENV FAKE_SATELLITE_SEED=/app/seed/satellite.yml

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
