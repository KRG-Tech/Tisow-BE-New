# Use an official Python base image
FROM ubuntu:22.04 AS builder

# Install dependencies for PyInstaller and FastAPI app
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-venv \
    python3-dev \
    python3-pip \
    curl \
    libmariadb-dev \
    libglib2.0-0


# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and source code
COPY requirements.txt .
COPY . .

# Create a virtual environment
RUN python3 -m venv venv

# Install dependencies inside the virtual environment
RUN . venv/bin/activate && pip install --no-cache-dir -r requirements.txt

# Install PyInstaller inside the virtual environment
RUN . venv/bin/activate && pip install pyinstaller

# Copy the custom hook file into the container
COPY /app/hooks/hook-sqlalchemy.dialects.mariadb.mariadbconnector.py /app/hooks/

# Package the FastAPI app into a single executable
#RUN . venv/bin/activate && pyinstaller --onefile /app/app/main.py
RUN . venv/bin/activate && pyinstaller /app/app/main.py --onefile --collect-all sqlalchemy --collect-all mariadb


FROM ubuntu:22.04
# Set the working directory for the final container
WORKDIR /app

# Copy the FastAPI standalone executable from the build stage
COPY --from=builder /app/dist/main /app/main


# Make the executable runnable
RUN chmod +x /app/main

# Expose the FastAPI port (adjust if needed)
EXPOSE 8000

# Command to run the FastAPI app as the standalone executable
CMD ["/app/main"]
