from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_protect
from core.decorators import tiene_permiso, administranet_login_required
from core.models import UsuarioExtendido, Permiso, Rol
from django.contrib import messages
from core.utils import permisos_contextuales
from django.core.paginator import Paginator
from core.constantes_permisos import PERMISOS_POR_MODULO
# Firebase deshabilitado para administraNET Analytics
# from django_project.firebase_config import get_firebase_app
import logging
from django.utils.translation import gettext_lazy as _
# import firebase_admin
# from firebase_admin import firestore, auth
from core.models.models import Empresa
from django import forms
from core.models import Branch
from core.utils.utils import require_empresa_activa
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from core.models.fiscal_responsibility import FiscalResponsibility
from core.models import State, Country
import defusedxml.ElementTree as DefusedET
from django.core.exceptions import ValidationError
import bleach

logger = logging.getLogger(__name__)

@csrf_protect
@tiene_permiso("administrar.usuarios")
def usuarios_admin_view(request):
    context = permisos_contextuales(request, "usuarios.ver", roles_permitidos=["Administrador"], debug=True)
    if not context.get("puede_usuarios_ver") and not context.get("rol_permitido"):
        return render(request, "core/403.html", context, status=403)

    q = request.GET.get("q", "")
    rol_filter = request.GET.get("rol_filter", "")
    usuarios = UsuarioExtendido.objects.all().prefetch_related("roles", "permisos_extra")

    if q:
        usuarios = usuarios.filter(nombre__icontains=q) | usuarios.filter(email__icontains=q)
    if rol_filter:
        usuarios = usuarios.filter(roles__id=rol_filter)

    usuarios = usuarios.order_by("email")
    paginator = Paginator(usuarios, 15)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    roles = Rol.objects.all().order_by("nombre")
    todos_permisos = Permiso.objects.all().order_by("nombre")

    # Agrupar permisos por módulo según PERMISOS_POR_MODULO
    modulos_permisos = {}
    codigos_usados = set()

    for modulo, lista_codigos in PERMISOS_POR_MODULO.items():
        codigos = [c for c, _ in lista_codigos]
        permisos_modulo = todos_permisos.filter(codigo__in=codigos)
        modulos_permisos[modulo] = permisos_modulo
        codigos_usados.update(codigos)

    permisos_restantes = todos_permisos.exclude(codigo__in=codigos_usados)
    if permisos_restantes.exists():
        modulos_permisos["Otros"] = permisos_restantes

    # 🔄 Actualización (roles + permisos) - Firebase deshabilitado
    if request.method == "POST":
        # Firebase deshabilitado para instalación mínima de Reportes
        # db = firestore.client()

        for usuario in usuarios:
            # ✅ Asignar múltiples roles
            roles_ids = request.POST.getlist(f"roles_{usuario.uid}")
            roles_objs = Rol.objects.filter(id__in=roles_ids)
            usuario.roles.set(roles_objs)
            nombres_roles = [r.nombre for r in roles_objs]

            # ✅ Asignar permisos adicionales
            permisos_ids = request.POST.getlist(f"perm_{usuario.uid}")
            usuario.permisos_extra.set(permisos_ids)

            usuario.save()

            # 🔁 Sincronizar Firestore - DESHABILITADO (Firebase no disponible)
            # try:
            #     doc_ref = db.collection("usuarios").document(usuario.uid)
            #     doc = doc_ref.get()
            #     if doc.exists:
            #         doc_ref.update({"roles": nombres_roles})
            #     else:
            #         doc_ref.set({
            #             "email": usuario.email,
            #             "nombre": usuario.nombre,
            #             "idioma": usuario.idioma or "es",
            #             "roles": nombres_roles
            #         })
            #     logger.info(f"📡 Firestore actualizado para {usuario.email}")
            # except Exception as e:
            #     logger.warning(f"⚠️ Error al sincronizar con Firestore para {usuario.email}: {e}")

        messages.success(request, _("✅ Changes saved successfully."))
        return redirect("core:usuarios")

    # 🔽 Render final
    context.update({
        "usuarios": page_obj,
        "roles": roles,
        "modulos_permisos": modulos_permisos,
        "q": q,
        "rol_filter": rol_filter,
    })
    return render(request, "core/usuarios_admin.html", context)


@tiene_permiso("usuarios.ver")
def listar_permisos(request):
    permisos = Permiso.objects.all()
    return render(request, "core/permisos_list.html", {"permisos": permisos})

@csrf_protect
@tiene_permiso("administrar.usuarios")
def crear_usuario_view(request):
    if not request.user.tiene_permiso("administrar.usuarios"):
        messages.error(request, _("You do not have permission to create users."))
        return redirect("core:usuarios")

    context = permisos_contextuales(request, "usuarios.crear", roles_permitidos=["Administrador"])

    if not context.get("puede_usuarios_crear") and not context.get("rol_permitido"):
        return render(request, "core/403.html", context, status=403)

    roles = Rol.objects.all()

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        nombre = request.POST.get("nombre", "").strip()
        idioma = request.POST.get("idioma", "es")
        password = request.POST.get("password", "")
        confirmar = request.POST.get("confirmar", "")
        roles_ids = request.POST.getlist("roles")

        if not email or not password or not confirmar or not nombre:
            messages.error(request, _("All fields are required."))
            return render(request, "core/usuarios_form.html", {"roles": roles})

        if password != confirmar:
            messages.error(request, _("Passwords do not match."))
            return render(request, "core/usuarios_form.html", {"roles": roles})

        # ⚠️ Verificar si el usuario ya existe localmente
        if UsuarioExtendido.objects.filter(email=email).exists():
            messages.error(request, _("A user with that email already exists in the database."))
            return render(request, "core/usuarios_form.html", {"roles": roles})

        # Firebase deshabilitado para administraNET Analytics
        # Los usuarios se crean directamente en la base de datos local
        # 1. Crear en Firebase Auth - DESHABILITADO
        # try:
        #     firebase_user = auth.create_user(email=email, password=password, display_name=nombre)
        #     uid = firebase_user.uid
        # except auth.EmailAlreadyExistsError:
        #     messages.error(request, _("That email is already registered in Firebase."))
        #     return render(request, "core/usuarios_form.html", {"roles": roles})
        # except Exception as e:
        #     messages.error(request, _("Error creating user in Firebase: %(error)s") % {'error': e})
        #     return render(request, "core/usuarios_form.html", {"roles": roles})

        # 2. Crear en DB local (sin Firebase)
        # Generar un uid temporal o usar email como identificador único
        import hashlib
        uid = hashlib.md5(email.encode()).hexdigest()[:28]  # Formato similar a Firebase UID
        
        usuario = UsuarioExtendido.objects.create(
            uid=uid,
            email=email,
            nombre=nombre,
            idioma=idioma,
        )
        if roles_ids:
            usuario.roles.set(roles_ids)
        
        # Establecer contraseña si se proporciona
        if password:
            usuario.set_password(password)
            usuario.save()

        # 3. Crear en Firestore - DESHABILITADO
        # try:
        #     firestore.client().collection("usuarios").document(uid).set({
        #         "email": email,
        #         "nombre": nombre,
        #         "idioma": idioma,
        #         "roles": [Rol.objects.get(id=r).nombre for r in roles_ids]
        #     })
        # except Exception as e:
        #     messages.warning(request, _("User created locally, but not synced with Firebase: %(error)s") % {'error': e})

        messages.success(request, _("✅ User %(email)s created successfully.") % {'email': email})
        return redirect("core:usuarios")

    return render(request, "core/usuarios_form.html", {
        "roles": roles
    })


