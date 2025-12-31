import sqlite3
import pokebase as pb
from config import Config


def preparar_y_rellenar():
    # 1. CONEXIÓN
    conn = sqlite3.connect(Config.DB_PATH)
    cursor = conn.cursor()

    # 2. ASEGURAR COLUMNAS (ALTER TABLE si no existen)
    print("--- COMPROBANDO ESTRUCTURA DE LA TABLA ---")
    columnas_a_añadir = {
        "height": "DECIMAL(10,2)",
        "description": "VARCHAR(500)"
    }

    # Obtenemos las columnas actuales de la tabla
    cursor.execute("PRAGMA table_info(PokeEspecie)")
    columnas_existentes = [col[1] for col in cursor.fetchall()]

    for col_nombre, col_tipo in columnas_a_añadir.items():
        if col_nombre not in columnas_existentes:
            try:
                print(f"Añadiendo columna faltante: {col_nombre}...")
                cursor.execute(f"ALTER TABLE PokeEspecie ADD COLUMN {col_nombre} {col_tipo}")
                conn.commit()
            except sqlite3.OperationalError as e:
                print(f"Error al añadir {col_nombre}: {e}")
        else:
            print(f"Columna '{col_nombre}' ya existe.")

    # 3. ACTUALIZACIÓN DE DATOS DESDE POKEAPI
    print("\n--- INICIANDO ACTUALIZACIÓN DESDE POKEAPI ---")

    # Obtenemos los IDs que ya tenemos en la base de datos para actualizarlos
    cursor.execute("SELECT id_pokedex, name FROM PokeEspecie ORDER BY id_pokedex")
    pokemons = cursor.fetchall()

    if not pokemons:
        print("ALERTA: No hay Pokémon en la tabla PokeEspecie para actualizar.")
        return

    for p_id, p_name in pokemons:
        try:
            # Datos de Altura (Endpoint Pokemon)
            # La API devuelve decímetros, convertimos a metros
            p_data = pb.pokemon(p_id)
            height_m = p_data.height / 10

            # Datos de Descripción (Endpoint Species)
            s_data = pb.pokemon_species(p_id)
            descripcion = "No description available."

            # Buscamos la descripción en inglés ('en')
            for entry in s_data.flavor_text_entries:
                if entry.language.name == "en":
                    # Limpiamos caracteres raros de la PokeAPI (\n y \f)
                    descripcion = entry.flavor_text.replace('\n', ' ').replace('\f', ' ')
                    break

            # Guardamos los nuevos datos
            cursor.execute("""
                UPDATE PokeEspecie 
                SET height = ?, description = ? 
                WHERE id_pokedex = ?
            """, (height_m, descripcion, p_id))

            print(f"✅ [{p_id}] {p_name}: H={height_m}m | Desc: {descripcion[:50]}...")

            # Commit cada 10 para no perder progreso
            if p_id % 10 == 0:
                conn.commit()

        except Exception as e:
            print(f"❌ Error en ID {p_id} ({p_name}): {e}")

    conn.commit()
    conn.close()
    print("\n--- PROCESO FINALIZADO CON ÉXITO ---")


if __name__ == "__main__":
    preparar_y_rellenar()