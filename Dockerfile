FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all Python files
COPY *.py ./

# Run the bot with unbuffered output for better logging
CMD ["python", "-u", "main.py"]