@tiene_permiso("permisos.eliminar")
def eliminar_permiso(request, permiso_id):
    permiso = get_object_or_404(Permiso, id=permiso_id)
    permiso.delete()
    messages.success(request, _("Permission deleted."))
    return redirect("core:listar_permisos")


def error_403_view(request, exception=None):
    return render(request, "core/403.html", status=403)

# dashboard_view está definido en views_general.py y se importa desde __init__.py


@administranet_login_required
def perfil_view(request):
    """
    Vista de perfil de usuario para administraNET Analytics
    Permite ver y editar datos del usuario logueado y cambiar contraseña
    """
    from core.services.administranet_users import AdministraNETUserService
    from login.administranet_auth import AdministraNETAuth
    
    session_user = request.session.get("user")
    if not session_user:
        return redirect("login:login")
    
    base_empresa = session_user.get("base_empresa")
    id_usuario = session_user.get("id_usuario")
    
    if not base_empresa or not id_usuario:
        messages.error(request, "No se pudo determinar la información del usuario.")
        return redirect("core:dashboard")
    
    user_service = AdministraNETUserService()
    auth_service = AdministraNETAuth()
    
    # Obtener datos del usuario desde administraNET
    logger.info(f"🔍 Obteniendo usuario id_usuario={id_usuario} de base_empresa={base_empresa}")
    usuario = user_service.obtener_usuario(base_empresa, id_usuario)
    
    if not usuario:
        logger.error(f"❌ No se encontró usuario con id_usuario={id_usuario} en base_empresa={base_empresa}")
        messages.error(request, "Usuario no encontrado.")
        return redirect("core:dashboard")
    
    logger.info(f"✅ Usuario obtenido: cod_usuario={usuario.get('cod_usuario')}, nombre_empresa={usuario.get('nombre_empresa')}, nombre_sucursal={usuario.get('nombre_sucursal')}, nombre_puesto={usuario.get('nombre_puesto')}")
    
    logger.info(f"Usuario obtenido para perfil: cod_usuario={usuario.get('cod_usuario')}, nombre={usuario.get('nombre_usuario')}, apellido={usuario.get('apellido_usuario')}")
    
    if request.method == "POST":
        # Preparar datos de actualización
        datos_actualizacion = {}
        actualizaciones_realizadas = []
        tiene_errores = False
        
        # Actualizar nombre y apellido (si se proporcionaron)
        nombre_usuario = request.POST.get("nombre_usuario", "").strip()
        apellido_usuario = request.POST.get("apellido_usuario", "").strip()
        
        if nombre_usuario and nombre_usuario != usuario.get('nombre_usuario', ''):
            datos_actualizacion['nombre_usuario'] = nombre_usuario
            actualizaciones_realizadas.append('nombre')
        
        if apellido_usuario and apellido_usuario != usuario.get('apellido_usuario', ''):
            datos_actualizacion['apellido_usuario'] = apellido_usuario
            actualizaciones_realizadas.append('apellido')
        
        # Cambio de contraseña (según lógica de CargaUsuario.frm)
        password_actual = request.POST.get("password_actual", "").strip()
        nueva_password = request.POST.get("nueva_password", "").strip()
        confirmar_password = request.POST.get("confirmar_password", "").strip()
        
        # Solo procesar cambio de contraseña si se proporcionó una nueva contraseña
        if nueva_password:
            logger.info(f"🔍 Procesando cambio de contraseña")
            # Validar que las contraseñas coincidan (igual que CargaUsuario.frm línea 1592)
            if nueva_password != confirmar_password:
                messages.error(request, "La contraseña y la validación deben ser iguales.")
                tiene_errores = True
                logger.warning(f"⚠️ Las contraseñas no coinciden")
            elif len(nueva_password) < 4:
                messages.error(request, "La contraseña debe tener al menos 4 caracteres.")
                tiene_errores = True
                logger.warning(f"⚠️ La contraseña es muy corta")
            elif not password_actual:
                messages.error(request, "Debe ingresar la contraseña actual para cambiarla.")
                tiene_errores = True
                logger.warning(f"⚠️ No se proporcionó contraseña actual")
            else:
                # Validar contraseña actual usando AdministraNETAuth (igual que login)
                cod_usuario = usuario.get('cod_usuario', '')
                if not cod_usuario:
                    messages.error(request, "No se pudo obtener el código de usuario.")
                    tiene_errores = True
                    logger.error(f"❌ No se pudo obtener cod_usuario")
                else:
                    # Validar contraseña actual usando AES_DECRYPT (igual que login)
                    logger.info(f"🔍 Validando contraseña actual para usuario {cod_usuario}")
                    user_validated = auth_service.validate_user(cod_usuario, password_actual, base_empresa)
                    
                    if not user_validated:
                        messages.error(request, "La contraseña actual es incorrecta.")
                        tiene_errores = True
                        logger.warning(f"⚠️ Contraseña actual incorrecta")
                    else:
                        # Guardar nueva contraseña usando AES_ENCRYPT (igual que CargaUsuario.frm línea 1697 y 1797)
                        datos_actualizacion['password'] = nueva_password
                        actualizaciones_realizadas.append('contraseña')
                        logger.info(f"✅ Contraseña validada correctamente, se actualizará")
        
        # Ejecutar actualización solo si hay cambios Y no hay errores
        if datos_actualizacion and not tiene_errores:
            logger.info(f"🔍 Intentando actualizar usuario: datos_actualizacion keys={list(datos_actualizacion.keys())}, actualizaciones_realizadas={actualizaciones_realizadas}")
            if user_service.actualizar_usuario(base_empresa, id_usuario, datos_actualizacion):
                logger.info(f"✅ Usuario actualizado exitosamente en la base de datos")
                # Mensajes de éxito según qué se actualizó
                if 'contraseña' in actualizaciones_realizadas:
                    messages.success(request, "✅ Contraseña actualizada correctamente.")
                    logger.info(f"📨 Mensaje de éxito de contraseña enviado")
                if 'nombre' in actualizaciones_realizadas or 'apellido' in actualizaciones_realizadas:
                    messages.success(request, "✅ Datos personales actualizados correctamente.")
                    logger.info(f"📨 Mensaje de éxito de datos personales enviado")
                
                # Actualizar sesión con nuevos datos (si se actualizaron nombre/apellido)
                if 'nombre' in actualizaciones_realizadas or 'apellido' in actualizaciones_realizadas:
                    session_user['nombre_usuario'] = datos_actualizacion.get('nombre_usuario', session_user.get('nombre_usuario'))
                    session_user['apellido_usuario'] = datos_actualizacion.get('apellido_usuario', session_user.get('apellido_usuario'))
                    session_user['nombre_completo'] = f"{session_user['nombre_usuario']} {session_user['apellido_usuario']}"
                    request.session['user'] = session_user
                
                # Hacer redirect para mostrar mensajes (patrón POST-REDIRECT-GET)
                logger.info(f"🔄 Redirigiendo a perfil para mostrar mensajes")
                return redirect('core:perfil')
            else:
                messages.error(request, "Error al actualizar los datos. Por favor intente nuevamente.")
                logger.error(f"❌ Error al actualizar usuario en la base de datos")
        
        # Si hay errores o no hay cambios, recargar datos y mostrar formulario con mensajes
        logger.info(f"📋 Recargando datos del usuario (errores={tiene_errores}, cambios={len(datos_actualizacion)})")
        usuario = user_service.obtener_usuario(base_empresa, id_usuario)
    
    # Debug: verificar que los datos estén disponibles
    logger.info(f"Renderizando perfil - nombre_empresa: {usuario.get('nombre_empresa')}, nombre_sucursal: {usuario.get('nombre_sucursal')}, nombre_puesto: {usuario.get('nombre_puesto')}, baja_usuario: {usuario.get('baja_usuario')}")
    
    context = {
        "usuario": usuario,
        "session_user": session_user
        # Los mensajes se pasan automáticamente por django.contrib.messages.context_processors.messages
    }
    
    return render(request, "core/perfil.html", context)


