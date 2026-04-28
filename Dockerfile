FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

ARG CACHE_BUST=1
RUN echo $CACHE_BUST

COPY . .

ENV PYTHONUNBUFFERED=1

EXPOSE 8080

CMD ["python", "start.py"]
