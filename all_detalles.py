import sqlite3
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Función para inicializar el navegador de Selenium
def iniciar_navegador():
    chrome_options = Options()
    chrome_options.add_argument("--headless") 
    return webdriver.Chrome(options=chrome_options)

# Función para registrar cambios en la tabla de auditoría
def registrar_cambio(conexion, licitacion_id, operacion, columna_modificada, valor_anterior, valor_nuevo):
    cursor = conexion.cursor()
    query = '''
    INSERT INTO auditoria_cambios (licitacion_id, operacion, columna_modificada, valor_anterior, valor_nuevo)
    VALUES (?, ?, ?, ?, ?)
    '''
    cursor.execute(query, (licitacion_id, operacion, columna_modificada, valor_anterior, valor_nuevo))
    conexion.commit()

# Función para comparar y registrar cambios (INSERT y UPDATE)
def comparar_y_registrar_cambios(conexion, registros_nuevos):
    cursor = conexion.cursor()

    # Obtener los registros actuales de la tabla detalles_licitaciones
    cursor.execute('SELECT * FROM detalles_licitaciones')
    registros_existentes = cursor.fetchall()

    # Crear un diccionario con los registros existentes para compararlos por licitacion_id
    registros_existentes_dict = {registro[0]: registro for registro in registros_existentes}

    for registro_nuevo in registros_nuevos:
        licitacion_id = registro_nuevo[0]
        if licitacion_id in registros_existentes_dict:
            # El registro ya existe, hacer la comparación de cada columna
            registro_existente = registros_existentes_dict[licitacion_id]

            # Comparar columna por columna
            for i, columna_nueva in enumerate(registro_nuevo[1:], 1):  # Excluyendo licitacion_id
                columna_nombre = cursor.description[i][0]
                valor_existente = registro_existente[i]
                if columna_nueva != valor_existente:
                    # Si los valores son diferentes, registrar el cambio
                    registrar_cambio(conexion, licitacion_id, 'UPDATE', columna_nombre, valor_existente, columna_nueva)
        else:
            # El registro no existe, registrarlo como un nuevo INSERT
            for i, columna_nueva in enumerate(registro_nuevo[1:], 1):  # Excluyendo licitacion_id
                columna_nombre = cursor.description[i][0]
                registrar_cambio(conexion, licitacion_id, 'INSERT', columna_nombre, 'N/A', columna_nueva)


