FROM python:3.10-slim

# Set the working directory
WORKDIR /usr/src/app

# Install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app files
COPY . .

# Command to run the analytics service
CMD ["python", "analytics_service.py"]
