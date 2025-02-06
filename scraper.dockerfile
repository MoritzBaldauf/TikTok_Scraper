FROM mcr.microsoft.com/playwright/python:v1.41.0-focal

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create necessary directories
RUN mkdir -p tiktok_data

# Install the specific version of browsers we need
RUN playwright install chromium

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the script
CMD ["python", "main.py"]