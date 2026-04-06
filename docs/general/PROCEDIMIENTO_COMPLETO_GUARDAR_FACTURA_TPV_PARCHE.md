# Procedimiento completo Guardar_Factura (con parche)

Fuente: administranet_vb6/Formularios/TPV.frm

Rango extraido: lineas 7834 a 10326.

INICIO_PROCEDIMIENTO
Private Sub Guardar_Factura()

error_fiscal_ejecutado = "No"
fe_aprobada = "No"

Validaciones_Factura

If MsgBox("Desea generar el comprobante?", vbYesNo + vbQuestion, "ATENCION") = vbYes Then

' Capturamos el ERROR
On Error GoTo captura
    
    ' Verifico limite de extraccion de caja
    limite_efectivo = Principal.limite_efectivo_caja("No")
    If limite_efectivo = "Si" Then
        Exit Sub
    End If
    
'    ''REDONDEO - Redondeo mayor a cero y a favor
'    If txtRedondeo.Text > 0 And cmbTipoR.ListIndex = 0 Then
'        ' Validaciones de tipo de cobro efectivo
'        If CDec(Label_Total) > CDec(importe_cobrado_efectivo) + CDec(Total_CtaCte) + CDec(Total_Tarjeta) + CDec(Total_Cheque) + CDec(interes_tarjeta_total) Then
'            MsgBox "El importe ingresado no alcanza para cancelar el comprobante", vbCritical, "ATENCION"
'            'importe_cobrado_efectivo.SetFocus
'            Exit Sub
'        End If
'    End If

    'Valido limites de credito  /  'Si el contribuyente es distinto de consumidor final
'    If ID_Cat_Contribuyente <> 4 Then
    If Codigo_Cliente <> 1 Then
        '''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
        'Limites Credito'
        '''''''''''''''''
        verificar_limites
        If generaigual = "No" Then
            Exit Sub
        End If
    End If
                                     
    ' Formulario de espera
    form_espera.label_mje = "Espere por favor procesando datos...Generando comprobante"
    form_espera.Show
    DoEvents
         
    form_espera.ProgressBar.Value = 25
    
    Deshabilita_Guardar_F12 = "No"
         
    ' Abro Conexion
    conn.Open
    
    Dim rs_codmov As New ADODB.Recordset
    Dim rs_cuentacliente As New ADODB.Recordset
    Dim rs_saldo_cliente As New ADODB.Recordset
    Dim rs_saldo_caja As New ADODB.Recordset
    Dim rs_caja As New ADODB.Recordset
    Dim rs_stock As New ADODB.Recordset
    Dim rs_saldo_stock As New ADODB.Recordset
    Dim rs_lote As New ADODB.Recordset
    Dim rs_recibo_factura As New ADODB.Recordset
    Dim rs_pedido As New ADODB.Recordset
    Dim rs_remito As New ADODB.Recordset
    Dim rs_pedido_factura As New ADODB.Recordset
    Dim rs_remito_factura As New ADODB.Recordset
    Dim rs_stock_deposito As New ADODB.Recordset
    Dim rs_nro_fact As New ADODB.Recordset
    Dim rs_cliente As New ADODB.Recordset
    Dim rs_informe As New ADODB.Recordset
    Dim rs_cond_venta As New ADODB.Recordset
    Dim rs_chequetercero As New ADODB.Recordset
    Dim rs_banco As New ADODB.Recordset
    Dim rs_cv As New ADODB.Recordset
    Dim rs_tc_comprobante As New ADODB.Recordset
    Dim rs_valid_pedido As New ADODB.Recordset
    Dim rs_cuerpostock As New ADODB.Recordset
    Dim rs_percep_cli_temp As New ADODB.Recordset
    Dim rs_percep_cli As New ADODB.Recordset
    Dim rs_stockp As New ADODB.Recordset
    Dim rs_stock_facturado As New ADODB.Recordset
    Dim rs_consulta_articulo As New ADODB.Recordset
    Dim rs_cuentacliente_fe As New ADODB.Recordset
    Dim rs_consulta_pedido_cliente As New ADODB.Recordset
    Dim fe_aprobada As String
    
    
    ' Inicio Transaccion de CodMov
    conn.CursorLocation = adUseClient
    conn.BeginTrans
    conn.Execute "SET AUTOCOMMIT=0"
            
    ' Actualizo el numero de movimiento
    rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn, adOpenDynamic, adLockPessimistic
    contador = rs_codmov.Fields!CodigoMovimiento
'    contador = contador + 1

    If Principal.activ_contabilidad = "Si" Then
        'Contador con costo venta
        contador = contador + 2
    Else
        contador = contador + 1
    End If

    rs_codmov.Fields!CodigoMovimiento = contador
    CodMov = contador
    ' Control error
'    control_error = "CodMov"
    rs_codmov.Update
    rs_codmov.Close
    
    ' Cierro transaccion de CodMov
    If conn.State = 1 Then
        conn.CommitTrans
    End If
                               
    ' Asigno a la variable para guardar el Codigo del movimiento para la FA
    CodigoMovInf = CStr(contador)
                   
    ' Inicio Transaccion
     conn.BeginTrans
     conn.Execute "SET AUTOCOMMIT=0"
     
    ' Procedimiento datos adicionales
    Actualiza_datos_adicionales
        
    'Guardar id_deposito_despacho en cuentacliente y en comp_ped
    ''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
     
    ' Guardo Tipo de Factura
    
    ' Si la empresa es RI
    ' Si es RI
    ' Si es Factura A la categoria del IVA es Responsable Inscripto
    If Principal.IDIVA = 1 Or Principal.IDIVA = 7 Or (ID_Cat_Contribuyente = 2 And Principal.resol_afip_5003 = "Si") Then
        If ID_Cat_Contribuyente = 1 Or (ID_Cat_Contribuyente = 2 And Principal.resol_afip_5003 = "Si") Then
            TipoFactura = "FA"
        End If
    End If
    
    ' Si es Factura M - Si la empresa es de Categoria M
    If Principal.IDIVA = 6 Or Principal.IDIVA = 7 Then
'        ' Si es RI M
'        If ID_Cat_Contribuyente = 6 Then
            TipoFactura = "FM"
'        End If
    End If
             
    ' Si es CF, MON, EXENTO
    If (ID_Cat_Contribuyente = 2 And Principal.resol_afip_5003 = "No") Or ID_Cat_Contribuyente = 3 Or ID_Cat_Contribuyente = 4 Or ID_Cat_Contribuyente = 8 Then
        TipoFactura = "FB"
    End If

    ' Si la empresa es MON, Exento
    If (Principal.IDIVA = 2 Or Principal.IDIVA = 3) Then
        TipoFactura = "FC"
    End If

    ' *** Localizacion
    If Principal.id_pais <> 1 Then
        ' Si er RI
        TipoFactura = "FA"
    End If

    ' Verificacion si es PV electronico
    Verifica_pv_electronico
    
    ' Validacion de seleccion de PV
    If Principal.selec_pv = "Si" Then
    
        Reporte_Comprobante_PV_Fiscal punto_venta.BoundText, TipoFactura, "Otra"
        
        ' Si el PV seleccion es igual al del usuario
        If punto_venta.BoundText = Principal.id_punto_venta Then
            mod_pv = "No"
            
            tipo_impresora = Obtener_Tipo_Impresora_Factura("tipo_impresora", TipoFactura)
            nombre_impresora = Obtener_Tipo_Impresora_Factura("nombre_impresora", TipoFactura)
            
            ' Cambio codigo Impresora fiscal con seleccion de PV
            If tipo_impresora = "Fiscal" Then
                Reporte_Comprobante_PV_Fiscal punto_venta.BoundText, TipoFactura, "Fiscal"
            End If
            
        ' Si es diferente
        Else
            mod_pv = "Si"
            ' Traigo el tipo de impresora del PV seleccionado manualmente
            rs_informe.Open "select * FROM reporte_comprobante WHERE id_punto_venta = " & punto_venta.BoundText & _
            " AND nombre_reporte_comprobante = '" & TipoFactura & "'", conn, adOpenDynamic, adLockOptimistic
            tipo_impresora = rs_informe.Fields!tipo_impresora
            nombre_impresora = rs_informe.Fields!nombre_impresora
            rs_informe.Close
        End If
        
        ' Cambio codigo Impresora fiscal con seleccion de PV
        If tipo_impresora = "Fiscal" Then
            Reporte_Comprobante_PV_Fiscal punto_venta.BoundText, TipoFactura, "Fiscal"
'        Else
'            Reporte_Comprobante_PV_Fiscal punto_venta.BoundText, TipoFactura, "Otra"
        End If
        
        ' Seleccion de sucursal de punto de venta
        id_sucursal = Obtener_Datos_PV_Sucursal(punto_venta.BoundText)
        
        id_pv_fiscal = punto_venta.BoundText

    Else
        mod_pv = "No"
        
         tipo_impresora = Obtener_Tipo_Impresora_Factura("tipo_impresora", TipoFactura)
         nombre_impresora = Obtener_Tipo_Impresora_Factura("nombre_impresora", TipoFactura)
                
        ' Seleccion de sucursal de punto de venta
        id_sucursal = Principal.codSucursal
        
        id_pv_fiscal = Principal.id_punto_venta
        
    End If
       
    ' Control de limites de pv esta habilitado
    If Obtener_Datos_Licencia("evalua_modulos") = "Si" Then
        If Habilita_Licencia_PV(CDbl(id_pv_fiscal), "pv_elect") = "No" Then
            conn.RollbackTrans
            conn.Close
            Unload form_espera
            MsgBox "El punto de venta se encuentra deshabilitado para usar el sistema. Contactese con el sector de ventas de administraNET Gestin", vbExclamation, "ATENCION"
            Exit Sub
        End If
    End If
              
    ' Asigno numeracion
    If TipoFactura = "FB" Then
        ' Valida si selecciona PV
        If pv_electronico = "No" Then
            If Principal.selec_pv = "Si" Then
                rs_nro_fact.Open "select * from talonarios where id_punto_venta = " & id_pv_fiscal & " And TipoComprobante = 'FB'", conn, adOpenDynamic, adLockOptimistic
            Else
                rs_nro_fact.Open "select * from talonarios where id_punto_venta = " & Principal.id_punto_venta & " And TipoComprobante = 'FB'", conn, adOpenDynamic, adLockOptimistic
            End If
        End If
    
        If pv_electronico = "Si" Then
            rs_nro_fact.Open "select * from talonarios where id_punto_venta = " & id_pv_electronico & " And TipoComprobante = 'FB'", conn, adOpenDynamic, adLockOptimistic
        End If
    End If
         
    If TipoFactura = "FA" Then
        ' Valida si selecciona PV
        If pv_electronico = "No" Then
            If Principal.selec_pv = "Si" Then
                rs_nro_fact.Open "select * from talonarios where id_punto_venta = " & id_pv_fiscal & " And TipoComprobante = 'FA'", conn, adOpenDynamic, adLockOptimistic
            Else
                rs_nro_fact.Open "select * from talonarios where id_punto_venta = " & Principal.id_punto_venta & " And TipoComprobante = 'FA'", conn, adOpenDynamic, adLockOptimistic
            End If
        End If
        
        If pv_electronico = "Si" Then
            rs_nro_fact.Open "select * from talonarios where id_punto_venta = " & id_pv_fiscal & " And TipoComprobante = 'FA'", conn, adOpenDynamic, adLockOptimistic
        End If
    End If
    
    If TipoFactura = "FC" Then
        ' Valida si selecciona PV
        If pv_electronico = "No" Then
            If Principal.selec_pv = "Si" Then
                rs_nro_fact.Open "select * from talonarios where id_punto_venta = " & id_pv_fiscal & " And TipoComprobante = 'FC'", conn, adOpenDynamic, adLockOptimistic
            Else
                rs_nro_fact.Open "select * from talonarios where id_punto_venta = " & Principal.id_punto_venta & " And TipoComprobante = 'FC'", conn, adOpenDynamic, adLockOptimistic
            End If
        End If
        
        If pv_electronico = "Si" Then
            rs_nro_fact.Open "select * from talonarios where id_punto_venta = " & id_pv_electronico & " And TipoComprobante = 'FC'", conn, adOpenDynamic, adLockOptimistic
        End If
    End If
    
     If TipoFactura = "FM" Then
        ' Valida si selecciona PV
        If pv_electronico = "No" Then
            If Principal.selec_pv = "Si" Then
                rs_nro_fact.Open "select * from talonarios where id_punto_venta = " & id_pv_fiscal & " And TipoComprobante = 'FM'", conn, adOpenDynamic, adLockOptimistic
            Else
                rs_nro_fact.Open "select * from talonarios where id_punto_venta = " & Principal.id_punto_venta & " And TipoComprobante = 'FM'", conn, adOpenDynamic, adLockOptimistic
            End If
        End If
        
        If pv_electronico = "Si" Then
            rs_nro_fact.Open "select * from talonarios where id_punto_venta = " & id_pv_electronico & " And TipoComprobante = 'FM'", conn, adOpenDynamic, adLockOptimistic
        End If
    End If
    
    ' Valido si es factura por sistema o Controlador Fiscal o Electronica
        ' Factura electronica - ' FE con CAEA
        If pv_electronico = "Si" And fe_regimen_tipo = "CAE" Then

'            ' Verifico si servidor de AFIP esta online
'            If AFIP_Estado_Servidor = False Then
'                ' Cierro transaccion
'                If conn.State = 1 Then
'                    conn.RollbackTrans
'                    conn.Close
'                End If
'                MsgBox "El servidor de AFIP se encuentra temporalmente fuera de servicio, intente mas tarde", vbInformation, "ATENCION"
'                Unload form_espera
'                Exit Sub
'            End If

            ' *** Free ***
            ' URL de servidores de AFIP
            URLWSAA = Principal.fe_url_login  ' URL de Login
            URLWSW = Principal.fe_url_acceso_servidor  ' URL de acceso a servidor

            Dim wsfev1 As FEAFIPLib.wsfev1
            Dim Nro_elect As Double
            CAE$ = ""
            Vencimiento$ = ""
            resultado$ = ""
            Reproceso$ = ""

            Nro_elect = 0
            ' Seleccion de PV
'            If Principal.selec_pv = "Si" And Facturacion.TipoFactura = "Sistema" Then
'                PtoVta = CDbl(punto_venta.Text)
'            Else
'                PtoVta = Principal.PV
'            End If

            PtoVta = nro_pv_electronico
            
            TipoComp = Obtener_Tipo_Doc_AFIP(TipoFactura)
            
            FechaComp = Format(Fecha, "yyyymmdd")
            TipoVenta = 3 ' Venta de productos y servicios (Concepto por defecto)
            FechaServDesde = Format(Fecha(), "yyyymmdd") ' Solo para el caso de facturacion servicios
            FechaServHasta = Format(Fecha(), "yyyymmdd")
            FechaVencPago = Format(Fecha, "yyyymmdd")
            CodigoMoneda = "PES" ' Codigo de moneda de la AFIP (Por defecto pesos) Ya que la factura normal se emite en Pesos, la de exportacin sale en dolares, de todas formas se puede calcular el valor en dolares
            cotizacion_moneda = 1
            impTotalConceptos = 0

            Set wsfev1 = New FEAFIPLib.wsfev1

            fact_2da_emp = Obtener_CUIT_2da_Empresa(id_pv_electronico)
            
            If fact_2da_emp = "No" Then
                wsfev1.CUIT = Principal.fe_CUIT_empresa   ' Aca va el CUIT de la empresa, debo traerlo de una variable
                cuit_qr = Principal.fe_CUIT_empresa
            Else
                wsfev1.CUIT = Formato_CUIT_AFIP(CStr(fact_2da_emp))   ' Aca va el CUIT de la empresa, debo traerlo de una variable
                cuit_qr = Formato_CUIT_AFIP(CStr(fact_2da_emp))
            End If

            wsfev1.URL = URLWSW
            If wsfev1.login(Principal.ruta_certificado + "\certificado.crt", Principal.ruta_certificado + "\clave.key", URLWSAA) Then  'Consultar la FEDOCS.rar para ver como obtener certificado y clave

