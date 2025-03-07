from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.service import Service 
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from bs4 import BeautifulSoup
import csv
import time

# Configurar Selenium
options = webdriver.ChromeOptions()
options.add_argument("--headless")  # Ejecutar en segundo plano
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# URL de búsqueda
URL_BUSQUEDA = "https://contrataciondelestado.es/wps/portal/licitaciones"

# Código CPV a buscar
CPV_OBJETIVO = ["72200000", "72300000"]

#Para entrada de CPV con input
#entrada_cpv = input("Introduce los codigos CPV separados por coma (por ejemplo: 72200000,72300000): ")
#CPV_OBJETIVO = [cpv.strip() for cpv in entrada_cpv.split(',')]

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
        print("Pagina licitaciones cargada")
    except Exception as e:
        print(f"Error al acceder al buscador de licitaciones: {e}")


def seleccionar_estado():
    """Selecciona el estado 'Licitaciones en plazo'."""
    try:
        select_element = driver.find_element(By.ID, "viewns_Z7_AVEQAI930OBRD02JPMTPG21004_:form1:estadoLici")
        select = Select(select_element)
        select.select_by_value("PUB")  # Seleccionar 'Publicada'
        time.sleep(3)
        print("Estado Publicado seleccionado")
    except Exception as e:
        print(f"No se pudo seleccionar el estado: {e}")

def introducir_cpv(cpv):
    """Introduce un CPV en el campo correspondiente y lo añade correctamente."""
    try:
        # Localizar el input
        cpv_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[contains(@id, 'cpvMultiple:codigoCpv')]"))
        )
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//input[contains(@id, 'cpvMultiple:codigoCpv')]")))

        # Borrar y escribir el CPV
        cpv_input.clear()
        time.sleep(1)
        cpv_input.send_keys(cpv)
        time.sleep(1)
        cpv_input.send_keys(Keys.TAB)
        time.sleep(2)

        # Buscar botón 'Añadir' correctamente
        boton_anyadir = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "viewns_Z7_AVEQAI930OBRD02JPMTPG21004_:form1:cpvMultiplebuttonAnyadirMultiple"))
        )

        # Verificar si el botón es visible e interactuable antes de hacer click
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
            print("Busqueda realizada")
        else:
            print("El botón de buscar no esta disponible")
    except Exception as e:
        print(f"Error al realizar la búsqueda: {e}")

    except Exception as e:
        print(f"Error en la búsqueda CPV: {e}")

def extraer_datos():
    """Extrae datos de la tabla de licitaciones y los guarda en CSV."""
    soup = BeautifulSoup(driver.page_source, "html.parser")
    tabla = soup.find("table", id="myTablaBusquedaCustom")

    if not tabla:
        print("No se encontró la tabla de licitaciones.")
        return []

    licitaciones = []
    for fila in tabla.find_all("tr")[1:]:  # Omitimos la cabecera
        celdas = fila.find_all("td")

        # Si alguna celda falta, completamos con "N/A" para que no falle el proceso
        while len(celdas) < 6:
            celdas.append("N/A")  # Añadimos un valor por defecto si faltan celdas

        # Verificamos que las celdas son objetos <td> y no cadenas
        try:
            expediente = celdas[0].text.strip() if isinstance(celdas[0], str) is False else "N/A"
            tipo_contrato = celdas[1].text.strip() if isinstance(celdas[1], str) is False else "N/A"
            estado = celdas[2].text.strip() if isinstance(celdas[2], str) is False else "N/A"
            importe = celdas[3].text.strip() if isinstance(celdas[3], str) is False else "N/A"
            presentacion = celdas[4].text.strip() if isinstance(celdas[4], str) is False else "N/A"
            organo_contractante = celdas[5].text.strip() if isinstance(celdas[5], str) is False else "N/A"
            enlace = celdas[0].find("a")["href"] if celdas[0].find("a") else "N/A"
        except Exception as e:
            print(f"Error al procesar una fila: {e}")
            continue  

        licitaciones.append((expediente, tipo_contrato, estado, importe, presentacion, organo_contractante, enlace))

    return licitaciones

def manejar_paginacion():
    """Maneja la paginación y extrae datos de todas las páginas."""
    licitaciones_totales = []
    
    while True:
        # Extraer datos de la página actual
        licitaciones = extraer_datos()
        if not licitaciones:
            print("No se encontraron licitaciones en esta página.")
            break
        
        # Añadir las licitaciones de esta página a la lista total
        licitaciones_totales.extend(licitaciones)
        
        # Buscar el botón "Siguiente"
        try:
            boton_siguiente = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "viewns_Z7_AVEQAI930OBRD02JPMTPG21004_:form1:footerSiguiente"))
            )
            if boton_siguiente.is_displayed() and boton_siguiente.is_enabled():
                # Hacer click en el botón "Siguiente"
                boton_siguiente.click()
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                time.sleep(3)  # Esperar a que la página cargue completamente
            else:
                print("No se puede hacer clic en el botón 'Siguiente'. Finalizando paginación.")
                break  # No hay más páginas para cargar
        except (NoSuchElementException, TimeoutException):
            print("No se encontro el boton 'Siguiente'. Se ha llegado al final de la paginacion")
            break
        except Exception as e:
            print(f"No se pudo encontrar o hacer click en el botón 'Siguiente': {e}")
            break  # No hay más páginas para cargar
    
    return licitaciones_totales


def guardar_en_csv(licitaciones, archivo="licitaciones.csv"):
    """Guarda los datos en CSV."""
    with open(archivo, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Expediente", "Tipo de contrato", "Estado", "Importe", "Presentación", "Órgano de Contratación"])
        writer.writerows(licitaciones)

# Ejecutar proceso
print("Iniciando proceso de búsqueda...")
navegar_a_licitaciones()
seleccionar_estado()
for cpv in CPV_OBJETIVO:
    introducir_cpv(cpv)
realizar_busqueda()
licitaciones_totales = manejar_paginacion()
if licitaciones_totales:
    guardar_en_csv(licitaciones_totales)
else:
    print("No se encontraron licitaciones para guardar.")
print("Proceso finalizado")

driver.quit()
