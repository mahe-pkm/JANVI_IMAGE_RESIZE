FROM python:3.11-slim
WORKDIR /app
COPY requirements-cpu.txt .
RUN pip install --no-cache-dir -r requirements-cpu.txt
COPY . .
ENV BASE_DIR=/data HOST=0.0.0.0 PYTHONUNBUFFERED=1
EXPOSE 5000
CMD ["python", "app.py"]