'            If wsfev1.login(App.Path + "\Certificado FE\certificado.crt", App.Path + "\Certificado FE\clave.key", URLWSAA) Then 'Consultar la FEDOCS.rar para ver como obtener certificado y clave

                ' Recupero el ultimo nro de comprobante emitido FA
                ' Si hay error de conectividad muestro el mensaje de error y aviso
                If Not wsfev1.RecuperaLastCMP(PtoVta, TipoComp, Nro_elect) Then

                    EnviarMensaje (wsfev1.ErrorDesc) & Chr(13) + "No se pudo recuperar el ultimo nmero de comprobante informado por AFIP"

'                    MsgBox (wsfev1.ErrorDesc) & Chr(13) + "No se pudo recuperar el ultimo nmero de comprobante informado por AFIP", vbInformation, "ATENCION"
'                    error_fe = (wsfev1.ErrorDesc) & "Error de conectividad"
                    GoTo captura

                ' Si no hay error asigno el numero de AFIP
                Else

                    Nro_elect = Nro_elect + 1

                    ' Fallan los numeradores de AFIP
                    If Nro_elect = 1 And rs_nro_fact.Fields!Nro > 1 Then
                        EnviarMensaje "El servidor de AFIP se encuentra cado. Por favor reintente mas tarde"
'                        MsgBox "El servidor de AFIP se encuentra cado. Por favor reintente mas tarde", vbExclamation, "ATENCION"
                        GoTo captura
                    End If

                    ' Validacion que el nro de la AFIP + 1 coincida con el talonario del sistema
                    If rs_nro_fact.Fields!Nro <> Nro_elect Then
                        conn.RollbackTrans
                        conn.Close
                        Unload form_espera
                        MsgBox "No coincide el Nro. de talonario con el Nro. de comprobante de la AFIP. Controle las facturas emitidas en sistema con las de AFIP", vbCritical, "ATENCION"
'                        GoTo captura
                        Exit Sub
                    End If

                    ' Nro Comprobante
                    NroComp = CDbl(Nro_elect)

                    Ceros_Nro_Comp = Principal.Ceros_Nro_Comp(Nro_elect)

                    ' Nro PV
                    ceros_pv = Principal.Ceros_Nro_pv(rs_nro_fact.Fields!PV)
                    Nro = ceros_pv & rs_nro_fact.Fields!PV & "-" & Ceros_Nro_Comp & Nro_elect

                    ' Asigno el Nro para la busqueda
                    NroBusq = NroComp

                    ' Actualizo Numeracion
                    ContadorComp = CDbl(Nro_elect)
                    ContadorComp = ContadorComp + 1
                    rs_nro_fact.Fields!Nro = ContadorComp
                    rs_nro_fact.Update

                End If

            ' Si no pudo loguearse a la AFIP, genero comprobante en sistema
            Else

'                MsgBox "EL SERVICIO DE AFIP SE ENCUENTRA CAIDO MOMENTANEAMENTE. REINTENTE MAS TARDE" & Chr(13) + (wsfev1.ErrorDesc), vbInformation, "ATENCION"
                EnviarMensaje "EL SERVICIO DE AFIP SE ENCUENTRA CAIDO MOMENTANEAMENTE. REINTENTE MAS TARDE" & Chr(13) + (wsfev1.ErrorDesc)
                GoTo captura

            End If

        End If

'    If Principal.tipo_impresora_FA = "Normal" Or Principal.tipo_impresora_FA = "Ventana" Or Principal.tipo_impresora_FA = "Sin impresion" Or Principal.tipo_impresora_FB = "Normal" Or Principal.tipo_impresora_FB = "Ventana" Or Principal.tipo_impresora_FB = "Sin impresion" Then
    If pv_electronico = "No" And (tipo_impresora = "Normal" Or tipo_impresora = "Ventana" Or tipo_impresora = "Sin impresion" Or mod_pv = "Si") Or (pv_electronico = "Si" And fe_regimen_tipo = "CAEA") Then
    '  Principal.fe_regimen = "No" And
    ' Numeracion de Factura por Sistema
                                                            
        ' Nro Comprobante
        NroComp = CDbl(rs_nro_fact.Fields!Nro)
        
        Ceros_Nro_Comp = Principal.Ceros_Nro_Comp(rs_nro_fact.Fields!Nro)
                
        ' Nro PV
        ceros_pv = Principal.Ceros_Nro_pv(rs_nro_fact.Fields!PV)
        Nro = ceros_pv & rs_nro_fact.Fields!PV & "-" & Ceros_Nro_Comp & rs_nro_fact.Fields!Nro
                                   
        ' Asigno el Nro para la busqueda
        NroBusq = NroComp
                                   
         ' Actualizo Numeracion
         ContadorComp = CDbl(rs_nro_fact.Fields!Nro)
         ContadorComp = ContadorComp + 1
         rs_nro_fact.Fields!Nro = ContadorComp
         rs_nro_fact.Update
        
    End If
                   
    ' Impresora Fiscal
    Dim nro_fiscal As Double
    Dim str_comprobante_numero As String
    Dim str_comprobante_tipo As String
     
     ' Cambio codigo Impresora fiscal con seleccion de PV
     If (pv_electronico = "No" And tipo_impresora = "Fiscal") Or fe_regimen_tipo = "CAEA" Then    ' And mod_pv = "No"
                        
        ' Validacion si es impresora de ticket, los limites fiscales, para cliente Consumidores Finales
        If TipoFactura = "FB" Or TipoFactura = "FC" Then
        
            ' Validacion si es impresora de ticket, los limites fiscales, para cliente Consumidores Finales
'            If Principal.tipo_imp_fiscal_FB = "Ticket" Then
                If (CDec(ImporteTotal.Caption) > CDec(Principal.fiscal_monto_CF_FB)) And Codigo_Cliente = 1 Then
                    conn.RollbackTrans
                    conn.Close
                    MsgBox "El limite fiscal para comprobantes consumidor final es: " & Principal.fiscal_monto_CF_FB, vbCritical, "ATENCION"
                    Exit Sub
                End If
'             End If
             
        End If
    
    End If
                
     If (pv_electronico = "No" And tipo_impresora = "Fiscal") Then     ' And mod_pv = "No"
                
        If Principal.marca_imp_fiscal_FA = "Hasar" Or Principal.marca_imp_fiscal_FB = "Hasar" Or Principal.marca_imp_fiscal_FA = "Olivetti" Or Principal.marca_imp_fiscal_FA = "NCR" Or Principal.marca_imp_fiscal_FB = "Olivetti" Or Principal.marca_imp_fiscal_FB = "NCR" Then
                   
            ' Impresoras Hasar 1ra Generacion
            If Principal.codigo_modelo_imp_fiscal_FB < 36 Then
          
                If TipoFactura = "FA" Then
                    Impresion_Encabezado_Hasar_1G TipoFactura
                    ' Traigo ultimo numero del controlador fiscal
                    nro_fiscal = Principal.HASAR1.UltimoDocumentoFiscalA + 1
                End If
                
                If TipoFactura = "FB" Or TipoFactura = "FC" Then
                    Impresion_Encabezado_Hasar_1G TipoFactura
                    ' Traigo ultimo numero del controlador fiscal
                    nro_fiscal = Principal.HASAR1.UltimoDocumentoFiscalBC + 1
                End If
                                           
                If nro_fiscal = 0 Then
                    nro_fiscal = 1
                End If
            
            ' Impresoras Hasar 2da Generacion
            Else
            
                Principal.HasarNG.Conectar Principal.ip_imp_fiscal_FA
                Carga_Cliente_Hasar_2da_Gen
                
                Dim respabrir As RespuestaAbrirDocumento
                respabrir = Principal.HasarNG.AbrirDocumento(Obtener_Tipo_Doc_AFIP(TipoFactura))
                
                ' Traigo ultimo numero del controlador fiscal
                nro_fiscal = respabrir.numeroComprobante + 1
            
            End If
        
        End If
                                                                              
        If Principal.marca_imp_fiscal_FA = "Epson" Or Principal.marca_imp_fiscal_FB = "Epson" Then
        
            ' Impresoras Epson 1ra Generacion
            If Principal.codigo_modelo_imp_fiscal_FA < 10 Then
        
                If TipoFactura = "FA" Then
                    ' Traigo ultimo numero del controlador fiscal
                    Principal.PrinterFiscal1.PortNumber = Principal.puerto_impresora_FA
                    respuesta_cf_epson = Principal.PrinterFiscal1.Status("A")
                    nro_fiscal = CDbl(Principal.PrinterFiscal1.AnswerField_7) + 1
                End If
                
                If TipoFactura = "FB" Then
                    ' Traigo ultimo numero del controlador fiscal
                    Principal.PrinterFiscal1.PortNumber = Principal.puerto_impresora_FB
                    respuesta_cf_epson = Principal.PrinterFiscal1.Status("A")
                    nro_fiscal = CDbl(Principal.PrinterFiscal1.AnswerField_5) + 1
                End If
                
                If TipoFactura = "FC" Then
                    ' Traigo ultimo numero del controlador fiscal
                    Principal.PrinterFiscal1.PortNumber = Principal.puerto_impresora_FC
                    respuesta_cf_epson = Principal.PrinterFiscal1.Status("A")
                    nro_fiscal = CDbl(Principal.PrinterFiscal1.AnswerField_5) + 1
                End If
                
                If respuesta_cf_epson = False Then
                    GoTo captura:
                End If
                
                If nro_fiscal = 0 Then
                    nro_fiscal = 1
                End If
            
            ' Impresoras Epson 2da Generacion
            Else
                
                ' Conexion impresora fiscal
                ConfigurarVelocidad (Principal.baudios_imp_fiscal_FA)
                ConfigurarPuerto (Principal.puerto_impresora_FA)
                error_fiscal_epson = Conectar()
                                            
                ' Cargo datos de cliente Epson 2da Generacion
                Carga_Cliente_Epson_2da_Gen
                
                error_fiscal_epson = CargarComprobanteAsociado("081-00001-00000001")
                
'                            error_fiscal_epson = EstablecerEncabezado(2, "")
                
                ' Abro conexion de impresora tipo comprobante FA o FB
                 AbrirComprobante (2)

                ' Consultar numero y tipo de comprobante actual
                str_comprobante_numero = String(60, vbNullChar)
                error_fiscal_epson = ConsultarNumeroComprobanteActual(str_comprobante_numero, Len(str_comprobante_numero))
                                            
                nro_fiscal = CDbl(str_comprobante_numero)
                
                If nro_fiscal = 0 Then
                    nro_fiscal = 1
                End If
            
            End If
            
        End If
                                                                              
        ' Nro Comprobante
        NroComp = CDbl(nro_fiscal)
                
        Ceros_Nro_Comp = Principal.Ceros_Nro_Comp(nro_fiscal)
                
        ' Nro PV
        ceros_pv = Principal.Ceros_Nro_pv(rs_nro_fact.Fields!PV)
        Nro = ceros_pv & rs_nro_fact.Fields!PV & "-" & Ceros_Nro_Comp & nro_fiscal
                                      
        ' Asigno el Nro para la busqueda
        NroBusq = NroComp
                                   
         ' Actualizo Numeracion
         ContadorComp = CDbl(nro_fiscal)
         ContadorComp = ContadorComp + 1
         rs_nro_fact.Fields!Nro = ContadorComp
         rs_nro_fact.Update
        
    End If
                   
    ' Guardo en la tabla cuentacliente la factura
    rs_cuentacliente.Open "SELECT * FROM cuentacliente WHERE CodigoMovimiento = 1", conn, adOpenDynamic, adLockOptimistic
    rs_cuentacliente.AddNew
    
    'Comprobante supervisor - x loguin
    If comp_supervisor = "Si" Then
        rs_cuentacliente.Fields!comp_supervisor = "Si"
    End If
    
    Fecha = Principal.Fecha
    rs_cuentacliente.Fields!Fecha = Format(Fecha, "short date")
    
    rs_cuentacliente.Fields!TipoComprobante = TipoFactura
    
    ' Factura por sistema ****************************************************
    
    rs_cuentacliente.Fields!NroComprobante = Nro
    rs_cuentacliente.Fields!NroCompBusq = NroBusq
    NroComp = Nro
    
    ' Valida si seleccion PV
    If Principal.selec_pv = "Si" Then
        If pv_electronico = "Si" Then
            rs_cuentacliente.Fields!id_pv = id_pv_electronico
        Else
            rs_cuentacliente.Fields!id_pv = punto_venta.BoundText
        End If
    Else
        rs_cuentacliente.Fields!id_pv = Principal.id_punto_venta
    End If
            
    If Detalle <> "" Then
        rs_cuentacliente.Fields!Detalle = Detalle.Text
    End If
    
