# rellenar_vaina.py
from app.database.GestorBD import GestorBD
from app import init_db

# 1. Aseguramos que las tablas existan
init_db()

# 2. Instanciamos el gestor
db = GestorBD()

# 3. Lanzamos la carga MASIVA
print("--- INICIANDO CARGA INDEPENDIENTE ---")
db.cargar_toda_la_base_de_datos()