FROM python:3.13-slim

WORKDIR /app

RUN pip install --no-cache-dir flask kubernetes gunicorn

COPY app.py ./
COPY templates/ ./templates/

EXPOSE 5000

CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "app:app"]