'    ' Consulta para obtener saldo actual
'    With rs_saldo_cliente
'        .ActiveConnection = conn
'        .CursorType = adOpenDynamic
'        .Source = "select cliente.codigo,cliente.saldo, cliente.id_cobrador from cliente where codigo = " & CDbl(Codigo_Cliente)
'        .Open
'    End With
    
    rs_saldo_cliente.Open "SELECT cliente.codigo,cliente.saldo, cliente.id_cobrador FROM cliente WHERE codigo = " & CDbl(Codigo_Cliente), conn, adOpenDynamic, adLockReadOnly
        
    ' Si el cliente es CF guardo el saldo que tiene CF por defecto 0
    If Codigo_Cliente = 1 Then
        If rs_saldo_cliente.RecordCount > 0 Then
            rs_cuentacliente.Fields!Saldo = rs_saldo_cliente.Fields!Saldo
        Else
            rs_cuentacliente.Fields!Saldo = 0
        End If
    End If

    ' Si el cliente no es CF y vendio en cuenta corriente actualizo saldo
    If Codigo_Cliente <> 1 And Total_CtaCte <> 0 Then

        rs_cuentacliente.Fields!Saldo = CDbl(Format(CDbl(Total_CtaCte) + CDbl(rs_saldo_cliente.Fields!Saldo), "##,###.00"))

        ' Guardo el saldo en la tabla cliente
        rs_cliente.Open "SELECT cliente.codigo,cliente.saldo, cliente.id_cobrador FROM cliente where codigo = " & CDbl(Codigo_Cliente), conn, adOpenDynamic, adLockOptimistic
        rs_cliente.Fields!Saldo = rs_cuentacliente.Fields!Saldo
        'Cobrador
        id_cobrador = rs_cliente.Fields!id_cobrador
        rs_cliente.Update
        rs_cliente.Close
    
    ' Dejo el saldo igual
    Else
    
        rs_cuentacliente.Fields!Saldo = rs_saldo_cliente.Fields!Saldo
        'Cobrador
        id_cobrador = rs_saldo_cliente.Fields!id_cobrador
        
    End If
                                                                                                                        
    rs_cuentacliente.Fields!ReciboMov = 0
    rs_cuentacliente.Fields!ImporteVenta = CDbl(Format(Label_Total, "##,###.00"))
    rs_cuentacliente.Fields!ImporteVentaL = Principal.ESCRITO(CDbl(Format(Label_Total, "##,###.00")))
       
    rs_cond_venta.Open "SELECT * FROM cond_venta WHERE Codigo = " & Cond_Venta_Cliente_ID, conn, adOpenDynamic, adLockOptimistic
    
    rs_cuentacliente.Fields!ImporteCobro = Null
    
    ' Neto / IVA Interes
    iva_interes = 0
    neto_interes = 0
    valor_alicuota = Principal.Alicuota_IVA1 / 100 + 1
    neto_interes = CDbl(interes_tarjeta_total) / valor_alicuota
    iva_interes = interes_tarjeta_total - neto_interes
    
    rs_cuentacliente.Fields!Iva1 = CDbl(Format(CDbl(Iva1.Caption) + CDbl(iva_interes), "##,###.00"))
    rs_cuentacliente.Fields!Iva2 = CDbl(Format(Iva2.Caption, "##,###.00"))
    rs_cuentacliente.Fields!Alicuota1 = CDbl(Format(Alic1, "##,###.00"))
    rs_cuentacliente.Fields!alicuota2 = CDbl(Format(Alic2, "##,###.00"))
       
    If Exento.Caption = 0 Then
        rs_cuentacliente.Fields!Exento = 0
    Else
        rs_cuentacliente.Fields!Exento = CDbl(Format(Exento, "##,###.00"))
    End If
       
    rs_cuentacliente.Fields!anulado = "No"
    rs_cuentacliente.Fields!Subtotal1 = CDbl(Format(CDbl(Subtotal1.Caption), "##,###.00"))  ' + neto_interes
    rs_cuentacliente.Fields!Subtotal2 = CDbl(Format(Subtotal2.Caption, "##,###.00"))
    rs_cuentacliente.Fields!SubtotalGral = CDbl(Format(CDbl(SubtotalGral.Caption), "##,###.00")) ' + neto_interes
    rs_cuentacliente.Fields!PorDesc1 = CDbl(PorDesc1)
    rs_cuentacliente.Fields!ImpDesc1 = CDbl(Format(ImpDesc1.Caption, "##,###.00"))
    rs_cuentacliente.Fields!ImpDesc2 = CDbl(Format(ImpDesc2.Caption, "##,###.00"))
    rs_cuentacliente.Fields!SubTotalDesc1 = CDbl(Format(CDbl(SubTotalDesc1.Caption) + neto_interes, "##,###.00"))
    rs_cuentacliente.Fields!SubTotalDesc2 = CDbl(Format(SubTotalDesc2.Caption, "##,###.00"))
    rs_cuentacliente.Fields!SubtotalDesc = CDbl(Format(CDbl(SubtotalDesc.Caption) + neto_interes, "##,###.00"))
    rs_cuentacliente.Fields!idUsuario = Principal.idUsuario
    ' Seleccion de sucursal de punto de venta
    rs_cuentacliente.Fields!codSucursal = id_sucursal
     
    ' Si es factura por sistema o Controlador fiscal ********************
        
    rs_cuentacliente.Fields!TipoFactura = "Sistema"
    
    If Codigo_Cliente = 1 Then
        rs_cuentacliente.Fields!Codigo = 1
        Codigo_Cliente = 1
    Else
        rs_cuentacliente.Fields!Codigo = Codigo_Cliente
        Codigo_Cliente = Codigo_Cliente
    End If

    rs_cuentacliente.Fields!CodigoMovimiento = contador
     
    ' Guardo la CV
    
    ' Si es solo contado
    If Total_Efectivo <> 0 And Total_Cheque = 0 And Total_Tarjeta = 0 And Total_CtaCte = 0 Then
        rs_cuentacliente.Fields!CondVenta = "Contado"
        Condicion_Venta = "Contado"
        rs_cuentacliente.Fields!id_condventa = 1
        id_condventa = 1
    End If
    
    ' Si es solo Cheque
    If Total_Efectivo = 0 And Total_Cheque <> 0 And Total_Tarjeta = 0 And Total_CtaCte = 0 Then
        rs_cuentacliente.Fields!CondVenta = "Cheque"
        Condicion_Venta = "Cheque / Transf."
        rs_cuentacliente.Fields!id_condventa = 3
        id_condventa = 3
    End If
    
    ' Si es solo Tarjeta
    If Total_Efectivo = 0 And Total_Cheque = 0 And Total_Tarjeta <> 0 And Total_CtaCte = 0 Then
        rs_cuentacliente.Fields!CondVenta = "Tarjeta"
        Condicion_Venta = "Tarjeta"
        rs_cuentacliente.Fields!id_condventa = 2
        id_condventa = 2
    End If
    
    ' Si es solo Cta Cte
    If Total_Efectivo = 0 And Total_Cheque = 0 And Total_Tarjeta = 0 And Total_CtaCte <> 0 Then
        rs_cuentacliente.Fields!CondVenta = CV.Text
        Condicion_Venta = CV.Text
        rs_cuentacliente.Fields!id_condventa = CV.BoundText
        id_condventa = CV.BoundText
    End If

    ' Si es Multiple
    If Total_Efectivo <> 0 Then
        var_multiple = var_multiple + 1
    End If
    
    If Total_Cheque <> 0 Then
        var_multiple = var_multiple + 1
    End If
    
    If Total_Tarjeta <> 0 Then
        var_multiple = var_multiple + 1
    End If
    
    If Total_CtaCte <> 0 Then
        var_multiple = var_multiple + 1
    End If
    
    If var_multiple >= 2 Then
        rs_cuentacliente.Fields!CondVenta = "Multiple"
        Condicion_Venta = "Multiple"
        rs_cuentacliente.Fields!id_condventa = 12
        id_condventa = 12
    End If
    
    ' Guardo lo importes de los medios de cobro
    If Total_Efectivo <> 0 Then
        rs_cuentacliente.Fields!tpv_importe_efectivo = CDbl(Format(Total_Efectivo, "##,###.00"))
        rs_cuentacliente.Fields!tpv_cambio_efectivo = CDbl(Format(cambio_efectivo, "##,###.00"))
        rs_cuentacliente.Fields!tpv_pago_efectivo = CDbl(Format(importe_cobrado_efectivo, "##,###.00"))
    
        'Bandera Dolar
        '23/05/2018
        rs_cuentacliente.Fields!CotiDolar = CDbl(Format(ValorPesos, "##,###.00"))
        rs_cuentacliente.Fields!TotalEfectivoD = CDbl(Format(TotalEfectivoD, "##,###.00"))
    End If
    
    If Total_Cheque <> 0 Then
        rs_cuentacliente.Fields!tpv_importe_cheque = CDbl(Format(Total_Cheque, "##,###.00"))
    End If
     
    If Total_Tarjeta <> 0 Then
        rs_cuentacliente.Fields!tpv_importe_tarjeta = CDbl(Format(Total_Tarjeta, "##,###.00"))
        rs_cuentacliente.Fields!interes = CDbl(Format(interes_tarjeta_total, "##,###.00"))
    End If
    
    If Total_CtaCte <> 0 Then
        rs_cuentacliente.Fields!tpv_importe_ctacte = CDbl(Format(Total_CtaCte, "##,###.00"))
    End If
    
    ' Guardo los datos del cliente ocasional
    If datos_ocasional.Visible = True Then
        rs_cuentacliente.Fields!tpv_nombre_ocasional = datos_ocasional
        rs_cuentacliente.Fields!tpv_domicilio_ocasional = Domicilio
        rs_cuentacliente.Fields!tpv_nro_identif_ocasional = CUIT
        rs_cuentacliente.Fields!tpv_cel_wp_ocasional = tpv_cel_wp_ocasional
        rs_cuentacliente.Fields!tpv_mail_ocasional = tpv_mail_ocasional
        rs_cuentacliente.Fields!tpv_doc_cliente_ocasional = tipo_doc_cliente_ocasional
    End If
    
    ''''''
    'Caja'
    ''''''
    
    ' Pago en efectivo *******************************
    If Total_Efectivo <> 0 Then
                                                                                                                                                                     
        ' Actualizo caja
        Mon = "Pesos" ' Los comprobantes son siempre generados en moneda local, pudiendo convertir a moneda extranjera segun la cotizacion
        
        'Consulto el saldo de la caja, segun tipo de caja y Usuario
        rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja = " & Principal.id_caja & " AND moneda = '" & Mon & "'", conn, adOpenDynamic, adLockOptimistic
        
        If rs_saldo_caja.RecordCount > 0 Then
                
            If txtRedondeo <> "" And txtRedondeo > 0 Then
                'A favor
                If cmbTipoR.ListIndex = 1 Then
                    rs_saldo_caja.Fields!Saldo = CDbl(Format(rs_saldo_caja.Fields!Saldo + (Total_Efectivo - CDec(txtRedondeo)), "##,###.00"))
                Else
                    rs_saldo_caja.Fields!Saldo = CDbl(Format(rs_saldo_caja.Fields!Saldo + (Total_Efectivo + CDec(txtRedondeo)), "##,###.00"))
                End If
            Else
                
                ' Si a ingresado un valor en dolares
                If TotalEfectivoD <> "0" Then
                    rs_saldo_caja.Fields!Saldo = CDbl(Format(rs_saldo_caja.Fields!Saldo + txtPesos, "##,###.00"))
                Else
                    rs_saldo_caja.Fields!Saldo = CDbl(Format(rs_saldo_caja.Fields!Saldo + Total_Efectivo, "##,###.00"))
                End If
                
            End If

            rs_saldo_caja.Fields!id_usuario = Principal.idUsuario
            rs_saldo_caja.Update
            
        End If
                                                                                
        ' Actualizo la tabla caja
        rs_caja.Open "SELECT * from caja where codigo_movimiento = 1", conn, adOpenDynamic, adLockOptimistic
        rs_caja.AddNew

        rs_caja.Fields!Fecha = Format(Fecha, "short date")
        rs_caja.Fields!tipo_comprobante = TipoFactura
        rs_caja.Fields!Tipo = "Factura Contado TPV"
        rs_caja.Fields!nro_comprobante = Nro
        rs_caja.Fields!nro_comp_busq = NroBusq
        rs_caja.Fields!egreso = 0
        rs_caja.Fields!id_usuario = Principal.idUsuario
        rs_caja.Fields!cod_vendedor = Principal.id_vendedor_usr

        ' Seleccion de sucursal de punto de venta
        rs_caja.Fields!cod_sucursal = id_sucursal
        
        rs_caja.Fields!Moneda = "Pesos"
        
        'REDONDEO
        If txtRedondeo.Text > 0 Then
        
            Dim rs_pv_redondeo As New ADODB.Recordset
            
            rs_pv_redondeo.Open "SELECT punto_venta.id_punto_venta,punto_venta.nro_punto_venta,punto_venta.id_sucursal as id_sucursal_pv,sucursales.id_sucursal,sucursales.nombre_sucursal as nomb_suc, sucursales.lim_redondeo_tpv FROM punto_venta,sucursales WHERE " & _
            "punto_venta.id_sucursal = sucursales.id_sucursal AND punto_venta.id_punto_venta = " & punto_venta.BoundText & " ORDER BY punto_venta.nro_punto_venta", conn, adOpenDynamic, adLockOptimistic
            
            If Not IsNull(rs_pv_redondeo.Fields!lim_redondeo_tpv) Then

                If CDbl(txtRedondeo.Text) > rs_pv_redondeo.Fields!lim_redondeo_tpv Then

                    If conn.State = 1 Then
                        conn.RollbackTrans
                        conn.Close
                    End If
                    MsgBox "El importe por redondeo supera el limite permitido de $" & rs_pv_redondeo.Fields!lim_redondeo_tpv & "  ", vbInformation, "ATENCION"
                    txtRedondeo.SetFocus
                    Exit Sub

                End If

                If CDbl(txtRedondeo.Text) >= ImporteTotal Then
                    If conn.State = 1 Then
                        conn.RollbackTrans
                        conn.Close
                    End If
                    MsgBox "El importe por redondeo no puede superar o igualar el total de la factura  " & rs_pv_redondeo.Fields!lim_redondeo_tpv & "  ", vbInformation, "ATENCION"
                    txtRedondeo.SetFocus
                    Exit Sub
                End If

            End If
        
            'A favor
            If cmbTipoR.ListIndex = 0 Then
            
                rs_caja.Fields!ingreso = Format(Total_Efectivo, "##,###.00") + CDbl(txtRedondeo.Text)
                rs_caja.Fields!Detalle = Detalle & "Imp. Fact. " & Label_Total & " - Redon. " & cmbTipoR.Text & " $ " & txtRedondeo.Text & " "
                'Debug.Print rs_caja.Fields!Detalle
            Else
        
                rs_caja.Fields!ingreso = Format(Total_Efectivo, "##,###.00") - CDbl(txtRedondeo.Text)
                rs_caja.Fields!Detalle = Detalle & "Imp. Fact. " & Label_Total & " - Redon. " & cmbTipoR.Text & " $ " & txtRedondeo.Text & " "
              
            End If
            
            rs_cuentacliente.Fields!redondeo = CDbl(txtRedondeo.Text)
            rs_cuentacliente.Fields!tipo_redondeo = cmbTipoR.Text
            
        Else
        
            ' Si a ingresado un valor en dolares
            If TotalEfectivoD <> "0" Then
                rs_caja.Fields!ingreso = CDbl(Format(txtPesos, "##,###.00"))
            Else
                rs_caja.Fields!ingreso = CDbl(Format(Total_Efectivo, "##,###.00"))
            End If
            
            rs_caja.Fields!Detalle = Detalle

            rs_cuentacliente.Fields!redondeo = CDbl(txtRedondeo.Text)
            rs_cuentacliente.Fields!tipo_redondeo = "No"
            
        End If
                                   
        rs_caja.Fields!codigo_movimiento = contador
        rs_caja.Fields!Codigo_Cliente = Codigo_Cliente
        rs_caja.Fields!codigo_prov = 1
        rs_caja.Fields!tipo_cp = "Cliente"
        rs_caja.Fields!anulado = "No"
        rs_caja.Fields!Saldo = rs_saldo_caja.Fields!Saldo

        rs_caja.Fields!id_caja_abm_origen = Principal.id_caja
        
        rs_caja.Update
        
        rs_caja.Close
        
        rs_saldo_caja.Close
        
        ' Guardo el efectivo en el campo correspondiente de la base cuentacliente
        ' Si a ingresado un valor en dolares
        If TotalEfectivoD <> "0" Then
            rs_cuentacliente.Fields!tpv_importe_efectivo = CDec(txtPesos)
        Else
            rs_cuentacliente.Fields!tpv_importe_efectivo = CDec(Total_Efectivo)
        End If
        
        rs_cuentacliente.Fields!tpv_cambio_efectivo = CDec(cambio_efectivo)
        rs_cuentacliente.Fields!tpv_pago_efectivo = CDec(importe_cobrado_efectivo)
        
    End If
    
    '23/05/2018
    If TotalEfectivoD.Text > 0 Then
        guardar_caja_dolar
    End If
        
    ' Valido si la factura queda cancelada o no, si hay monto en cuenta corriente la factura queda N/Canc
    If (Total_Efectivo <> 0 Or Total_Tarjeta <> 0 Or Total_Cheque <> 0) And Total_CtaCte = 0 Then
        rs_cuentacliente.Fields!Estado = "Canc"
        rs_cuentacliente.Fields!Vencimiento = Format(Fecha.Text, "short Date")
    Else
        rs_cuentacliente.Fields!Estado = "N/Canc"
        ' La combo de cuenta corriente
        
        ' Consulto los Dias de la Condicion de Venta para utilizarla en la fecha de Vencimiento
        rs_cv.Open "SELECT * FROM cond_venta WHERE Codigo = " & CV.BoundText, conn, adOpenDynamic, adLockOptimistic
        rs_cuentacliente.Fields!Vencimiento = DateAdd("d", rs_cv.Fields!Dias, Fecha)
        rs_cv.Close

    End If
        
    If CDate(rs_cuentacliente.Fields!Vencimiento) <= Principal.Fecha Then
        rs_cuentacliente.Fields!Vencido = "Si"
    Else
        rs_cuentacliente.Fields!Vencido = "No"
    End If

    rs_cuentacliente.Fields!CodViajante = CodViajante
    
    If CodViajante_Asistente <> 0 Then
        rs_cuentacliente.Fields!id_vendedor_asistente = CodViajante_Asistente
    Else
        ' Si es 0 no fue atendido por asistente
        rs_cuentacliente.Fields!id_vendedor_asistente = 0
    End If
    
    rs_cuentacliente.Fields!tpv_comp = "Si"
    
    ' Cambio codigo Impresora fiscal con seleccion de PV
    If tipo_impresora = "Fiscal" Then  ' And mod_pv = "No"
        rs_cuentacliente.Fields!comprobante_fiscal = "Si"
    End If
    
    ' Impuesto interno
    rs_cuentacliente.Fields!impuesto_interno_total = CDbl(Format(ImpInt.Caption, "##,###.00"))

    ' Guardo el monto de las percepcion en la tabla cuentacliente y en la tabla percep_cli
    If Principal.agente_percep = "Si" Then
        If total_percep <> 0 Then
            rs_cuentacliente.Fields!total_percep = CDbl(Format(total_percep, "##,###.00"))
            
            rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE id_usuario = " & Principal.idUsuario, conn, adOpenDynamic, adLockOptimistic
            If rs_percep_cli_temp.RecordCount > 0 Then
                rs_percep_cli.Open "SELECT * FROM percep_cli WHERE id_percep_cli = 0", conn, adOpenDynamic, adLockOptimistic
                Do While Not rs_percep_cli_temp.EOF
                    rs_percep_cli.AddNew
                    rs_percep_cli.Fields!id_percep_cli_tipo = rs_percep_cli_temp.Fields!id_percep_cli_tipo
                    rs_percep_cli.Fields!alicuota_percep_cli = rs_percep_cli_temp.Fields!alicuota_percep_cli_temp
                    rs_percep_cli.Fields!importe_percep_cli = rs_percep_cli_temp.Fields!importe_percep_cli_temp
                    rs_percep_cli.Fields!codigo_movimiento = contador
                    rs_percep_cli.Fields!id_cliente = Codigo_Cliente
                    rs_percep_cli.Fields!tipo_comp = TipoFactura
                    rs_percep_cli.Update
                rs_percep_cli_temp.MoveNext
                Loop
                
            End If
        
        rs_percep_cli_temp.Close
        rs_percep_cli.Close
        
        End If
                
    End If

    '''''''''''''''''''
    'Datos Adicionales'
    '''''''''''''''''''
    rs_cuentacliente.Fields!id_deposito_despacho = id_deposito_despacho

    rs_cuentacliente.Fields!CotiDolar = CDbl(Format(Principal.cotizacion, "##,###.00"))

    ' Guardo Costo de venta total del comprobante
    rs_cuentacliente.Fields!total_costo = Obtener_Total_Costo_Comprobante_Temporal(Principal.idUsuario)

    rs_cuentacliente.Update
                    
    id_cuentacliente_fe = rs_cuentacliente.Fields!id_cuentacliente
                    
