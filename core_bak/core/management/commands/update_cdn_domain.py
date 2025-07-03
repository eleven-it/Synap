from django.core.management.base import BaseCommand
from core.models import SystemConfiguration

class Command(BaseCommand):
    help = 'Actualiza el dominio del CDN'

    def add_arguments(self, parser):
        parser.add_argument(
            'domain',
            type=str,
            help='Nuevo dominio del CDN (ej: cdn.tudominio.com)',
        )
        parser.add_argument(
            '--provider',
            type=str,
            choices=['cloudflare', 'aws', 'bunny'],
            default='cloudflare',
            help='Proveedor del CDN (default: cloudflare)',
        )

    def handle(self, *args, **options):
        domain = options['domain']
        provider = options['provider']
        
        self.stdout.write(f"🔄 Actualizando dominio del CDN...")
        self.stdout.write(f"Proveedor: {provider}")
        self.stdout.write(f"Nuevo dominio: {domain}")
        
        # Actualizar configuración según el proveedor
        if provider == 'cloudflare':
            config_key = 'cdn.cloudflare.domain'
            env_var = 'CLOUDFLARE_DOMAIN'
        elif provider == 'aws':
            config_key = 'cdn.aws.domain'
            env_var = 'AWS_S3_CUSTOM_DOMAIN'
        elif provider == 'bunny':
            config_key = 'cdn.bunny.domain'
            env_var = 'BUNNY_CDN_DOMAIN'
        
        # Actualizar en SystemConfiguration
        config, created = SystemConfiguration.objects.update_or_create(
            key=config_key,
            defaults={
                'value': domain,
                'description': f'Dominio del CDN {provider}',
                'is_active': True
            }
        )
        
        if created:
            self.stdout.write(f"✅ Configuración creada: {config_key} = {domain}")
        else:
            self.stdout.write(f"✅ Configuración actualizada: {config_key} = {domain}")
        
        # Limpiar cache
        from django.core.cache import cache
        cache.delete('system_configuration')
        
        # Mostrar configuración actualizada
        self.stdout.write("\n📋 Configuración actual del CDN:")
        cdn_configs = SystemConfiguration.objects.filter(key__startswith='cdn.')
        for config in cdn_configs:
            self.stdout.write(f"  {config.key}: {config.value}")
        
        # Instrucciones para variables de entorno
        self.stdout.write(f"\n💡 Para usar variables de entorno, agrega a tu .env:")
        self.stdout.write(f"   {env_var}={domain}")
        
        # Verificar configuración
        self.stdout.write("\n🔍 Verificando configuración...")
        from core.utils.cdn import get_cdn_status
        status = get_cdn_status()
        
        if status['enabled']:
            self.stdout.write(f"✅ CDN habilitado: {status['provider']}")
            self.stdout.write(f"🌐 MEDIA_URL: {status['media_url']}")
            self.stdout.write(f"📁 STATIC_URL: {status['static_url']}")
        else:
            self.stdout.write("⚠️  CDN no está habilitado")
        
        self.stdout.write("\n🎉 ¡Dominio del CDN actualizado!")
        self.stdout.write("📝 Recuerda configurar el DNS en tu proveedor de CDN") 