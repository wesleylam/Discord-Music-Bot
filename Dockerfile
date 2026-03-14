# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Install system dependencies
# ffmpeg for audio processing, libopus for voice, and git for patch notes
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libopus-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container at /app
COPY . .

# Define the command to run the application
CMD ["python", "DJ.py"]