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
    path("armado/legacy/<int:id_en_abm>/", views.ArmadoLegacyView.as_view(), name="armado_bom"),
    path("reclasificacion/", views.ReclasificacionView.as_view(), name="reclasificacion"),
    path("armado-surtido/", views.ArmadoSurtidoRedirectView.as_view(), name="armado_surtido"),
    path(
        "imputacion-armado-1ra/",
        views.ImputacionArmado1raView.as_view(),
        name="imputacion_armado_1ra",
    ),
    path(
        "api/imputacion-armado-1ra/sugerir/",
        views.ImputacionArmadoSugerirAPIView.as_view(),
        name="api_imputacion_armado_sugerir",
    ),
    path(
        "api/imputacion-armado-1ra/confirmar/",
        views.ImputacionArmadoConfirmarAPIView.as_view(),
        name="api_imputacion_armado_confirmar",
    ),
    path(
        "api/armado/packs-catalog/",
        views.ArmadoPacksCatalogAPIView.as_view(),
        name="api_armado_packs_catalog",
    ),
    path(
        "api/armado/bom-pack/",
        views.ArmadoBomPackAPIView.as_view(),
        name="api_armado_bom_pack",
    ),
    path(
        "api/armado-surtido/stock-origen/",
        views.ArmadoSurtidoStockOrigenAPIView.as_view(),
        name="api_armado_surtido_stock",
    ),
    path(
        "api/armado-surtido/validar-item-lote/",
        views.ArmadoSurtidoValidarItemLoteAPIView.as_view(),
        name="api_armado_surtido_validar_item_lote",
    ),
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
    path("opt/<int:id_lista>/trazabilidad/", views.TrazabilidadOptView.as_view(), name="opt_trazabilidad"),
    path("opt/<int:id_lista>/armado/", views.ArmadoOptView.as_view(), name="armado_opt"),
    # DEPRECATED (E6/E11): usar /mpr/parte-produccion/ para registrar parte de producción.
    path("opt/<int:id_lista>/registrar-opp/", views.RegistrarOppView.as_view(), name="registrar_opp"),
    path("opt/<int:id_lista>/cerrar/", views.CerrarOptView.as_view(), name="opt_cerrar"),
    path("opt/<int:id_lista>/comprobante.pdf/", views.opt_comprobante_pdf_view, name="opt_comprobante_pdf"),
    # Etapa 2: Tablero de Demanda Consolidado por Artículo
    path("tablero-produccion/", views.TableroProduccionView.as_view(), name="tablero_produccion"),
    path("tablero-produccion/actualizar/", views.TableroProduccionActualizarView.as_view(), name="tablero_produccion_actualizar"),
    # Etapa 3: Turnos (CRUD) + Roster Rotativo
    path("turnos/", views.TurnosListView.as_view(), name="turnos_list"),
    path("turnos/nuevo/", views.TurnoCreateView.as_view(), name="turno_create"),
    path("turnos/<int:id_turno>/editar/", views.TurnoUpdateView.as_view(), name="turno_edit"),
    path("planificacion-turnos/", views.PlanificacionTurnosView.as_view(), name="planificacion_turnos"),
    path("planificacion-turnos/asignar/", views.AsignarTurnoRosterView.as_view(), name="roster_asignar"),
    path("planificacion-turnos/eliminar/", views.EliminarAsignacionRosterView.as_view(), name="roster_eliminar"),
    # Etapa 4: Parte de producción (ledger OPP-parte)
    path("parte-produccion/", views.ParteProduccionView.as_view(), name="parte_produccion"),
    path("parte-produccion/registrar/", views.RegistrarParteProduccionView.as_view(), name="parte_produccion_registrar"),
    path("parte-produccion/<str:parte_id>/ajuste/", views.AjusteParteView.as_view(), name="parte_ajuste"),
    # Etapa 5: Transición de stock entre etapas MPR
    # DEPRECADO UI (E9): la UI de transición por fila fue reemplazada por las pantallas
    # globales de Inspección y Clasificación. La URL se mantiene backward-safe.
    path("tablero-produccion/transicion/", views.TransicionLoteView.as_view(), name="transicion_lote"),
    # Etapa 7: Envío directo a producción desde el Tablero (ledger-componente, lote)
    path("tablero-produccion/enviar/", views.EnviarProduccionLoteView.as_view(), name="tablero_produccion_enviar"),
    path("tablero-produccion/envios/", views.EnviosProduccionListView.as_view(), name="envios_produccion"),
    path("tablero-produccion/envios/anular/", views.AnularEnviosProduccionView.as_view(), name="envios_produccion_anular"),
    # Etapa 10: Clasificación de Producción (pantalla única; reemplaza Inspección/Clasificación E9)
    path("tablero-produccion/clasificacion-produccion/", views.ClasificacionProduccionView.as_view(), name="clasificacion_produccion"),
    path("tablero-produccion/clasificacion-produccion/registrar/", views.RegistrarClasificacionProduccionView.as_view(), name="clasificacion_produccion_registrar"),
]
