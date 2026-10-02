#IMOPORTAR DEPENDENCIAS NECESARIAS
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials


#IMPORTAR DEPENDENCIAS SELENIUM
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as condiciones

#CONGURACIÓN INICIAL PAGINA
st.set_page_config(page_title="Validación Curp´s Alumnos", page_icon = "🎓",layout="centered")

st.title("🎓 Validador CURP Alumnos - RENAPO 🎓")


# 1. Función con caché para leer Google Sheets
@st.cache_data(ttl=600)
def cargar_datos_google_sheets():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    # Carga las credenciales desde los Secrets configurados en Streamlit
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)

    client = gspread.authorize(creds)

    sheet = client.open("prueba validacion curp").sheet1
    data = sheet.get_all_records()
    return pd.DataFrame(data)


# 2. Función de Web Scraping con Selenium optimizada para la Nube
@st.cache_data(ttl=3600)
def consultar_renapo_selenium(curp_a_buscar):
    options = Options()

    # Opciones requeridas para entorno de servidor Linux / Streamlit Cloud
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    options.binary_location = "/usr/bin/chromium"
    service = Service("/usr/bin/chromedriver")

    driver = webdriver.Chrome(service=service, options=options)
    datos_extraidos = None

    try:
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

        # Esperar resultados
        WebDriverWait(driver, 15).until(
            condiciones.presence_of_element_located((By.CLASS_NAME, "datos-solicitante"))
        )

        # Extracción de campos basados en la estructura HTML del portal
        nombres = driver.find_element(By.XPATH, "//td[contains(text(), 'Nombre(s):')]/following-sibling::td").text
        primer_apellido = driver.find_element(By.XPATH,
                                              "//td[contains(text(), 'Primer apellido:')]/following-sibling::td").text
        segundo_apellido = driver.find_element(By.XPATH,
                                               "//td[contains(text(), 'Segundo apellido:')]/following-sibling::td").text

        datos_extraidos = {
            "nombres": nombres.strip().upper(),
            "primer_apellido": primer_apellido.strip().upper(),
            "segundo_apellido": segundo_apellido.strip().upper()
        }

    except Exception as e:
        print(f"Error en el proceso de scraping: {e}")
        datos_extraidos = None

    finally:
        driver.quit()

    return datos_extraidos

#INTEERFAZ USUARIO STREAMLIT
curp_input = st.text_input("Introduce CURP a verificar:").strip().upper()

if st.button("Verificar Alumno", type = "primary"):
    if not curp_input:
        st.warning("Porfavor, escriba un CURP válido")
    else:
        with st.spinner("Consultando en portal oficial de RENAPO..."):

            #CARGAR GOOGLE SHEETS
            try:
                df_alumnos = cargar_datos_google_sheets()
            except Exception as e:
                st.error(f"Error al conectar con Google Sheets: {e}")
                st.stop()

            #VERIFICANDO COLUMNAS
            columnas_requeridas = ["CURP", "Nombre(s)", "Apellido Paterno", "Apellido Materno"]
            for col in columnas_requeridas:
                if col not in columnas_requeridas:
                    st.error(f"❌ No se encontró la columna '{col}' en tu Google Sheet. Revisa los nombres de las columnas.")
                    st.stop()

            #BUSCAR CURP EN GOOGLE SHEETS
            df_alumnos["CURP_clean"] = df_alumnos["CURP"].str.strip().str.upper()
            alumno_db = df_alumnos[df_alumnos["CURP_clean"] == curp_input]

            if alumno_db.empty:
                st.error("❌ El CURP ingresado no se encuentra registrado en tu Base de Datos.")
            else:
                #EXTRAER DATOS GOOGLE SHEETS
                nombre_db = str(alumno_db.iloc[0]["Nombre(s)"]).strip().upper()
                apellido1_db = str(alumno_db.iloc[0]["Apellido Paterno"]).strip().upper()
                apellido2_db = str(alumno_db.iloc[0]["Apellido Materno"]).strip().upper()

                #EJECUTAR CACHE SCARPING ORIGINAL
                datos_gobierno = consultar_renapo_selenium(curp_input)

                if not datos_gobierno:
                    st.error("⚠️ No se pudo obtener respuesta del portal oficial de la CURP. Es posible que el sitio esté saturado.")
                else:
                    #COMPARACIÓN DATOS
                    coinciden_nombres = (datos_gobierno["nombres"] == nombre_db)
                    coinciden_ap1 = (datos_gobierno["primer_apellido"] == apellido1_db)
                    coinciden_ap2 = (datos_gobierno["segundo_apellido"] == apellido2_db)

                    if coinciden_nombres and coinciden_ap1 and coinciden_ap2:
                        st.success("✅ ¡Validación exitosa! Los datos coinciden perfectamente con el registro oficial de la RENAPO.")

                        st.subheader("Datos de Alumno Validado")
                        #MUESTRA COLUMNAS SOLICITADAS
                        st.dataframe(alumno_db[["Nombre(s)", "Apellido Paterno", "Apellido Materno", "CURP", "Grado", "Grupo"]])
                    else:
                        st.error("🚨 ¡Alerta de discrepancia! Los datos arrojados por el gobierno NO coinciden con los registrados en la Base de Datos.")

                        #MOSTRAR TABLA COMPARATIVA
                        col_1, col_2 = st.columns(2)
                        with col_1:
                            st.markdown("**Datos en Base de Datos**")
                            st.write(f"- Nombre(s): {nombre_db}")
                            st.write(f"- Apellido Paterno: {apellido1_db}")
                            st.write(f"- Apellido Materno: {apellido2_db}")
                        with col_2:
                            st.markdown("**Datos Oficiales RENAPO**")
                            st.write(f"-Nombre(s): {datos_gobierno["nombres"]}")
                            st.write(f"Apellido Paterno: {datos_gobierno['primer_apellido']}")
                            st.write(f"Apellido Materno: {datos_gobierno['segundo_apellido']}")








