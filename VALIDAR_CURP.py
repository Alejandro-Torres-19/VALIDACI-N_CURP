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

# Estilos CSS personalizados para mejorar la interfaz visual
st.markdown("""
    <style>
        .main-title { font-size: 2.2rem; font-weight: 700; color: #1E3A8A; text-align: center; margin-bottom: 0px; }
        .sub-title { font-size: 1.1rem; color: #4B5563; text-align: center; margin-bottom: 25px; }
        .card-box { background-color: #F8FAFC; padding: 20px; border-radius: 12px; border: 1px solid #E2E8F0; margin-bottom: 15px; }
        .success-box { background-color: #ECFDF5; padding: 15px; border-radius: 10px; border: 1px solid #A7F3D0; color: #065F46; }
        .error-box { background-color: #FEF2F2; padding: 15px; border-radius: 10px; border: 1px solid #FECACA; color: #991B1B; }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='main-title'>🎓 Validador y Analizador de CURP</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-title'>Sistema de control escolar con auditoría cruzada de datos oficiales</p>", unsafe_allow_html=True)

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

# --- FUNCIÓN DE DECODIFICACIÓN ---
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

# --- ENTRADA PRINCIPAL ---
st.markdown("### 🔍 Ingresa la CURP del alumno")
curp_input = st.text_input("", placeholder="Ej. CAHD140521HMCDRYA3", label_visibility="collapsed").strip().upper()

patron_curp = re.compile(r'^[A-Z]{4}\d{6}[HM][A-Z]{5}[0-9A-Z]{2}$')

if st.button("🚀 Ejecutar Validación y Análisis", type="primary", use_container_width=True):
    if not curp_input:
        st.warning("⚠️ Por favor, introduce una CURP en el campo de texto.")
    else:
        if not patron_curp.match(curp_input):
            st.error("🔴 **CURP Inválida:** La estructura no cumple con los 18 caracteres oficiales exigidos por RENAPO.")
        else:
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
                    # Extracción de columnas de Google Sheets
                    ap_p_db = str(resultado.get('Apellido Paterno', '')).strip().upper()
                    ap_m_db = str(resultado.get('Apellido Materno', '')).strip().upper()
                    nombre_db = str(resultado.get('Nombre(s)', '')).strip().upper()
                    grado_db = str(resultado.get('Grado', '')).strip()
                    grupo_db = str(resultado.get('Grupo', '')).strip()
                    cct_db = str(resultado.get('CCT', '')).strip()
                    fecha_db = str(resultado.get('Fecha de Nacimiento', '')).strip()
                    entidad_db = str(resultado.get('Entidad Nacimiento', '')).strip().upper()
                    
                    # Normalización de fecha
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

                    # Validaciones cruzadas
                    val_ap_p = ap_p_db.startswith(info_curp['letra_primer_apellido']) if ap_p_db else False
                    val_ap_m = ap_m_db.startswith(info_curp['letra_segundo_apellido']) if ap_m_db else False
                    val_nom = nombre_db.startswith(info_curp['letra_nombre']) if nombre_db else False
                    
                    errores = []
                    if not coincide_fecha:
                        errores.append(f"Fecha en Sheets ({fecha_mostrar}) no coincide con la CURP ({info_curp['fecha_nacimiento']}).")
                    if not val_ap_p:
                        errores.append(f"La inicial del Apellido Paterno (`{info_curp['letra_primer_apellido']}`) no concuerda con `{ap_p_db}`.")
                    if not val_ap_m and ap_m_db:
                        errores.append(f"La inicial del Apellido Materno (`{info_curp['letra_segundo_apellido']}`) no concuerda con `{ap_m_db}`.")
                    if not val_nom:
                        errores.append(f"La inicial del Nombre (`{info_curp['letra_nombre']}`) no concuerda con `{nombre_db}`.")

                    st.write("")
                    
                    # --- DISEÑO EN PESTAÑAS (TABS) ---
                    tab1, tab2, tab3 = st.tabs(["👤 Perfil del Alumno", "🔍 Desglose CURP", "⚖️ Auditoría y Estado"])
                    
                    with tab1:
                        st.markdown("#### Información Registrada en Google Sheets")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Nombre Completo", f"{nombre_db} {ap_p_db} {ap_m_db}")
                            st.metric("Grado y Grupo", f"{grado_db}° - '{grupo_db}'")
                        with col2:
                            st.metric("CCT Escuela", cct_db if cct_db else "No asignado")
                            st.metric("Fecha de Nacimiento", fecha_mostrar)
                        st.write(f"**Entidad de Nacimiento (Sheets):** {entidad_db if entidad_db else 'No especificada'}")

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

                    with tab3:
                        st.markdown("#### Dictamen General del Alumno")
                        if not errores:
                            st.markdown("""
                                <div class='success-box'>
                                    <h3>🟢 Validación Exitosa</h3>
                                    <p>Todos los datos de la base de datos concuerdan perfectamente con la estructura matemática y oficial de la CURP.</p>
                                </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown("""
                                <div class='error-box'>
                                    <h3>🔴 Alerta de Discrepancia Detectada</h3>
                                    <p>Se encontraron inconsistencias entre las columnas del registro y la CURP:</p>
                                </div>
                            """, unsafe_allow_html=True)
                            for err in errores:
                                st.warning(f"• {err}")
                else:
                    st.error("🔴 **Sin Registro Asociado:** La CURP es estructuralmente correcta, pero no se encontró ningún alumno coincidente en la base de datos.")
