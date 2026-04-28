<?php
/**
 * Configuración MySQL para administraNET-ecom en el contenedor PHP de Synap.
 * Se monta en mayoristapp/includes/; las credenciales vienen de variables de entorno del servicio Docker.
 * No incluir contraseñas de producción aquí.
 */

$host = getenv('SYNAP_MYSQL_HOST') ?: 'Synap_mysql57';
$port = getenv('SYNAP_MYSQL_PORT') ?: '3306';

if (!defined('administranetLOCAL')) {
    define('administranetLOCAL', $host);
}
if (!defined('administranetEXTERNO')) {
    define('administranetEXTERNO', $host);
}
if (!defined('servidor_db')) {
    define('servidor_db', $host);
}
if (!defined('puerto_db')) {
    define('puerto_db', $port);
}

define('usuario_db', getenv('SYNAP_MYSQL_USER') ?: 'administranet');
define('password_db', getenv('SYNAP_MYSQL_PASSWORD') ?: 'administranet_local');
