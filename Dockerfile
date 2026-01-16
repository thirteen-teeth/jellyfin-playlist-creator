FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the script
COPY jellyfin_playlist_creator.py .

# Set the entrypoint
ENTRYPOINT ["python", "jellyfin_playlist_creator.py"]
