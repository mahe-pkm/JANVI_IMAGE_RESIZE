FROM python:3.10-slim

# Set work directory
WORKDIR /app

# Install system dependencies needed for imaging libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install CPU-only PyTorch and torchvision first to optimize image footprint
RUN pip install --no-cache-dir torch==2.2.1 torchvision==0.17.1 --index-url https://download.pytorch.org/whl/cpu

# Install remaining dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application files
COPY . .

# Ensure standard directory structures exist inside the container
RUN mkdir -p Resizing Re-sized

# Expose flask port
EXPOSE 5000

# Set environment variables
ENV BASE_DIR=/app
ENV PYTHONUNBUFFERED=1

# Command to run the Flask application
CMD ["python", "app.py"]
