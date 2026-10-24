FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Run as an unprivileged user. The app writes its log files to the working directory.
RUN useradd --create-home --uid 1000 ibc && chown -R ibc:ibc /app
USER ibc

# Redis and MongoDB hosts. Override these at runtime (compose.yml sets them).
ENV REDIS_GATEWAY=redis \
    MONGODB_GATEWAY=mongo

EXPOSE 2611

# Starts the web app, the consensus service and the execution service.
CMD ["bash", "docker-start.sh"]
