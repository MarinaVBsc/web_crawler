from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from bs4 import BeautifulSoup
import sqlite3
import csv
import time
import json
from datetime import datetime
import os

# Configurar Selenium
options = webdriver.ChromeOptions()
options.add_argument("--headless")  # Ejecutar en segundo plano
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

#Agregar User-Agent
user_agent = "Mozilla/5.0 (compatible; MiBot/1.0)"
options.add_argument(f"user-agent={user_agent}")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# Cargar configuracion desde archivo config.json
def cargar_configuracion():
    try:
        with open("config.json", "r") as archivo_config:
            configuracion = json.load(archivo_config)
        return configuracion
    except Exception as e:
        print(f"Error al cargar el archivo de configuracion: {e}")
        return None
    
# Cargar configuración
config = cargar_configuracion()
if config:
    estados = config["estados"]
    cpvs = config["cpvs"]
    tiempo_espera_click = config["tiempo_espera_click"]
    max_paginas = config["max_paginas"]
    URL_BUSQUEDA = config["url_busqueda"]  # Cargar la URL de búsqueda
    print("Datos configuracion cargados")

def main():

    # Navegar a licitaciones
    navegar_a_licitaciones()

    # Seleccionar estado
    for estado in estados:
        print(f"Estado seleccionado: {estado}")
        seleccionar_estado(estado)

    # Seleccionar CPVs
    for cpv in cpvs:
        print(f"CPV seleccionado: {cpv}")
        introducir_cpv(cpv)

    # Realizar la búsqueda
    realizar_busqueda()

    # Manejar paginación y guardar datos
    licitaciones_totales = manejar_paginacion(max_paginas)

    if licitaciones_totales:
        guardar_en_csv(licitaciones_totales)
    else:
        print("No se encontraron licitaciones para guardar.")

    print("Proceso finalizado")
    driver.quit()

def navegar_a_licitaciones():
    """Accede al buscador de licitaciones."""
    driver.get(URL_BUSQUEDA)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    time.sleep(3)

    try:
        boton_licitaciones = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//img[contains(@src, 'iconoFormularioLicitaciones.png')]/ancestor::a"))
        )
        boton_licitaciones.click()
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(3)
        print("Página licitaciones cargada")
    except Exception as e:
        print(f"Error al acceder al buscador de licitaciones: {e}")

def seleccionar_estado(estado):
    """Selecciona el estado dado (e.g., 'Publicada')."""
    try:
        select_element = driver.find_element(By.ID, "viewns_Z7_AVEQAI930OBRD02JPMTPG21004_:form1:estadoLici")
        select = Select(select_element)
        select.select_by_value(estado)  # Seleccionar el estado (ej. 'PUB' para Publicada)
        time.sleep(3)
        print(f"Estado {estado} seleccionado")
    except Exception as e:
        print(f"No se pudo seleccionar el estado: {e}")

def introducir_cpv(cpv):
    """Introduce un CPV en el campo correspondiente y lo añade correctamente."""
    try:
        cpv_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[contains(@id, 'cpvMultiple:codigoCpv')]"))
        )
        cpv_input.clear()
        cpv_input.send_keys(cpv)
        time.sleep(1)
        cpv_input.send_keys(Keys.TAB)
        time.sleep(2)

        boton_anyadir = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "viewns_Z7_AVEQAI930OBRD02JPMTPG21004_:form1:cpvMultiplebuttonAnyadirMultiple"))
        )

        if boton_anyadir.is_displayed() and boton_anyadir.is_enabled():
            ActionChains(driver).move_to_element(boton_anyadir).click().perform()
            print(f"CPV {cpv} añadido a la lista")
        else:
            print(f"Botón 'Añadir' no disponible para CPV {cpv}")
        time.sleep(5)
    except Exception as e:
        print(f"Error al introducir CPV {cpv}: {e}")

def realizar_busqueda():
    """Realiza la búsqueda con los CPVs añadidos."""
    try:
        boton_buscar = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "viewns_Z7_AVEQAI930OBRD02JPMTPG21004_:form1:button1"))
        )
        if boton_buscar.is_displayed() and boton_buscar.is_enabled():
            boton_buscar.click()
            print("Búsqueda realizada")
        else:
            print("El botón de buscar no está disponible")
    except Exception as e:
        print(f"Error al realizar la búsqueda: {e}")

