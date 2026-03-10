from django.urls import path
from . import views

app_name = "mpr"

urlpatterns = [
    path("", views.TableroView.as_view(), name="tablero"),
    path("wizard/", views.WizardProduccionView.as_view(), name="wizard"),
    path("bom/", views.BomListView.as_view(), name="bom_list"),
    path("bom/nuevo/", views.BomCreateView.as_view(), name="bom_create"),
    path("bom/<int:id_en_abm>/", views.BomDetailView.as_view(), name="bom_detail"),
    path("bom/<int:id_en_abm>/editar/", views.BomEditView.as_view(), name="bom_edit"),
    path("armado/", views.ArmadoView.as_view(), name="armado"),
    path("armado/<int:id_en_abm>/", views.ArmadoView.as_view(), name="armado_bom"),
    path("reclasificacion/", views.ReclasificacionView.as_view(), name="reclasificacion"),
    path("reportes/", views.ReportesMPRView.as_view(), name="reportes"),
    path("config/depositos/", views.ConfigDepositosView.as_view(), name="config_depositos"),
    path("demanda/ventana-pack/", views.VentanaPackView.as_view(), name="ventana_pack"),
    path("demanda/ventana-pack/actualizar/", views.VentanaPackActualizarView.as_view(), name="ventana_pack_actualizar"),
    path("demanda/ventana-pack/agrupar/", views.VentanaPackAgruparView.as_view(), name="ventana_pack_agrupar"),
    path("demanda/pedidos-fabrica/", views.PedidosFabricaListView.as_view(), name="pedidos_fabrica_list"),
    path("opt/", views.OptListView.as_view(), name="opt_list"),
    path("opt/nueva/", views.NuevaOptView.as_view(), name="opt_create"),
    path("opt/<int:id_lista>/", views.OptDetailView.as_view(), name="opt_detail"),
    # Deprecado: usar asistente (wizard ?paso=3&id_lista=X) para registrar OPP.
    path("opt/<int:id_lista>/registrar-opp/", views.RegistrarOppView.as_view(), name="registrar_opp"),
    path("opt/<int:id_lista>/cerrar/", views.CerrarOptView.as_view(), name="opt_cerrar"),
]
