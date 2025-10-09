# Use an official lightweight Python image as a parent image
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY ca.pem .

# This EXPOSE is for documentation; Cloud Run uses the PORT env var.
EXPOSE 8000

# Run the application as a module to enable relative imports
# and execute the __main__ block.
CMD ["python", "-m", "src.main"]
