import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import re
from rapidfuzz import process, fuzz

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Validador Beta Escolar - CURP", 
    page_icon="🎓", 
    layout="centered"
)

st.markdown("<h1 style='text-align: center;'>🎓 Validador Inteligente de Alumnos (Beta) 🎓</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray;'>Sistema interno con control de errores de dedo y validación cruzada</p>", unsafe_allow_html=True)
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
    
    # Utiliza tus credenciales configuradas en st.secrets (o archivo .streamlit/secrets.toml local)
    credentials_dict = dict(st.secrets["gcp_service_account"])
    pk = credentials_dict.get("private_key", "")
    try:
        pk = pk.encode().decode('unicode-escape')
    except Exception:
        pk = pk.replace("\\n", "\n")
    credentials_dict["private_key"] = pk
    
    creds = Credentials.from_service_account_info(credentials_dict, scopes=scopes)
    client = gspread.authorize(creds)
    
    # Abre la hoja con el nombre exacto que especificaste
    spreadsheet = client.open("prueba validacion curp") 
    worksheet = spreadsheet.get_worksheet(0)
    return worksheet

# Carga segura de datos
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

# --- INTERFAZ DE USUARIO ---
st.markdown("### Ingrese o escanee la CURP del alumno:")
curp_input = st.text_input("CURP a verificar:", placeholder="Ej. CUEA140525MMCRSLB4").strip().upper()

# Expresión regular oficial de 18 caracteres
patron_curp = re.compile(r'^[A-Z]{4}\d{6}[HM][A-Z]{5}[0-9A-Z]{2}$')

if st.button("Verificar e Inspeccionar Alumno", type="primary"):
    if not curp_input:
        st.warning("Por favor, introduce una CURP.")
    else:
        # 1. Validación Estructural (Regex)
        if not patron_curp.match(curp_input):
            st.error("🔴 **CURP Inválida:** La estructura no cumple con los 18 caracteres oficiales exigidos por RENAPO (letras, fecha AAMMDD, género y homoclave).")
        else:
            st.success("🟢 **Formato Correcto:** La estructura matemática de 18 caracteres es válida.")
            
            if df_alumnos.empty or 'CURP' not in df_alumnos.columns:
                st.error("La base de datos de Google Sheets está vacía o no contiene la columna 'CURP'.")
            else:
                # Limpiar datos de la base de tabla para búsqueda
                lista_curps_db = df_alumnos['CURP'].astype(str).str.strip().str.upper().tolist()
                
                # 2. Búsqueda exacta o tolerante a errores de dedo (Fuzzy Matching)
                match_exacto = df_alumnos[df_alumnos['CURP'].str.strip().str.upper() == curp_input]
                
                resultado = None
                if not match_exacto.empty:
                    resultado = match_exacto.iloc[0]
                    st.info("✨ **Coincidencia Exacta:** Encontrada textualmente en la base de datos institucional.")
                else:
                    # Búsqueda difusa para detectar errores de dedo leves (Umbral de 85% de similitud)
                    mejor_match, puntuacion, indice = process.extractOne(
                        curp_input, 
                        lista_curps_db, 
                        scorer=fuzz.ratio
                    )
                    
                    if puntuacion >= 85:
                        st.warning(f"⚠️ **Atención - Error de dedo probable:** No existe exactamente esa CURP, pero se detectó un registro muy cercano (Similitud: {puntuacion:.1f}%).")
                        resultado = df_alumnos.iloc[indice]
                        st.write(f"CURP sugerida en base de datos: **{resultado.get('CURP')}**")
                    else:
                        st.error("🔴 **No Registrado:** La CURP tiene buen formato, pero no existe ningún alumno asociado en la base de datos de Google Sheets.")
                
                # 3. Validación Cruzada Interna (Intra-CURP) si se encontró al alumno
                if resultado is not None:
                    st.markdown("---")
                    st.markdown("### 📋 Ficha de Control Escolar e Inspección")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Nombre(s):** {resultado.get('Nombre(s)', 'N/A')}")
                        st.write(f"**Apellido Paterno:** {resultado.get('Apellido Paterno', 'N/A')}")
                        st.write(f"**Apellido Materno:** {resultado.get('Apellido Materno', 'N/A')}")
                    with col2:
                        st.write(f"**Grado:** {resultado.get('Grado', 'N/A')}")
                        st.write(f"**Grupo:** {resultado.get('Grupo', 'N/A')}")
                        st.write(f"**CURP Evaluada:** {resultado.get('CURP', 'N/A')}")
                    
                    st.markdown("#### 🔍 Auditoría de Consistencia Interna:")
                    
                    # Extraer el código de estado de las posiciones 11 y 12 de la CURP ingresada
                    codigo_estado_curp = curp_input[11:13]
                    estado_en_curp = CODIGOS_ESTADOS.get(codigo_estado_curp, "DESCONOCIDO")
                    
                    # Obtener el estado registrado en la base de datos del alumno
                    estado_en_bd = str(resultado.get('Estado de Nacimiento', '')).strip().upper()
                    
                    st.write(f"- Estado extraído matemáticamente de la CURP: **{estado_en_curp}** (`{codigo_estado_curp}`)")
                    st.write(f"- Estado registrado en la celda de Google Sheets: **{estado_en_bd if estado_en_bd else 'No especificado'}**")
                    
                    # Comparación lógica de consistencia
                    if estado_en_bd and estado_en_curp != estado_en_bd:
                        st.markdown(
                            f"🔴 **ALERTA DE INCONSISTENCIA:** El estado de nacimiento oficial cifrado en la CURP (**{estado_en_curp}**) "
                            f"no coincide con el registrado en la base de datos (**{estado_en_bd}**). **Se requiere revisión manual.**"
                        )
                    else:
                        st.markdown("🟢 **Consistencia Verificada:** Los datos internos de la CURP concuerdan con el estado de nacimiento registrado.")
