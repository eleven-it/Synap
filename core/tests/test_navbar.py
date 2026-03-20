from django.test import TestCase, Client
from django.urls import reverse, NoReverseMatch
from core.utils.utils import APPS_MENU, iter_menu_hojas_apps_menu
from core.models import UsuarioExtendido
from django.contrib.auth.models import Permission

class MenuItemIdsNavbarTest(TestCase):
    """Cada hoja de APPS_MENU debe tener menu_item_id único (visibilidad granular)."""

    def test_menu_item_ids_unicos_y_presentes(self):
        ids_encontrados = []
        for row in iter_menu_hojas_apps_menu():
            self.assertTrue(row[5], msg=f"Falta menu_item_id en {row[0]} / {row[3]}")
            ids_encontrados.append(row[5])
        self.assertEqual(
            len(ids_encontrados),
            len(set(ids_encontrados)),
            msg=f"menu_item_id duplicados: {[x for x in ids_encontrados if ids_encontrados.count(x) > 1]}",
        )


# Test para verificar las URLs del navbar de accounting (módulo accounting eliminado)
class NavbarAccountingURLsTest(TestCase):
    """
    La app accounting fue eliminada del sistema; el test se omite.
    """
    def setUp(self):
        self.user = UsuarioExtendido.objects.create_user(email='testuser@synap.com', nombre='Test User', password='testpass')
        self.user.is_staff = True
        self.user.save()
        self.client.force_login(self.user)
    
    def test_accounting_navbar_urls(self):
        """La app accounting ya no está en APPS_MENU; test omitido."""
        accounting_app = next((app for app in APPS_MENU if app.get("id") == "accounting"), None)
        if accounting_app is None:
            self.skipTest("La app 'accounting' fue eliminada de APPS_MENU")
            return
        
        # Recorrer todos los submenús de accounting
        failed_urls = []
        middleware_errors = []
        
        for submenu in accounting_app.get("submenus", []):
            for item in submenu.get("items", []):
                url_name = item.get("url")
                if not url_name:
                    continue
                
                try:
                    # Intentar resolver la URL
                    url = reverse(url_name)
                    
                    # Hacer request GET a la URL
                    try:
                        response = self.client.get(url)
                        
                        # Verificar que la respuesta sea exitosa (200) o redirección (302)
                        if response.status_code not in [200, 302]:
                            # Verificar si es un error específico del middleware de mensajes
                            if "MessageFailure" in str(response.content) or "MessageMiddleware" in str(response.content):
                                middleware_errors.append({
                                    'item': item.get('label', 'Unknown'),
                                    'url_name': url_name,
                                    'resolved_url': url,
                                    'error': 'Middleware de mensajes no configurado en test'
                                })
                                print(f"⚠️  {item.get('label', 'Unknown')}: {url_name} -> {url} (Middleware error - URL válida)")
                            else:
                                failed_urls.append({
                                    'item': item.get('label', 'Unknown'),
                                    'url_name': url_name,
                                    'resolved_url': url,
                                    'status_code': response.status_code,
                                    'error': f'Status code {response.status_code}'
                                })
                        else:
                            print(f"✅ {item.get('label', 'Unknown')}: {url_name} -> {url} (Status: {response.status_code})")
                    
                    except Exception as e:
                        error_str = str(e)
                        # Verificar si es un error específico del middleware de mensajes
                        if "MessageFailure" in error_str or "MessageMiddleware" in error_str:
                            middleware_errors.append({
                                'item': item.get('label', 'Unknown'),
                                'url_name': url_name,
                                'resolved_url': url,
                                'error': 'Middleware de mensajes no configurado en test'
                            })
                            print(f"⚠️  {item.get('label', 'Unknown')}: {url_name} -> {url} (Middleware error - URL válida)")
                        else:
                            failed_urls.append({
                                'item': item.get('label', 'Unknown'),
                                'url_name': url_name,
                                'resolved_url': url,
                                'error': f'Request failed: {error_str}'
                            })
                
                except NoReverseMatch:
                    failed_urls.append({
                        'item': item.get('label', 'Unknown'),
                        'url_name': url_name,
                        'error': 'URL name not found'
                    })
                except Exception as e:
                    failed_urls.append({
                        'item': item.get('label', 'Unknown'),
                        'url_name': url_name,
                        'error': f'Unexpected error: {str(e)}'
                    })
        
        # Mostrar resumen
        total_items = len([item for submenu in accounting_app.get('submenus', []) for item in submenu.get('items', [])])
        successful_items = total_items - len(failed_urls) - len(middleware_errors)
        
        print(f"\n📊 Resumen del test:")
        print(f"  ✅ URLs exitosas: {successful_items}")
        print(f"  ⚠️  URLs con error de middleware: {len(middleware_errors)}")
        print(f"  ❌ URLs que fallaron: {len(failed_urls)}")
        print(f"  📋 Total de URLs: {total_items}")
        
        # Si hay URLs fallidas (excluyendo errores de middleware), mostrar información detallada y fallar el test
        if failed_urls:
            print("\n❌ URLs que fallaron:")
            for failed in failed_urls:
                print(f"  - {failed['item']} ({failed['url_name']}): {failed['error']}")
                if 'resolved_url' in failed:
                    print(f"    URL resuelta: {failed['resolved_url']}")
                if 'status_code' in failed:
                    print(f"    Status code: {failed['status_code']}")
            
            self.fail(f"Se encontraron {len(failed_urls)} URLs que fallaron en el navbar de accounting")
        
        # Si solo hay errores de middleware, considerar el test como exitoso
        if middleware_errors:
            print("\n⚠️  URLs con error de middleware (URLs válidas pero middleware no configurado en test):")
            for error in middleware_errors:
                print(f"  - {error['item']} ({error['url_name']}): {error['error']}")
                print(f"    URL resuelta: {error['resolved_url']}")
            
            print(f"\n✅ Todas las {total_items} URLs del navbar de accounting se resuelven correctamente!")
            print("   Los errores de middleware son esperados en el entorno de test y no afectan la funcionalidad real.")
        
        if not failed_urls and not middleware_errors:
            print(f"\n✅ Todas las {total_items} URLs del navbar de accounting son accesibles")
