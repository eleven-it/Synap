# PHP 5.6 + Apache para administraNET-ecom (legacy procedural + mysqli).
# Base: imagen oficial php:5.6-apache (Debian Stretch) → Apache 2.4.x, no 2.2 (ver docs).
# El código se monta por volumen (git pull en el host).

FROM php:5.6-apache

# Stretch está en archive.debian.org; claves apt expiradas en Stretch.
RUN printf '%s\n' \
        'deb http://archive.debian.org/debian stretch main' \
        'deb http://archive.debian.org/debian-security stretch/updates main' \
        > /etc/apt/sources.list \
    && printf '%s\n' \
        'Acquire::Check-Valid-Until "false";' \
        'APT::Get::AllowUnauthenticated "true";' \
        'Acquire::AllowInsecureRepositories "true";' \
        'Acquire::AllowDowngradeToInsecureRepositories "true";' \
        > /etc/apt/apt.conf.d/99synap-ecom-archive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libfreetype6-dev \
        libjpeg62-turbo-dev \
        libpng-dev \
        libzip-dev \
        libicu-dev \
        unzip \
    && docker-php-ext-configure gd \
        --with-freetype-dir=/usr/include/ \
        --with-jpeg-dir=/usr \
        --with-png-dir=/usr \
    && docker-php-ext-install -j"$(nproc)" \
        gd \
        intl \
        mysqli \
        pdo_mysql \
        opcache \
        zip \
        mbstring \
    && a2enmod rewrite headers access_compat \
    && rm -rf /var/lib/apt/lists/*

# Composer 2 requiere PHP ≥ 7.2; para 5.6 usar rama 1.x
COPY --from=composer:1.10 /usr/bin/composer /usr/bin/composer

COPY apache-site.conf /etc/apache2/sites-available/000-default.conf
COPY conf.d/synap-ecom.ini /usr/local/etc/php/conf.d/synap-ecom.ini

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint-ecom-php.sh
RUN chmod +x /usr/local/bin/docker-entrypoint-ecom-php.sh

EXPOSE 80

ENTRYPOINT ["/usr/local/bin/docker-entrypoint-ecom-php.sh"]
CMD ["apache2-foreground"]
