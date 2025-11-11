FROM python:3.11-slim

WORKDIR /app

# X¢Â’³ÔüWf¤ó¹Èüë
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ¢×ê±ü·çó³üÉ’³Ôü
COPY . .

# İüÈ’l‹
EXPOSE 8050

# ¢×ê±ü·çó’wÕ
CMD ["python3", "main.py"]
