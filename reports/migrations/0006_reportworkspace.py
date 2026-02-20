# Modified to check table existence before creating
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


def create_reportworkspace_table(apps, schema_editor):
    """Crea la tabla ReportWorkspace si no existe."""
    from django.db import connection
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user_table = User._meta.db_table  # AUTH_USER_MODEL (core_usuarioextendido), no auth_user
    cursor = connection.cursor()
    try:
        # Verificar si la tabla existe
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'reports_reportworkspace'
            );
        """)
        table_exists = cursor.fetchone()[0]
        
        if table_exists:
            print("⚠️  Tabla reports_reportworkspace ya existe, saltando creación")
            return
        
        # Crear la tabla usando SQL directo (FK a la tabla real de AUTH_USER_MODEL, no auth_user)
        cursor.execute(f"""
            CREATE TABLE reports_reportworkspace (
                id BIGSERIAL NOT NULL PRIMARY KEY,
                name VARCHAR(128) NOT NULL DEFAULT 'Workspace',
                items JSONB NOT NULL DEFAULT '[]'::jsonb,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
                empresa_id BIGINT NULL,
                owner_id BIGINT NOT NULL,
                CONSTRAINT reports_reportworkspace_empresa_id_fkey 
                    FOREIGN KEY (empresa_id) REFERENCES core_empresa(id) ON DELETE CASCADE,
                CONSTRAINT reports_reportworkspace_owner_id_fkey 
                    FOREIGN KEY (owner_id) REFERENCES {user_table}(id) ON DELETE CASCADE,
                CONSTRAINT reports_reportworkspace_owner_id_empresa_id_uniq 
                    UNIQUE (owner_id, empresa_id)
            );
        """)
        
        # Crear índices
        cursor.execute("""
            CREATE INDEX reports_reportworkspace_empresa_id_idx 
            ON reports_reportworkspace(empresa_id);
        """)
        cursor.execute("""
            CREATE INDEX reports_reportworkspace_owner_id_idx 
            ON reports_reportworkspace(owner_id);
        """)
        
        print("✅ Tabla reports_reportworkspace creada exitosamente")
        
    except Exception as e:
        print(f"⚠️  Error creando tabla reports_reportworkspace: {e}")
    finally:
        cursor.close()


def drop_reportworkspace_table(apps, schema_editor):
    """Elimina la tabla ReportWorkspace si existe."""
    from django.db import connection
    cursor = connection.cursor()
    
    try:
        # Verificar si la tabla existe
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'reports_reportworkspace'
            );
        """)
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            print("⚠️  Tabla reports_reportworkspace no existe, saltando eliminación")
            return
        
        # Eliminar la tabla
        cursor.execute("DROP TABLE IF EXISTS reports_reportworkspace CASCADE;")
        print("✅ Tabla reports_reportworkspace eliminada exitosamente")
        
    except Exception as e:
        print(f"⚠️  Error eliminando tabla reports_reportworkspace: {e}")
    finally:
        cursor.close()


class Migration(migrations.Migration):
    dependencies = [
        ("reports", "0005_clientes_churn_axis_labels"),
        ("core", "0007_increase_permiso_codigo_length"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(create_reportworkspace_table, drop_reportworkspace_table),
    ]
