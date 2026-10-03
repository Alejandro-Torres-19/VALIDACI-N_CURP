import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import re
import unicodedata
import datetime
from rapidfuzz import process, fuzz

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Validador y Analizador CURP - Escolar", 
    page_icon="🎓", 
    layout="centered"
)

# Estilos CSS personalizados para un diseño uniforme, elegante y sin recortes
st.markdown("""
    <style>
        .main-title { font-size: 2.2rem; font-weight: 700; color: #1E3A8A; text-align: center; margin-bottom: 0px; }
        .sub-title { font-size: 1.1rem; color: #4B5563; text-align: center; margin-bottom: 25px; }
        
        /* Tarjetas de información uniformes */
        .info-card {
            background-color: #1E293B;
            border: 1px solid #334155;
            padding: 15px 18px;
            border-radius: 10px;
            margin-bottom: 12px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .info-label {
            font-size: 0.85rem;
            color: #94A3B8;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
            font-weight: 600;
        }
        .info-value {
            font-size: 1.2rem;
            color: #F8FAFC;
            font-weight: 700;
            word-break: break-word;
            line-height: 1.3;
        }
        .success-box { background-color: #ECFDF5; padding: 15px; border-radius: 10px; border: 1px solid #A7F3D0; color: #065F46; }
        .error-box { background-color: #FEF2F2; padding: 15px; border-radius: 10px; border: 1px solid #FECACA; color: #991B1B; }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='main-title'>🎓 Validador y Analizador de CURP</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-title'>Sistema de control escolar - Versión Alpha (Evaluación Directiva)</p>", unsafe_allow_html=True)

# Botón superior discreto para actualizar datos
col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
with col_btn2:
    if st.button("🔄 Actualizar Base de Datos (Google Sheets)", use_container_width=True):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.success("¡Datos actualizados correctamente!")

st.write("")

# --- DICCIONARIO OFICIAL DE CÓDIGOS DE ENTIDAD (CURP) ---
CODIGOS_ESTADOS = {
    "AS": "AGUASCALIENTES", "BC": "BAJA CALIFORNIA", "BS": "BAJA CALIFORNIA SUR",
    "CC": "CAMPECHE", "CL": "COAHUILA", "CM": "COLIMA", "CS": "CHIAPAS",
    "CH": "CHIHUAHUA", "DF": "CIUDAD DE MÉXICO", "DG": "DURANGO", "GT": "GUANAJUATO",
    "GR": "GUERRERO", "HG": "HIDALGO", "JC": "JALISCO", "MC": "ESTADO DE MÉXICO",
    "MN": "MICHOACÁN", "MS": "MORELOS", "NT": "NAYARIT", "NL": "NUEVO LEÓN",
    "OC": "OAXACA", "PL": "PUEBLA", "QT": "QUERÉTARO", "QR": "QUINTANA ROO",
    "SL": "SAN LUIS POTOSÍ", "SP": "SINALOA", "SR": "SONORA", "TC": "TABASCO",
    "TS": "TAMAULIPAS", "TL": "TLAXCALA", "VZ": "VERACRUZ", "YN": "YUCATÁN", "ZS": "ZACATECAS",
    "NE": "NACIDO EN EL EXTRANJERO"
}

# --- CONEXIÓN A GOOGLE SHEETS ---
@st.cache_resource
def conectar_google_sheets():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    credentials_dict = dict(st.secrets["gcp_service_account"])
    pk = credentials_dict.get("private_key", "")
    try:
        pk = pk.encode().decode('unicode-escape')
    except Exception:
        pk = pk.replace("\\n", "\n")
    credentials_dict["private_key"] = pk
    
    creds = Credentials.from_service_account_info(credentials_dict, scopes=scopes)
    client = gspread.authorize(creds)
    spreadsheet = client.open("prueba validacion curp") 
    return spreadsheet.get_worksheet(0)

@st.cache_data(ttl=600)
def cargar_datos():
    try:
        ws = conectar_google_sheets()
        data = ws.get_all_values()
        if len(data) > 1:
            headers = [h.strip() for h in data[0]]
            rows = []
            for row in data[1:]:
                if len(row) < len(headers):
                    row = row + [''] * (len(headers) - len(row))
                else:
                    row = row[:len(headers)]
                rows.append(row)
            df = pd.DataFrame(rows, columns=headers)
            df = df.loc[:, df.columns != ''] 
            return df
        else:
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {e}")
        return pd.DataFrame()

df_alumnos = cargar_datos()

# --- FUNCIONES AUXILIARES DE MATEMÁTICA Y CURP ---
def validar_digito_verificador_curp(curp: str) -> bool:
    curp = curp.strip().upper()
    if len(curp) != 18:
        return False
    patron_estricto = re.compile(r'^[A-Z]{4}\d{6}[HM][A-Z]{5}[0-9A-Z]\d$')
    if not patron_estricto.match(curp):
        return False
        
    diccionario = "0123456789ABCDEFGHIJKLMNÑOPQRSTUVWXYZ"
    suma = 0
    for i in range(17):
        caracter = curp[i]
        valor = diccionario.find(caracter)
        if valor == -1:
            return False
        suma += valor * (18 - i)
    
    digito_esperado = (10 - (suma % 10)) % 10
    digito_real = int(curp[17]) if curp[17].isdigit() else diccionario.find(curp[17])
    return digito_esperado == digito_real

def decodificar_curp(curp):
    curp = curp.strip().upper()
    if len(curp) != 18:
        return None
    yy, mm, dd = curp[4:6], curp[6:8], curp[8:10]
    siglo = "20" if int(yy) <= 30 else "19"
    return {
        "letra_primer_apellido": curp[0],
        "vocal_primer_apellido": curp[1],
        "letra_segundo_apellido": curp[2],
        "letra_nombre": curp[3],
        "fecha_nacimiento": f"{siglo}{yy}-{mm}-{dd}",
        "genero": "Hombre" if curp[10] == "H" else ("Mujer" if curp[10] == "M" else "Desconocido"),
        "codigo_estado": curp[11:13],
        "estado_nacimiento": CODIGOS_ESTADOS.get(curp[11:13], "Desconocido")
    }

def normalizar_texto(texto):
    if not isinstance(texto, str):
        return ""
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join([c for c in texto if not unicodedata.combining(c)])
    return texto.upper().strip()

def obtener_primera_vocal_interna(palabra):
    for letra in palabra[1:]:
        if letra in "AEIOU":
            return letra
    return 'X'

def calcular_prefijo_teorico(nombre, ap_paterno, ap_materno, fecha_nac, genero, entidad):
    p_pat = normalizar_texto(ap_paterno).split()[0] if ap_paterno else "X"
    p_mat = normalizar_texto(ap_materno).split()[0] if ap_materno else "X"
    p_nom = normalizar_texto(nombre).split()[0] if nombre else "X"
    
    c1 = p_pat[0] if len(p_pat) > 0 else "X"
    c2 = obtener_primera_vocal_interna(p_pat)
    c3 = p_mat[0] if len(p_mat) > 0 else "X"
    c4 = p_nom[0] if len(p_nom) > 0 else "X"
    
    try:
        partes_fecha = str(fecha_nac).split(' ')[0].split('-')
        if len(partes_fecha) == 3:
            aa = partes_fecha[0][2:]
            mm = partes_fecha[1]
            dd = partes_fecha[2]
            f_str = f"{aa}{mm}{dd}"
        else:
            f_str = "000000"
    except:
        f_str = "000000"
        
    g_str = "H" if "H" in str(genero).upper() else "M"
    
    estados_inverso = {v: k for k, v in CODIGOS_ESTADOS.items()}
    ent_limpia = normalizar_texto(entidad)
    ent_str = estados_inverso.get(ent_limpia, "NE")
    
    return f"{c1}{c2}{c3}{c4}{f_str}{g_str}{ent_str}"

# --- SELECCIÓN DE MODOS / PESTAÑAS PRINCIPALES (VERSIÓN ALPHA) ---
modo_app = st.radio(
    "Selecciona el Modo de Validación (Evaluación Directiva):",
    [
        "🔍 Modo A: Búsqueda y Validación por CURP", 
        "📝 Modo B: Auditoría por Datos Demográficos (Manual)", 
        "⚡ Modo C: Búsqueda Inteligente por Nombre",
        "📊 Modo D: Auditoría Masiva de CURPs",
        "🛡️ Modo E: Antifraude y Duplicados"
    ],
    horizontal=True
)

st.markdown("---")

# ==============================================================================
# MODO A: BÚSQUEDA Y VALIDACIÓN POR CURP DIRECTA
# ==============================================================================
if modo_app == "🔍 Modo A: Búsqueda y Validación por CURP":
    st.markdown("### 🔍 Ingresa la CURP del alumno")
    curp_input = st.text_input("", placeholder="Ej. CAHD140521HMCDRYA3", label_visibility="collapsed").strip().upper()

    patron_curp = re.compile(r'^[A-Z]{4}\d{6}[HM][A-Z]{5}[0-9A-Z]{2}$')

    if st.button("🚀 Ejecutar Validación por CURP", type="primary", use_container_width=True):
        if not curp_input:
            st.warning("⚠️ Por favor, introduce una CURP en el campo de texto.")
        else:
            if not patron_curp.match(curp_input):
                st.error("🔴 **CURP Inválida:** La estructura no cumple con los 18 caracteres oficiales exigidos por RENAPO.")
            else:
                es_matematicamente_valida = validar_digito_verificador_curp(curp_input)
                info_curp = decodificar_curp(curp_input)
                
                if df_alumnos.empty or 'CURP' not in df_alumnos.columns:
                    st.error("La base de datos de Google Sheets está vacía o no contiene la columna 'CURP'.")
                else:
                    lista_curps_db = df_alumnos['CURP'].astype(str).str.strip().str.upper().tolist()
                    match_exacto = df_alumnos[df_alumnos['CURP'].str.strip().str.upper() == curp_input]
                    
                    resultado = None
                    if not match_exacto.empty:
                        resultado = match_exacto.iloc[0]
                    else:
                        mejor_match, puntuacion, indice = process.extractOne(curp_input, lista_curps_db, scorer=fuzz.ratio)
                        if puntuacion >= 85:
                            resultado = df_alumnos.iloc[indice]
                    
                    if resultado is not None:
                        ap_p_db = str(resultado.get('Apellido Paterno', '')).strip().upper()
                        ap_m_db = str(resultado.get('Apellido Materno', '')).strip().upper()
                        nombre_db = str(resultado.get('Nombre(s)', '')).strip().upper()
                        grado_db = str(resultado.get('Grado', '')).strip()
                        grupo_db = str(resultado.get('Grupo', '')).strip()
                        cct_db = str(resultado.get('CCT', '')).strip()
                        fecha_db = str(resultado.get('Fecha de Nacimiento', '')).strip()
                        entidad_db = str(resultado.get('Entidad Nacimiento', '')).strip().upper()
                        
                        nombre_completo = f"{nombre_db} {ap_p_db} {ap_m_db}"
                        
                        fecha_mostrar = fecha_db
                        coincide_fecha = False
                        if fecha_db and fecha_db != "nan" and fecha_db != "":
                            try:
                                fecha_dt = pd.to_datetime(fecha_db, dayfirst=True, errors='coerce')
                                if pd.notna(fecha_dt):
                                    fecha_db_norm = fecha_dt.strftime('%Y-%m-%d')
                                    fecha_mostrar = fecha_db_norm
                                    coincide_fecha = (fecha_db_norm == info_curp['fecha_nacimiento'])
                                else:
                                    coincide_fecha = (fecha_db == info_curp['fecha_nacimiento'])
                            except Exception:
                                coincide_fecha = (fecha_db == info_curp['fecha_nacimiento'])

                        val_ap_p = ap_p_db.startswith(info_curp['letra_primer_apellido']) if ap_p_db else False
                        val_ap_m = ap_m_db.startswith(info_curp['letra_segundo_apellido']) if ap_m_db else False
                        val_nom = nombre_db.startswith(info_curp['letra_nombre']) if nombre_db else False
                        
                        errores = []
                        if not es_matematicamente_valida:
                            errores.append("⚠️ **Alerta Crítica:** El dígito verificador matemático de la CURP es falso (posible CURP inventada o alterada).")
                        if not coincide_fecha:
                            errores.append(f"Fecha en Sheets ({fecha_mostrar}) no coincide con la CURP ({info_curp['fecha_nacimiento']}).")
                        if not val_ap_p:
                            errores.append(f"La inicial del Apellido Paterno (`{info_curp['letra_primer_apellido']}`) no concuerda con `{ap_p_db}`.")
                        if not val_ap_m and ap_m_db:
                            errores.append(f"La inicial del Apellido Materno (`{info_curp['letra_segundo_apellido']}`) no concuerda con `{ap_m_db}`.")
                        if not val_nom:
                            errores.append(f"La inicial del Nombre (`{info_curp['letra_nombre']}`) no concuerda con `{nombre_db}`.")

                        st.write("")
                        tab1, tab2, tab3 = st.tabs(["👤 Perfil del Alumno", "🔍 Desglose CURP", "⚖️ Auditoría y Estado"])
                        
                        with tab1:
                            st.markdown("#### Información Registrada en Google Sheets")
                            st.markdown(f"""
                                <div class='info-card'>
                                    <div class='info-label'>Nombre Completo</div>
                                    <div class='info-value'>{nombre_completo}</div>
                                </div>
                            """, unsafe_allow_html=True)
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown(f"""
                                    <div class='info-card'>
                                        <div class='info-label'>Grado y Grupo</div>
                                        <div class='info-value'>{grado_db}° - '{grupo_db}'</div>
                                    </div>
                                """, unsafe_allow_html=True)
                            with col2:
                                st.markdown(f"""
                                    <div class='info-card'>
                                        <div class='info-label'>CCT Escuela</div>
                                        <div class='info-value'>{cct_db if cct_db else 'No asignado'}</div>
                                    </div>
                                """, unsafe_allow_html=True)
                                
                            col3, col4 = st.columns(2)
                            with col3:
                                st.markdown(f"""
                                    <div class='info-card'>
                                        <div class='info-label'>Fecha de Nacimiento</div>
                                        <div class='info-value'>{fecha_mostrar}</div>
                                    </div>
                                """, unsafe_allow_html=True)
                            with col4:
                                st.markdown(f"""
                                    <div class='info-card'>
                                        <div class='info-label'>Entidad (Sheets)</div>
                                        <div class='info-value'>{entidad_db if entidad_db else 'No especificada'}</div>
                                    </div>
                                """, unsafe_allow_html=True)

                        with tab2:
                            st.markdown("#### Análisis Cifrado de los Dígitos de la CURP")
                            c_a, c_b = st.columns(2)
                            with c_a:
                                st.info(f"📌 **1er Apellido:** Letra `{info_curp['letra_primer_apellido']}` | Vocal `{info_curp['vocal_primer_apellido']}`")
                                st.info(f"📌 **2do Apellido:** Letra `{info_curp['letra_segundo_apellido']}`")
                                st.info(f"📌 **Nombre:** Letra `{info_curp['letra_nombre']}`")
                            with c_b:
                                st.success(f"📅 **Fecha Cifrada:** {info_curp['fecha_nacimiento']}")
                                st.success(f"🚻 **Género:** {info_curp['genero']}")
                                st.success(f"📍 **Entidad:** {info_curp['estado_nacimiento']} ({info_curp['codigo_estado']})")
                            
                            if es_matematicamente_valida:
                                st.success("🔒 **Verificación Oficial:** El dígito verificador matemático es **CORRECTO**.")
                            else:
                                st.error("🚨 **Verificación Oficial:** El dígito verificador matemático es **INCORRECTO**.")

                        with tab3:
                            st.markdown("#### Dictamen General del Alumno")
                            if not errores:
                                st.markdown("""
                                    <div class='success-box'>
                                        <h3>🟢 Validación Exitosa</h3>
                                        <p>Todos los datos concuerdan perfectamente y la estructura matemática es correcta.</p>
                                    </div>
                                """, unsafe_allow_html=True)
                            else:
                                st.markdown("""
                                    <div class='error-box'>
                                        <h3>🔴 Alerta de Discrepancia Detectada</h3>
                                        <p>Se encontraron inconsistencias en el registro:</p>
                                    </div>
                                """, unsafe_allow_html=True)
                                for err in errores:
                                    st.warning(f"• {err}")
                    else:
                        st.error("🔴 **Sin Registro Asociado:** La CURP es estructuralmente correcta, pero no se encontró ningún alumno coincidente en la base de datos.")

# ==============================================================================
# MODO B: AUDITORÍA POR DATOS DEMOGRÁFICOS (NOMBRE Y APELLIDOS MANUAL)
# ==============================================================================
elif modo_app == "📝 Modo B: Auditoría por Datos Demográficos (Manual)":
    st.markdown("### 📝 Auditoría por Datos Demográficos y Generación Teórica")
    st.write("Introduce los datos personales para calcular y contrastar automáticamente con la CURP registrada en la hoja de datos.")

    with st.form("form_auditoria"):
        col_n1, col_n2 = st.columns(2)
        with col_n1:
            input_nombre = st.text_input("Nombre(s):", placeholder="Ej. ALEJANDRO")
            input_ap_pat = st.text_input("Apellido Paterno:", placeholder="Ej. TORRES")
        with col_n2:
            input_ap_mat = st.text_input("Apellido Materno:", placeholder="Ej. REYES")
            input_genero = st.selectbox("Género:", ["HOMBRE (H)", "MUJER (M)"])
            
        st.markdown("##### Fecha de Nacimiento (Día / Mes / Año)")
        f_col1, f_col2, f_col3 = st.columns(3)
        with f_col1:
            input_dia = st.number_input("Día", min_value=1, max_value=31, value=1)
        with f_col2:
            input_mes = st.number_input("Mes", min_value=1, max_value=12, value=1)
        with f_col3:
            input_anio = st.number_input("Año", min_value=2006, max_value=2026, value=2010)
            
        input_entidad = st.selectbox("Entidad de Nacimiento:", list(CODIGOS_ESTADOS.values()))
            
        btn_auditar = st.form_submit_button("⚖️ Comprobar Coherencia y Alarma CURP", type="primary")

    if btn_auditar:
        if not input_nombre or not input_ap_pat:
            st.warning("⚠️ Por favor, llena al menos el Nombre y el Apellido Paterno.")
        else:
            input_fecha = datetime.date(int(input_anio), int(input_mes), int(input_dia))
            
            genero_letra = "H" if "HOMBRE" in input_genero else "M"
            prefijo_calculado = calcular_prefijo_teorico(
                input_nombre, input_ap_pat, input_ap_mat, 
                input_fecha, genero_letra, input_entidad
            )
            
            st.info(f"⚙️ **Base Teórica Generada:** `{prefijo_calculado}XXXXXXXX` (Primeros 10-11 caracteres lógicos)")
            
            if df_alumnos.empty:
                st.error("La base de datos de Google Sheets está vacía.")
            else:
                coincidencias = df_alumnos[df_alumnos['Apellido Paterno'].astype(str).str.upper().str.contains(input_ap_pat.upper(), na=False)]
                
                if not coincidencias.empty:
                    st.success(f"Se encontraron {len(coincidencias)} registros con similitud de apellido en Google Sheets:")
                    
                    for idx, row in coincidencias.iterrows():
                        curp_registrada = str(row.get('CURP', '')).strip().upper()
                        nombre_reg = row.get('Nombre(s)', '')
                        pat_reg = row.get('Apellido Paterno', '')
                        mat_reg = row.get('Apellido Materno', '')
                        
                        coincide_base = curp_registrada.startswith(prefijo_calculado[:10])
                        
                        st.markdown(f"""
                            <div class='info-card'>
                                <div class='info-label'>Alumno: {nombre_reg} {pat_reg} {mat_reg}</div>
                                <div class='info-value'>CURP en Base de Datos: <code>{curp_registrada}</code></div>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        if coincide_base:
                            st.success(f"🟢 **Coherencia Validada:** Los datos demográficos coinciden con la estructura de la CURP registrada.")
                        else:
                            st.error(f"🚨 **ALARMA DIRECTIVA:** Discrepancia detectada. Los datos personales ingresados no generan la misma base de CURP guardada en el sistema. **Requiere revisión manual en gob.mx**.")
                else:
                    st.warning("No se encontró ningún registro en Google Sheets con ese Apellido Paterno para contrastar.")

# ==============================================================================
# MODO C: BÚSQUEDA INTELIGENTE Y DESAMBIGUACIÓN AUTOMÁTICA (AMIGABLE)
# ==============================================================================
elif modo_app == "⚡ Modo C: Búsqueda Inteligente por Nombre":
    st.markdown("### ⚡ Búsqueda Inteligente por Nombre o Apellido")
    st.write("Escribe el nombre o apellido del alumno. El sistema autocompletará los datos y validará su CURP al instante sin necesidad de ingresarlos manualmente.")

    termino_busqueda = st.text_input("Buscar alumno en Google Sheets:", placeholder="Ej. Alejandro Torres o solo Torres")

    if termino_busqueda:
        if df_alumnos.empty or 'CURP' not in df_alumnos.columns:
            st.error("La base de datos de Google Sheets está vacía o no contiene la columna 'CURP'.")
        else:
            mask = (
                df_alumnos['Nombre(s)'].astype(str).str.contains(termino_busqueda, case=False, na=False) |
                df_alumnos['Apellido Paterno'].astype(str).str.contains(termino_busqueda, case=False, na=False) |
                df_alumnos['Apellido Materno'].astype(str).str.contains(termino_busqueda, case=False, na=False)
            )
            alumnos_encontrados = df_alumnos[mask]
            cantidad = len(alumnos_encontrados)
            
            if cantidad == 0:
                st.warning("⚠️ No se encontró ningún alumno con ese nombre o apellido en la base de datos.")
            
            elif cantidad == 1:
                alumno = alumnos_encontrados.iloc[0]
                
                nom_g = str(alumno.get('Nombre(s)', '')).strip()
                pat_g = str(alumno.get('Apellido Paterno', '')).strip()
                mat_g = str(alumno.get('Apellido Materno', '')).strip()
                curp_g = str(alumno.get('CURP', '')).strip().upper()
                grado_g = str(alumno.get('Grado', '')).strip()
                grupo_g = str(alumno.get('Grupo', '')).strip()
                cct_g = str(alumno.get('CCT', '')).strip()
                
                nombre_completo = f"{nom_g} {pat_g} {mat_g}"
                st.success(f"🎯 ¡Alumno encontrado de forma única!")
                
                es_valida_mat = validar_digito_verificador_curp(curp_g)
                
                st.markdown(f"""
                    <div class='info-card'>
                        <div class='info-label'>Nombre Completo</div>
                        <div class='info-value'>{nombre_completo}</div>
                    </div>
                """, unsafe_allow_html=True)
                
                col_r1, col_r2 = st.columns(2)
                with col_r1:
                    st.markdown(f"""
                        <div class='info-card'>
                            <div class='info-label'>Grado y Grupo</div>
                            <div class='info-value'>{grado_g}° - '{grupo_g}'</div>
                        </div>
                    """, unsafe_allow_html=True)
                with col_r2:
                    st.markdown(f"""
                        <div class='info-card'>
                            <div class='info-label'>CCT Escuela</div>
                            <div class='info-value'>{cct_g if cct_g else 'No asignado'}</div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                st.markdown(f"""
                    <div class='info-card'>
                        <div class='info-label'>CURP Registrada</div>
                        <div class='info-value'><code>{curp_g}</code></div>
                    </div>
                """, unsafe_allow_html=True)
                
                if es_valida_mat:
                    st.markdown("""
                        <div class='success-box'>
                            <h3>🟢 Validación Exitosa</h3>
                            <p>El dígito verificador matemático de esta CURP es oficial y correcto.</p>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                        <div class='error-box'>
                            <h3>🔴 Alerta Crítica</h3>
                            <p>El dígito verificador de esta CURP es falso (posible CURP inventada o alterada).</p>
                        </div>
                    """, unsafe_allow_html=True)
                    
            else:
                st.info(f"ℹ Se encontraron **{cantidad} alumnos** con similitudes. Selecciona al alumno exacto para continuar:")
                
                opciones_map = {}
                for idx, row in alumnos_encontrados.iterrows():
                    n = str(row.get('Nombre(s)', '')).strip()
                    p = str(row.get('Apellido Paterno', '')).strip()
                    m = str(row.get('Apellido Materno', '')).strip()
                    g = str(row.get('Grado', '')).strip()
                    gr = str(row.get('Grupo', '')).strip()
                    
                    etiqueta_amigable = f"{p} {m}, {n}  —  [{g}° '{gr}']"
                    opciones_map[etiqueta_amigable] = idx
                    
                seleccion_usuario = st.selectbox("Elige el registro correcto de la lista:", list(opciones_map.keys()))
                
                idx_real = opciones_map[seleccion_usuario]
                alumno = df_alumnos.loc[idx_real]
                
                nom_g = str(alumno.get('Nombre(s)', '')).strip()
                pat_g = str(alumno.get('Apellido Paterno', '')).strip()
                mat_g = str(alumno.get('Apellido Materno', '')).strip()
                curp_g = str(alumno.get('CURP', '')).strip().upper()
                grado_g = str(alumno.get('Grado', '')).strip()
                grupo_g = str(alumno.get('Grupo', '')).strip()
                cct_g = str(alumno.get('CCT', '')).strip()
                nombre_completo = f"{nom_g} {pat_g} {mat_g}"
                
                es_valida_mat = validar_digito_verificador_curp(curp_g)
                
                st.write("")
                st.markdown(f"""
                    <div class='info-card'>
                        <div class='info-label'>Nombre Completo</div>
                        <div class='info-value'>{nombre_completo}</div>
                    </div>
                """, unsafe_allow_html=True)
                
                col_r1, col_r2 = st.columns(2)
                with col_r1:
                    st.markdown(f"""
                        <div class='info-card'>
                            <div class='info-label'>Grado y Grupo</div>
                            <div class='info-value'>{grado_g}° - '{grupo_g}'</div>
                        </div>
                    """, unsafe_allow_html=True)
                with col_r2:
                    st.markdown(f"""
                        <div class='info-card'>
                            <div class='info-label'>CCT Escuela</div>
                            <div class='info-value'>{cct_g if cct_g else 'No asignado'}</div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                st.markdown(f"""
                    <div class='info-card'>
                        <div class='info-label'>CURP Seleccionada</div>
                        <div class='info-value'><code>{curp_g}</code></div>
                    </div>
                """, unsafe_allow_html=True)
                
                if es_valida_mat:
                    st.markdown("""
                        <div class='success-box'>
                            <h3>🟢 Validación Exitosa</h3>
                            <p>El alumno seleccionado cuenta con una CURP matemáticamente correcta.</p>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                        <div class='error-box'>
                            <h3>🔴 Alerta Directiva</h3>
                            <p>El alumno seleccionado tiene una CURP con errores en el dígito verificador (Requiere revisión manual).</p>
                        </div>
                    """, unsafe_allow_html=True)

# ==============================================================================
# MODO D: AUDITORÍA MASIVA DE CURPS EN GOOGLE SHEETS
# ==============================================================================
elif modo_app == "📊 Modo D: Auditoría Masiva de CURPs":
    st.markdown("### 📊 Auditoría Masiva de la Base de Datos")
    st.write("Revisión automática de todas las CURPs registradas en Google Sheets. Los registros con anomalías aparecerán primero.")

    if st.button("🚀 Ejecutar Análisis Masivo", type="primary", use_container_width=True):
        if df_alumnos.empty or 'CURP' not in df_alumnos.columns:
            st.error("La base de datos de Google Sheets está vacía o no contiene la columna 'CURP'.")
        else:
            resultados_masivos = []
            
            for index, row in df_alumnos.iterrows():
                curp_val = str(row.get('CURP', '')).strip().upper()
                nombre_val = f"{row.get('Nombre(s)', '')} {row.get('Apellido Paterno', '')} {row.get('Apellido Materno', '')}".strip()
                
                grado_val = row.get('Grado', '')
                grupo_val = row.get('Grupo', '')
                
                es_valida = validar_digito_verificador_curp(curp_val) if curp_val else False
                estado_str = "🟢 Válido (Correcto)" if es_valida else "🔴 Inválido (Falso / Erróneo)"
                
                resultados_masivos.append({
                    "Alumno": nombre_val if nombre_val else "Sin Nombre Registrado",
                    "Grado/Grupo": f"{grado_val}° '{grupo_val}'",
                    "CURP": curp_val if curp_val else "VACÍA",
                    "Estado": estado_str,
                    "_es_valido_bool": es_valida
                })
                
            df_reporte = pd.DataFrame(resultados_masivos)
            df_reporte = df_reporte.sort_values(by="_es_valido_bool", ascending=True)
            
            total_alumnos = len(df_reporte)
            total_invalidos = len(df_reporte[df_reporte['_es_valido_bool'] == False])
            total_validos = len(df_reporte[df_reporte['_es_valido_bool'] == True])
            
            col_m1, col_m2, col_m3 = st.columns(3)
            with col_m1:
                st.metric("Total Alumnos Analizados", total_alumnos)
            with col_m2:
                st.metric("CURPs Correctas (Verdes)", total_validos)
            with col_m3:
                st.metric("CURPs con Errores (Rojas)", total_invalidos)
                
            st.write("")
            
            df_mostrar = df_reporte.drop(columns=["_es_valido_bool"])
            
            def colorear_estado(val):
                color = '#4A1515' if 'Inválido' in str(val) or 'VACÍA' in str(val) else '#113a22'
                return f'background-color: {color}; color: #ffffff;'
                
            st.markdown("#### Listado General de Auditoría (Ordenado con alertas prioritarias al inicio):")
            st.dataframe(
                df_mostrar.style.map(colorear_estado, subset=['Estado']),
                use_container_width=True,
                hide_index=True
            )

# ==============================================================================
# MODO E: ANTIFRAUDE ESCOLAR (DUPLICADOS Y HOMOCLAVES)
# ==============================================================================
else:
    st.markdown("### 🛡 Auditoría Antifraude: Detección de Duplicados y Coincidencias")
    st.write("Escaneo avanzado de la base de datos para localizar CURPs repetidas de forma exacta y posibles alumnos duplicados con nombres similares.")

    if st.button("🔍 Iniciar Escaneo Antifraude", type="primary", use_container_width=True):
        if df_alumnos.empty or 'CURP' not in df_alumnos.columns:
            st.error("La base de datos de Google Sheets está vacía o no contiene la columna 'CURP'.")
        else:
            st.markdown("---")
            st.markdown("#### 1️⃣ Análisis de CURPs Duplicadas (Colisión Exacta)")
            
            temp_df = df_alumnos.copy()
            temp_df['CURP_LIMPIA'] = temp_df['CURP'].astype(str).str.strip().str.upper()
            
            validas_curp = temp_df[temp_df['CURP_LIMPIA'] != '']
            duplicados_curp = validas_curp[validas_curp.duplicated(subset=['CURP_LIMPIA'], keep=False)]
            
            if not duplicados_curp.empty:
                st.error(f"🚨 **¡Alerta Roja! Se encontraron {len(duplicados_curp)} registros con CURPs idénticas compartidas entre diferentes alumnos:**")
                
                tabla_dup = []
                for _, row in duplicados_curp.iterrows():
                    nom = f"{row.get('Nombre(s)', '')} {row.get('Apellido Paterno', '')} {row.get('Apellido Materno', '')}".strip()
                    tabla_dup.append({
                        "Alumno": nom,
                        "Grado/Grupo": f"{row.get('Grado', '')}° '{row.get('Grupo', '')}'",
                        "CURP Duplicada": row.get('CURP', '')
                    })
                st.dataframe(pd.DataFrame(tabla_dup), use_container_width=True, hide_index=True)
            else:
                st.markdown("""
                    <div class='success-box'>
                        <h3>🟢 Sin Colisiones de CURP</h3>
                        <p>No se detectó ninguna CURP repetida en toda la base de datos.</p>
                    </div>
                """, unsafe_allow_html=True)
                
            st.markdown("---")
            st.markdown("#### 2️⃣ Análisis de Similitud de Nombres (Posibles Alumnos Duplicados)")
            st.write("Búsqueda cruzada mediante algoritmos de aproximación para detectar nombres muy parecidos (variaciones de dedo o doble registro).")
            
            nombres_completos = []
            for _, row in df_alumnos.iterrows():
                n = str(row.get('Nombre(s)', '')).strip()
                p = str(row.get('Apellido Paterno', '')).strip()
                m = str(row.get('Apellido Materno', '')).strip()
                completo = f"{n} {p} {m}".upper()
                nombres_completos.append(completo)
                
            parejas_similares = []
            nombres_vistos = set()
            
            for i, nom_a in enumerate(nombres_completos):
                if not nom_a or nom_a == "  ":
                    continue
                for j, nom_b in enumerate(nombres_completos):
                    if i >= j or not nom_b or nom_b == "  ":
                        continue
                    
                    score = fuzz.ratio(nom_a, nom_b)
                    if 85 <= score < 100:
                        par_key = tuple(sorted([nom_a, nom_b]))
                        if par_key not in nombres_vistos:
                            nombres_vistos.add(par_key)
                            
                            row_a = df_alumnos.iloc[i]
                            row_b = df_alumnos.iloc[j]
                            
                            parejas_similares.append({
                                "Registro 1": f"{nom_a} ({row_a.get('Grado', '')}° '{row_a.get('Grupo', '')}')",
                                "Registro 2": f"{nom_b} ({row_b.get('Grado', '')}° '{row_b.get('Grupo', '')}')",
                                "Similitud": f"{score}%"
                            })
                            
            if parejas_similares:
                st.warning(f"⚠️ Se detectaron **{len(parejas_similares)} parejas de registros con nombres sospechosamente similares** (posible duplicidad de captura):")
                st.dataframe(pd.DataFrame(parejas_similares), use_container_width=True, hide_index=True)
            else:
                st.markdown("""
                    <div class='success-box'>
                        <h3>🟢 Nombres Claros y Únicos</h3>
                        <p>No se encontraron registros con nombres inusualmente parecidos o duplicados.</p>
                    </div>
                """, unsafe_allow_html=True)
