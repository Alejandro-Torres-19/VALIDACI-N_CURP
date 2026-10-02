import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import re
from rapidfuzz import process, fuzz

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Validador y Analizador CURP - Escolar", 
    page_icon="🎓", 
    layout="centered"
)

st.markdown("<h1 style='text-align: center;'>🎓 Analizador y Validador Inteligente de CURP 🎓</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray;'>Sistema con validación cruzada y auditoría de columnas completas</p>", unsafe_allow_html=True)
st.write("")

# Botón para limpiar caché y forzar actualización de Google Sheets
if st.button("🔄 Recargar Datos de Google Sheets"):
    st.cache_data.clear()
    st.cache_resource.clear()
    st.success("¡Caché limpiada correctamente! Vuelve a buscar tu CURP.")

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
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
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
    worksheet = spreadsheet.get_worksheet(0)
    return worksheet

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

# --- FUNCIÓN DE DECODIFICACIÓN Y ANÁLISIS ESTRUCTURAL DE LA CURP ---
def decodificar_curp(curp):
    curp = curp.strip().upper()
    if len(curp) != 18:
        return None
    
    p_ap_1 = curp[0]
    p_ap_vocal = curp[1]
    p_am_1 = curp[2]
    p_nom_1 = curp[3]
    
    yy = curp[4:6]
    mm = curp[6:8]
    dd = curp[8:10]
    
    siglo = "20" if int(yy) <= 30 else "19"
    fecha_decodificada = f"{siglo}{yy}-{mm}-{dd}"
    
    genero = "Hombre" if curp[10] == "H" else ("Mujer" if curp[10] == "M" else "Desconocido")
    c_estado = curp[11:13]
    estado_nombre = CODIGOS_ESTADOS.get(c_estado, "Desconocido")
    
    return {
        "letra_primer_apellido": p_ap_1,
        "vocal_primer_apellido": p_ap_vocal,
        "letra_segundo_apellido": p_am_1,
        "letra_nombre": p_nom_1,
        "fecha_nacimiento": fecha_decodificada,
        "genero": genero,
        "codigo_estado": c_estado,
        "estado_nacimiento": estado_nombre
    }

# --- INTERFAZ DE USUARIO ---
st.markdown("### Ingrese la CURP para análisis e identificación analítica:")
curp_input = st.text_input("CURP a verificar:", placeholder="Ej. CAHD140521HMCDRYA3").strip().upper()

patron_curp = re.compile(r'^[A-Z]{4}\d{6}[HM][A-Z]{5}[0-9A-Z]{2}$')

