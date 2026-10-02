import os
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as condiciones

# --- CONFIGURACIÓN DE LA PÁGINA EN STREAMLIT ---
st.set_page_config(page_title="Validador CURP Alumnos", page_icon="🎓", layout="centered")

st.markdown("<h1 style='text-align: center;'>🎓 Validador CURP Alumnos - RENAPO 🎓</h1>", unsafe_allow_html=True)
st.write("")

# --- CONEXIÓN A GOOGLE SHEETS USANDO SECRETS ---
@st.cache_resource
def conectar_google_sheets():
    # Definimos los permisos necesarios para Google Sheets y Drive
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    # Extraemos el diccionario de los secretos de Streamlit
    credentials_dict = dict(st.secrets["gcp_service_account"])
    
    # Creamos las credenciales con los scopes explícitos
    creds = Credentials.from_service_account_info(credentials_dict, scopes=scopes)
    
    # Autorizamos el cliente gspread
    client = gspread.authorize(creds)
    
    # Abrimos la hoja de cálculo por su nombre exacto y obtenemos la primera pestaña
    spreadsheet = client.open("BD_Alumnos") 
    worksheet = spreadsheet.get_worksheet(0)
    return worksheet

# Cargamos los datos de la hoja evitando errores de celdas vacías
try:
    ws = conectar_google_sheets()
    data = ws.get_all_values()
    if len(data) > 1:
        headers = [h.strip() for h in data[0] if h.strip() != '']
        df_alumnos = pd.DataFrame(data[1:], columns=data[0][:len(data[1])])
        df_alumnos = df_alumnos.loc[:, df_alumnos.columns != '']
    else:
        df_alumnos = pd.DataFrame()
except Exception as e:
    st.error(f"Error detallado al conectar con Google Sheets: {e}")
    df_alumnos = pd.DataFrame()


# --- FUNCIÓN DE SCRAPING CON UNDETECTED-CHROMEDRIVER ---
@st.cache_data(ttl=3600)
def consultar_renapo_selenium(curp_a_buscar):
    options = uc.ChromeOptions()
    
    # Opciones esenciales para entornos sin pantalla (headless) en la nube
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    driver = None
    datos_extraidos = None
    
    try:
        # Detección automática del binario de Chromium en Linux (Streamlit Cloud) o uso automático en Windows
        if os.path.exists("/usr/bin/chromium"):
            options.binary_location = "/usr/bin/chromium"
            driver = uc.Chrome(options=options, headless=True, use_subprocess=True)
        else:
            driver = uc.Chrome(options=options, headless=True, use_subprocess=True)
            
        driver.get("https://www.gob.mx/curp/")
        
        # Ingresar CURP
        input_curp = WebDriverWait(driver, 15).until(
            condiciones.presence_of_element_located((By.ID, "curp"))
        )
        input_curp.clear()
        input_curp.send_keys(curp_a_buscar)
        
        # Hacer clic en buscar
        boton_buscar = WebDriverWait(driver, 10).until(
            condiciones.element_to_be_clickable((By.ID, "search-curp"))
        )
        boton_buscar.click()
        
        # Esperar resultados oficiales
        WebDriverWait(driver, 15).until(
            condiciones.presence_of_element_located((By.CLASS_NAME, "datos-solicitante"))
        )
        
        # Extracción de campos
        nombres = driver.find_element(By.XPATH, "//td[contains(text(), 'Nombre(s):')]/following-sibling::td").text
        primer_apellido = driver.find_element(By.XPATH, "//td[contains(text(), 'Primer apellido:')]/following-sibling::td").text
        segundo_apellido = driver.find_element(By.XPATH, "//td[contains(text(), 'Segundo apellido:')]/following-sibling::td").text
        
        datos_extraidos = {
            "nombres": nombres.strip().upper(),
            "primer_apellido": primer_apellido.strip().upper(),
            "segundo_apellido": segundo_apellido.strip().upper()
        }
        
    except Exception as e:
        print(f"Error en el proceso de scraping con undetected-chromedriver: {e}")
        datos_extraidos = None
        
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass
        
    return datos_extraidos


# --- INTERFAZ DE USUARIO EN STREAMLIT ---
curp_input = st.text_input("Introduce CURP a verificar:").strip().upper()

if st.button("Verificar Alumno"):
    if curp_input:
        with st.spinner("Consultando en portal oficial de RENAPO de forma segura..."):
            datos_gobierno = consultar_renapo_selenium(curp_input)
            
        if datos_gobierno:
            st.success("¡CURP verificada exitosamente en el portal oficial!")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Datos en Base de Datos**")
                if not df_alumnos.empty and 'CURP' in df_alumnos.columns:
                    df_alumnos['CURP_clean'] = df_alumnos['CURP'].astype(str).str.strip().str.upper()
                    resultado_db = df_alumnos[df_alumnos['CURP_clean'] == curp_input]
                    
                    if not resultado_db.empty:
                        st.write(f"Nombre(s): {resultado_db.iloc[0]['Nombre(s)']}")
                        st.write(f"Apellido Paterno: {resultado_db.iloc[0]['Apellido Paterno']}")
                        st.write(f"Apellido Materno: {resultado_db.iloc[0]['Apellido Materno']}")
                        st.write(f"Grado: {resultado_db.iloc[0]['Grado']}")
                        st.write(f"Grupo: {resultado_db.iloc[0]['Grupo']}")
                    else:
                        st.warning("El CURP es válido en RENAPO, pero no se encontró en la base de datos de Google Sheets.")
                else:
                    st.error("La base de datos está vacía o no tiene la columna CURP.")
                    
            with col2:
                st.markdown("**Datos Oficiales RENAPO**")
                st.write(f"Nombre(s): {datos_gobierno['nombres']}")
                st.write(f"Apellido Paterno: {datos_gobierno['primer_apellido']}")
                st.write(f"Apellido Materno: {datos_gobierno['segundo_apellido']}")
                
        else:
            st.error("No se pudo obtener respuesta del portal oficial de la CURP. El sitio podría requerir validación manual o estar saturado.")
    else:
        st.warning("Por favor, introduce una CURP antes de verificar.")
            st.error("No se pudo obtener respuesta del portal oficial de la CURP. El sitio podría requerir validación manual o estar saturado.")
    else:
        st.warning("Por favor, introduce una CURP antes de verificar.")