@tiene_permiso("usuarios.historial")
def historial_view(request):
    return render(request, "core/historial.html", {"user": request.session["user"]})

# Firebase deshabilitado para administraNET Analytics
# get_firebase_app()

@administranet_login_required
def empresa_listar_view(request):
    """
    En AdministraNET hay una sola empresa por base de datos (DatosEmpresa, id_empresa=1).
    Si existe, se redirige directo a la vista de detalle/edición; si no, se muestra estado vacío.
    Ver docs/general/EMPRESA_UNA_POR_BASE_ADMINISTRANET.md.
    """
    from core.services.administranet_empresas import AdministraNETEmpresaService

    session_user = request.session.get("user", {})
    base_empresa = session_user.get("base_empresa")

    if not base_empresa:
        logger.error("❌ No se encontró base_empresa en la sesión")
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:dashboard")

    empresa_service = AdministraNETEmpresaService()
    empresa = empresa_service.obtener_empresa(base_empresa)

    if empresa:
        # Una empresa por base: mostrar directamente datos (detalle/edición)
        empresa_id = empresa.get("id_empresa") or 1
        return redirect("core:empresa_detalle", empresa_id=int(empresa_id))

    # Sin datos: estado vacío y opción "Crear primera empresa"
    logger.warning("⚠️ No se encontró empresa en base_empresa: %s", base_empresa)
    return render(request, "core/system_config/empresa_list.html", {
        "empresas": [],
        "sin_datos_administranet": True,
        "base_empresa": base_empresa,
    })

