# Fix bugs VB6 módulo BOM (administraNET)

>

---

# Objetivo

Corregir 3 bugs del módulo de artículos ensamblados (BOM) aplicando **cambios mínimos y localizados** en la sección de código de 4 formularios. El resultado debe abrir y compilar en el IDE de VB6 sin errores de carga.

# BUG A — Borrado físico de artículo sin validar referencias BOM

**Archivos:** `AltaArticulo.frm` y `ABMArticulo_seleccion.frm`, dentro de `Private Sub Eliminar()`.
En ambos existe **exactamente una vez** este bloque (validan solo `stock`, luego borran):

**Ancla a reemplazar (idéntica en los dos archivos):**

```vb
            Else
            
                ' Elimino el articulo
```

**Reemplazar por:**

```vb
            Else
            
                'Validacion BOM: no eliminar si es insumo de formulas de ensamblados
                Dim rs_bom As New ADODB.Recordset
                
                rs_bom.Open "SELECT en_abm_formula.id_en_abm FROM en_abm_formula " & _
                            "INNER JOIN en_abm ON (en_abm.id_en_abm = en_abm_formula.id_en_abm) " & _
                            "WHERE en_abm_formula.id_articulo = " & DataABMArt.Recordset.Fields!IDArt & " " & _
                            "AND en_abm_formula.anulado = 'No' AND en_abm.anulado = 'No'", conn, adOpenDynamic, adLockReadOnly
                
                If rs_bom.RecordCount > 0 Then
                    MsgBox "No se puede eliminar el articulo porque es insumo de la formula de " & rs_bom.RecordCount & " articulo(s) ensamblado(s)." & vbCrLf & _
                           "Debe quitarlo de las formulas o anular los ensamblados antes de eliminarlo", vbCritical + vbOKOnly, "ATENCION"
                    rs_bom.Close
                    conn.Close
                    Exit Sub
                End If
                
                rs_bom.Close
                
                'Validacion BOM: no eliminar si es el articulo generado por un ensamblado activo
                rs_bom.Open "SELECT en_abm.id_en_abm FROM en_abm " & _
                            "INNER JOIN articulo ON (articulo.id_en_abm = en_abm.id_en_abm) " & _
                            "WHERE articulo.IDArt = " & DataABMArt.Recordset.Fields!IDArt & " " & _
                            "AND en_abm.anulado = 'No'", conn, adOpenDynamic, adLockReadOnly
                
                If rs_bom.RecordCount > 0 Then
                    MsgBox "No se puede eliminar el articulo porque pertenece a un articulo ensamblado activo." & vbCrLf & _
                           "Debe anular el articulo ensamblado antes de eliminarlo", vbCritical + vbOKOnly, "ATENCION"
                    rs_bom.Close
                    conn.Close
                    Exit Sub
                End If
                
                rs_bom.Close
                
                ' Elimino el articulo
```

---



# BUG B — Alta en dos fases (encabezado en_abm queda huérfano)



### B.1 `En_CargaAbm.frm` — capturar el id generado (rama alta manual)

**Ancla:**

```vb
                rs_EnArt.Fields!anulado = anulado.Text
    
                rs_EnArt.Update
                rs_EnArt.Close
                
                If conn.State = 1 Then
                    conn.CommitTrans
                    conn.Close
                End If
```

**Reemplazar por:**

```vb
                rs_EnArt.Fields!anulado = anulado.Text
    
                rs_EnArt.Update
                
                'Guardo el id generado para encadenar la definicion de formula
                Dim nuevoIdEnAbm As Double
                nuevoIdEnAbm = rs_EnArt.Fields!id_en_abm
                
                rs_EnArt.Close
                
                If conn.State = 1 Then
                    conn.CommitTrans
                    conn.Close
                End If
```



### B.2 `En_CargaAbm.frm` — encadenar la definición tras el alta

**Ancla:**

```vb
                ' Frame de Existencia de Registros
                If En_abm.GridArtEn.BOF = True Then
                    En_abm.FrameTitulo.Visible = True
                Else
                    En_abm.FrameTitulo.Visible = False
                End If
                
                Unload Me
                
            Else
                '''''''''''''''''''''''''''''''''''''''''''''
                'Se selecciono un articulo desde abmArticulo'
                '''''''''''''''''''''''''''''''''''''''''''''
                conn.CursorLocation = adUseClient
                conn.BeginTrans
```

**Reemplazar por:**

```vb
                ' Frame de Existencia de Registros
                If En_abm.GridArtEn.BOF = True Then
                    En_abm.FrameTitulo.Visible = True
                Else
                    En_abm.FrameTitulo.Visible = False
                End If
                
                'Encadeno la definicion de formula para que el alta no quede
                'incompleta (en_abm sin articulo asociado en la tabla articulo)
                'Mismo patron modeless que usa En_abm en keyAgrDef
                If anulado.Text = "No" Then
                    En_abmDef.IDArt = 0
                    En_abmDef.lblArtEn = Nombre.Text
                    En_abmDef.Id_articuloEn = nuevoIdEnAbm
                    En_abmDef.modificacion = "No"
                    En_abmDef.Show
                End If
                
                Unload Me
                
            Else
                '''''''''''''''''''''''''''''''''''''''''''''
                'Se selecciono un articulo desde abmArticulo'
                '''''''''''''''''''''''''''''''''''''''''''''
                If ExisteNombreEnAbm(Nombre.Text, 0) Then
                    MsgBox "El Nombre del articulo ensamblado ya existe"
                    Nombre.SetFocus
                    conn.Close
                    Exit Sub
                End If
                
                conn.CursorLocation = adUseClient
                conn.BeginTrans
```