' Para hacer saltar error
'    rs_cuentacliente.Close
                                                                                                                   
    form_espera.ProgressBar.Value = 50
                                                                                                                   
    ' Actualizo el Stock
    rs_stock.Open "SELECT * FROM stock where CodigoMovimiento = 1", conn, adOpenDynamic, adLockOptimistic
        
    ' Hago el Calculo del Campo Saldo de Stock
    data_renglon_tpv.Recordset.MoveFirst
    
'     ' Procedimiento Sentencia_Insert_SQL_Bloque_Directo
'    datos_campo_SQL_UPDATE = ""
'    datos_valor_SQL_INSERT = ""
'    datos_campo_SQL_INSERT = ""
'    genero_campos_SQL_INSERT = "No"
    
    Do While Not data_renglon_tpv.Recordset.EOF
        
        ''''''''''''''
        'Ensamble Vta'
        ''''''''''''''
        'Modulo de ensamblaje activo
        If Principal.activ_ensamblaje_venta = "Si" Then
                       
            'Dentro del procedimiento consulto si el articulo es ensamblado.
            'Si ensambla en la venta
            Ensamblaje
    
            'Por error en ensamblaje se cerro la transanccion y conexion
            'Escapo del procedimiento para no generar un error de nuevo
            If conn.State = 0 Then
                Exit Sub
            End If
         
        End If
        
        'Si hace control stock, stock art sin lotes, con lote
        rs_stock.AddNew

        ' Guardo el saldo en la tabla stock_deposito
        rs_saldo_stock.Open "SELECT * FROM stock_deposito WHERE id_articulo = " & data_renglon_tpv.Recordset.Fields!IDArt & " And id_deposito = " & data_renglon_tpv.Recordset.Fields!CodDeposito & "", conn, adOpenDynamic, adLockOptimistic

        ' Si hay stock ya ingresado en la tabla stock_deposito
        If rs_saldo_stock.RecordCount > 0 Then

            '***FREE*** / Validacion
            ' Valido si la factura fue a traves de un pedido descuento el campo saldo_pedido_cliente, es un dato estadistico
            If Comprobante_Pedido = "Si" Or Comprobante_Pedido = "Si PED Avanzado" Then

                ' Busco la cantidad pedida por el pedido y descuento saldo_pedido_cliente
                If Not IsNull(data_renglon_tpv.Recordset.Fields!codmov_pedido) Then

                    rs_consulta_pedido_cliente.Open "SELECT stockp.CodigoMovimiento,stockp.cantidad,stockp.IDArt FROM stockp WHERE " & _
                    "stockp.id_stock = " & data_renglon_tpv.Recordset.Fields!id_stock & "", conn, adOpenDynamic, adLockOptimistic

                    If rs_consulta_pedido_cliente.RecordCount > 0 Then
                        rs_saldo_stock.Fields!saldo_pedido_cliente = rs_saldo_stock.Fields!saldo_pedido_cliente - rs_consulta_pedido_cliente.Fields!Cantidad
                    End If

                    rs_consulta_pedido_cliente.Close

                End If

            End If

            ' Validacion de stock en articulos sin lote
            ' Valido si la sucursal valida stock o no
            ' Permite salidas sin stock

            '  Funcionalidad Bulto Cerrado / Display
            cantidad_multiplicar = 1
            If (Principal.utiliza_bulto_cerrado = "Si" Or Principal.utiliza_display = "Si") Then

                cantidad_unidad_display = Obtener_Datos_Articulo_Mayorista(data_renglon_tpv.Recordset.Fields!IDArt, "cantidad_unidad_display")
                cantidad_por_bulto = Obtener_Datos_Articulo_Mayorista(data_renglon_tpv.Recordset.Fields!IDArt, "multiplicador_comp")

                If data_renglon_tpv.Recordset.Fields!tipo_unidad = "Display" Then
                    ' Si la cantidad de unidad por display es 1 significa que la unidad y el display es lo mismo: Ej: Un alfajor dentor de una caja
                    If cantidad_unidad_display = 1 Then
                    ' Busco la cantidad de unidad por bulto
                        cantidad_multiplicar = cantidad_por_bulto
                    Else
                        cantidad_multiplicar = 1
                    End If

                    If CDbl(cantidad_unidad_display) > 1 Then
                        cantidad_multiplicar = cantidad_unidad_display
                    End If

                    If cantidad_unidad_display = 0 Then
                        cantidad_multiplicar = 1
                    End If

                    rs_stock.Fields!tipo_unidad = "Display"

                    ' Validacion si el precio del producto esta por unidad pero selecciono display
                    If Obtener_Datos_Articulo_Mayorista(data_renglon_tpv.Recordset.Fields!IDArt, "precio_unidad") = "Unidad" Then
                        cantidad_multiplicar = 1
                    End If

                End If

                If data_renglon_tpv.Recordset.Fields!tipo_unidad = "Bulto" Then
                    cantidad_multiplicar = cantidad_unidad_display * cantidad_por_bulto
                    rs_stock.Fields!tipo_unidad = "Bulto"
                End If

                rs_stock.Fields!cantidad_unidad_display = cantidad_unidad_display
                rs_stock.Fields!cantidad_dividir = cantidad_multiplicar

            End If

            '  Funcionalidad Bulto Cerrado / Display
            cantidad_ingresada = data_renglon_tpv.Recordset.Fields!Cantidad * cantidad_multiplicar

            If IsNull(data_renglon_tpv.Recordset.Fields!Lote) Then ' Articulo sin lote

                If Principal.salida_sin_stock = "Si" Then ' Permite salidas sin stock, stock en negativo

                    '  Funcionalidad Bulto Cerrado / Display
                    rs_saldo_stock.Fields!Saldo = rs_saldo_stock.Fields!Saldo - (data_renglon_tpv.Recordset.Fields!Cantidad * cantidad_multiplicar)

                    rs_saldo_stock.Update

                ' No permite salidas sin stock
                Else

                    ' Valido si es un servicio para que no entre en la validacion de stock
                    rs_consulta_articulo.Open "SELECT articulo.IDArt,articulo.tipo_art FROM articulo WHERE IDArt = " & data_renglon_tpv.Recordset.Fields!IDArt & "", conn, adOpenDynamic, adLockOptimistic

                    If (CDec(rs_saldo_stock.Fields!Saldo) >= CDec(cantidad_ingresada)) Or rs_consulta_articulo.Fields!tipo_art = "Servicio" Then

'                        rs_saldo_stock.Fields!Saldo = rs_saldo_stock.Fields!Saldo - data_renglon_tpv.Recordset.Fields!Cantidad

                        '  Funcionalidad Bulto Cerrado / Display
                        rs_saldo_stock.Fields!Saldo = rs_saldo_stock.Fields!Saldo - (data_renglon_tpv.Recordset.Fields!Cantidad * cantidad_multiplicar)

                        rs_saldo_stock.Update

                    Else

                        If conn.State = 1 Then
                            conn.RollbackTrans
                            conn.Close
                        End If

                        MsgBox "No hay stock suficiente del artculo: " & data_renglon_tpv.Recordset.Fields!Descripcion & " su saldo es: " & rs_saldo_stock.Fields!Saldo & "", vbInformation, "ATENCION"

                        ' Primera posicion de cuerpostock
                        data_renglon_tpv.Recordset.MoveFirst
                        ' Descargo formulario de espera
                        Unload form_espera
                        Nro.Caption = ""
                        Exit Sub

                    End If

                    rs_consulta_articulo.Close

                End If

            ' Si es articulo con lote resta directamente en la tabla stock_deposito
            Else

'                rs_saldo_stock.Fields!Saldo = rs_saldo_stock.Fields!Saldo - data_renglon_tpv.Recordset.Fields!Cantidad

                '  Funcionalidad Bulto Cerrado / Display
                rs_saldo_stock.Fields!Saldo = rs_saldo_stock.Fields!Saldo - (data_renglon_tpv.Recordset.Fields!Cantidad * cantidad_multiplicar)

                rs_saldo_stock.Update

            End If

        End If

        rs_stock.Fields!Fecha = Format(Fecha, "short date")
        rs_stock.Fields!CodigoArticulo = data_renglon_tpv.Recordset.Fields!CodigoArticulo
        rs_stock.Fields!Descripcion = data_renglon_tpv.Recordset.Fields!Descripcion
        rs_stock.Fields!PrecioVentaxU = data_renglon_tpv.Recordset.Fields!PrecioVentaxU
        rs_stock.Fields!PrecioCostoxU = data_renglon_tpv.Recordset.Fields!PrecioCostoxU
        rs_stock.Fields!PrecioIVAxU = data_renglon_tpv.Recordset.Fields!PrecioIVAxU
        rs_stock.Fields!PrecioBrutoxU = data_renglon_tpv.Recordset.Fields!PrecioBrutoxU
        rs_stock.Fields!PrecioNetoxU = data_renglon_tpv.Recordset.Fields!PrecioNetoxU
        rs_stock.Fields!Impdesc = data_renglon_tpv.Recordset.Fields!Impdesc
        rs_stock.Fields!Pordesc = data_renglon_tpv.Recordset.Fields!Pordesc
        rs_stock.Fields!PrecioVentaxR = data_renglon_tpv.Recordset.Fields!PrecioVentaxR
        rs_stock.Fields!PrecioCostoxR = data_renglon_tpv.Recordset.Fields!PrecioCostoxR
        rs_stock.Fields!PrecioIVAxR = data_renglon_tpv.Recordset.Fields!PrecioIVAxR
        rs_stock.Fields!PrecioBrutoxR = data_renglon_tpv.Recordset.Fields!PrecioBrutoxR
        rs_stock.Fields!PrecioNetoxR = data_renglon_tpv.Recordset.Fields!PrecioNetoxR
        rs_stock.Fields!Alicuota = data_renglon_tpv.Recordset.Fields!Alicuota
        rs_stock.Fields!AlicuotaIB = data_renglon_tpv.Recordset.Fields!AlicuotaIB
        rs_stock.Fields!imp_alicuota_iva = data_renglon_tpv.Recordset.Fields!imp_alicuota_iva
        rs_stock.Fields!imp_alicuota_iibb = data_renglon_tpv.Recordset.Fields!imp_alicuota_iibb

        '  Funcionalidad Bulto Cerrado / Display
        rs_stock.Fields!Cantidad = data_renglon_tpv.Recordset.Fields!Cantidad * cantidad_multiplicar
        rs_stock.Fields!Salida = data_renglon_tpv.Recordset.Fields!Cantidad * cantidad_multiplicar