@administranet_login_required
def empresa_detalle_view(request, empresa_id):
    """
    Muestra y edita los datos de la empresa desde administraNET Gestión
    Basado en Empresa.frm
    """
    from core.services.administranet_empresas import AdministraNETEmpresaService
    
    session_user = request.session.get("user", {})
    base_empresa = session_user.get("base_empresa")
    
    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:dashboard")
    
    empresa_service = AdministraNETEmpresaService()
    empresa = empresa_service.obtener_empresa(base_empresa)
    modo_creacion = empresa is None
    error = None
    
    if request.method == 'POST':
        data = request.POST.copy()
        
        # Preparar datos según estructura de DatosEmpresa
        datos_empresa = {
            'Nombre': data.get('Nombre', '').strip(),
            'Domicilio': data.get('Domicilio', '').strip(),
            'CodProvincia': int(data.get('CodProvincia')) if data.get('CodProvincia') else None,
            'CodDepartamento': int(data.get('CodDepartamento')) if data.get('CodDepartamento') else None,
            'Pais': data.get('Pais', '').strip(),
            'id_pais': int(data.get('id_pais')) if data.get('id_pais') else 1,
            'Telefono': data.get('Telefono', '').strip(),
            'Email': data.get('Email', '').strip(),
            'Fax': data.get('Fax', '').strip(),
            'Timbrado': data.get('Timbrado', '').strip(),
            'CUIT': data.get('CUIT', '').strip(),
            'Establecimiento': data.get('Establecimiento', '').strip(),
            'IngBrutos': data.get('IngBrutos', '').strip(),
            'InicioAct': data.get('InicioAct') or None,
            'IDIva': int(data.get('IDIva')) if data.get('IDIva') else None,
            'cod_postal': data.get('cod_postal', '').strip(),
            'whatsapp': data.get('whatsapp', '-').strip(),
            'facebook_messenger': data.get('facebook_messenger', '-').strip(),
            'twitter': data.get('twitter', '-').strip(),
            'direccion_web': data.get('direccion_web', '-').strip(),
            'url_ecommerce_cliente': data.get('url_ecommerce_cliente', '-').strip(),
            'url_ecommerce_vendedor': data.get('url_ecommerce_vendedor', '-').strip(),
            'observaciones': data.get('observaciones', '').strip(),
            'rubro_canal': data.get('rubro_canal', 'Venta minorista').strip() or 'Venta minorista',
            'actividad': data.get('actividad', 'Drugstore / Minimarket / Kioscos').strip() or 'Drugstore / Minimarket / Kioscos',
        }
        
        # Validar campos obligatorios según Empresa.frm
        required_fields = {
            'Nombre': datos_empresa['Nombre'],
            'Domicilio': datos_empresa['Domicilio'],
            'CUIT': datos_empresa['CUIT'],
            'Departamento': datos_empresa['CodDepartamento'],
            'Provincia': datos_empresa['CodProvincia'],
            'Telefono': datos_empresa['Telefono'],
            'Fax': datos_empresa['Fax'],
            'Email': datos_empresa['Email'],
            'Pais': datos_empresa['Pais'],
            'IngBrutos': datos_empresa['IngBrutos'],
            'InicioAct': datos_empresa['InicioAct'],
            'Timbrado': datos_empresa['Timbrado'],
            'Establecimiento': datos_empresa['Establecimiento'],
        }
        
        missing_fields = [field for field, value in required_fields.items() if not value]
        
        if missing_fields:
            error = f"Complete todos los campos obligatorios: {', '.join(missing_fields)}"
        else:
            # Validar email si se proporciona
            if datos_empresa['Email']:
                import re
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, datos_empresa['Email']):
                    error = "El formato del email es inválido"
            
            if not error:
                if empresa_service.guardar_empresa(base_empresa, datos_empresa):
                    # Si se subió un logo, guardarlo también en el modelo Django Empresa
                    if 'logo' in request.FILES:
                        try:
                            from core.models import Empresa
                            # Buscar empresa Django por nombre o CUIT
                            nombre_empresa = datos_empresa.get('Nombre', '')
                            cuit_empresa = datos_empresa.get('CUIT', '').replace('-', '').replace(' ', '')  # Limpiar formato CUIT
                            
                            empresa_django = None
                            
                            # Primero intentar por CUIT (más confiable)
                            if cuit_empresa:
                                try:
                                    # Buscar con CUIT limpio
                                    empresa_django = Empresa.objects.filter(identificador_fiscal__icontains=cuit_empresa).first()
                                    if not empresa_django:
                                        # Intentar con formato con guiones
                                        cuit_formateado = f"{cuit_empresa[:2]}-{cuit_empresa[2:10]}-{cuit_empresa[10:]}" if len(cuit_empresa) == 11 else cuit_empresa
                                        empresa_django = Empresa.objects.filter(identificador_fiscal__icontains=cuit_formateado).first()
                                except Exception as e:
                                    logger.warning(f"Error al buscar por CUIT: {e}")
                            
                            # Si no se encontró por CUIT, intentar por nombre
                            if not empresa_django and nombre_empresa:
                                try:
                                    empresa_django = Empresa.objects.filter(nombre__iexact=nombre_empresa).first()
                                    if not empresa_django:
                                        # Intentar búsqueda parcial
                                        empresa_django = Empresa.objects.filter(nombre__icontains=nombre_empresa).first()
                                except Exception as e:
                                    logger.warning(f"Error al buscar por nombre: {e}")
                            
                            # Si se encontró, actualizar el logo y datos si es necesario
                            if empresa_django:
                                logo_file = request.FILES['logo']
                                logger.info(f"📤 Guardando logo: nombre={logo_file.name}, tamaño={logo_file.size}, tipo={logo_file.content_type}")
                                empresa_django.logo = logo_file
                                # Actualizar nombre y CUIT si no coinciden exactamente
                                if nombre_empresa and empresa_django.nombre != nombre_empresa:
                                    empresa_django.nombre = nombre_empresa
                                if cuit_empresa and empresa_django.identificador_fiscal != cuit_empresa:
                                    empresa_django.identificador_fiscal = cuit_empresa
                                empresa_django.save()
                                # Verificar que el archivo se guardó físicamente
                                import os
                                from django.conf import settings
                                if empresa_django.logo:
                                    logo_path = os.path.join(settings.MEDIA_ROOT, empresa_django.logo.name)
                                    logo_exists = os.path.exists(logo_path)
                                    logger.info(f"✅ Logo guardado en BD: {empresa_django.logo.name}")
                                    logger.info(f"📁 Ruta física: {logo_path}")
                                    logger.info(f"📁 Archivo existe: {logo_exists}")
                                    if logo_exists:
                                        logger.info(f"📁 Tamaño del archivo: {os.path.getsize(logo_path)} bytes")
                                    else:
                                        logger.error(f"❌ ERROR: El archivo NO existe en el sistema de archivos después de guardar")
                                else:
                                    logger.error(f"❌ ERROR: empresa_django.logo es None después de guardar")
                            else:
                                logger.warning(f"⚠️ No se encontró empresa Django para actualizar logo (Nombre: {nombre_empresa}, CUIT: {cuit_empresa})")
                                # Si no existe, crear la empresa Django si tenemos datos suficientes
                                if nombre_empresa and cuit_empresa:
                                    try:
                                        from core.models import Country, FiscalResponsibility, Currency
                                        # Crear empresa Django básica
                                        empresa_django = Empresa(
                                            nombre=nombre_empresa,
                                            razon_social=nombre_empresa,
                                            identificador_fiscal=cuit_empresa,
                                            activa=True
                                        )
                                        # Intentar obtener valores por defecto
                                        try:
                                            empresa_django.country = Country.objects.filter(is_active=True).first()
                                        except:
                                            pass
                                        try:
                                            empresa_django.fiscal_responsibility = FiscalResponsibility.objects.filter(is_active=True).first()
                                        except:
                                            pass
                                        try:
                                            empresa_django.currency = Currency.objects.filter(is_default=True).first()
                                        except:
                                            pass
                                        empresa_django.logo = request.FILES['logo']
                                        empresa_django.save()
                                        logger.info(f"✅ Empresa Django creada con logo: {empresa_django.nombre}")
                                    except Exception as create_error:
                                        logger.error(f"❌ Error al crear empresa Django: {create_error}")
                        except Exception as e:
                            logger.error(f"❌ Error al guardar logo en Django Empresa: {e}")
                            import traceback
                            logger.error(traceback.format_exc())
                            # No fallar el guardado principal si hay error con el logo
                    
                    messages.success(request, "✅ Empresa guardada exitosamente.")
                    return redirect('core:empresa_detalle', empresa_id=1)
                else:
                    error = "Error al guardar la empresa. Por favor intente nuevamente."
    
    # Obtener datos relacionados para los dropdowns
    paises = empresa_service.obtener_paises(base_empresa)
    valores_rubro_canal = empresa_service.obtener_valores_rubro_canal(base_empresa)
    valores_actividad = empresa_service.obtener_valores_actividad(base_empresa)
    
    # Obtener provincias según el país de la empresa (si existe)
    id_pais_empresa = None
    if empresa and empresa.get('id_pais'):
        try:
            id_pais_empresa = int(empresa.get('id_pais'))
        except (ValueError, TypeError):
            id_pais_empresa = None
    
    provincias = empresa_service.obtener_provincias(base_empresa, id_pais_empresa)
    
    # Obtener departamentos según la provincia de la empresa (si existe)
    cod_provincia_empresa = None
    if empresa and empresa.get('CodProvincia'):
        try:
            cod_provincia_empresa = int(empresa.get('CodProvincia'))
        except (ValueError, TypeError):
            cod_provincia_empresa = None
    
    departamentos = empresa_service.obtener_departamentos(base_empresa, cod_provincia_empresa)
    contribuyentes = empresa_service.obtener_contribuyentes(base_empresa, id_pais_empresa)
    
    # Debug: verificar valores
    logger.info(f"🔍 Empresa - id_pais: {id_pais_empresa}, CodProvincia: {cod_provincia_empresa}, CodDepartamento: {empresa.get('CodDepartamento') if empresa else None}")
    logger.info(f"🔍 Provincias encontradas: {len(provincias)}")
    logger.info(f"🔍 Departamentos encontrados: {len(departamentos)}")
    
    # Preparar contexto para el template
    context = {
        'empresa': empresa,
        'modo_creacion': modo_creacion,
        'error': error,
        'paises': paises,
        'provincias': provincias,
        'departamentos': departamentos,
        'contribuyentes': contribuyentes,
        'valores_rubro_canal': valores_rubro_canal,
        'valores_actividad': valores_actividad,
        'base_empresa': base_empresa,
    }
    
    return render(request, 'core/system_config/empresa_detail.html', context)

