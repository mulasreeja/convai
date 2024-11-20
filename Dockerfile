# Use the official Python image
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy requirements.txt and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app code
COPY . .

# Copy the Google Cloud credentials file
COPY assignment1-436717-bb91a69867dc.json /app/assignment1-436717-bb91a69867dc.json

# Set the environment variable for Google Cloud credentials
ENV GOOGLE_APPLICATION_CREDENTIALS="/app/assignment1-436717-bb91a69867dc.json"

# Expose the port the app runs on
EXPOSE 8080

# Run the Flask app
CMD ["python", "main.py"]