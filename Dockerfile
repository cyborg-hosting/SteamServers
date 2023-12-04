FROM python:3.11-slim

ADD requirements.txt .
RUN pip install --no-cache-dir --requirement requirements.txt

ADD main.py /app/
ADD querybot/ /app/querybot/

WORKDIR /data

CMD [ "python", "/app/main.py"]
