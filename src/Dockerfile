FROM docker.io/python:3.13-alpine AS base

# Install run-time and compile-time system dependencies
USER root
RUN apk add --no-cache \
    make \
    bash

# Create and switch to non-root user
RUN addgroup -g 1000 runner \
    && adduser -G runner -u 1000 -D runner
USER runner

# Install run-time and compile-time local dependencies

# Create required folders and change to source directory
RUN mkdir -p /home/runner/src \
    /var/tmp/deps
WORKDIR /home/runner/src

# Install run-time and compile-time project dependencies
COPY --chown=runner:runner requirements.tx[t] ./
RUN [ -f "requirements.txt" ] \
    && python -m venv venv \
    && . venv/bin/activate \
    && pip install -r requirements.txt

#
# Production
#

FROM base AS production

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_APP=app

# Copy source and build
USER runner
WORKDIR /home/runner/src
COPY --chown=runner:runner . .

# Create required folders
RUN mkdir -p /home/runner/src/data

# Expose required ports
EXPOSE 5000

# Define entrypoint
COPY --chown=runner:runner ./scripts/entrypoint-prod.sh /var/tmp
ENTRYPOINT ["/var/tmp/entrypoint-prod.sh"]

#
# Development
#

FROM base AS development

# Install dev-time system dependencies
USER root
RUN apk add --no-cache \
    libstdc++ \
    curl \
    inotify-tools \
    ripgrep

# Change to non-root user
USER runner

# Install dev-time local dependencies

# Change to source directory
WORKDIR /home/runner/src

# Install dev-time project dependencies

# Move temporally project dependencies and clean source directory
RUN mv venv /var/tmp/deps \
    && find /home/runner/src -mindepth 1 -delete

# Expose required ports
EXPOSE 5000

# Define entrypoint
COPY --chown=runner:runner ./scripts/entrypoint-dev.sh /var/tmp
ENTRYPOINT ["/var/tmp/entrypoint-dev.sh"]

