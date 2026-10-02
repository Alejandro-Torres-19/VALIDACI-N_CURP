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
st.markdown("<p style='text-align: center; color: gray;'>Sistema con validación cruzada y decodificación de fecha oficial</p>", unsafe_allow_html=True)
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

# --- CONEXIÓN A GOOGLE SHEETS ("prueba validacion curp") ---
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
            df = pd.DataFrame(data[1:], columns=data[0][:len(data[1])])
            df = df.loc[:, df.columns != ''] # Limpiar columnas vacías
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
    
    # Fecha AAMMDD extraída directamente de la CURP
    yy = curp[4:6]
    mm = curp[6:8]
    dd = curp[8:10]
    
    # Resolver siglo (asumiendo formato estándar 19xx / 20xx)
    siglo = "20" if int(yy) <= 30 else "19"
    
    # Formato estándar YYYY-MM-DD para comparar con Google Sheets
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
curp_input = st.text_input("CURP a verificar:", placeholder="Ej. CUEA140525MMCRSLB4").strip().upper()

patron_curp = re.compile(r'^[A-Z]{4}\d{6}[HM][A-Z]{5}[0-9A-Z]{2}$')

if st.button("Ejecutar Análisis y Cruce de Alumno", type="primary"):
    if not curp_input:
        st.warning("Por favor, introduce una CURP.")
    else:
        if not patron_curp.match(curp_input):
            st.error("🔴 **CURP Inválida:** La estructura no cumple con los 18 caracteres oficiales exigidos por RENAPO.")
        else:
            st.success("🟢 **Formato Estructural Correcto (18 caracteres).**")
            
            # Desglose analítico de la CURP introducida
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
                st.write(f"- **Fecha Nacimiento calculada de la CURP:** `{info_curp['fecha_nacimiento']}`")
                st.write(f"- **Género cifrado:** `{info_curp['genero']}`")
                st.write(f"- **Estado de Nacimiento cifrado:** `{info_curp['estado_nacimiento']} ({info_curp['codigo_estado']})`")
            
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
                        st.warning(f"⚠️ **Atención:** No está exactamente escrita, pero el sistema detectó una correspondencia muy cercana en la base de datos (Similitud: {puntuacion:.1f}%).")
                        resultado = df_alumnos.iloc[indice]
                    else:
                        st.error("🔴 **Sin Registro Asociado:** La CURP es estructuralmente correcta, pero no hay ningún alumno en la base de datos de Google Sheets que coincida.")
                
                if resultado is not None:
                    st.markdown("---")
                    st.markdown("### 📋 Perfil del Alumno Asociado y Validación Analítica")
                    
                    nombre_db = str(resultado.get('Nombre(s)', '')).strip().upper()
                    ap_p_db = str(resultado.get('Apellido Paterno', '')).strip().upper()
                    ap_m_db = str(resultado.get('Apellido Materno', '')).strip().upper()
                    estado_db = str(resultado.get('Estado de Nacimiento', '')).strip().upper()
                    fecha_db = str(resultado.get('Fecha de Nacimiento', '')).strip()
                    
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.write(f"**Nombre(s) en BD:** {resultado.get('Nombre(s)', 'N/A')}")
                        st.write(f"**Primer Apellido en BD:** {resultado.get('Apellido Paterno', 'N/A')}")
                        st.write(f"**Segundo Apellido en BD:** {resultado.get('Apellido Materno', 'N/A')}")
                    with col_b:
                        st.write(f"**Grado y Grupo:** {resultado.get('Grado', 'N/A')} - {resultado.get('Grupo', 'N/A')} ")
                        st.write(f"**Fecha en BD (Fórmula):** {fecha_db if fecha_db else 'No disponible'}")
                        st.write(f"**Estado en BD:** {resultado.get('Estado de Nacimiento', 'N/A')}")
                    
                    st.markdown("#### ⚖️ Auditoría de Coherencia de Datos y Fecha:")
                    
                    # Verificaciones lógicas
                    coincide_ap_p = ap_p_db.startswith(info_curp['letra_primer_apellido']) if ap_p_db else False
                    coincide_nom = nombre_db.startswith(info_curp['letra_nombre']) if nombre_db else False
                    coincide_estado = (estado_db == info_curp['estado_nacimiento']) if estado_db else True
                    
                    # Comparar la fecha calculada de la CURP con la fecha obtenida de la fórmula de Google Sheets
                    coincide_fecha = True
                    if fecha_db:
                        # Limpiamos posibles formatos de hora o espacios que devuelva Google Sheets
                        fecha_db_clean = fecha_db.split("T")[0] 
                        coincide_fecha = (fecha_db_clean == info_curp['fecha_nacimiento'])
                    
                    if coincide_ap_p and coincide_nom and coincide_estado and coincide_fecha:
                        st.markdown("🟢 **Validación Analítica Exitosa:** Los datos, las iniciales y **la fecha de nacimiento calculada de la CURP** coinciden perfectamente con los registros de la base de datos.")
                    else:
                        st.markdown("🔴 **ALERTA DE DISCREPANCIA ESTRUCTURAL:**")
                        if not coincide_fecha:
                            st.write(f"- 📅 **Discrepancia en Fecha:** La fecha calculada matemáticamente de los dígitos de la CURP (**{info_curp['fecha_nacimiento']}**) **no coincide** con la fecha arrojada por la fórmula en la base de datos (**{fecha_db}**).")
                        if not coincide_ap_p:
                            st.write(f"- La letra del primer apellido en la CURP (`{info_curp['letra_primer_apellido']}`) no coincide con el apellido guardado (`{ap_p_db}`).")
                        if not coincide_nom:
                            st.write(f"- La letra del nombre en la CURP (`{info_curp['letra_nombre']}`) no coincide con el nombre guardado (`{nombre_db}`).")
                        if not coincide_estado:
                            st.write(f"- El estado cifrado en la CURP (**{info_curp['estado_nacimiento']}**) difiere del registrado (**{estado_db}**).")
