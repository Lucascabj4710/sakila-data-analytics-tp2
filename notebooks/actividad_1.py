import sys
import os
import time
import pandas as pd
from sqlalchemy import text

# Agregar la raíz del proyecto al path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config_conexion import obtener_motor

motor = obtener_motor()

# 1. Extracción parametrizada (consigna: NUNCA usar f-strings ni concatenación de valores)
fecha_corte = '2005-01-01'

query_extraccion = text("""
SELECT 
    a.id_alquiler,
    a.fecha_alquiler,
    a.fecha_devolucion,
    c.id_cliente,
    c.nombre AS nombre_cliente,
    c.apellido AS apellido_cliente,
    p.id_pelicula,
    p.titulo,
    p.duracion_alquiler,
    p.costo_reposicion,
    p.tarifa_alquiler,
    cat.nombre AS categoria
FROM alquiler a
INNER JOIN inventario i ON a.id_inventario = i.id_inventario
INNER JOIN pelicula p ON i.id_pelicula = p.id_pelicula
INNER JOIN cliente c ON a.id_cliente = c.id_cliente
LEFT JOIN pelicula_categoria pc ON p.id_pelicula = pc.id_pelicula
LEFT JOIN categoria cat ON pc.id_categoria = cat.id_categoria
WHERE a.fecha_alquiler >= :fecha
ORDER BY a.fecha_alquiler ASC;
""")

print("Cargando datos con pandas.read_sql parametrizado...")
df_alquileres = pd.read_sql(query_extraccion, motor, params={"fecha": fecha_corte})
print(f"Filas recuperadas: {len(df_alquileres)}")

# 2. Comparación de Métrica: Promedio de costo de reposición
# Enfoque A: 100% en SQL Server
t0_sql = time.perf_counter()
query_metrica_sql = text("""
SELECT AVG(CAST(p.costo_reposicion AS FLOAT)) AS promedio_costo
FROM alquiler a
INNER JOIN inventario i ON a.id_inventario = i.id_inventario
INNER JOIN pelicula p ON i.id_pelicula = p.id_pelicula
WHERE a.fecha_alquiler >= :fecha
""")
df_res_sql = pd.read_sql(query_metrica_sql, motor, params={"fecha": fecha_corte})
t1_sql = time.perf_counter()
tiempo_sql = t1_sql - t0_sql
promedio_sql = df_res_sql.iloc[0, 0]

# Enfoque B: 100% en Pandas sobre el DataFrame cargado
t0_pd = time.perf_counter()
promedio_pandas = df_alquileres['costo_reposicion'].astype(float).mean()
t1_pd = time.perf_counter()
tiempo_pandas = t1_pd - t0_pd

print("\n--- COMPARACIÓN DE RESULTADOS Y TIEMPOS (ACTIVIDAD 1) ---")
print(f"Métrica en SQL Server : {promedio_sql:.4f} (Tiempo: {tiempo_sql:.6f} seg)")
print(f"Métrica en Pandas     : {promedio_pandas:.4f} (Tiempo: {tiempo_pandas:.6f} seg)")
print(f"Diferencia entre ambos: {abs(promedio_sql - promedio_pandas):.8f}")