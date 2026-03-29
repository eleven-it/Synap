from django.urls import path
from . import views

app_name = "mpr"

urlpatterns = [
    path("", views.TableroView.as_view(), name="tablero"),
    path("ordenes/", views.OpListView.as_view(), name="op_list"),
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
    path("operarios/", views.OperariosListView.as_view(), name="operarios_list"),
    path("operarios/nuevo/", views.OperarioCreateView.as_view(), name="operario_create"),
    path("operarios/<int:id_operario>/editar/", views.OperarioUpdateView.as_view(), name="operario_edit"),
    path("operarios/<int:id_operario>/anular/", views.OperarioAnularView.as_view(), name="operario_anular"),
    path("operarios/<int:id_operario>/reactivar/", views.OperarioReactivarView.as_view(), name="operario_reactivar"),
    path("demanda/ventana-pack/", views.VentanaPackView.as_view(), name="ventana_pack"),
    path("demanda/ventana-pack/actualizar/", views.VentanaPackActualizarView.as_view(), name="ventana_pack_actualizar"),
    path("demanda/ventana-pack/agrupar/", views.VentanaPackAgruparView.as_view(), name="ventana_pack_agrupar"),
    path("api/empleados/", views.EmpleadosOperariosAPIView.as_view(), name="api_empleados"),
    path("demanda/pedidos-fabrica/", views.PedidosFabricaListView.as_view(), name="pedidos_fabrica_list"),
    path("demanda/opts-por-pedido/", views.OptsPorPedidoView.as_view(), name="opts_por_pedido"),
    path("opt/", views.OptListView.as_view(), name="opt_list"),
    path("opt/nueva/", views.NuevaOptView.as_view(), name="opt_create"),
    path("opt/<int:id_lista>/", views.OptDetailView.as_view(), name="opt_detail"),
    path("opt/<int:id_lista>/armado/", views.ArmadoOptView.as_view(), name="armado_opt"),
    # Deprecado: usar asistente (wizard ?paso=3&id_lista=X) para registrar OPP.
    path("opt/<int:id_lista>/registrar-opp/", views.RegistrarOppView.as_view(), name="registrar_opp"),
    path("opt/<int:id_lista>/cerrar/", views.CerrarOptView.as_view(), name="opt_cerrar"),
    path("opt/<int:id_lista>/comprobante.pdf/", views.opt_comprobante_pdf_view, name="opt_comprobante_pdf"),
]