### B.3 `En_abmDef.frm` — compensar al cancelar un alta incompleta

**Nota de tipos:** `IDArt` es `Public ... As String`; comparar con `Val(IDArt & "")` para evitar *Type Mismatch*.
**Ancla (Cancelar_Click completo):**

```vb
Private Sub Cancelar_Click()
    If MsgBox("¿Desea cancelar la generación de la definición de formula?", vbYesNo + vbQuestion, "ATENCION") = vbYes Then
        ' Elimina tabla Temporal
        Elimina_Temporal
        Unload Me
    End If
End Sub
```

**Reemplazar por** (conservá el `¿`/acentos SOLO en el literal ya existente del `MsgBox`; el código nuevo es ASCII):

```vb
Private Sub Cancelar_Click()
On Error GoTo ManejoError

    If MsgBox("¿Desea cancelar la generación de la definición de formula?", vbYesNo + vbQuestion, "ATENCION") = vbYes Then
        
        'Compensacion: en un alta, si el ensamblado quedo sin articulo asociado
        'ofrezco eliminar el encabezado incompleto para no dejar huerfanos en en_abm
        'IDArt es Public As String: se compara con Val para evitar Type Mismatch
        If modificacion = "No" And Val(IDArt & "") = 0 And Id_articuloEn > 0 Then
            
            If MsgBox("El articulo ensamblado quedara sin formula ni articulo asociado y no podra utilizarse." & vbCrLf & _
                      "Desea eliminar el articulo ensamblado incompleto?", vbYesNo + vbQuestion, "ATENCION") = vbYes Then
                
                If conn.State = 1 Then
                    conn.Close
                End If
                
                conn.ConnectionString = IngresoUsuario.Conex
                conn.CursorLocation = adUseClient
                conn.Open
                
                'Solo se elimina si sigue sin articulo asociado y sin formula guardada
                conn.Execute "DELETE FROM en_abm WHERE id_en_abm = " & Id_articuloEn & " " & _
                             "AND NOT EXISTS (SELECT 1 FROM articulo WHERE articulo.id_en_abm = " & Id_articuloEn & ") " & _
                             "AND NOT EXISTS (SELECT 1 FROM en_abm_formula WHERE en_abm_formula.id_en_abm = " & Id_articuloEn & ")"
                
                conn.Close
                
                En_abm.Consulta_Busqueda
                
            End If
            
        End If
        
        ' Elimina tabla Temporal
        Elimina_Temporal
        Unload Me
    End If

Exit Sub
ManejoError:
    Call Principal.Guardar_Error(Err.Description, Me.Caption, Err.Number)
    
    If conn.State = 1 Then
        conn.Close
    End If
End Sub
```

---



# BUG C — Validación de duplicados unificada (`En_CargaAbm.frm`)



### C.1 Reemplazar la validación de la rama de alta manual

**Ancla:**

```vb
            If DeArtaArtE = "No" Then
            
                 rs_EnArt.Open "SELECT * FROM en_abm WHERE Nombre_en_abm = '" & Nombre.Text & "' AND anulado='No'", conn, adOpenDynamic, adLockOptimistic
                
                If rs_EnArt.RecordCount > 0 Then
                    MsgBox "El Nombre del artículo ensamblado ya existe"
                    Nombre.SetFocus
                    rs_EnArt.Close
                    conn.Close
                    Exit Sub
                End If
                
                rs_EnArt.Close
                
```

**Reemplazar por:**

```vb
            If DeArtaArtE = "No" Then
            
                If ExisteNombreEnAbm(Nombre.Text, 0) Then
                    MsgBox "El Nombre del articulo ensamblado ya existe"
                    Nombre.SetFocus
                    conn.Close
                    Exit Sub
                End If
                
```



### C.2 Validar duplicado también en la rama Modificar

**Ancla:**

```vb
            'Modificar
            conn.CursorLocation = adUseClient
            conn.BeginTrans
```

**Reemplazar por:**

```vb
            'Modificar
            If ExisteNombreEnAbm(Nombre.Text, id_en_abm) Then
                MsgBox "El Nombre del articulo ensamblado ya existe"
                Nombre.SetFocus
                conn.Close
                Exit Sub
            End If
            
            conn.CursorLocation = adUseClient
            conn.BeginTrans
```



### C.3 Agregar la función auxiliar Private (antes de `Cancelar_Click`)

**Ancla:**

```vb
Private Sub Cancelar_Click()
    Unload Me
    En_abm.modificacion = "No"
End Sub
```

**Reemplazar por:**

```vb
Private Function ExisteNombreEnAbm(ByVal nombreVal As String, ByVal idExcluir As Double) As Boolean
'Valida que no exista otro articulo ensamblado activo con el mismo nombre
'Requiere conn abierta. Compara con TRIM y escapa comillas simples
On Error GoTo ManejoError

    Dim rs_dup As New ADODB.Recordset
    Dim nombreSql As String
    
    nombreSql = Replace(Trim(nombreVal), "'", "''")
    
    rs_dup.Open "SELECT id_en_abm FROM en_abm WHERE TRIM(Nombre_en_abm) = '" & nombreSql & "' " & _
                "AND anulado = 'No' AND id_en_abm <> " & idExcluir & " ", conn, adOpenDynamic, adLockReadOnly
    
    ExisteNombreEnAbm = (rs_dup.RecordCount > 0)
    
    rs_dup.Close

Exit Function
ManejoError:
    Call Principal.Guardar_Error(Err.Description, Me.Caption, Err.Number)
End Function

Private Sub Cancelar_Click()
    Unload Me
    En_abm.modificacion = "No"
End Sub
```

---