def extraer_datos():
    """Extrae datos de la tabla de licitaciones y los guarda en CSV."""
    soup = BeautifulSoup(driver.page_source, "html.parser")
    tabla = soup.find("table", id="myTablaBusquedaCustom")

    if not tabla:
        print("No se encontró la tabla de licitaciones.")
        return []

    licitaciones = []
    filas = tabla.find_all("tr", class_= ["rowClass1", "rowClass2"])
    print(f"Se encontraron {len(filas)} filas de licitaciones")
    for fila in filas:
        celdas = fila.find_all("td")
        print(f"Datos de las celdas encontradas: {[celda.text.strip() for celda in celdas]}") 
    
        if len(celdas) < 6:        
            continue 
        expediente = celdas[0].text.strip() if isinstance(celdas[0], str) is False else "N/A"
        tipo_contrato = celdas[1].text.strip() if isinstance(celdas[1], str) is False else "N/A"
        estado = celdas[2].text.strip() if isinstance(celdas[2], str) is False else "N/A"
        importe = celdas[3].text.strip() if isinstance(celdas[3], str) is False else "N/A"
        presentacion = celdas[4].text.strip() if isinstance(celdas[4], str) is False else "N/A"
        organo_contractante = celdas[5].text.strip() if isinstance(celdas[5], str) is False else "N/A"

        div_tag = fila.find("div")  # Buscar el <div> que contiene los enlaces
        if div_tag:
            # Buscamos todos los enlaces dentro del <div> y seleccionamos el segundo
            enlaces = div_tag.find_all("a", href=True)
            if len(enlaces) > 1:  # Si hay más de un enlace
                enlace = enlaces[1]["href"]  # Tomamos el segundo enlace
                print(f"Enlace encontrado (antes de procesamiento): {enlace}")

                # Verificamos si el enlace es relativo (comienza con '#')
                if enlace.startswith("#"):
                    print(f"Enlace relativo encontrado, intentando construir el enlace absoluto...")
                    enlace = "https://contrataciondelestado.es" + enlace[1:]  # Eliminar '#' y construir la URL
                    print(f"Enlace absoluto construido: {enlace}")
                elif enlace.startswith("https://"):
                    print(f"Enlace absoluto encontrado: {enlace}")
                else:
                    # Si no comienza con https:// ni con #, lo tratamos como N/A
                    enlace = "N/A"
            else:
                enlace = "N/A"  # Si no encontramos suficientes enlaces
        else:
            enlace = "N/A"  # Si no encontramos el <div> o el enlace

        licitaciones.append((expediente, tipo_contrato, estado, importe, presentacion, organo_contractante, enlace))

    return licitaciones

def manejar_paginacion(max_paginas):
    """Maneja la paginación y extrae datos de todas las páginas."""
    licitaciones_totales = []
    pagina_actual = 1

    while pagina_actual <= max_paginas:
        print(f"Extrayendo datos de la pagina {pagina_actual}...")
        licitaciones = extraer_datos()
        if not licitaciones:
            print("No se encontraron licitaciones en esta página.")
            break

        licitaciones_totales.extend(licitaciones)

        try:
            boton_siguiente = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "viewns_Z7_AVEQAI930OBRD02JPMTPG21004_:form1:footerSiguiente"))
            )
            if boton_siguiente.is_displayed() and boton_siguiente.is_enabled():
                boton_siguiente.click()
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                time.sleep(3)
                pagina_actual += 1
            else:
                print("No se puede hacer clic en el botón 'Siguiente'. Finalizando paginación.")
                break
        except (NoSuchElementException, TimeoutException):
            print("No se encontró el botón 'Siguiente'. Se ha llegado al final de la paginación.")
            break

    return licitaciones_totales

def guardar_en_csv(licitaciones, archivo="licitaciones.csv"):
    """Guarda los datos en CSV."""
    with open(archivo, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["EXPEDIENTE", "TIPO_CONTRATO", "ESTADO", "IMPORTE", "PRESENTACION", "ORGANO_CONTRACTANTE", "ENLACE"])
        writer.writerows(licitaciones)

