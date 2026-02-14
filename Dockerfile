# 1. Use an official, lightweight Python image
FROM python:3.10-slim

# 2. Prevent Python from writing messy .pyc files and force standard output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Create a clean working directory inside the container
WORKDIR /app

# 4. Copy ONLY the requirements first (this tricks Docker into caching the heavy installations!)
COPY requirements.txt .

# 5. Install your bot dependencies without storing unnecessary cache files
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 6. Now copy the rest of your actual bot code into the container
COPY . .

# 7. Expose the port your Flask dashboard uses (Render often defaults to 10000)
EXPOSE 10000

# 8. The command that fires up the bot when the container starts
CMD ["python", "app.py"]
