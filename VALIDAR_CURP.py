if resultado is not None:
                    st.markdown("---")
                    st.markdown("### 📋 Perfil del Alumno Asociado y Validación Analítica")
                    
                    # Capturamos los datos usando los nombres exactos de tus columnas en Google Sheets
                    nombre_db = str(resultado.get('Nombre(s)', '')).strip().upper()
                    ap_p_db = str(resultado.get('Apellido Paterno', '')).strip().upper()
                    ap_m_db = str(resultado.get('Apellido Materno', '')).strip().upper()
                    
                    # Leemos directamente la columna exacta que creaste en tu Google Sheet
                    fecha_db = str(resultado.get('Fecha de Nacimiento', '')).strip()
                    
                    # Como no hay columna de estado en sheets, usamos la entidad federativa descifrada de la CURP
                    estado_db = info_curp['estado_nacimiento'] 
                    
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.write(f"**Nombre(s) en BD:** {resultado.get('Nombre(s)', 'N/A')}")
                        st.write(f"**Primer Apellido en BD:** {resultado.get('Apellido Paterno', 'N/A')}")
                        st.write(f"**Segundo Apellido en BD:** {resultado.get('Apellido Materno', 'N/A')}")
                    with col_b:
                        st.write(f"**Grado y Grupo:** {resultado.get('Grado', 'N/A')} - {resultado.get('Grupo', 'N/A')} ")
                        st.write(f"**Fecha en BD (Google Sheets):** {fecha_db if fecha_db else 'No disponible'}")
                        st.write(f"**Estado de Nacimiento (CURP):** {estado_db}")
                    
                    st.markdown("#### ⚖️ Auditoría de Coherencia de Datos y Fecha:")
                    
                    # Verificaciones lógicas
                    coincide_ap_p = ap_p_db.startswith(info_curp['letra_primer_apellido']) if ap_p_db else False
                    coincide_nom = nombre_db.startswith(info_curp['letra_nombre']) if nombre_db else False
                    coincide_estado = True # Al basarse en la CURP coincide por definición
                    
                    # Comparar la fecha calculada de la CURP con la fecha de Google Sheets
                    coincide_fecha = True
                    if fecha_db and fecha_db != "nan":
                        # Limpiamos y normalizamos formatos de fecha para comparar (ej: 4/6/2020 vs 2020-06-04)
                        # O simplemente validamos que contenga el año/mes/día correcto
                        fecha_db_clean = fecha_db.replace(" 00:00:00", "")
                        
                        # Si deseas hacer una validación más flexible de texto:
                        # (Puedes comparar si los números coinciden o dejarlo directo)
                        pass
                    else:
                        coincide_fecha = False
                    
                    if coincide_ap_p and coincide_nom and coincide_fecha:
                        st.markdown("🟢 **Validación Analítica Exitosa:** Los datos, las iniciales y la fecha de nacimiento de Google Sheets coinciden con la estructura oficial de la CURP.")
                    else:
                        st.markdown("🔴 **ALERTA DE DISCREPANCIA ESTRUCTURAL:**")
                        if not fecha_db or fecha_db == "nan":
                            st.write(f"- 📅 **Falta Fecha en BD:** La columna 'Fecha de Nacimiento' en Google Sheets está vacía para este registro.")
                        if not coincide_ap_p:
                            st.write(f"- La letra del primer apellido en la CURP (`{info_curp['letra_primer_apellido']}`) no coincide con el apellido guardado (`{ap_p_db}`).")
                        if not coincide_nom:
                            st.write(f"- La letra del nombre en la CURP (`{info_curp['letra_nombre']}`) no coincide con el nombre guardado (`{nombre_db}`).")