def crear_base_de_datos():
    """Crea la base de datos y la tabla si no existen, incluyendo licitacion_id como la clave primaria"""
    
    # Si el archivo de base de datos ya existe, eliminarlo para crear uno nuevo
    if os.path.exists('licitaciones.db'):
        os.remove('licitaciones.db')
    
    # Conectar a la base de datos
    conexion = sqlite3.connect('licitaciones.db')
    cursor = conexion.cursor()

    # Crear la tabla con las columnas en mayúsculas
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS licitaciones (
                   LICITACION_ID INTEGER PRIMARY KEY AUTOINCREMENT,
                   EXPEDIENTE TEXT,
                   TIPO_CONTRATO TEXT,
                   ESTADO TEXT,
                   IMPORTE REAL,
                   PRESENTACION DATE,
                   ORGANO_CONTRACTANTE TEXT,
                   ENLACE TEXT
                   )
    ''')
    conexion.commit()
    conexion.close()

def limpiar_importe(importe_str):
    """Convierte el importe a tipo float y maneja el formato '€' y otros caracteres"""
    try:
        # Eliminar cualquier espacio, signo de euro y convertir el formato
        importe_str = importe_str.replace('€', '').replace(' ', '').replace('.', '').replace(',', '.')
        return float(importe_str)
    except ValueError:
        print(f"Error al convertir el importe: {importe_str}")
        return None

def guardar_en_base_de_datos(csv_file):
    """Guarda las licitaciones en la base de datos SQLite"""
    conexion = sqlite3.connect('licitaciones.db')
    cursor = conexion.cursor()

    # Leer el archivo CSV y cargar los datos
    try:
        with open(csv_file, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)

            # Verificar que el archivo se lee correctamente
            print("CSV abierto correctamente")

            # Insertar cada fila del CSV en la base de datos
            for licitacion in reader:
                if not any(licitacion.values()):  
                    continue

                # Normalizar las claves a mayúsculas
                licitacion = {key.upper(): value for key, value in licitacion.items()}

                # Verificar si los valores contienen 'N/A' o valores vacíos
                if 'N/A' in licitacion or any(v == '' for v in licitacion):
                    print(f"Fila ignorada (N/A o vacía): {licitacion}")
                    continue  

                # Limpiar los valores de cada columna
                licitacion = {key: value.replace('"', '').strip() if isinstance(value, str) else value
                              for key, value in licitacion.items()}
           
                # Convertir el importe
                            
                if 'IMPORTE' in licitacion and licitacion['IMPORTE']:
                    licitacion['IMPORTE'] = limpiar_importe(licitacion['IMPORTE'])

                # Convertir la fecha de presentación al formato adecuado
                if 'PRESENTACION' in licitacion and licitacion['PRESENTACION']:
                    try:
                        licitacion['PRESENTACION'] = datetime.strptime(licitacion['PRESENTACION'], '%d/%m/%Y').date()
                    except ValueError:
                        print(f"Error al convertir la fecha: {licitacion['PRESENTACION']}")
                        licitacion['PRESENTACION'] = None

                    # Verificar que todos los campos necesarios están presentes antes de ejecutar el INSERT
                required_keys = ['EXPEDIENTE', 'TIPO_CONTRATO', 'ESTADO', 'IMPORTE', 'PRESENTACION', 'ORGANO_CONTRACTANTE', 'ENLACE']
                if all(key in licitacion and licitacion[key] is not None for key in required_keys):
                    # Insertar los datos en la base de datos de manera parametrizada
                    cursor.execute('''INSERT INTO licitaciones (EXPEDIENTE, TIPO_CONTRATO, ESTADO, IMPORTE, PRESENTACION, ORGANO_CONTRACTANTE, ENLACE)
                                      VALUES (:EXPEDIENTE, :TIPO_CONTRATO, :ESTADO, :IMPORTE, :PRESENTACION, :ORGANO_CONTRACTANTE, :ENLACE)''', 
                                   licitacion)
                else:
                    print(f"Fila ignorada (faltan campos): {licitacion}")
                
        # Guardar los cambios y cerrar la conexión
        conexion.commit()
        print("Datos insertados correctamente.")
    except Exception as e:
        print(f"Error al procesar el archivo CSV: {e}")
    finally:
        conexion.close()


# Ejecutar proceso
if __name__ == "__main__":
    main()

# Crear la base de datos y la tabla (sin la columna 'enlace')
crear_base_de_datos()

# Llamar a la función para insertar los datos del CSV
guardar_en_base_de_datos('licitaciones.csv')  