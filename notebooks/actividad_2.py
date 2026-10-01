import sys
import os
import pandas as pd
import numpy as np
from sqlalchemy import text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config_conexion import obtener_motor

motor = obtener_motor()

# 1. Cargar el conjunto de trabajo
query = text("""
SELECT 
    a.id_alquiler,
    a.fecha_alquiler,
    a.fecha_devolucion,
    c.id_cliente,
    p.id_pelicula,
    p.duracion_alquiler,
    p.costo_reposicion,
    p.tarifa_alquiler
FROM alquiler a
INNER JOIN inventario i ON a.id_inventario = i.id_inventario
INNER JOIN pelicula p ON i.id_pelicula = p.id_pelicula
INNER JOIN cliente c ON a.id_cliente = c.id_cliente;
""")

df = pd.read_sql(query, motor)
df['fecha_alquiler'] = pd.to_datetime(df['fecha_alquiler'])
df['fecha_devolucion'] = pd.to_datetime(df['fecha_devolucion'])

print("==================================================")
print("1. FORMA Y TIPOS DE DATOS")
print(f"Dimensiones: {df.shape[0]} filas, {df.shape[1]} columnas\n")
print(df.dtypes)

print("\n==================================================")
print("2. VALORES NULOS Y DUPLICADOS")
nulos = df.isnull().sum()
pct_nulos = (df.isnull().sum() / len(df)) * 100
df_nulos = pd.DataFrame({'Nulos': nulos, 'Porcentaje (%)': pct_nulos})
print(df_nulos[df_nulos['Nulos'] > 0])

duplicados_pk = df.duplicated(subset=['id_alquiler']).sum()
print(f"\nDuplicados por clave primaria (id_alquiler): {duplicados_pk}")

print("\n==================================================")
print("3. CONTROL ESPECÍFICO DE VARIANTE: ALQUILERES SIN DEVOLUCIÓN")
sin_devolucion = df[df['fecha_devolucion'].isnull()]
total_sin_dev = len(sin_devolucion)
pct_sin_dev = (total_sin_dev / len(df)) * 100

print(f"Cantidad de alquileres sin devolución (censurados): {total_sin_dev} ({pct_sin_dev:.2f}%)")
print("Diagnóstico: NO son datos erróneos ni valores faltantes ordinarios;")
print("representan películas en préstamo al momento de corte del sistema (censura a derecha).")

print("\n==================================================")
print("4. REGLAS DE NEGOCIO PROPIAS")

# Regla 1: Inconsistencia temporal
viajes_tiempo = df[df['fecha_devolucion'] < df['fecha_alquiler']]
print(f"Regla 1 (fecha_devolucion < fecha_alquiler): {len(viajes_tiempo)} filas violan la regla.")

# Regla 2: Duración real de alquiler fuera de rango razonable (> 30 días para devueltos)
df_devueltos = df[df['fecha_devolucion'].notnull()].copy()
df_devueltos['dias_prestamo'] = (df_devueltos['fecha_devolucion'] - df_devueltos['fecha_alquiler']).dt.total_seconds() / 86400.0

duracion_extrema = df_devueltos[df_devueltos['dias_prestamo'] > 30]
print(f"Regla 2 (Devoluciones con más de 30 días de préstamo): {len(duracion_extrema)} filas violan la regla.")

print("\n==================================================")
print("5. OUTLIERS CON MÉTODO IQR (Días de préstamo en devueltos)")
q1 = df_devueltos['dias_prestamo'].quantile(0.25)
q3 = df_devueltos['dias_prestamo'].quantile(0.75)
iqr = q3 - q1
lim_inf = q1 - 1.5 * iqr
lim_sup = q3 + 1.5 * iqr

outliers = df_devueltos[(df_devueltos['dias_prestamo'] < lim_inf) | (df_devueltos['dias_prestamo'] > lim_sup)]
print(f"Q1: {q1:.2f} días | Q3: {q3:.2f} días | IQR: {iqr:.2f} días")
print(f"Límite inferior: {lim_inf:.2f} días | Límite superior: {lim_sup:.2f} días")
print(f"Cantidad de outliers: {len(outliers)}")
print("Diagnóstico: Son casos reales de retención prolongada permitidos por el negocio, no errores de tipeo.")

print("\n==================================================")
print("6. COMPARACIÓN EN MOTOR SQL (Control Espejo)")

query_espejo = text("""
SELECT 
    COUNT(CASE WHEN fecha_devolucion IS NULL THEN 1 END) AS nulos_devolucion,
    COUNT(CASE WHEN fecha_devolucion < fecha_alquiler THEN 1 END) AS violaciones_fechas
FROM alquiler;
""")
df_espejo = pd.read_sql(query_espejo, motor)
print("Resultados calculados en SQL Server:")
print(f"- Nulos en devolución: {df_espejo.iloc[0]['nulos_devolucion']} (Pandas: {total_sin_dev})")
print(f"- Violaciones temporales: {df_espejo.iloc[0]['violaciones_fechas']} (Pandas: {len(viajes_tiempo)})")
print("==================================================")