# Función para crear las tablas necesarias
def crear_tablas():
    conexion = sqlite3.connect('licitaciones.db')
    cursor = conexion.cursor()

    cursor.execute("DROP TABLE IF EXISTS detalles_licitaciones")
    cursor.execute("DROP TABLE IF EXISTS detalles_licitaciones_temp")
    cursor.execute("DROP TABLE IF EXISTS licitaciones_documentos")
    cursor.execute("DROP TABLE IF EXISTS licitaciones_documentos_generales")

   # Crear la tabla detalles_licitaciones sin la clave foránea
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS detalles_licitaciones (
            licitacion_id TEXT PRIMARY KEY,
            id_publicacion TEXT,
            organo_contratacion TEXT,
            id_organo TEXT,
            estado_licitacion TEXT,
            objeto_contrato TEXT,
            financiacion_ue TEXT,
            presupuesto_base TEXT,
            valor_estimado TEXT,
            tipo_contrato TEXT,
            codigo_cpv TEXT,
            lugar_ejecucion TEXT,
            sistema_contratacion TEXT,
            procedimiento TEXT,
            tramitacion TEXT,
            metodo_presentacion TEXT,
            fecha_fin_presentacion TEXT,
            resultado TEXT,
            adjudicatario TEXT,
            num_licitadores TEXT,
            importe_adjudicacion TEXT
        )
    ''')

    # Crear una nueva tabla con la restricción de clave foránea
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS detalles_licitaciones_temp (
            licitacion_id TEXT PRIMARY KEY,
            id_publicacion TEXT,
            organo_contratacion TEXT,
            id_organo TEXT,
            estado_licitacion TEXT,
            objeto_contrato TEXT,
            financiacion_ue TEXT,
            presupuesto_base TEXT,
            valor_estimado TEXT,
            tipo_contrato TEXT,
            codigo_cpv TEXT,
            lugar_ejecucion TEXT,
            sistema_contratacion TEXT,
            procedimiento TEXT,
            tramitacion TEXT,
            metodo_presentacion TEXT,
            fecha_fin_presentacion TEXT,
            resultado TEXT,
            adjudicatario TEXT,
            num_licitadores TEXT,
            importe_adjudicacion TEXT,
            FOREIGN KEY (licitacion_id) REFERENCES licitaciones (licitacion_id)
        )
    ''')

    # Copiar los datos de la tabla original a la nueva tabla
    cursor.execute('''
        INSERT INTO detalles_licitaciones_temp (licitacion_id, id_publicacion, organo_contratacion,
        id_organo, estado_licitacion, objeto_contrato, financiacion_ue, presupuesto_base,
        valor_estimado, tipo_contrato, codigo_cpv, lugar_ejecucion, sistema_contratacion,
        procedimiento, tramitacion, metodo_presentacion,fecha_fin_presentacion,resultado, adjudicatario, num_licitadores,
        importe_adjudicacion)
        SELECT licitacion_id, id_publicacion, organo_contratacion, id_organo, estado_licitacion,
        objeto_contrato, financiacion_ue, presupuesto_base, valor_estimado, tipo_contrato,
        codigo_cpv, lugar_ejecucion, sistema_contratacion, procedimiento, tramitacion, metodo_presentacion, fecha_fin_presentacion, resultado,
        adjudicatario, num_licitadores, importe_adjudicacion
        FROM detalles_licitaciones
    ''')

    # Eliminar la tabla original
    cursor.execute("DROP TABLE IF EXISTS detalles_licitaciones")

    # Renombrar la tabla temporal para que tenga el nombre de la tabla original
    cursor.execute("ALTER TABLE detalles_licitaciones_temp RENAME TO detalles_licitaciones")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS licitaciones_documentos (
            documento_id INTEGER PRIMARY KEY AUTOINCREMENT,
            licitacion_id TEXT,
            fecha_publicacion_plataforma TEXT,
            tipo_documento TEXT,
            documento_html TEXT,
            doue_envio TEXT,
            doue_publicacion TEXT,
            FOREIGN KEY (licitacion_id) REFERENCES licitaciones (licitacion_id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS licitaciones_documentos_generales (
            documento_id INTEGER PRIMARY KEY AUTOINCREMENT,
            licitacion_id TEXT,
            fecha TEXT,
            tipo_documento TEXT,
            enlace_documento TEXT,
            FOREIGN KEY (licitacion_id) REFERENCES licitaciones (licitacion_id) ON DELETE CASCADE
        )
    ''')

     # Crear la tabla de auditoría para registrar los cambios
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS auditoria_cambios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        licitacion_id TEXT,
        operacion TEXT,  -- 'INSERT', 'UPDATE', 'DELETE'
        columna_modificada TEXT,
        valor_anterior TEXT,
        valor_nuevo TEXT,
        fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (licitacion_id) REFERENCES licitaciones (licitacion_id)
    )
    ''')

    conexion.commit()
    conexion.close()

def insertar_y_comparar_cambios(conexion, registros_nuevos):
    cursor = conexion.cursor()

    # Realizar el INSERT INTO (suponiendo que 'registros_nuevos' es una lista de tuplas)
    for registro_nuevo in registros_nuevos:
        cursor.execute('''
            INSERT OR REPLACE INTO detalles_licitaciones (licitacion_id, id_publicacion, organo_contratacion,
            id_organo, estado_licitacion, objeto_contrato, financiacion_ue, presupuesto_base,
            valor_estimado, tipo_contrato, codigo_cpv, lugar_ejecucion, sistema_contratacion,
            procedimiento, tramitacion, metodo_presentacion, fecha_fin_presentacion, resultado, adjudicatario,
            num_licitadores, importe_adjudicacion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', registro_nuevo)

    # Comparar los registros nuevos con los existentes y registrar los cambios
    comparar_y_registrar_cambios(conexion, registros_nuevos)

    conexion.commit()

def obtener_html(url, intentos=3):
    headers = {'User-Agent': 'Mozilla/5.0'}
    for i in range(intentos):
        try:
            response = requests.get(url, headers= headers, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except requests.RequestException as e:
            print(f"Error al obtener {url}: {e}. Reintentando ({i+1}/{intentos})...")
            time.sleep(2)
    return None

# Función para extraer el texto de un elemento de manera segura
def extraer_texto_de_elemento(soup, elemento_id):
    elemento = soup.find("span", id=elemento_id)
    if elemento:
        return elemento.text.strip()
    return "N/A"  

# Función para obtener detalles de una licitación
def obtener_licitacion_con_bs(driver, url, licitacion_id):
    driver.get(url)
    time.sleep(5)
    soup = BeautifulSoup(driver.page_source, "html.parser") 

    detalles = {}
    detalles['licitacion_id'] = licitacion_id
    detalles['id_publicacion'] = soup.find('span', id=lambda x: x and 'text_IdPublicacionTED' in x).text.strip() if soup.find('span', id=lambda x: x and 'text_IdPublicacionTED' in x) else 'N/A'
    detalles['organo_contratacion'] = soup.find('span', id=lambda x: x and 'text_OC_con' in x).text.strip() if soup.find('span', id=lambda x: x and 'text_OC_con' in x) else 'N/A'
    detalles['id_organo'] = soup.find('span', id=lambda x: x and 'text_IdOrganoContratacion' in x).text.strip() if soup.find('span', id=lambda x: x and 'text_IdOrganoContratacion' in x) else 'N/A'
    detalles['estado_licitacion'] = soup.find('span', id=lambda x: x and 'text_Estado' in x).text.strip() if soup.find('span', id=lambda x: x and 'text_Estado' in x) else 'N/A'
    detalles['objeto_contrato'] = soup.find('span', id=lambda x: x and 'text_ObjetoContrato' in x).text.strip() if soup.find('span', id=lambda x: x and 'text_ObjetoContrato' in x) else 'N/A'
    detalles['financiacion_ue'] = soup.find('span', id=lambda x: x and 'text_FinanciacionUE' in x).text.strip() if soup.find('span', id=lambda x: x and 'text_FinanciacionUE' in x) else 'N/A'  
    detalles['presupuesto_base'] = soup.find('span', id=lambda x: x and 'text_Presupuesto' in x).text.strip() if soup.find('span', id=lambda x: x and 'text_Presupuesto' in x) else 'N/A'
    detalles['valor_estimado'] = soup.find('span', id=lambda x: x and 'text_ValorContrato' in x).text.strip() if soup.find('span', id=lambda x: x and 'text_ValorContrato' in x) else 'N/A'
    detalles['tipo_contrato'] = soup.find('span', id=lambda x: x and 'text_TipoContrato' in x).text.strip() if soup.find('span', id=lambda x: x and 'text_TipoContrato' in x) else 'N/A'
    detalles['codigo_cpv'] = soup.find('span', id=lambda x: x and 'text_CPV' in x).text.strip() if soup.find('span', id=lambda x: x and 'text_CPV' in x) else 'N/A'
    detalles['lugar_ejecucion'] = soup.find('span', id=lambda x: x and 'text_LugarEjecucion' in x).text.strip() if soup.find('span', id=lambda x: x and 'text_LugarEjecucion' in x) else 'N/A'
    detalles['sistema_contratacion'] = soup.find('span', id=lambda x: x and 'text_SistemaContratacion' in x).text.strip() if soup.find('span', id=lambda x: x and 'text_SistemaContratacion' in x) else 'N/A'
    detalles['procedimiento'] = soup.find('span', id=lambda x: x and 'text_Procedimiento' in x).text.strip() if soup.find('span', id=lambda x: x and 'text_Procedimiento' in x) else 'N/A'
    detalles['tramitacion'] = soup.find('span', id=lambda x: x and 'text_TipoTramitacion' in x).text.strip() if soup.find('span', id=lambda x: x and 'text_TipoTramitacion' in x) else 'N/A'
    detalles['metodo_presentacion'] = soup.find('span', id=lambda x: x and 'text_PresentacionOferta' in x).text.strip() if soup.find('span', id=lambda x: x and 'text_PresentacionOferta' in x) else 'N/A'
    detalles['fecha_fin_presentacion'] = soup.find('span', id=lambda x: x and 'text_FechaPresentacionOfertaConHora' in x).text.strip() if soup.find('span', id=lambda x: x and 'text_FechaPresentacionOfertaConHora' in x) else 'N/A'
    detalles['resultado'] = soup.find('span', id=lambda x: x and 'text_Resultado' in x).text.strip() if soup.find('span', id=lambda x: x and 'text_Resultado' in x) else 'N/A'
    detalles['adjudicatario'] = soup.find('span', id=lambda x: x and 'text_Adjudicatario' in x).text.strip() if soup.find('span', id=lambda x: x and 'text_Adjudicatario' in x) else 'N/A'
    detalles['num_licitadores'] = soup.find('span', id=lambda x: x and 'text_NumeroLicitadores' in x).text.strip() if soup.find('span', id=lambda x: x and 'text_NumeroLicitadores' in x) else 'N/A'
    detalles['importe_adjudicacion'] = soup.find('span', id=lambda x: x and 'text_ImporteAdjudicacion' in x).text.strip() if soup.find('span', id=lambda x: x and 'text_ImporteAdjudicacion' in x) else 'N/A'

    return detalles

# Funcion para insertar detalles en la base de datos
def insertar_detalles(detalles):
    conexion = sqlite3.connect('licitaciones.db')
    cursor = conexion.cursor()

    cursor.execute('''
        INSERT OR REPLACE INTO detalles_licitaciones (
        licitacion_id, id_publicacion, organo_contratacion, id_organo, estado_licitacion, objeto_contrato,
        financiacion_ue, presupuesto_base, valor_estimado, tipo_contrato, codigo_cpv, lugar_ejecucion,
        sistema_contratacion, procedimiento, tramitacion, metodo_presentacion,fecha_fin_presentacion,resultado, adjudicatario, num_licitadores,
        importe_adjudicacion)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        detalles["licitacion_id"], detalles["id_publicacion"], detalles["organo_contratacion"],
        detalles["id_organo"], detalles["estado_licitacion"], detalles["objeto_contrato"],
        detalles["financiacion_ue"], detalles["presupuesto_base"], detalles["valor_estimado"],
        detalles["tipo_contrato"], detalles["codigo_cpv"], detalles["lugar_ejecucion"],
        detalles["sistema_contratacion"], detalles["procedimiento"], detalles["tramitacion"],
        detalles["metodo_presentacion"], detalles["fecha_fin_presentacion"], detalles["resultado"],
        detalles["adjudicatario"], detalles["num_licitadores"], detalles["importe_adjudicacion"]
    ))

    conexion.commit()
    conexion.close()