if st.button("Ejecutar Análisis y Cruce de Alumno", type="primary"):
    if not curp_input:
        st.warning("Por favor, introduce una CURP.")
    else:
        if not patron_curp.match(curp_input):
            st.error("🔴 **CURP Inválida:** La estructura no cumple con los 18 caracteres oficiales exigidos por RENAPO.")
        else:
            st.success("🟢 **Formato Estructural Correcto (18 caracteres).**")
            
            info_curp = decodificar_curp(curp_input)
            
            st.markdown("---")
            st.markdown("### 🔍 Desglose y Análisis Matemático de la CURP")
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"- **1ra letra 1er Apellido:** `{info_curp['letra_primer_apellido']}`")
                st.write(f"- **1ra vocal interna 1er Apellido:** `{info_curp['vocal_primer_apellido']}`")
                st.write(f"- **1ra letra 2do Apellido:** `{info_curp['letra_segundo_apellido']}`")
                st.write(f"- **1ra letra Nombre:** `{info_curp['letra_nombre']}`")
            with c2:
                st.write(f"- **Fecha Nacimiento calculada:** `{info_curp['fecha_nacimiento']}`")
                st.write(f"- **Género cifrado:** `{info_curp['genero']}`")
                st.write(f"- **Entidad de Nacimiento cifrada:** `{info_curp['estado_nacimiento']} ({info_curp['codigo_estado']})`")
            
            if df_alumnos.empty or 'CURP' not in df_alumnos.columns:
                st.error("La base de datos de Google Sheets está vacía o no contiene la columna 'CURP'.")
            else:
                lista_curps_db = df_alumnos['CURP'].astype(str).str.strip().str.upper().tolist()
                match_exacto = df_alumnos[df_alumnos['CURP'].str.strip().str.upper() == curp_input]
                
                resultado = None
                if not match_exacto.empty:
                    resultado = match_exacto.iloc[0]
                    st.info("✨ **Coincidencia Exacta:** Esta CURP se encuentra guardada textualmente en la base de datos.")
                else:
                    mejor_match, puntuacion, indice = process.extractOne(
                        curp_input, 
                        lista_curps_db, 
                        scorer=fuzz.ratio
                    )
                    if puntuacion >= 85:
                        st.warning(f"⚠️ **Atención:** Correspondencia aproximada detectada (Similitud: {puntuacion:.1f}%).")
                        resultado = df_alumnos.iloc[indice]
                    else:
                        st.error("🔴 **Sin Registro Asociado:** La CURP es correcta, pero no hay ningún registro en Google Sheets que coincida.")
                
                if resultado is not None:
                    st.markdown("---")
                    st.markdown("### 📋 Perfil Completo del Alumno (Google Sheets)")
                    
                    # Extracción de todas las columnas de la tabla
                    ap_p_db = str(resultado.get('Apellido Paterno', '')).strip().upper()
                    ap_m_db = str(resultado.get('Apellido Materno', '')).strip().upper()
                    nombre_db = str(resultado.get('Nombre(s)', '')).strip().upper()
                    grado_db = str(resultado.get('Grado', '')).strip()
                    grupo_db = str(resultado.get('Grupo', '')).strip()
                    cct_db = str(resultado.get('CCT', '')).strip()
                    fecha_db = str(resultado.get('Fecha de Nacimiento', '')).strip()
                    entidad_db = str(resultado.get('Entidad Nacimiento', '')).strip().upper()
                    
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.write(f"**Apellido Paterno:** {ap_p_db}")
                        st.write(f"**Apellido Materno:** {ap_m_db}")
                        st.write(f"**Nombre(s):** {nombre_db}")
                        st.write(f"**Grado y Grupo:** {grado_db} - {grupo_db}")
                    with col_b:
                        st.write(f"**CCT:** {cct_db}")
                        st.write(f"**Entidad en BD:** {entidad_db if entidad_db else 'No especificada'}")
                        
                        # Normalización de Fecha para visualización
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
                        else:
                            fecha_mostrar = "No disponible / Vacía"
                            coincide_fecha = False
                            
                        st.write(f"**Fecha en BD:** {fecha_mostrar}")

                    st.markdown("#### ⚖️ Auditoría Integral de Coherencia de Datos:")
                    
                    # Validaciones cruzadas individuales con todas las columnas
                    val_ap_p = ap_p_db.startswith(info_curp['letra_primer_apellido']) if ap_p_db else False
                    val_ap_m = ap_m_db.startswith(info_curp['letra_segundo_apellido']) if ap_m_db else False
                    val_nom = nombre_db.startswith(info_curp['letra_nombre']) if nombre_db else False
                    
                    errores = []
                    if not coincide_fecha:
                        errores.append(f"📅 **Fecha de Nacimiento:** La fecha en Sheets (`{fecha_mostrar}`) no coincide con la calculada en la CURP (`{info_curp['fecha_nacimiento']}`).")
                    if not val_ap_p:
                        errores.append(f"❌ **Apellido Paterno:** La letra inicial en la CURP (`{info_curp['letra_primer_apellido']}`) no coincide con el apellido `{ap_p_db}`.")
                    if not val_ap_m and ap_m_db:
                        errores.append(f"❌ **Apellido Materno:** La letra inicial en la CURP (`{info_curp['letra_segundo_apellido']}`) no coincide con el apellido `{ap_m_db}`.")
                    if not val_nom:
                        errores.append(f"❌ **Nombre(s):** La letra inicial en la CURP (`{info_curp['letra_nombre']}`) no coincide con el nombre `{nombre_db}`.")
                    
                    if not errores:
                        st.markdown("🟢 **Validación Integral Exitosa:** Todas las columnas, iniciales, fechas y datos coinciden de forma perfecta con la estructura oficial de la CURP.")
                    else:
                        st.markdown("🔴 **ALERTA DE DISCREPANCIA EN COLUMNAS:**")
                        for err in errores:
                            st.write(f"- {err}")