'        rs_stock.Fields!Cantidad = data_renglon_tpv.Recordset.Fields!Cantidad
        rs_stock.Fields!Saldo = rs_saldo_stock.Fields!Saldo
        rs_stock.Fields!orden = data_renglon_tpv.Recordset.Fields!orden
        rs_stock.Fields!CodViajante = CodViajante
        rs_stock.Fields!CodLaboratorio = data_renglon_tpv.Recordset.Fields!CodLaboratorio
        rs_stock.Fields!Detalle = data_renglon_tpv.Recordset.Fields!Detalle

        rs_stock.Fields!CodigoMovimiento = contador

        ' Aca Validar si el Art es Servicio o Mercaderia para asignar deposito
        rs_stock.Fields!CodDeposito = data_renglon_tpv.Recordset.Fields!CodDeposito

        rs_stock.Fields!IDArt = data_renglon_tpv.Recordset.Fields!IDArt

        '''''''''''''''
        'Multiplicador'
        '''''''''''''''
        If Principal.utiliza_embalaje = "Si" Then
            rs_stock.Fields!multiplicador_vta = data_renglon_tpv.Recordset.Fields!multiplicador_vta
            rs_stock.Fields!multiplicador_comp = data_renglon_tpv.Recordset.Fields!multiplicador_comp
            'Presentacion vta
            rs_stock.Fields!id_unimed_vta = data_renglon_tpv.Recordset.Fields!id_unimed_vta
            rs_stock.Fields!id_presentacion_vta = data_renglon_tpv.Recordset.Fields!id_presentacion_vta
            rs_stock.Fields!nombre_unimed_vta = data_renglon_tpv.Recordset.Fields!nombre_unimed_vta
            rs_stock.Fields!nombre_presentacion_vta = data_renglon_tpv.Recordset.Fields!nombre_presentacion_vta
            'Presentacion comp
            rs_stock.Fields!id_unimed_comp = data_renglon_tpv.Recordset.Fields!id_unimed_comp
            rs_stock.Fields!id_presentacion_comp = data_renglon_tpv.Recordset.Fields!id_presentacion_comp
            rs_stock.Fields!nombre_unimed_comp = data_renglon_tpv.Recordset.Fields!nombre_unimed_comp
            rs_stock.Fields!nombre_presentacion_comp = data_renglon_tpv.Recordset.Fields!nombre_presentacion_comp
            'Cantidad_uni
            rs_stock.Fields!cantidad_uni = data_renglon_tpv.Recordset.Fields!cantidad_uni

        End If

        If Not IsNull(data_renglon_tpv.Recordset.Fields!id_manual) Then
            rs_stock.Fields!id_manual = data_renglon_tpv.Recordset.Fields!id_manual
        End If

        ''''''''''''''''''
        '      Lote      '
        ''''''''''''''''''

           '# por cada stock que tenga lote, grabo el id de lote y disminuyo el lote..y anularla si encima quedo en cero...
           If data_renglon_tpv.Recordset.Fields!Lote = "Si" Then

               rs_lote.Open "SELECT * From Lote " & _
               "INNER JOIN lote_stock ON (lote.id_lote = lote_stock.id_lote) " & _
               "Where lote.id_lote = " & data_renglon_tpv.Recordset.Fields!id_lote & " AND " & _
               "lote_stock.id_deposito = " & data_renglon_tpv.Recordset.Fields!CodDeposito & " AND " & _
               "lote.anulado = 'No'", conn, adOpenDynamic, adLockOptimistic

               If rs_lote.Fields!stock_lote >= cantidad_ingresada Then

                    '  Funcionalidad Bulto Cerrado / Display
                    If (Principal.utiliza_bulto_cerrado = "No" Or Principal.utiliza_display = "No") Then
                        'Actuliza stock por deposito
                        rs_lote.Fields!stock_lote = rs_lote.Fields!stock_lote - data_renglon_tpv.Recordset.Fields!Cantidad
                        'Actualiza stock total
                        rs_lote.Fields!stock_total_lote = rs_lote.Fields!stock_total_lote - data_renglon_tpv.Recordset.Fields!Cantidad
                    End If

                    If (Principal.utiliza_bulto_cerrado = "Si" Or Principal.utiliza_display = "Si") Then
                        'Actuliza stock por deposito
                        rs_lote.Fields!stock_lote = rs_lote.Fields!stock_lote - (data_renglon_tpv.Recordset.Fields!Cantidad * cantidad_multiplicar)
                        'Actualiza stock total
                        rs_lote.Fields!stock_total_lote = rs_lote.Fields!stock_total_lote - (data_renglon_tpv.Recordset.Fields!Cantidad * cantidad_multiplicar)
                    End If

                   ' Actualizo campo lote e id en tabla stock
                   rs_stock.Fields!stock_lote_deposito = rs_lote.Fields!stock_total_lote
                   rs_stock.Fields!id_lote = data_renglon_tpv.Recordset.Fields!id_lote

                   rs_lote.Update

                   rs_lote.Close

               Else