#Funcion para obtener detalles licitacion
def obtener_detalles_licitacion(soup, licitacion_id):
    if not soup:
        return []
    
    rows = soup.select('table#myTablaDetalleVISUOE tbody tr')
    detalles = []
    for row in rows:
        fecha_publicacion_plataforma = row.select_one('td.fechaPubLeft')
        tipo_documento = row.select_one('td.tipoDocumento')
        documento = row.select_one('td.documentosPub a')
        doue_envio = row.select_one('td.fechaDOUE span')
        doue_publicacion = row.select_one('td.enlaceDOUE a')
        
        detalles.append({
            "licitacion_id": licitacion_id,
            "fecha_publicacion_plataforma": fecha_publicacion_plataforma.text.strip() if fecha_publicacion_plataforma else None,
            "tipo_documento": tipo_documento.text.strip() if tipo_documento else None,
            "documento_html": documento['href'].strip() if documento else None,
            "doue_envio": doue_envio.text.strip() if doue_envio else None,
            "doue_publicacion": doue_publicacion.text.strip() if doue_publicacion else None
        })
    return detalles

# Funcion para obtener los documentos de licitacion
def obtener_documentos(soup, licitacion_id, base_url):
    if not soup:
        return []
    
    documentos_generales = []
    tabla = soup.select_one('table#datosDocumentosGenerales')
    if tabla:
        filas = tabla.select('tr.rowClass1, tr.rowClass2')
        
        for fila in filas:
            fecha = fila.select_one('span[id*="textSfecha1PadreGen"]')
            tipo_documento = fila.select_one('span[id*="textStipo1PadreGen"]')
            enlace_element = fila.select_one('a[id*="linkVerDocPadreGen"]')
            enlace_documento = urljoin(base_url, enlace_element['href'].strip()) if enlace_element else None
            
            documentos_generales.append({
                "licitacion_id": licitacion_id,
                "fecha": fecha.text.strip() if fecha else None,
                "tipo_documento": tipo_documento.text.strip() if tipo_documento else None,
                "enlace_documento": enlace_documento
            })
    return documentos_generales

