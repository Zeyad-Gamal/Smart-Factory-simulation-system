# ══════════════════════════════════════════════
#  SCADA Backend — Dockerfile
#  Runs: Laravel server + scheduler (via supervisor)
#  Build: docker build -t scada-back .
# ══════════════════════════════════════════════
FROM php:8.3-cli-alpine

RUN rm -rf /var/cache/apk/*

# System dependencies
RUN apk update && apk add --no-cache \
    bash \
    git \
    unzip \
    curl \
    libzip-dev \
    oniguruma-dev \
    icu-dev \
    autoconf \
    g++ \
    make \
    libc-dev \
    file \
    re2c \
    supervisor

# PHP extensions
RUN docker-php-ext-install \
    pdo \
    pdo_mysql \
    mbstring \
    intl \
    zip

# Composer
COPY --from=composer:latest /usr/bin/composer /usr/bin/composer

# Security
RUN addgroup -S laravelgroup && adduser -S laraveluser -G laravelgroup

WORKDIR /var/www

# Copy full Laravel project
COPY Scada-main-system/ /var/www

# Install dependencies
RUN composer install \
    --no-dev \
    --optimize-autoloader \
    --no-interaction

# Permissions
RUN chown -R laraveluser:laravelgroup /var/www
RUN chmod -R 775 storage bootstrap/cache
RUN rm -f bootstrap/cache/*.php

# Supervisor config
COPY docker/scada-backend/supervisord.conf /etc/supervisord.conf
EXPOSE 8000


CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]