'                    sepaso = data_renglon_tpv.Recordset.Fields!Cantidad - rs_lote.Fields!stock_lote

                    '  Funcionalidad Bulto Cerrado / Display
                    If (Principal.utiliza_bulto_cerrado = "No" Or Principal.utiliza_display = "No") Then
                        sepaso = data_renglon_tpv.Recordset.Fields!Cantidad - rs_lote.Fields!stock_lote
                    End If

                    '  Funcionalidad Bulto Cerrado / Display
                    If (Principal.utiliza_bulto_cerrado = "Si" Or Principal.utiliza_display = "Si") Then
                        sepaso = (data_renglon_tpv.Recordset.Fields!Cantidad * cantidad_multiplicar) - rs_lote.Fields!stock_lote
                    End If

                    'La cantidad solicitada del articulo xxx se sobrepasa en xxx unidades respercto al stock del deposito"

                    If conn.State = 1 Then
                       conn.RollbackTrans
                       conn.Close
                    End If

                    MsgBox "La cantidad solicitada del articulo: " & Chr(34) & " " & data_renglon_tpv.Recordset.Fields!Descripcion & " " & Chr(34) & " del lote: " & data_renglon_tpv.Recordset.Fields!cod_lote & "  se sobrepasa en " & sepaso & " unidad/es respecto al stock del deposito ", vbInformation, "ATENCION"

                    ' Descargo formulario de espera
                    Unload form_espera

                    Nro.Caption = ""

                    Exit Sub

               End If

           End If

           rs_saldo_stock.Close

        ' Fin Lote '''''''''''''''''''''''''''''''''''

        ' Seleccion de sucursal de punto de venta
        rs_stock.Fields!codSucursal = id_sucursal
        rs_stock.Fields!idUsuario = Principal.idUsuario
        rs_stock.Fields!TipoIVA = data_renglon_tpv.Recordset.Fields!TipoIVA

        If Codigo_Cliente = 1 Then
            rs_stock.Fields!CodigoCP = 1
        Else
            rs_stock.Fields!CodigoCP = Codigo_Cliente
        End If

        rs_stock.Fields!Tipo = "Cliente"
        rs_stock.Fields!TipoComp = "Venta TPV"
        rs_stock.Fields!anulado = "No"
        rs_stock.Fields!Comprobante = TipoFactura
        rs_stock.Fields!NroComprobante = NroComp

        If Not IsNull(data_renglon_tpv.Recordset.Fields!NroPresupuesto) Then
            rs_stock.Fields!NroPresupuesto = data_renglon_tpv.Recordset.Fields!NroPresupuesto
            rs_stock.Fields!codmov_presupuesto = data_renglon_tpv.Recordset.Fields!codmov_presupuesto
        End If

        If Not IsNull(data_renglon_tpv.Recordset.Fields!NroPedido) Then
            rs_stock.Fields!NroPedido = data_renglon_tpv.Recordset.Fields!NroPedido
            rs_stock.Fields!codmov_pedido = data_renglon_tpv.Recordset.Fields!codmov_pedido
        End If

        If Not IsNull(data_renglon_tpv.Recordset.Fields!NroRemito) Then
            rs_stock.Fields!NroRemito = data_renglon_tpv.Recordset.Fields!NroPedido
            rs_stock.Fields!codmov_remito = data_renglon_tpv.Recordset.Fields!codmov_remito
        End If

        rs_stock.Fields!Lista_Precio = data_renglon_tpv.Recordset.Fields!Lista_Precio
        If data_renglon_tpv.Recordset.Fields!promocion = "Si" Then
            'Promocion
            rs_stock.Fields!promocion = data_renglon_tpv.Recordset.Fields!promocion
            rs_stock.Fields!promocion_por = data_renglon_tpv.Recordset.Fields!promocion_por
            rs_stock.Fields!promocion_tipo = data_renglon_tpv.Recordset.Fields!promocion_tipo
            rs_stock.Fields!promocion_cant = data_renglon_tpv.Recordset.Fields!promocion_cant
        End If

        '''''''''''''''''''''''''''''''
        'Cantidad - Unidad <- Rprecios'
        '''''''''''''''''''''''''''''''
        If data_renglon_tpv.Recordset.Fields!promocion = "No" Then
            rs_stock.Fields!promocion = data_renglon_tpv.Recordset.Fields!promocion
            rs_stock.Fields!promocion_por = data_renglon_tpv.Recordset.Fields!promocion_por
            rs_stock.Fields!promocion_tipo = data_renglon_tpv.Recordset.Fields!promocion_tipo
            rs_stock.Fields!promocion_cant = data_renglon_tpv.Recordset.Fields!promocion_cant
        End If

        ''''''''''''''''''
        'Impuesto Interno'
        ''''''''''''''''''
        rs_stock.Fields!impuesto_interno = data_renglon_tpv.Recordset.Fields!impuesto_interno
        rs_stock.Fields!impuesto_interno_subtotal = data_renglon_tpv.Recordset.Fields!impuesto_interno_subtotal

        ' Si es una factura a traves de pedido, marco en la tabla stockp los articulos que salieron para saber si quedo uno sin salir
        If Not IsNull(data_renglon_tpv.Recordset.Fields!NroPedido) Then
            rs_stockp.Open "SELECT * FROM stockp WHERE stockp.id_stock = " & data_renglon_tpv.Recordset.Fields!id_stock & " AND stockp.CodigoMovimiento = " & data_renglon_tpv.Recordset.Fields!codmov_pedido, conn, adOpenDynamic, adLockOptimistic
            If rs_stockp.RecordCount > 0 Then
                rs_stockp.MoveFirst
'                totalRemitido = rs_stockp.Fields!cantidad_pendiente - data_renglon_tpv.Recordset.Fields!Cantidad
                totalRemitido = rs_stockp.Fields!cantidad_pendiente - rs_stock.Fields!Cantidad

                If totalRemitido = 0 Or totalRemitido < 0 Then
                    rs_stockp.Fields!remitido_facturado = "Si"
                    ' Control error
                    totalRemitido = 0
                End If
                rs_stockp.Fields!cantidad_pendiente = CDbl(totalRemitido)
                rs_stockp.Update
            End If

            rs_stockp.Close

            rs_stock.Fields!id_stockp = data_renglon_tpv.Recordset.Fields!id_stock
        End If

        ' Si tiene permiso para seleccionar si la factura entrega articulos
'        If Principal.remite_factura_art = "Si" Then
'            ' Guardo la cantidad pendiente de entrega
'            If remite_factura_art.ListIndex = 1 Then
'                rs_stock.Fields!cantidad_entregada_pend = data_renglon_tpv.Recordset.Fields!Cantidad
'            End If
'        End If

        ''''''''''''''
        'serie Stock '
        ''''''''''''''
        If data_renglon_tpv.Recordset.Fields!serie = "Si" Then
            'rs_stock.Fields!id_serie_entrada = data_renglon_tpv.Recordset.Fields!id_serie_entrada
            rs_stock.Fields!desc_serie = data_renglon_tpv.Recordset.Fields!desc_serie
            rs_stock.Fields!serie = "Si"
        End If

        ''''''''''''''
        'Ensamble Vta'
        ''''''''''''''
        'Indica si se trata de un articulo ensamblado
        rs_consulta_articulo.Open "SELECT en_abm_formula.id_articulo  " & _
                                  "FROM articulo " & _
                                  "INNER JOIN en_abm_formula ON (en_abm_formula.id_en_abm = articulo.id_en_abm ) " & _
                                  "WHERE IDArt = " & data_renglon_tpv.Recordset.Fields!IDArt & " ", conn, adOpenDynamic, adLockReadOnly
        If rs_consulta_articulo.RecordCount > 0 Then
            rs_stock.Fields!ensamblado = "Si"
        End If

        rs_consulta_articulo.Close

        rs_stock.Fields!coti_dolar = Actualiza_Cotizacion_Dolar_Articulo(data_renglon_tpv.Recordset.Fields!IDArt, "coti_dolar")
        rs_stock.Fields!id_cotizacion = Actualiza_Cotizacion_Dolar_Articulo(data_renglon_tpv.Recordset.Fields!IDArt, "id_cotizacion")

        rs_stock.Update
        
        data_renglon_tpv.Recordset.MoveNext
              
    Loop
    
    rs_stock.Close
              
    ' Guardo copia de tabla cuerpostock en cuerpostock_copia por error en AFIP
'    Guardar_cuerpostock_copia

    ' Si el Medio de Cobro es con cheque
    ' Agrego el los cheques de terceros a la tabla chequetercero de la tabla chequetercero_temp
    If Total_Cheque <> 0 Then
        
        If DataChequeTerceroTemp.Recordset.RecordCount > 0 Then
            
            DataChequeTerceroTemp.Recordset.MoveFirst
                            
            rs_chequetercero.Open "SELECT * FROM chequetercero where ID = 1", conn, adOpenDynamic, adLockOptimistic

            Do While Not DataChequeTerceroTemp.Recordset.EOF
                rs_chequetercero.AddNew
                rs_chequetercero.Fields!NroCheque = DataChequeTerceroTemp.Recordset.Fields!NroCheque
                rs_chequetercero.Fields!CodBanco = DataChequeTerceroTemp.Recordset.Fields!CodBanco
                rs_chequetercero.Fields!CodCliente = DataChequeTerceroTemp.Recordset.Fields!CodCliente
                rs_chequetercero.Fields!Librador = DataChequeTerceroTemp.Recordset.Fields!Librador
                rs_chequetercero.Fields!fechaEmision = Format(DataChequeTerceroTemp.Recordset.Fields!fechaEmision, "short date")
                rs_chequetercero.Fields!fechaVto = Format(DataChequeTerceroTemp.Recordset.Fields!fechaVto, "short date")
                rs_chequetercero.Fields!fechaCobro = Format(DataChequeTerceroTemp.Recordset.Fields!fechaCobro, "short date")
                rs_chequetercero.Fields!Importe = DataChequeTerceroTemp.Recordset.Fields!Importe
                rs_chequetercero.Fields!anulado = "No"
                rs_chequetercero.Fields!Encartera = "Si"
                rs_chequetercero.Fields!Entregado = "No"
                rs_chequetercero.Fields!rechazado = "No"
                rs_chequetercero.Fields!Depositado = "No"
                rs_chequetercero.Fields!NroCompREC = NroComp
                rs_chequetercero.Fields!tipo_comp = TipoFactura
                rs_chequetercero.Fields!CodigoMovimientoREC = contador
                rs_chequetercero.Fields!CUITLibrador = DataChequeTerceroTemp.Recordset.Fields!CUITLibrador
                rs_chequetercero.Update

                ' Agrego los datos de cheque a la tabla caja para la Caja de Cheque
                    
                    'Consulto el saldo de la caja, segun tipo de caja y Usuario
                    rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja = " & Principal.id_caja_cheque & "", conn, adOpenDynamic, adLockOptimistic
                    
                    If rs_saldo_caja.RecordCount > 0 Then
                        rs_saldo_caja.Fields!Saldo = CDbl(Format(rs_saldo_caja.Fields!Saldo + DataChequeTerceroTemp.Recordset.Fields!Importe, "##,###.00"))
                        rs_saldo_caja.Fields!id_usuario = Principal.idUsuario
                        ' Seleccion de sucursal de punto de venta
                        rs_saldo_caja.Fields!cod_sucursal = id_sucursal
                        rs_saldo_caja.Fields!id_caja = Principal.id_caja_cheque
                        rs_saldo_caja.Update
                    End If
                                                                                            
                    ' Actualizo la tabla caja
                    rs_caja.Open "SELECT * from caja where codigo_movimiento = 1", conn, adOpenDynamic, adLockOptimistic
                    rs_caja.AddNew
            
                    rs_caja.Fields!Fecha = Format(Fecha, "short date")
                    rs_caja.Fields!tipo_comprobante = "CHEQ"
                    rs_caja.Fields!Tipo = "Cheque"
                    rs_caja.Fields!nro_comprobante = DataChequeTerceroTemp.Recordset.Fields!NroCheque
                    rs_caja.Fields!nro_comp_busq = DataChequeTerceroTemp.Recordset.Fields!NroCheque
                    rs_caja.Fields!egreso = 0
                    rs_caja.Fields!id_usuario = Principal.idUsuario
                    rs_caja.Fields!cod_vendedor = Principal.id_vendedor_usr

                    ' Seleccion de sucursal de punto de venta
                    rs_caja.Fields!cod_sucursal = id_sucursal
                    
                    rs_caja.Fields!Moneda = "No"
                    rs_caja.Fields!ingreso = CDbl(Format(DataChequeTerceroTemp.Recordset.Fields!Importe, "##,###.00"))
                                               
                    ' Traigo el banco para mostrar en el campo detalle
                    rs_banco.Open "SELECT banco.Nombre,banco.CodBanco from banco WHERE CodBanco = " & DataChequeTerceroTemp.Recordset.Fields!CodBanco & "", conn, adOpenDynamic, adLockReadOnly

                    rs_caja.Fields!Detalle = "Cheque Nro: " & DataChequeTerceroTemp.Recordset.Fields!NroCheque & " - Banco: " & rs_banco.Fields!Nombre & " - Librador: " & DataChequeTerceroTemp.Recordset.Fields!Librador & " - CUIT: " & DataChequeTerceroTemp.Recordset.Fields!CUITLibrador & " - Fecha Cob: " & Format(DataChequeTerceroTemp.Recordset.Fields!fechaCobro, "short date") & " - Importe: " & DataChequeTerceroTemp.Recordset.Fields!Importe
                    datos_de_cheque = datos_de_cheque & " " & rs_caja.Fields!Detalle
                    
                    rs_banco.Close
                    
                    rs_caja.Fields!codigo_movimiento = contador
                    rs_caja.Fields!Codigo_Cliente = Codigo_Cliente
                    rs_caja.Fields!codigo_prov = 1
                    rs_caja.Fields!tipo_cp = "Cliente"
                    rs_caja.Fields!anulado = "No"
                    rs_caja.Fields!Saldo = rs_saldo_caja.Fields!Saldo
                    rs_caja.Fields!id_caja_abm_origen = Principal.id_caja_cheque
                    rs_caja.Fields!id_chequetercero = rs_chequetercero.Fields!ID
                    rs_caja.Fields!nro_comp_cheq = NroComp
                    rs_caja.Fields!tipo_comp_cheq = TipoFactura
                    
                    rs_caja.Update
                    
                    rs_caja.Close
                    
                    rs_saldo_caja.Close

                DataChequeTerceroTemp.Recordset.MoveNext
                
            Loop
                rs_chequetercero.Close
        End If
    End If
                                                                          
    ' Si es medio de cobro en cuenta corriente guardo el saldo de la factura en recibo_factura para ser cancelada despues
    If (Cond_Venta_Cliente_ID <> 1 Or Cond_Venta_Cliente_ID <> 2 Or Cond_Venta_Cliente_ID <> 3) And Total_CtaCte <> 0 Then

        rs_recibo_factura.Open "SELECT * FROM recibo_factura where CodigoMovimiento =1", conn, adOpenDynamic, adLockOptimistic
        rs_recibo_factura.AddNew
        
        rs_recibo_factura.Fields!Fecha = Format(Fecha, "Short date")
        
        rs_recibo_factura.Fields!TipoComprobante = TipoFactura
        
        rs_recibo_factura.Fields!Importe = CDbl(Format(Label_Total, "##,###.00"))
        rs_recibo_factura.Fields!cancelado = CDbl(Format(CDbl(Total_Efectivo) + CDbl(Total_Tarjeta) + CDbl(Total_Cheque), "##,###.00"))
        rs_recibo_factura.Fields!Saldo = CDbl(Format(Total_CtaCte, "##,###.00"))
        rs_recibo_factura.Fields!ImporteNC = CDbl(Format(Label_Total, "##,###.00"))
        rs_recibo_factura.Fields!Neto = CDbl(Format(SubtotalDesc.Caption, "##,###.00"))
        rs_recibo_factura.Fields!NroComprobante = NroComp
        rs_recibo_factura.Fields!Estado = "N/Canc"
        
        ' Consulto los Dias de la Condicion de Venta para utilizarla en la fecha de Vencimiento
        rs_cv.Open "SELECT * FROM cond_venta WHERE Codigo = " & CV.BoundText, conn, adOpenDynamic, adLockOptimistic
        rs_recibo_factura.Fields!Vencimiento = DateAdd("d", rs_cv.Fields!Dias, Fecha)
        
        rs_recibo_factura.Fields!CodigoMovimiento = contador
        rs_recibo_factura.Fields!Codigo = Codigo_Cliente

        rs_recibo_factura.Fields!CondVenta = CV.Text
        rs_recibo_factura.Fields!Imp = "No"
        rs_recibo_factura.Fields!anulado = "No"
        rs_recibo_factura.Fields!Modificado = "No"
        rs_recibo_factura.Fields!Tipo = "Cliente"
        rs_recibo_factura.Fields!CodViajante = CodViajante
        rs_recibo_factura.Update
        
        rs_recibo_factura.Close

    End If
                                                                              
    form_espera.ProgressBar.Value = 75
                                                                              
    ' Si el Medio de Cobro es con tarjeta
    ' Agrego los datos de la tarjeta de la tabla temporal tc_temp a la tabla tc_comprobante
    If Total_Tarjeta <> 0 Then
        
        If data_tarjeta_temp.Recordset.RecordCount > 0 Then
            
            data_tarjeta_temp.Recordset.MoveFirst
                            
            rs_tc_comprobante.Open "SELECT * FROM tc_comprobante where id_tc_comprobante = 1", conn, adOpenDynamic, adLockOptimistic

            Do While Not data_tarjeta_temp.Recordset.EOF
                rs_tc_comprobante.AddNew
                rs_tc_comprobante.Fields!nombre_tc_comprobante = data_tarjeta_temp.Recordset.Fields!nombre_tc_temp
                rs_tc_comprobante.Fields!nombre_plan_tc_comprobante = data_tarjeta_temp.Recordset.Fields!nombre_plan_tc_temp
                rs_tc_comprobante.Fields!id_tc = data_tarjeta_temp.Recordset.Fields!id_tc
                rs_tc_comprobante.Fields!id_tc_plan = data_tarjeta_temp.Recordset.Fields!id_tc_plan
                rs_tc_comprobante.Fields!cuotas_tc_comprobante = data_tarjeta_temp.Recordset.Fields!cuotas_tc_temp
                rs_tc_comprobante.Fields!interes_tc_comprobante = CDbl(Format(data_tarjeta_temp.Recordset.Fields!interes_tc_temp, "##,###.00"))
                rs_tc_comprobante.Fields!descuento_tc_comprobante = data_tarjeta_temp.Recordset.Fields!descuento_tc_temp
                rs_tc_comprobante.Fields!nro_tarjeta_tc_comprobante = data_tarjeta_temp.Recordset.Fields!nro_tarjeta_tc_temp
                rs_tc_comprobante.Fields!nro_cupon_tc_comprobante = data_tarjeta_temp.Recordset.Fields!nro_cupon_tc_temp
                rs_tc_comprobante.Fields!importe_tc_comprobante = CDbl(Format(data_tarjeta_temp.Recordset.Fields!importe_tc_temp, "##,###.00"))
                rs_tc_comprobante.Fields!importe_cuota = CDbl(Format(data_tarjeta_temp.Recordset.Fields!importe_cuota, "##,###.00"))
                rs_tc_comprobante.Fields!importe_con_interes = CDbl(Format(data_tarjeta_temp.Recordset.Fields!importe_con_interes, "##,###.00"))
                rs_tc_comprobante.Fields!codigo_movimiento = contador
                
                'Lote_tc
                rs_tc_comprobante.Fields!nro_lote_tc = data_tarjeta_temp.Recordset.Fields!nro_lote_tc_temp
                
                rs_tc_comprobante.Update

                ' Agrego los datos de la tarjeta a la tabla caja para la Caja de Tarjeta
                    
                    'Consulto el saldo de la caja, segun tipo de caja y Usuario
                    rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja = " & Principal.id_caja_tarjeta & "", conn, adOpenDynamic, adLockOptimistic
                    
                    If rs_saldo_caja.RecordCount > 0 Then
                        rs_saldo_caja.Fields!Saldo = CDbl(Format(rs_saldo_caja.Fields!Saldo + data_tarjeta_temp.Recordset.Fields!importe_con_interes, "##,###.00"))
                        rs_saldo_caja.Fields!id_usuario = Principal.idUsuario
                        ' Seleccion de sucursal de punto de venta
                        rs_saldo_caja.Fields!cod_sucursal = id_sucursal
                        rs_saldo_caja.Fields!id_caja = Principal.id_caja_tarjeta
                        rs_saldo_caja.Update
                    End If
                                                                                            
                    ' Actualizo la tabla caja
                    rs_caja.Open "SELECT * from caja where codigo_movimiento = 1", conn, adOpenDynamic, adLockOptimistic
                    rs_caja.AddNew
            
                    rs_caja.Fields!Fecha = Format(Fecha, "short date")
                    rs_caja.Fields!tipo_comprobante = "TARJ"
                    rs_caja.Fields!Tipo = "Tarjeta"
                    rs_caja.Fields!nro_comprobante = data_tarjeta_temp.Recordset.Fields!nro_cupon_tc_temp
                    rs_caja.Fields!nro_comp_busq = data_tarjeta_temp.Recordset.Fields!nro_cupon_tc_temp
                    rs_caja.Fields!egreso = 0
                    rs_caja.Fields!id_usuario = Principal.idUsuario
                    rs_caja.Fields!cod_vendedor = Principal.id_vendedor_usr

                    ' Seleccion de sucursal de punto de venta
                    rs_caja.Fields!cod_sucursal = id_sucursal
                    
                    rs_caja.Fields!Moneda = "No"
                    rs_caja.Fields!ingreso = CDbl(Format(data_tarjeta_temp.Recordset.Fields!importe_con_interes, "##,###.00"))
                                               
                    rs_caja.Fields!Detalle = "Tarjeta: " & data_tarjeta_temp.Recordset.Fields!nombre_tc_temp & " - Cliente: " & Cliente.Caption & " - Plan: " & data_tarjeta_temp.Recordset.Fields!nombre_plan_tc_temp & " - Nro. Lote: " & data_tarjeta_temp.Recordset.Fields!nro_lote_tc_temp & " - Cupon: " & data_tarjeta_temp.Recordset.Fields!nro_cupon_tc_temp & " - Importe: " & CDbl(Format(data_tarjeta_temp.Recordset.Fields!importe_con_interes, "##,###.00")) & ""
                                        
                    rs_caja.Fields!codigo_movimiento = contador
                    rs_caja.Fields!Codigo_Cliente = Codigo_Cliente
                    rs_caja.Fields!codigo_prov = 1
                    rs_caja.Fields!tipo_cp = "Cliente"
                    rs_caja.Fields!anulado = "No"
                    rs_caja.Fields!Saldo = rs_saldo_caja.Fields!Saldo
                    rs_caja.Fields!id_caja_abm_origen = Principal.id_caja_tarjeta
                    rs_caja.Fields!nro_comp_cheq = NroComp
                    rs_caja.Fields!tipo_comp_cheq = TipoFactura
                    rs_caja.Fields!id_tc_comprobante = rs_tc_comprobante.Fields!id_tc_comprobante
                    rs_caja.Fields!id_tc = rs_tc_comprobante.Fields!id_tc
                    
                    rs_caja.Update
                    
                    rs_caja.Close
                    
                    rs_saldo_caja.Close

                data_tarjeta_temp.Recordset.MoveNext
            Loop
                rs_tc_comprobante.Close
        End If
    End If
                                                                              
     ' Si viene del proceso pedidos pendientes de seleccion de un pedido
    If Comprobante_Pedido = "Si" Or Comprobante_Pedido = "Si PED Avanzado" Then
    
         ' Valido si el usuario borro todos los items del pedido informo que debe figurar por lo menos un item del pedido
         rs_valid_pedido.Open "SELECT CodigoMovimiento,visualiza,codmov_pedido FROM cuerpostock WHERE visualiza = 'No' AND NOT ISNULL(CodigoMovimiento)", conn, adOpenDynamic, adLockOptimistic
              
         ' Si hay un CodigoMovimiento en el renglon es porque hay articulos del Pedido
         If rs_valid_pedido.RecordCount > 0 Then
              
             ' Guardo la relacin Pedido - Factura
             rs_cuerpostock.Open "SELECT DISTINCT CodigoMovimiento,NroPedido,visualiza,codmov_pedido FROM cuerpostock WHERE visualiza = 'No' AND cuerpostock.Codusuario = " & Principal.idUsuario, conn, adOpenDynamic, adLockOptimistic
             
             If rs_cuerpostock.RecordCount > 0 Then
             
                 rs_cuerpostock.MoveFirst
                         
                 Do While Not rs_cuerpostock.EOF
                                
                     If rs_cuerpostock.RecordCount > 0 And Not IsNull(rs_cuerpostock.Fields!NroPedido) Then
                         
                         rs_pedido_factura.Open "SELECT * FROM ped_fact WHERE id_ped_fact = 0", conn, adOpenDynamic, adLockOptimistic
                                      
                        ' Comprobar si el articulo es uno que se agrego nuevo. si no marcarlo en el pedido
                        If Not IsNull(rs_cuerpostock.Fields!CodigoMovimiento) Then
                                                        
                            rs_pedido.Open "SELECT * FROM comp_ped WHERE CodigoMovimiento = " & rs_cuerpostock.Fields!codmov_pedido & " And  TipoComprobante = 'PED'", conn, adOpenDynamic, adLockOptimistic
                            
                            rs_stock_facturado.Open "SELECT stockp.IDArt FROM stockp WHERE CodigoMovimiento=" & rs_cuerpostock.Fields!codmov_pedido & " AND remitido_facturado='No'  ", conn, adOpenDynamic, adLockOptimistic
                
                            If rs_stock_facturado.RecordCount = 0 Then
                                rs_pedido.Fields!Estado = "Facturado"
                                'hacer calculo del tipo de remito si parcial o no.
                                rs_pedido.Update
                                rs_pedido.Close
                            Else
                                rs_pedido.Fields!Estado = "Parcial"
                                'hacer calculo del tipo de remito si parcial o no.
                                 rs_pedido.Update
                                rs_pedido.Close
                            End If
                            
                            rs_stock_facturado.Close
    '
                            ' Guardo la relacion Pedido - Factura
                            rs_pedido_factura.AddNew
                            rs_pedido_factura.Fields!CodigoMovimientoF = contador
                            rs_pedido_factura.Fields!CodigoMovimientoP = rs_cuerpostock.Fields!codmov_pedido
                            rs_pedido_factura.Fields!anulado = "No"
                            ' Control error
'                            control_error = "relacion - comp_ped pedido"
                            rs_pedido_factura.Update
                            
                            rs_pedido_factura.Close
                            
                        End If
                 
                     End If
                     
                     rs_cuerpostock.MoveNext
                 
                 Loop
             
             End If
             
             rs_cuerpostock.Close
             
         ' El usuario borro todos los items del pedido informo que debe figurar por lo menos un item del pedido
         Else
                 
             If conn.State = 1 Then
                 conn.RollbackTrans
                 conn.Close
             End If

             MsgBox "Debe figurar al menos un articulo del pedido inicial para poder realizar la factura", vbInformation, "ATENCION"

             ' Descargo formulario de espera
             Unload form_espera
     
             CalculoTotales
                                        
         End If
         
     rs_valid_pedido.Close
         
    End If
    
    ' Guardo CodigoMovimiento en tabla cuerpostock
    conn.Execute "UPDATE cuerpostock SET cuerpostock.codigomovimiento = " & contador & " WHERE Codusuario = " & Principal.idUsuario & " And visualiza = 'No'"
        
        '''''''
        'Serie'     Insert serie_salida - Update disponible no en serie_entrada
        '''''''
                          
        GuardarSerie
    
''''''''''''''''''''''''''''''''''
        'GENERAR ASIENTO CONTABLE'
        ''''''''''''''''''''''''''
        Principal.Conta_PV_Esp (id_pv_electronico)
        
        If Principal.activ_contabilidad = "Si" And Principal.conta_pv = "Si" Then
        'Si la contabilidad esta activa entonces

            'inicializo variable
            Error_conta = "No"

            generar_asiento_cont CStr(NroComp), CStr(TipoFactura)

            If Error_conta = "Si" Then
                GoTo captura
            End If

        End If
