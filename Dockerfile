FROM python:3.11-slim

WORKDIR /app

COPY requerements.txt .
RUN pip install --no-cache-dir -r requerements.txt

COPY . .

CMD ["python", "main.py"]
