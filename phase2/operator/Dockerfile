FROM python:3.13-slim

WORKDIR /app

RUN pip install --no-cache-dir kopf kubernetes requests

COPY main.py reconciler.py ./

CMD ["kopf", "run", "/app/main.py", "--verbose", "--liveness=http://0.0.0.0:8080/healthz"]