''''''''''''''''''''''''''''''''''
               
        ' Sistema de puntaje y premios
        If Principal.mod_sp = "Si" And Principal.activ_sp = "Si" Then
        
            saldo_calculado = Actualiza_Puntos_SP(contador, CDbl(Codigo_Cliente), TipoFactura, NroComp, CDbl(SubtotalDesc), CDbl(ImporteTotal), Fecha)
            
            ' Asigno saldo acumulado de cliente para informar en detalle de factura
            If Principal.imprime_comp_sp = "Si" Then
                Detalle.Text = Detalle.Text & " - " & Principal.nombre_sp & " " & saldo_calculado
            End If
            
        End If
               
        ' Programa de descuentos y voucher
        If Principal.mod_pd = "Si" And Principal.activ_pd = "Si" Then
            
'            If Puntos_tipo_programa_PD = "Puntos" Then
                saldo_calculado_pd = Actualiza_Puntos_PD(contador, CDbl(Codigo_Cliente), TipoFactura, NroComp, CDbl(SubtotalDesc), CDbl(ImporteTotal), Fecha)
                
                ' Asigno saldo acumulado de cliente para informar en detalle de factura
                If Principal.imprime_comp_pd = "Si" Then
                    Detalle.Text = Detalle.Text & " - " & Principal.nombre_pd & " " & saldo_calculado_pd(1)
                End If
                
                Envia_Mail_PD CDbl(saldo_calculado_pd(0)), CDbl(Codigo_Cliente)
                
                ' Verifico si realizo canje de puntos
                If Descuenta_Canje_Puntos_PD(CDbl(contador), CDbl(Codigo_Cliente), Puntos_tipo_programa_PD, Fecha, Puntos_tipo_sp_desc_PD, CDbl(Puntos_ID_Descuento_PD)) = True Then
                    Envia_Mail_Canje_PD CDbl(contador), CDbl(Codigo_Cliente), Puntos_tipo_sp_desc_PD
                End If
'            End If
                               
'            If Puntos_tipo_programa_PD = "Voucher" Then
'                Impresion_Voucher_PD "Completa", "Configuracion", , CDbl(ImporteTotal), "TPV", contador
'            End If
            
        End If
               
        ' Deshabilito boton Generar y Cancelar_Boton para evitar cancelacion de proceso hasta la finalizacin de la impresion
        Aceptar.Enabled = False
        Cancelar_Boton.Enabled = False
        Deshabilita_Guardar_F12 = "Si"
        
         ' Funcion para guardar resumen_venta_cv
        cv_tpv = Seleccion_CV_Tipo_Cobro
            
        Guardar_resumen_venta_cv "Si", Fecha, CDbl(Codigo_Cliente), contador, NroComp, TipoFactura, "Factura", CDbl(Format(CDbl(SubtotalDesc.Caption) + neto_interes, "##,###.00")), CDbl(Format(CDbl(Iva1.Caption) + CDbl(iva_interes), "##,###.00")), CDbl(Iva2), CDbl(total_percep), CDbl(ImpInt), CDbl(interes_tarjeta_total), CDbl(Exento), CDbl(ImporteTotal), CDbl(cv_tpv), , , CDbl(Total_Efectivo), CDbl(Total_CtaCte), CDbl(Total_Tarjeta), CDbl(Total_Cheque)
               
        ' Impresion de Factura
        Dim Domicilio_var As String
        Dim cantidad_renglon As String
        Dim importe_bruto_renglon As String
        Dim importe_iva As String
                                        
        Dim crApp As New CRAXDDRT.Application
        Dim crApp2 As New CRAXDDRT.Application
        Dim crApp3 As New CRAXDDRT.Application
        Dim Report As CRAXDDRT.Report
        Dim Report2 As CRAXDDRT.Report
        Dim Report3 As CRAXDDRT.Report
        Dim tbl As CRAXDDRT.DatabaseTable
        Dim Sub_Report_encabezado As CRAXDDRT.Report
        Dim Sub_Report2_encabezado As CRAXDDRT.Report
        Dim Sub_Report3_encabezado As CRAXDDRT.Report
                                        
        ' Factura electronica - ' FE con CAEA
        If pv_electronico = "Si" And fe_regimen_tipo = "CAE" Then

            rs_informe.Open "SELECT * FROM cliente WHERE Codigo = " & Codigo_Cliente & "", conn, adOpenDynamic, adLockOptimistic

            ' Traigo los datos del CUIT y cambio de formato
            Nombre = Left(rs_informe.Fields!nombre_cliente, 30)
            ' Para pasar el parametro al Controlador Fiscal saco el "-"
            CUIT = rs_informe.Fields!CUIT
            If rs_informe.Fields!tipo_doc = "CUIT" Or tipo_doc_cliente_ocasional = "CUIT" Then

                If datos_ocasional.Visible = True Then
                    CUIT_FACT_ELECT = Formato_CUIT_AFIP(nro_doc_cliente_ocasional)
                Else
                    CUIT_FACT_ELECT = Formato_CUIT_AFIP(rs_informe.Fields!CUIT)
                End If

                tipo_doc = 80
            Else

                If rs_informe.Fields!CUIT = "00-00000000-0" Then
                    ' Validacion Cliente Ocasional
                    If datos_ocasional.Visible = True Then
                        CUIT_FACT_ELECT = nro_doc_cliente_ocasional
                    Else
                        CUIT_FACT_ELECT = "00000000000"
                    End If
                Else
                
                    If datos_ocasional.Visible = True Then
                        CUIT_FACT_ELECT = nro_doc_cliente_ocasional
                    Else
                        CUIT_FACT_ELECT = rs_informe.Fields!CUIT
                    End If
                
                End If
                
                Dim tipo_documento As String
                
                ' Validacion Cliente Ocasional
                If datos_ocasional.Visible = True Then
                    tipo_documento = tipo_doc_cliente_ocasional
                Else
                    tipo_documento = rs_informe.Fields!tipo_doc
                End If
                
                tipo_doc = Obtener_Tipo_Documentos_AFIP(tipo_documento)
                
            End If

            rs_informe.Close

            ' Validacion cuando la empresa es Exenta y emite factura a un CF - Informo DNI con valor 1 para que pase factura
            If Principal.IDIVA = 3 And Codigo_Cliente = 1 Then
                tipo_doc = 96
                CUIT_FACT_ELECT = 1
            End If

            ' Parametros de factura electronica
            wsfev1.Reset ' Inicializa variables internas

            ' Agrega datos de factura (TipoVenta = ' Venta de productos y servicios (Concepto por defecto) / CUIT: 80
             neto_interes_fe = CDbl(Format(neto_interes, "##,###.00"))
             subtotal_desc_fe = CDbl(SubtotalDesc) + CDbl(neto_interes_fe)
             
             wsfev1.AgregaFactura TipoVenta, tipo_doc, CUIT_FACT_ELECT, Nro_elect, Nro_elect, FechaComp, CDbl(ImporteTotal), impTotalConceptos, CDbl(subtotal_desc_fe), CDbl(Exento), FechaServDesde, FechaServHasta, FechaVencPago, CodigoMoneda, cotizacion_moneda

            ' Renglon de factura
            rs_cuerpostock.Open "SELECT SUM(PrecioVentaxRD) as PN, SUM(PrecioIVAxR) as PIVA, cuerpostock.alicuota " & _
            "FROM cuerpostock WHERE CodUsuario = " & Principal.idUsuario & " AND TipoIVA = 'Gravado' AND visualiza = 'No' GROUP BY cuerpostock.Alicuota", conn, adOpenDynamic, adLockOptimistic
            
            If rs_cuerpostock.RecordCount > 0 Then

                rs_cuerpostock.MoveFirst

                Do While Not rs_cuerpostock.EOF

                     Codigo_IVA_AFIP = Obtener_Alicuota_IVA_Temporal(rs_cuerpostock.Fields!Alicuota)

                    If PorDesc1 = 0 Then
                        precio_neto_elect = CDbl(Format(rs_cuerpostock.Fields!PN, "##,###.00"))
                        ' Validacion FE 0,01 centavos / 0,02 centavos
                        If CDbl(Format(rs_cuerpostock.Fields!PIVA, "##,###.00")) = 0 Then
                            iva_elect = CDbl("0,01")
                        Else
                            
                            If iva_interes = 0 Then
                                ' Funcion para Redondear el Valor del IVA del renglon por alicuota con el valor Neto de pie del Comprobante
                                iva_elect = Comparta_IVA_Renglon_PIE((rs_cuerpostock.Fields!PIVA), CDbl(Iva1), CDbl(Iva2), rs_cuerpostock.Fields!Alicuota)
                            Else
                                iva_elect = CDbl(Format(rs_cuerpostock.Fields!PIVA, "##,###.00"))
                            End If

                        End If
                    Else
                        precio_neto_elect = CDbl(Format((rs_cuerpostock.Fields!PN - rs_cuerpostock.Fields!PN * PorDesc1 / 100), "##,###.00"))
                                                                      
                        If iva_interes = 0 Then
                            ' Funcion para Redondear el Valor del IVA del renglon por alicuota con el valor Neto de pie del Comprobante
                            iva_elect = Comparta_IVA_Renglon_PIE((rs_cuerpostock.Fields!PIVA), CDbl(Iva1), CDbl(Iva2), rs_cuerpostock.Fields!Alicuota)
                        Else
                            iva_elect = CDbl(Format((rs_cuerpostock.Fields!PIVA - rs_cuerpostock.Fields!PIVA * PorDesc1 / 100), "##,###.00"))
                        End If
                    
                    End If
                    
                    If TipoFactura = "FB" Or TipoFactura = "FA" Or TipoFactura = "FM" Then
                    
                        ' Informo Neto + IVA Intereses por financiacin de terceros si la alicuota es la 1 (Primaria)
                        If iva_interes <> 0 Then
                            
                            ' 1 Alicuota
                            If rs_cuerpostock.RecordCount = 1 Then
                                If rs_cuerpostock.Fields!Alicuota = 1 Then
                            
                                    precio_neto_int = CDbl(Format(neto_interes, "##,###.00")) + precio_neto_elect
                                    iva_elect_int = CDbl(Format(iva_interes, "##,###.00")) + iva_elect
                                
                                    wsfev1.AgregaIVA Codigo_IVA_AFIP, precio_neto_int, iva_elect_int ' Agregar este metodo tantas veces como alicuotas de IVA distintas tenga el comprobante
                                End If
                                
                                If rs_cuerpostock.Fields!Alicuota = 2 Then
                            
                                    precio_neto_int = CDbl(Format(neto_interes, "##,###.00"))
                                    iva_elect_int = CDbl(Format(iva_interes, "##,###.00"))
                                    
                                    
                                    wsfev1.AgregaIVA Principal.Alicuota_IVA1_AFIP, precio_neto_int, iva_elect_int ' Agregar este metodo tantas veces como alicuotas de IVA distintas tenga el comprobante
                                    wsfev1.AgregaIVA Codigo_IVA_AFIP, precio_neto_elect, iva_elect ' Agregar este metodo tantas veces como alicuotas de IVA distintas tenga el comprobante
                                
                                End If
                                
                            End If
                            
                            ' 2 Alicuota
                             If rs_cuerpostock.RecordCount = 2 Then
                                If rs_cuerpostock.Fields!Alicuota = 1 Then
                            
                                    precio_neto_int = CDbl(Format(neto_interes, "##,###.00")) + precio_neto_elect
                                    iva_elect_int = CDbl(Format(iva_interes, "##,###.00")) + iva_elect
                                
                                    wsfev1.AgregaIVA Codigo_IVA_AFIP, precio_neto_int, iva_elect_int ' Agregar este metodo tantas veces como alicuotas de IVA distintas tenga el comprobante
                                End If
                                
                                If rs_cuerpostock.Fields!Alicuota = 2 Then
                            
                                    wsfev1.AgregaIVA Codigo_IVA_AFIP, precio_neto_elect, iva_elect ' Agregar este metodo tantas veces como alicuotas de IVA distintas tenga el comprobante
                                
                                End If
                                
                            End If
                            
                        ' Informo alicuota normal
                        Else
                            
                            wsfev1.AgregaIVA Codigo_IVA_AFIP, precio_neto_elect, iva_elect ' Agregar este metodo tantas veces como alicuotas de IVA distintas tenga el comprobante
                        
                        End If
                    
                    End If
                                        
                    rs_cuerpostock.MoveNext

                Loop

            End If

            rs_cuerpostock.Close

            ' Impuesto interno
            If ImpInt <> 0 Then
                wsfev1.AgregaTributo CDbl(4), "Impuesto interno", CDbl(SubTotalDesc1), 0, CDbl(ImpInt)
            End If

            ' Si es agente de percepcion agrega otros tributos
            If Principal.agente_percep = "Si" Then

                rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE id_usuario = " & Principal.idUsuario, conn, adOpenDynamic, adLockOptimistic
                If rs_percep_cli_temp.RecordCount > 0 Then
                    Do While Not rs_percep_cli_temp.EOF
                        wsfev1.AgregaTributo CDbl(rs_percep_cli_temp.Fields!cod_afip), rs_percep_cli_temp.Fields!nombre_percep_temp, CDbl(SubtotalDesc), rs_percep_cli_temp.Fields!alicuota_percep_cli_temp, rs_percep_cli_temp.Fields!importe_percep_cli_temp
                    rs_percep_cli_temp.MoveNext
                    Loop

                End If

            End If

'            ' Coloco el CodigoMovimiento en los renglones de cuerpostock para relacionar el codigo de barra del CAE
'            rs_cuerpostock.Open "SELECT cuerpostock.Orden,cuerpostock.CodUsuario, cuerpostock.CodigoMovimiento " & _
'            "FROM cuerpostock WHERE CodUsuario = " & Principal.idUsuario & " AND visualiza = 'No' ORDER BY Orden", conn, adOpenDynamic, adLockOptimistic
'
'            If rs_cuerpostock.RecordCount > 0 Then
'                rs_cuerpostock.MoveFirst
'
'                Do While Not rs_cuerpostock.EOF
'                    rs_cuerpostock.Fields!CodigoMovimiento = contador
'                    rs_cuerpostock.Update
'                    rs_cuerpostock.MoveNext
'                Loop
'
'            End If

'            rs_cuentacliente_fe1.Open

            ' Autorizacion de Factura electronica
            If wsfev1.Autorizar(PtoVta, TipoComp) Then
            
                ' Todavia no confirmar FE hasta validar resultado AFIP
                genero_fe = "No"
                genero_transaccion = "No"

                CAE_actual_fe = wsfev1.SFCAE(0)
                vencimiento_actual_fe = wsfev1.SFVencimiento(0)
                
'                rs_cuentacliente_fe1.Open

                wsfev1.AutorizarRespuesta 0, CAE, Vencimiento, resultado, Reproceso

                ' Si aprobo la transmision, traigo CAE y Vencimiento
                If resultado = "A" Then
                    fe_aprobada = "Si"
                    genero_fe = "Si"
                
                    ' Edito tabla cuentacliente para guardar CAE, Vencimiento, asignar que es comprobante fiscal y que fue transmitido
                    rs_cuentacliente_fe.Open "SELECT id_cuentacliente,fe_cae,fe_vto_cae,fe_comp,fe_transmitido FROM cuentacliente WHERE id_cuentacliente = " & rs_cuentacliente.Fields!id_cuentacliente, conn, adOpenDynamic, adLockOptimistic
                    rs_cuentacliente_fe.Fields!fe_cae = CAE

                    ' Recupero la fecha a forma VB y MySQL
                    fecha_nueva = Formato_Fecha_VB(Vencimiento)

                    rs_cuentacliente_fe.Fields!fe_vto_cae = Format(fecha_nueva, "short date")
                    rs_cuentacliente_fe.Fields!fe_comp = "Si"
                    rs_cuentacliente_fe.Fields!fe_transmitido = "Si"
                    rs_cuentacliente_fe.Update

                    ' Instancio variables de CAE para reportes electronicos nuevos
                    CAE = "CAE = " & CAE
                    fecha_nueva = "Vto CAE = " & fecha_nueva

                    ' Genero y guardo la imagen del codigo de barra del CAE
                    ' Traigo el codigo de documento de AFIP
                    cod_afip_barra = Obtener_Tipo_Doc_AFIP(TipoFactura)
                
'                    Obtener_Datos_Cliente(CStr(Codigo_Cliente), "cuit")
                    
                    texto_cod_qr = Principal.Generacion_QR_AFIP_2(Fecha, CStr(cuit_qr), CStr(nro_pv_electronico), CStr(cod_afip_barra), NroComp, "PES", "1", CStr(tipo_doc), CStr(CUIT_FACT_ELECT), CStr(CAE), fe_regimen_tipo, ImporteTotal.Caption)
                    
                    rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_usuario = " & Principal.idUsuario, conn, adOpenDynamic, adLockOptimistic
                    If rs_fe_codbarra.RecordCount = 0 Then
                        rs_fe_codbarra.AddNew
                    End If

                    Guardar_Cod_Barra
                    rs_fe_codbarra.Fields!codigo_movimiento = contador
                    rs_fe_codbarra.Fields!texto_cod_qr = texto_cod_qr
                    rs_fe_codbarra.Fields!id_usuario = Principal.idUsuario
                    rs_fe_codbarra.Update

                    ' Cierro Transaccion antes por si la factura se imprime directo en impresora
                    If conn.State = 1 Then
                        conn.CommitTrans
                        genero_transaccion = "Si"
                        conn.Close
                    End If

                    ' Llamo a procedimiento de impresion de FE
                    Llamada_Impresion_FE TipoFactura
                    
                ' Si el comprobante fue rechazado aborto el proceso
                Else
                    
                    fe_aprobada = "No"
                    genero_fe = "No"
                    genero_transaccion = "No"
'                    MsgBox wsfev1.AutorizarRespuestaObs(0) & Chr(13) + "Comprobante rechazado", vbCritical, "ATENCION"
                    EnviarMensaje wsfev1.AutorizarRespuestaObs(0) & Chr(13) + "Comprobante rechazado"
                    GoTo captura

                End If

            ' Si no se pudo conectar con el servidor de AFIP por errores del servidor o error de conectividad de cliente
            Else

                fe_aprobada = "No"
                genero_transaccion = "No"
                genero_fe = "No"

'                error_fe = wsfev1.ErrorDesc
'                MsgBox wsfev1.ErrorDesc & Chr(13) + "No se pudo generar el comprobante en AFIP", vbInformation, "ATENCION"
                EnviarMensaje wsfev1.ErrorDesc & Chr(13) + "No se pudo generar el comprobante en AFIP"
                GoTo captura

            End If
    End If

    ' Si la Factura es por Sistema
     If pv_electronico = "No" And (tipo_impresora = "Normal" Or tipo_impresora = "Ventana" Or tipo_impresora = "Sin impresion") Then  'And Principal.fe_regimen = "No"
         Impresion_Factura
     End If
                                                                             
    ' Impresion con controlador fiscal
    ' Cambio codigo Impresora fiscal con seleccion de PV
    If pv_electronico = "No" And tipo_impresora = "Fiscal" Then   'And Principal.fe_regimen = "No" ' And mod_pv = "No"
        
        ' Impresoras Hasar 1ra Generacion
        If Principal.codigo_modelo_imp_fiscal_FB < 36 Then
            Impresion_Factura_Hasar

            If Principal.Comp_Fiscal_abierto = "Si" And Principal.Error_Fiscal = "Si" Then
                GoTo captura:
            End If
                    
        ' Impresoras Hasar 2da Generacion
        Else
                        
            Imprime_CF_Hasar_2da_Gen_FACT
                    
        End If
                    
        ' Por Controlador Fiscal FA / FB Epson
        ' Cambio codigo Impresora fiscal con seleccion de PV
        If pv_electronico = "No" And tipo_impresora = "Fiscal" And (Principal.marca_imp_fiscal_FA = "Epson" Or Principal.marca_imp_fiscal_FB = "Epson") Then  ' And mod_pv = "No"
            ' Impresoras Epson 1ra Generacion
            If Principal.codigo_modelo_imp_fiscal_FA < 10 Then
            
                Imprime_CF_Epson_Fact
                If respuesta_cf_epson = False Then
                    GoTo captura:
                End If
            
            ' Impresora EPSON 2da Generacion
            Else
            
                Imprime_CF_Epson_2da_Gen_FACT
            
            End If
              
        End If
                                       
    End If
        
     ' FE con CAEA
    If fe_regimen_tipo = "CAEA" Then
                
        If Emitir_FE_CAEA(id_cuentacliente_fe) = "No" Then
'            MsgBox "No esta autorizado CAEA actualmente para el periodo utilizado, debe solicitarlo previamente", vbExclamation, "ATENCION"
            EnviarMensaje "No esta autorizado CAEA actualmente para el periodo utilizado, debe solicitarlo previamente"
            
            GoTo captura
        End If
                    
        ' Cierro Transaccion antes por si la factura se imprime directo en impresora
        If conn.State = 1 Then
            conn.CommitTrans
            genero_transaccion = "Si"
            conn.Close
        End If
        
        ' Llamo a procedimiento de impresion de FE
        Llamada_Impresion_FE TipoFactura
    End If
        
    form_espera.ProgressBar.Value = 100
        
    CtaCteCliente.Visualiza = "No"
                                       
    ' Cierro Transaccion
    If conn.State = 1 Then
        conn.CommitTrans
        conn.Close
    End If
                                                                                                               
    ' Programa de descuentos y voucher - Impresion
    If Principal.mod_pd = "Si" And Principal.activ_pd = "Si" Then
        Impresion_Voucher_PD "Completa", "Configuracion", , CDbl(ImporteTotal), "TPV", contador, CDbl(Codigo_Cliente), CStr(tpv_mail_ocasional)
    End If
                                                                                                               
    ' Guardo Costo de venta total del comprobante
'    Guardar_Total_Costo_Comprobante_Temporal (contador)
                                                                                                               
    ' Descargo formulario de espera
    Unload form_espera
    
    ' Mensaje al usr de generacion de comprobante
    If Principal.tpv_saltea_mje_generacion_comp = "No" Then
        MsgBox "Se gener el comprobante " & TipoFactura & " - " & NroComp & " ", vbInformation, "ATENCION"
    Else
        EnviarMensaje "Se gener el comprobante " & TipoFactura & " - " & NroComp & " "
    End If
                                        
'    conn.Close
        
    cambio_vendedor = "No"
    cambio_vendedor_asistente = "No"
    cambio_pv = "No"
       
    'Vuelvo a cero los TXT
    importe_ctacte = 0
    importe_cobrado_efectivo = 0
    tipo_doc_cliente_ocasional = ""
    nro_doc_cliente_ocasional = ""
                
    ''''''''''''''''''''''''''''''''''''
    'VISUALIZA ASIENTO CONTABLE'
    ''''''''''''''''''''''''''''
            
    If Principal.activ_contabilidad = "Si" And Principal.conta_pv = "Si" Then
        Balancea_asiento (contador)
    End If
    
    ''''''''''''''''''''''''''''''''''
                
'On Error GoTo captura_final
                
    If Comprobante_Pedido = "No" Then
    
        Elimina_Temporal
        
        Unload Me
        
        TPV.Show
        
        ' Llamo a inicial para poner todos los valores por defecto
        Inicial
        
        ' Calculo totales para refrescar la grilla
'        CalculoTotales
        
        ' Foco a busqueda para empezar con la siguiente factura
        Busqueda.SetFocus
    
    End If
    
    If Comprobante_Pedido = "Si" Then
    
        Elimina_Temporal
        
        Lista_Comp_Fact.codigo_cliente_actual = ""
        Lista_Comp_Fact.Inicial
        
        Unload Me
        
    End If
       
    If Comprobante_Pedido = "Si PED Avanzado" Then
    
        Elimina_Temporal
        
        Pedido_Avanzado.codigo_cliente_actual = ""
        Pedido_Avanzado.Inicial
        
        Unload Me
        
    End If
    

       
Exit Sub
captura:
        
      datos_de_cheque = ""
        
      If Principal.Error_Fiscal = "Si" Then
    
          Call Principal.Guardar_Error("Error fiscal " & Principal.Detalle_Error_Fiscal, Me.Caption, Err.Number)
        
      Else
                      
          If error_fiscal_ejecutado <> "Si" And Principal.Comp_Fiscal_abierto = "Si" Then
              Principal.HASAR1.CancelarComprobanteFiscal
          End If
          
            ' Factura electronica
            If pv_electronico = "Si" Then
                
                If fe_regimen_tipo = "CAE" Then
'                    If wsfev1.errorCode = -1 Then
'
'                    Else
'                        Call Principal.Guardar_Error("SE PRODUJO UN ERROR AL GENERAR LA FACTURA ELECTRNICA, VERIFICAR EN ADMINISTRACIN DE COMPROBANTES ELECTRONICOS " & Err.Description & wsfev1.ErrorDesc, Me.Caption, Err.Number)
'                    End If
                
                    If conn.State = 1 Then
                        If fe_aprobada = "Si" Then
                            If genero_transaccion = "No" Then
                                conn.CommitTrans
                                Guarda_Cod_Barra_AFIP_Error_Factura CStr(tipo_doc)
                                Logger "Error cuando por fallo no hace rollback y no guarda el comprobante. Valor CAE Actual = " & CAE_actual_fe & ""
                            End If
    
                                If TipoFactura = "FA" Or TipoFactura = "FM" Then
                                    Reimpresion_Factura_FA_FE contador, "No"
                                End If
                                If TipoFactura = "FB" Or TipoFactura = "FC" Then
                                    Reimpresion_Factura_FB_FE contador, "No"
                                End If
                        Else
                            conn.RollbackTrans
                        End If
                        conn.Close
                    Else
                    
                        If fe_aprobada = "Si" Then
                            If TipoFactura = "FA" Or TipoFactura = "FM" Then
                                Reimpresion_Factura_FA_FE contador, "No"
                            End If
                            If TipoFactura = "FB" Or TipoFactura = "FC" Then
                                Reimpresion_Factura_FB_FE contador, "No"
                            End If
                        End If
                    
                    End If
                
                ' CAEA
                Else
                
                    conn.RollbackTrans
                    conn.Close
                
                End If
                
                ' Descargo formulario de espera
                Unload form_espera
                                
                ' Factura de credito electronica
                factura_credito = ""
                                
                ' Habilito boton Generar y Cancelar_Boton
                Aceptar.Enabled = True
                Cancelar_Boton.Enabled = True
                Deshabilita_Guardar_F12 = "No"

                If fe_aprobada = "Si" Then
                    ' Si se produce un error con regimen de factura electronica genero la factura igualmente ya que fue generada en AFIP
                    EnviarMensaje "En caso que el comprobante haya sido generado en la AFIP y en el sistema puede reimprimirlo luego"

'                    MsgBox "En caso que el comprobante haya sido generado en la AFIP y en el sistema puede reimprimirlo luego", vbInformation, "ATENCION"
                    Unload Me
                End If
                
                genero_fe = ""
                                
                Exit Sub
            
            Else
                          
                ' Cambio codigo Impresora fiscal con seleccion de PV
                If tipo_impresora = "Fiscal" And Principal.marca_imp_fiscal_FA = "Epson" And respuesta_cf = False Then  ' And mod_pv = "No"
                
                    Call Principal.Guardar_Error("Error en controlador fiscal: " & error_fiscal_epson & " - " & Err.Description & " / Mje error: " & control_error, Me.Caption, Err.Number)
                
                    Mostrar_Mensaje_Epson_2da_Generacion CStr(error_fiscal_epson)

                Else
                
                    Call Principal.Guardar_Error(Err.Description & " / Mje error: " & control_error, Me.Caption, Err.Number)
                
                End If
            
                ' Cancelo documento Impresora EPSON 2da Generacion
                If Principal.marca_imp_fiscal_FA = "Epson" Then
                    If Principal.codigo_modelo_imp_fiscal_FA >= 10 Then
                        error_fiscal_epson = Cancelar()
                        error_fiscal_epson = Desconectar()
                    End If
                End If
            
            End If
            
      End If
      
      If conn.State = 1 Then
          conn.RollbackTrans
          conn.Close
      End If

    ' Descargo formulario de espera
    Unload form_espera
   
    ' Reinicio variables de error fiscal
    Principal.Comp_Fiscal_abierto = "No"
    Principal.Error_Fiscal = "No"

End If

'captura_final:
'Unload Me
'TPV.Show
'Inicial


End Sub
FIN_PROCEDIMIENTO
