import sqlite3
import pokebase as pb
import time
from config import Config

# Rango de Pokémon a descargar (Gen 9 llega hasta 1025)
TOTAL_POKEMON = 1025


def conectar_bd():
    return sqlite3.connect(Config.DB_PATH)


def cargar_tipos_y_efectividad(cursor):
    """
    Carga los 18 tipos elementales y llena la tabla 'Efectivo'
    para que funcione la calculadora de compatibilidad.
    """
    print("\n--- 1. CARGANDO TIPOS Y TABLA DE EFECTIVIDAD ---")
    tipos_base = [
        "normal", "fighting", "flying", "poison", "ground", "rock", "bug",
        "ghost", "steel", "fire", "water", "grass", "electric", "psychic",
        "ice", "dragon", "dark", "fairy"
    ]

    for tipo_nombre in tipos_base:
        try:
            # 1. Insertar el Tipo en la tabla maestra
            t_cap = tipo_nombre.capitalize()
            cursor.execute("INSERT OR IGNORE INTO Tipo (name) VALUES (?)", (t_cap,))

            # 2. Obtener datos de la API para la tabla 'Efectivo'
            # Esto define quién pega fuerte a quién.
            api_type = pb.type_(tipo_nombre)

            # Diccionario para mapear relaciones
            relaciones = {}

            # Doble daño (x2.0)
            for target in api_type.damage_relations.double_damage_to:
                relaciones[target.name] = 2.0

            # Mitad de daño (x0.5)
            for target in api_type.damage_relations.half_damage_to:
                relaciones[target.name] = 0.5

            # Sin daño (x0.0)
            for target in api_type.damage_relations.no_damage_to:
                relaciones[target.name] = 0.0

            # Insertar en la tabla Efectivo
            for defensor in tipos_base:
                multiplicador = relaciones.get(defensor, 1.0)  # Si no está en la lista, es 1.0 (neutro)
                defensor_cap = defensor.capitalize()

                cursor.execute("""
                    INSERT OR REPLACE INTO Efectivo (attacker, defender, multiplier)
                    VALUES (?, ?, ?)
                """, (t_cap, defensor_cap, multiplicador))

            print(f"   > Tipo {t_cap} y sus efectividades cargados.")

        except Exception as e:
            print(f"   ❌ Error con el tipo {tipo_nombre}: {e}")


def cargar_pokemons(conn, cursor):
    """
    Carga los datos de los Pokémon uno a uno.
    """
    print(f"\n--- 2. CARGANDO {TOTAL_POKEMON} POKÉMON (ESTO TOMARÁ TIEMPO) ---")

    start_time = time.time()

    for i in range(1, TOTAL_POKEMON + 1):
        try:
            # --- PETICIONES A LA API ---
            # Usamos la API para obtener datos básicos y especie (descripción)
            p = pb.pokemon(i)
            s = pb.pokemon_species(i)

            # --- PREPARAR DATOS ---
            p_id = p.id
            nombre = p.name.capitalize()
            peso = p.weight / 10.0  # API devuelve hectogramos -> pasamos a Kg
            altura = p.height / 10.0  # API devuelve decímetros -> pasamos a Metros

            # Stats (diccionario rápido)
            stats = {stat.stat.name: stat.base_stat for stat in p.stats}

            # Descripción en inglés (buscamos la primera disponible)
            desc = "No description available."
            for entry in s.flavor_text_entries:
                if entry.language.name == "en":
                    desc = entry.flavor_text.replace('\n', ' ').replace('\f', ' ')
                    break

            # --- INSERTAR EN PokeEspecie ---
            cursor.execute("""
                INSERT OR REPLACE INTO PokeEspecie 
                (id_pokedex, name, description, weight, height, ps, attack, defense, special_attack, special_defense, speed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                p_id, nombre, desc, peso, altura,
                stats.get('hp', 0), stats.get('attack', 0), stats.get('defense', 0),
                stats.get('special-attack', 0), stats.get('special-defense', 0), stats.get('speed', 0)
            ))

            # --- INSERTAR TIPOS (Tabla EsTipo) ---
            tipos_encontrados = []
            for t in p.types:
                t_name = t.type.name.capitalize()
                tipos_encontrados.append(t_name)

            type1 = tipos_encontrados[0]
            type2 = tipos_encontrados[1] if len(tipos_encontrados) > 1 else None

            cursor.execute("INSERT OR REPLACE INTO EsTipo (id_pokemon, type1, type2) VALUES (?, ?, ?)",
                           (p_id, type1, type2))

            # --- INSERTAR HABILIDADES (Tabla Habilidad y HabilidadesPosibles) ---
            for ab in p.abilities:
                ab_name = ab.ability.name.capitalize()
                # 1. Asegurar que la habilidad existe en la tabla maestra
                cursor.execute("INSERT OR IGNORE INTO Habilidad (name, description) VALUES (?, ?)",
                               (ab_name, "Descripción pendiente"))
                # 2. Relacionar con el Pokémon
                cursor.execute("INSERT OR IGNORE INTO HabilidadesPosibles (id_pokemon, ability_name) VALUES (?, ?)",
                               (p_id, ab_name))

            # Feedback visual simple
            print(f"✅ [{i}/{TOTAL_POKEMON}] {nombre}")

            # Guardar cambios cada 10 Pokémon para seguridad
            if i % 10 == 0:
                conn.commit()

        except Exception as e:
            print(f"❌ Error cargando ID {i}: {e}")
            # Si falla uno, seguimos con el siguiente, no paramos todo.
            continue

    # Commit final
    conn.commit()
    elapsed = time.time() - start_time
    print(f"\n--- CARGA COMPLETADA EN {elapsed / 60:.2f} MINUTOS ---")


def main():
    print(f"--- CONECTANDO A: {Config.DB_PATH} ---")
    conn = conectar_bd()
    cursor = conn.cursor()

    # 1. Primero cargamos la estructura de tipos (rápido)
    cargar_tipos_y_efectividad(cursor)
    conn.commit()

    # 2. Luego cargamos los bichos (lento)
    cargar_pokemons(conn, cursor)

    conn.close()


if __name__ == "__main__":
    main()