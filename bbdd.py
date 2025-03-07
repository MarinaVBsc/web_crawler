import sqlite3
import csv
from datetime import datetime
import os

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
                   ORGANO_CONTRACTANTE TEXT
                   )
    ''')
    conexion.commit()
    conexion.close()

def guardar_en_base_de_datos(csv_file):
    """Guarda las licitaciones en la base de datos SQLite filtradas por fecha de presentación posterior a marzo de 2025"""
    conexion = sqlite3.connect('licitaciones.db')
    cursor = conexion.cursor()

    # Leer el archivo CSV y cargar los datos
    try:
        with open(csv_file, mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)

            # Verificar que el archivo se lee correctamente
            print("CSV abierto correctamente")

            # Saltar la cabecera del archivo CSV
            next(reader, None)

            # Insertar cada fila del CSV en la base de datos
            for licitacion in reader:
                if not licitacion:  # Asegurarse de que la fila no esté vacía
                    continue

                # Verificar si los valores contienen 'N/A' o valores vacíos
                if 'N/A' in licitacion or any(v == '' for v in licitacion):
                    print(f"Fila ignorada (N/A o vacía): {licitacion}")
                    continue  # Ignorar filas con valores no válidos

                # Limpiar los valores de cada columna
                expediente, tipo_contrato, estado, importe, presentacion, organo_contractante = licitacion[:6]

                # Eliminar comillas innecesarias de los valores
                expediente = expediente.replace('"', '').strip()
                tipo_contrato = tipo_contrato.replace('"', '').strip()
                estado = estado.replace('"', '').strip()
                organo_contractante = organo_contractante.replace('"', '').strip()

                # Convertir el importe
                try:
                    importe = float(importe.replace('.', '').replace(',', '.').replace('€', '').strip())
                except ValueError:
                    print(f"Error al convertir el importe: {importe}")  # Depuración de importe
                    importe = None  # Si no se puede convertir, asignar None

                # Convertir la fecha de presentación al formato adecuado
                try:
                    presentacion = datetime.strptime(presentacion, '%d/%m/%Y').date()
                except ValueError:
                    print(f"Error al convertir la fecha: {presentacion}")  # Depuración de fecha
                    presentacion = None  # Si no se puede convertir, asignar None

                # Filtrar licitaciones con fecha posterior a febrero de 2025
                if presentacion and presentacion > datetime(2025, 2, 28).date():
                    # Verificación de los valores antes de la inserción
                    print(f"Ingresando en base de datos: {expediente}, {tipo_contrato}, {estado}, {importe}, {presentacion}, {organo_contractante}")

                    # Insertar los datos en la base de datos, la columna LICITACION_ID se genera automáticamente
                    cursor.execute('''INSERT INTO licitaciones (EXPEDIENTE, TIPO_CONTRATO, ESTADO, IMPORTE, PRESENTACION, ORGANO_CONTRACTANTE)
                                      VALUES (?, ?, ?, ?, ?, ?)''', 
                                   (expediente, tipo_contrato, estado, importe, presentacion, organo_contractante))
                else:
                    print(f"Fila ignorada (fecha de presentación antes de abril de 2025): {licitacion}")

        # Guardar los cambios y cerrar la conexión
        conexion.commit()
        print("Datos insertados correctamente.")
    except Exception as e:
        print(f"Error al procesar el archivo CSV: {e}")
    finally:
        conexion.close()


# Crear la base de datos y la tabla (sin la columna 'enlace')
crear_base_de_datos()

# Llamar a la función para insertar los datos del CSV
guardar_en_base_de_datos('licitaciones.csv')  