FROM python:3.12-slim

WORKDIR /app

# Install dependencies first to optimize layer caching
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app code
COPY . .
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# EXPOSE is for documentation purposes only.
# The actual port mapping is handled by Docker runtime.
EXPOSE 5500

ENTRYPOINT ["/entrypoint.sh"]