def empresa_eliminar_view(request, empresa_id):
    empresa = get_object_or_404(Empresa, id=empresa_id)
    # Aquí se agregarán chequeos de dependencias en el futuro
    tiene_dependencias = False  # Por ahora, siempre False
    if request.method == 'POST':
        if tiene_dependencias or empresa.activa:
            empresa.activa = False
            empresa.save()
            messages.success(request, _('Company deactivated successfully.'))
        else:
            empresa.delete()
            messages.success(request, _('Company deleted successfully.'))
        return redirect('core:empresa_listar')
    return render(request, 'core/system_config/empresa_confirm_delete.html', {'empresa': empresa, 'tiene_dependencias': tiene_dependencias})

def empresa_ficha_view(request, empresa_id=None):
    from core.models import Empresa
    from django.forms.models import model_to_dict
    context = {}
    error = None
    if empresa_id:
        empresa = Empresa.objects.get(id=empresa_id)
        if request.method == 'POST':
            data = request.POST.copy()
            # Campos normales
            for field in ['nombre', 'razon_social', 'identificador_fiscal', 'email', 'telefono', 'direccion', 'ciudad', 'sitio_web']:
                if field in data:
                    setattr(empresa, field, data.get(field))
            # ForeignKey por ID (validar y convertir a int)
            try:
                empresa.country_id = int(data.get('country_id')) if data.get('country_id') else None
            except (ValueError, TypeError):
                empresa.country_id = None
            try:
                empresa.state_id = int(data.get('state_id')) if data.get('state_id') else None
            except (ValueError, TypeError):
                empresa.state_id = None
            try:
                empresa.fiscal_responsibility_id = int(data.get('fiscal_responsibility_id')) if data.get('fiscal_responsibility_id') else None
            except (ValueError, TypeError):
                empresa.fiscal_responsibility_id = None
            try:
                empresa.currency_id = int(data.get('currency_id')) if data.get('currency_id') else None
            except (ValueError, TypeError):
                empresa.currency_id = None
            if 'logo' in request.FILES:
                empresa.logo = request.FILES['logo']
            # Validar campos obligatorios de referencia
            required_ids = [empresa.country_id, empresa.state_id, empresa.fiscal_responsibility_id, empresa.currency_id]
            if not all(required_ids):
                campos = [
                    (_('Nombre de la empresa'), empresa.nombre, '', 'nombre', False),
                    (_('Razón Social'), empresa.razon_social, '', 'razon_social', False),
                    (_('CUIT/RFC/NIF'), empresa.identificador_fiscal, _('Identificador fiscal según país'), 'identificador_fiscal', False),
                    (_('Tipo de Responsabilidad'), empresa.fiscal_responsibility.name if empresa.fiscal_responsibility else '', _('Tipo de contribuyente según AFIP/SAT/etc'), 'fiscal_responsibility', False),
                    (_('Dirección'), empresa.direccion, '', 'direccion', False),
                    (_('Ciudad'), empresa.ciudad, '', 'ciudad', False),
                    (_('Provincia/Estado'), empresa.state.name if empresa.state else '', '', 'state', False),
                    (_('País'), empresa.country.name if empresa.country else '', '', 'country', False),
                    (_('Teléfono'), empresa.telefono, '', 'telefono', False),
                    (_('Email'), empresa.email, '', 'email', False),
                    (_('Sitio web'), empresa.sitio_web if hasattr(empresa, 'sitio_web') else '', '', 'sitio_web', True),
                ]
                context = {'empresa': empresa, 'campos': campos, 'modo_creacion': False, 'error': _('Faltan campos obligatorios de referencia (país, provincia, responsabilidad fiscal o moneda).')}
                return render(request, 'core/system_config/empresa_detail.html', context)
            empresa.save()
            return redirect('core:empresa_detalle', empresa_id=empresa.id)
        # Campos para la ficha
        campos = [
            (_('Nombre de la empresa'), empresa.nombre, '', 'nombre', False),
            (_('Razón Social'), empresa.razon_social, '', 'razon_social', False),
            (_('CUIT/RFC/NIF'), empresa.identificador_fiscal, _('Identificador fiscal según país'), 'identificador_fiscal', False),
            (_('Tipo de Responsabilidad'), empresa.fiscal_responsibility.name if empresa.fiscal_responsibility else '', _('Tipo de contribuyente según AFIP/SAT/etc'), 'fiscal_responsibility', False),
            (_('Dirección'), empresa.direccion, '', 'direccion', False),
            (_('Ciudad'), empresa.ciudad, '', 'ciudad', False),
            (_('Provincia/Estado'), empresa.state.name if empresa.state else '', '', 'state', False),
            (_('País'), empresa.country.name if empresa.country else '', '', 'country', False),
            (_('Teléfono'), empresa.telefono, '', 'telefono', False),
            (_('Email'), empresa.email, '', 'email', False),
            (_('Sitio web'), empresa.sitio_web if hasattr(empresa, 'sitio_web') else '', '', 'sitio_web', True),
        ]
        context = {'empresa': empresa, 'campos': campos, 'modo_creacion': False}
    else:
        # Creación de empresa
        if request.method == 'POST':
            data = request.POST.copy()
            empresa = Empresa()
            for field in ['nombre', 'razon_social', 'identificador_fiscal', 'email', 'telefono', 'direccion', 'ciudad', 'sitio_web']:
                if field in data:
                    setattr(empresa, field, data.get(field))
            if 'country_id' in data and data.get('country_id'):
                empresa.country_id = data.get('country_id')
            if 'state_id' in data and data.get('state_id'):
                empresa.state_id = data.get('state_id')
            if 'fiscal_responsibility_id' in data and data.get('fiscal_responsibility_id'):
                empresa.fiscal_responsibility_id = data.get('fiscal_responsibility_id')
            if 'currency_id' in data and data.get('currency_id'):
                empresa.currency_id = data.get('currency_id')
            if 'logo' in request.FILES:
                empresa.logo = request.FILES['logo']
            empresa.save()
            return redirect('core:empresa_detalle', empresa_id=empresa.id)
        # Campos vacíos para la ficha
        campos = [
            (_('Nombre de la empresa'), '', '', 'nombre', False),
            (_('Razón Social'), '', '', 'razon_social', False),
            (_('CUIT/RFC/NIF'), '', _('Identificador fiscal según país'), 'identificador_fiscal', False),
            (_('Tipo de Responsabilidad'), '', _('Tipo de contribuyente según AFIP/SAT/etc'), 'fiscal_responsibility', False),
            (_('Dirección'), '', '', 'direccion', False),
            (_('Ciudad'), '', '', 'ciudad', False),
            (_('Provincia/Estado'), '', '', 'state', False),
            (_('País'), '', '', 'country', False),
            (_('Teléfono'), '', '', 'telefono', False),
            (_('Email'), '', '', 'email', False),
            (_('Sitio web'), '', '', 'sitio_web', True),
        ]
        context = {'empresa': None, 'campos': campos, 'modo_creacion': True}
    return render(request, 'core/system_config/empresa_detail.html', context)

