#!/bin/bash
set -euo pipefail

# Zona horaria en contenedor (logs, date() PHP si no hay ini)
if [[ -n "${TZ:-}" ]]; then
    echo "date.timezone = ${TZ}" > /usr/local/etc/php/conf.d/zz-timezone.ini
fi

# Instalación opcional de dependencias Composer en submódulos del repo (mPDF, chosen, etc.)
if [[ "${RUN_COMPOSER_INSTALL:-0}" == "1" ]]; then
    for d in \
        /var/www/html/mayoristapp/_lib/mpdf2 \
        /var/www/html/mayoristapp/chosen
    do
        if [[ -f "${d}/composer.json" ]]; then
            echo "ecom-php: composer install en ${d}"
            (cd "${d}" && composer install --no-interaction --prefer-dist --no-dev 2>/dev/null) || \
            (cd "${d}" && composer install --no-interaction --prefer-dist) || true
        fi
    done
fi

exec "$@"