# Funcion para insertar datos
def insertar_documentos(detalles, tabla):
    if not detalles:
        return
    
    conexion = sqlite3.connect('licitaciones.db')
    cursor = conexion.cursor()
    
    if tabla == "licitaciones_documentos":
        cursor.executemany('''
            INSERT INTO licitaciones_documentos (licitacion_id, fecha_publicacion_plataforma, tipo_documento, documento_html, doue_envio, doue_publicacion)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', [(d["licitacion_id"], d["fecha_publicacion_plataforma"], d["tipo_documento"], d["documento_html"], d["doue_envio"], d["doue_publicacion"]) for d in detalles])
    
    elif tabla == "licitaciones_documentos_generales":
        cursor.executemany('''
            INSERT INTO licitaciones_documentos_generales (licitacion_id, fecha, tipo_documento, enlace_documento)
            VALUES (?, ?, ?, ?)
        ''', [(d["licitacion_id"], d["fecha"], d["tipo_documento"], d["enlace_documento"]) for d in detalles])
    
    conexion.commit()
    conexion.close()

# Función principal para procesar las licitaciones
def procesar_licitaciones():
    conexion = sqlite3.connect('licitaciones.db')
    cursor = conexion.cursor()
    cursor.execute('SELECT LICITACION_ID, ENLACE FROM licitaciones WHERE ENLACE IS NOT NULL')
    licitaciones = cursor.fetchall()
    conexion.close()
    
    driver = iniciar_navegador()
    
    for licitacion_id, enlace in licitaciones:
        print(f"Procesando {licitacion_id}...")
        soup = obtener_html(enlace)
        
        detalles = obtener_licitacion_con_bs(driver, enlace, licitacion_id)
        insertar_detalles(detalles)
        
        documentos= obtener_detalles_licitacion(soup, licitacion_id)
        insertar_documentos(documentos,"licitaciones_documentos")

        documentos_generales = obtener_documentos(soup, licitacion_id, enlace)
        insertar_documentos(documentos_generales, "licitaciones_documentos_generales")
    
    print("Procesamiento completado.")

# Crear tablas e iniciar el procesamiento de licitaciones
crear_tablas()
procesar_licitaciones()