class BranchForm(forms.ModelForm):
    class Meta:
        model = Branch
        fields = [
            'empresa', 'name', 'code', 'address', 'city', 'state', 'country', 'phone', 'email', 'active'
        ]
        widgets = {
            'active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }

@administranet_login_required
def branch_list_view(request, empresa_id):
    """
    Lista las sucursales de la empresa activa desde administraNET Gestión
    Basado en ABMSucursal.frm
    """
    from core.services.administranet_sucursales import AdministraNETSucursalesService
    
    session_user = request.session.get("user", {})
    base_empresa = session_user.get("base_empresa")
    
    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:dashboard")
    
    sucursales_service = AdministraNETSucursalesService()
    
    # Obtener búsqueda si existe
    busqueda = request.GET.get('busqueda', '').strip()
    
    # Listar sucursales
    sucursales = sucursales_service.listar_sucursales(base_empresa, busqueda if busqueda else None)
    
    # Obtener datos de la empresa para el contexto
    from core.services.administranet_empresas import AdministraNETEmpresaService
    empresa_service = AdministraNETEmpresaService()
    empresa = empresa_service.obtener_empresa(base_empresa)
    
    context = {
        'empresa': empresa,
        'sucursales': sucursales,
        'busqueda': busqueda,
        'base_empresa': base_empresa,
    }
    
    return render(request, 'core/system_config/branch_list.html', context)

@administranet_login_required
def branch_create_view(request, empresa_id):
    """
    Crea una nueva sucursal en administraNET Gestión
    Basado en CargaSucursal.frm cuando modificacion = "No"
    """
    from core.services.administranet_sucursales import AdministraNETSucursalesService
    from core.services.administranet_empresas import AdministraNETEmpresaService
    
    session_user = request.session.get("user", {})
    base_empresa = session_user.get("base_empresa")
    
    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:dashboard")
    
    sucursales_service = AdministraNETSucursalesService()
    empresa_service = AdministraNETEmpresaService()
    empresa = empresa_service.obtener_empresa(base_empresa)
    
    error = None
    
    if request.method == 'POST':
        data = request.POST.copy()
        
        # Preparar datos según estructura de sucursales (Datos + COT + Geo + Envíos)
        def _float_or_none(v):
            if v is None or (isinstance(v, str) and not v.strip()):
                return None
            try:
                return float(v)
            except (ValueError, TypeError):
                return None

        datos_sucursal = {
            'nombre_sucursal': data.get('nombre_sucursal', '').strip(),
            'desc_sucursal': data.get('desc_sucursal', '').strip(),
            'id_provincia': int(data.get('id_provincia')) if data.get('id_provincia') else None,
            'id_pais': int(data.get('id_pais')) if data.get('id_pais') else None,
            'domicilio_sucursal': data.get('domicilio_sucursal', '').strip(),
            'telefono_sucursal': data.get('telefono_sucursal', '').strip(),
            'email_sucursal': data.get('email_sucursal', '').strip(),
            'nro_estab_sucursal': data.get('nro_estab_sucursal', '').strip(),
            'cod_postal': data.get('cod_postal', '').strip(),
            'activa': data.get('activa') == 'on' or data.get('anulado') != 'Si',
            'cot_clave_acceso': data.get('cot_clave_acceso', '').strip(),
            'cot_kg_limite': _float_or_none(data.get('cot_kg_limite')),
            'cot_monto_limite': _float_or_none(data.get('cot_monto_limite')),
            'cot_cantidad_operaciones': _float_or_none(data.get('cot_cantidad_operaciones')),
            'geo_latitud': data.get('geo_latitud', '').strip(),
            'geo_longitud': data.get('geo_longitud', '').strip(),
            'geo_api_key': data.get('geo_api_key', '').strip(),
            'geo_api_key_javascript': data.get('geo_api_key_javascript', '').strip(),
            'activa_calculo_envios': data.get('activa_calculo_envios') in ('Si', 'on', '1'),
            'id_articulo_fact_envio': data.get('id_articulo_fact_envio', '').strip() or None,
            # Configuración Sucursal (tabs Opciones Generales, Agente, Impresoras, DNF)
            'vendedor_defecto': _float_or_none(data.get('vendedor_defecto')),
            'limite_consulta': int(data.get('limite_consulta')) if data.get('limite_consulta', '').strip() else None,
            'ruta_reporte_servidor': data.get('ruta_reporte_servidor', '').strip() or None,
            'ruta_reporte_comprobante': data.get('ruta_reporte_comprobante', '').strip() or None,
            'cant_renglon_venta': int(data.get('cant_renglon_venta')) if data.get('cant_renglon_venta', '').strip() else None,
            'salida_sin_stock': 'Si' if data.get('salida_sin_stock') == 'Si' else 'No',
            'dias_venc_presup': int(data.get('dias_venc_presup')) if data.get('dias_venc_presup', '').strip() else None,
            'dias_venc_pedido': int(data.get('dias_venc_pedido')) if data.get('dias_venc_pedido', '').strip() else None,
            'tipo_calculo_precios_impuesto_venta': data.get('tipo_calculo_precios_impuesto_venta', '').strip() or None,
            'lim_redondeo_tpv': _float_or_none(data.get('lim_redondeo_tpv')),
            'agente_retib': 'Si' if data.get('agente_retib') == 'Si' else 'No',
            'agente_retg': 'Si' if data.get('agente_retg') == 'Si' else 'No',
            'agente_reti': 'Si' if data.get('agente_reti') == 'Si' else 'No',
            'agente_percep': 'Si' if data.get('agente_percep') == 'Si' else 'No',
            'agente_percep_resol_afip_5329_iva': 'Si' if data.get('agente_percep_resol_afip_5329_iva') == 'Si' else 'No',
            'tipo_impresora': data.get('tipo_impresora', '').strip() or None,
            'nombre_impresora': data.get('nombre_impresora', '').strip() or None,
            'puerto_impresora': data.get('puerto_impresora', '').strip() or None,
            'doble_imp_etiqueta': 'Si' if data.get('doble_imp_etiqueta') == 'Si' else 'No',
            'dnf_vta': 'Si' if data.get('dnf_vta') == 'Si' else 'No',
            'dnf_tipo': data.get('dnf_tipo', '').strip() or None,
            'dnf_texto': data.get('dnf_texto', '').strip() or None,
            'dnf_texto2': data.get('dnf_texto2', '').strip() or None,
            'dnf_texto3': data.get('dnf_texto3', '').strip() or None,
        }
        
        # Validar campos obligatorios: solo el nombre es obligatorio
        if not datos_sucursal['nombre_sucursal']:
            error = "El nombre de la sucursal es obligatorio."
        else:
            if sucursales_service.crear_sucursal(base_empresa, datos_sucursal):
                messages.success(request, "✅ Sucursal creada exitosamente.")
                return redirect('core:branch_list', empresa_id=1)
            else:
                error = "Error al crear la sucursal. Por favor intente nuevamente."
    
    # Obtener datos relacionados para los dropdowns (paises, provincias, viajantes como en Configuración.frm)
    paises = empresa_service.obtener_paises(base_empresa)
    provincias = empresa_service.obtener_provincias(base_empresa, empresa.get('id_pais') if empresa else None)
    viajantes = sucursales_service.obtener_viajantes(base_empresa)
    
    context = {
        'empresa': empresa,
        'empresa_id': empresa_id,
        'modo_creacion': True,
        'error': error,
        'paises': paises,
        'provincias': provincias,
        'viajantes': viajantes,
        'sucursal': None,
        'base_empresa': base_empresa,
    }
    
    return render(request, 'core/system_config/branch_form.html', context)

@administranet_login_required
def branch_edit_view(request, empresa_id, branch_id):
    """
    Edita una sucursal existente en administraNET Gestión
    Basado en CargaSucursal.frm cuando modificacion = "Si"
    """
    from core.services.administranet_sucursales import AdministraNETSucursalesService
    from core.services.administranet_empresas import AdministraNETEmpresaService
    
    session_user = request.session.get("user", {})
    base_empresa = session_user.get("base_empresa")
    
    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:dashboard")
    
    sucursales_service = AdministraNETSucursalesService()
    empresa_service = AdministraNETEmpresaService()
    empresa = empresa_service.obtener_empresa(base_empresa)
    
    sucursal = sucursales_service.obtener_sucursal(base_empresa, branch_id)
    
    if not sucursal:
        messages.error(request, "Sucursal no encontrada.")
        return redirect('core:branch_list', empresa_id=1)
    
    error = None
    
    if request.method == 'POST':
        data = request.POST.copy()

        def _float_or_none(v):
            if v is None or (isinstance(v, str) and not v.strip()):
                return None
            try:
                return float(v)
            except (ValueError, TypeError):
                return None

        # Preparar datos según estructura de sucursales (Datos + COT + Geo + Envíos)
        datos_sucursal = {
            'nombre_sucursal': data.get('nombre_sucursal', '').strip(),
            'desc_sucursal': data.get('desc_sucursal', '').strip(),
            'id_provincia': int(data.get('id_provincia')) if data.get('id_provincia') else None,
            'id_pais': int(data.get('id_pais')) if data.get('id_pais') else None,
            'domicilio_sucursal': data.get('domicilio_sucursal', '').strip(),
            'telefono_sucursal': data.get('telefono_sucursal', '').strip(),
            'email_sucursal': data.get('email_sucursal', '').strip(),
            'nro_estab_sucursal': data.get('nro_estab_sucursal', '').strip(),
            'cod_postal': data.get('cod_postal', '').strip(),
            'activa': data.get('activa') == 'on' or data.get('anulado') != 'Si',
            'cot_clave_acceso': data.get('cot_clave_acceso', '').strip(),
            'cot_kg_limite': _float_or_none(data.get('cot_kg_limite')),
            'cot_monto_limite': _float_or_none(data.get('cot_monto_limite')),
            'cot_cantidad_operaciones': _float_or_none(data.get('cot_cantidad_operaciones')),
            'geo_latitud': data.get('geo_latitud', '').strip(),
            'geo_longitud': data.get('geo_longitud', '').strip(),
            'geo_api_key': data.get('geo_api_key', '').strip(),
            'geo_api_key_javascript': data.get('geo_api_key_javascript', '').strip(),
            'activa_calculo_envios': data.get('activa_calculo_envios') in ('Si', 'on', '1'),
            'id_articulo_fact_envio': data.get('id_articulo_fact_envio', '').strip() or None,
            # Configuración Sucursal (tabs Opciones Generales, Agente, Impresoras, DNF)
            'vendedor_defecto': _float_or_none(data.get('vendedor_defecto')),
            'limite_consulta': int(data.get('limite_consulta')) if data.get('limite_consulta', '').strip() else None,
            'ruta_reporte_servidor': data.get('ruta_reporte_servidor', '').strip() or None,
            'ruta_reporte_comprobante': data.get('ruta_reporte_comprobante', '').strip() or None,
            'cant_renglon_venta': int(data.get('cant_renglon_venta')) if data.get('cant_renglon_venta', '').strip() else None,
            'salida_sin_stock': 'Si' if data.get('salida_sin_stock') == 'Si' else 'No',
            'dias_venc_presup': int(data.get('dias_venc_presup')) if data.get('dias_venc_presup', '').strip() else None,
            'dias_venc_pedido': int(data.get('dias_venc_pedido')) if data.get('dias_venc_pedido', '').strip() else None,
            'tipo_calculo_precios_impuesto_venta': data.get('tipo_calculo_precios_impuesto_venta', '').strip() or None,
            'lim_redondeo_tpv': _float_or_none(data.get('lim_redondeo_tpv')),
            'agente_retib': 'Si' if data.get('agente_retib') == 'Si' else 'No',
            'agente_retg': 'Si' if data.get('agente_retg') == 'Si' else 'No',
            'agente_reti': 'Si' if data.get('agente_reti') == 'Si' else 'No',
            'agente_percep': 'Si' if data.get('agente_percep') == 'Si' else 'No',
            'agente_percep_resol_afip_5329_iva': 'Si' if data.get('agente_percep_resol_afip_5329_iva') == 'Si' else 'No',
            'tipo_impresora': data.get('tipo_impresora', '').strip() or None,
            'nombre_impresora': data.get('nombre_impresora', '').strip() or None,
            'puerto_impresora': data.get('puerto_impresora', '').strip() or None,
            'doble_imp_etiqueta': 'Si' if data.get('doble_imp_etiqueta') == 'Si' else 'No',
            'dnf_vta': 'Si' if data.get('dnf_vta') == 'Si' else 'No',
            'dnf_tipo': data.get('dnf_tipo', '').strip() or None,
            'dnf_texto': data.get('dnf_texto', '').strip() or None,
            'dnf_texto2': data.get('dnf_texto2', '').strip() or None,
            'dnf_texto3': data.get('dnf_texto3', '').strip() or None,
        }
        
        # Validar campos obligatorios: solo el nombre es obligatorio
        if not datos_sucursal['nombre_sucursal']:
            error = "El nombre de la sucursal es obligatorio."
        else:
            if sucursales_service.actualizar_sucursal(base_empresa, branch_id, datos_sucursal):
                messages.success(request, "✅ Sucursal actualizada exitosamente.")
                return redirect('core:branch_list', empresa_id=1)
            else:
                error = "Error al actualizar la sucursal. Por favor intente nuevamente."
    
    # Obtener datos relacionados para los dropdowns (paises, provincias, viajantes como en Configuración.frm)
    paises = empresa_service.obtener_paises(base_empresa)
    provincias = empresa_service.obtener_provincias(base_empresa, sucursal.get('id_pais'))
    viajantes = sucursales_service.obtener_viajantes(base_empresa)
    
    context = {
        'empresa': empresa,
        'empresa_id': empresa_id,
        'modo_creacion': False,
        'error': error,
        'viajantes': viajantes,
        'paises': paises,
        'provincias': provincias,
        'sucursal': sucursal,
        'base_empresa': base_empresa,
        'branch_id': branch_id,  # id de sucursal para API tipos de envío (data-id-sucursal)
    }
    
    return render(request, 'core/system_config/branch_form.html', context)

@require_POST
@administranet_login_required
def branch_toggle_estado_view(request, empresa_id, branch_id):
    """
    Alterna el estado Activa/Anulada de una sucursal (Anulado=Si/No).
    Las sucursales no se eliminan en AdministraNET, solo se desactivan.
    """
    from core.services.administranet_sucursales import AdministraNETSucursalesService

    session_user = request.session.get("user", {})
    base_empresa = session_user.get("base_empresa")

    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:dashboard")

    sucursales_service = AdministraNETSucursalesService()
    result = sucursales_service.toggle_anulado_sucursal(base_empresa, branch_id)

    if result is None:
        messages.error(request, "Sucursal no encontrada o error al actualizar.")
    else:
        messages.success(
            request,
            "Sucursal marcada como activa." if result else "Sucursal desactivada (anulada).",
        )
    return redirect("core:branch_list", empresa_id=1)


@administranet_login_required
def branch_delete_view(request, empresa_id, branch_id):
    """
    Redirige a la lista. Las sucursales no se eliminan; usar toggle estado (Activa/Anulada).
    Se mantiene la ruta por compatibilidad con enlaces antiguos.
    """
    return redirect("core:branch_list", empresa_id=1)

@require_POST
@administranet_login_required
def cambiar_empresa_branch(request):
    """
    Cambia la sucursal activa del usuario en administraNET
    """
    from core.services.administranet_sucursales import AdministraNETSucursalesService
    import json
    
    session_user = request.session.get("user", {})
    base_empresa = session_user.get("base_empresa")
    
    if not base_empresa:
        if request.content_type == 'application/json':
            return JsonResponse({"error": "No se pudo determinar la empresa activa"}, status=400)
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:dashboard")
    
    # Obtener branch_id desde JSON (AJAX) o POST
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body)
            branch_id = data.get('branch_id')
        except json.JSONDecodeError:
            return JsonResponse({"error": "JSON inválido"}, status=400)
    else:
        branch_id = request.POST.get('branch_id')
    
    if not branch_id:
        if request.content_type == 'application/json':
            return JsonResponse({"error": "Sucursal requerida"}, status=400)
        messages.error(request, "Sucursal requerida.")
        return redirect("core:dashboard")
    
    try:
        branch_id = int(branch_id)
    except (ValueError, TypeError):
        if request.content_type == 'application/json':
            return JsonResponse({"error": "ID de sucursal inválido"}, status=400)
        messages.error(request, "ID de sucursal inválido.")
        return redirect("core:dashboard")
    
    # Validar que la sucursal existe y pertenece a la empresa
    sucursales_service = AdministraNETSucursalesService()
    sucursal = sucursales_service.obtener_sucursal(base_empresa, branch_id)
    
    if not sucursal or not sucursal.get('activa'):
        if request.content_type == 'application/json':
            return JsonResponse({"error": "Sucursal no encontrada o inactiva"}, status=400)
        messages.error(request, "Sucursal no encontrada o inactiva.")
        return redirect("core:dashboard")
    
    # Actualizar sesión con nueva sucursal
    session_user['id_sucursal'] = branch_id
    request.session['user'] = session_user
    request.session['branch_activa_id'] = branch_id
    
    if request.content_type == 'application/json':
        return JsonResponse({"success": True, "message": "Sucursal cambiada correctamente"})
    else:
        messages.success(request, "Sucursal cambiada correctamente.")
        next_url = request.META.get('HTTP_REFERER', '/')
        return redirect(next_url)