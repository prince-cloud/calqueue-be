# Pull base image (Python 3.13 stable)
FROM python:3.13-slim-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create and set work directory
RUN mkdir -p /code
WORKDIR /code

# Install system dependencies for building pycairo, weasyprint, and related libraries
RUN --mount=target=/var/lib/apt/lists,type=cache,sharing=locked \
    --mount=target=/var/cache/apt,type=cache,sharing=locked \
    apt update && \
    apt upgrade -y && \
    apt-get install -y \
        build-essential \
        libcairo2-dev \
        libpango1.0-dev \
        libgdk-pixbuf2.0-dev \
        libffi-dev \
        libjpeg-dev \
        libxslt1-dev \
        zlib1g-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /root/.cache/

# Install Python dependencies
COPY requirements.txt /tmp/requirements.txt

RUN --mount=type=cache,target=/root/.cache \
    set -ex && \
    pip install --upgrade pip && \
    pip install -r /tmp/requirements.txt

# Clean up cache to reduce image size
RUN rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /root/.cache/

# Copy local project
COPY . /code/

# Expose port 8000
EXPOSE 8000

# Use gunicorn on port 8000
CMD ["gunicorn", "--bind", ":8000", "--workers", "2", "config.wsgi"]
