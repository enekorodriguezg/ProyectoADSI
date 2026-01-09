import sqlite3
import pokebase as pb
import time
from config import Config

# Rango de Pokémon a descargar (Gen 9 llega hasta 1025)
TOTAL_POKEMON = 1025

def conectar_bd():
    return sqlite3.connect(Config.DB_PATH)

def cargar_tipos_y_efectividad(cursor):
    print("\n--- 1. CARGANDO TIPOS Y TABLA DE EFECTIVIDAD ---")
    tipos_base = [
        "normal", "fighting", "flying", "poison", "ground", "rock", "bug",
        "ghost", "steel", "fire", "water", "grass", "electric", "psychic",
        "ice", "dragon", "dark", "fairy"
    ]

    for tipo_nombre in tipos_base:
        try:
            t_cap = tipo_nombre.capitalize()
            cursor.execute("INSERT OR IGNORE INTO Tipo (name) VALUES (?)", (t_cap,))

            api_type = pb.type_(tipo_nombre)
            relaciones = {}

            for target in api_type.damage_relations.double_damage_to:
                relaciones[target.name] = 2.0
            for target in api_type.damage_relations.half_damage_to:
                relaciones[target.name] = 0.5
            for target in api_type.damage_relations.no_damage_to:
                relaciones[target.name] = 0.0

            for defensor in tipos_base:
                multiplicador = relaciones.get(defensor, 1.0)
                defensor_cap = defensor.capitalize()
                cursor.execute("""
                    INSERT OR REPLACE INTO Efectivo (attacker, defender, multiplier)
                    VALUES (?, ?, ?)
                """, (t_cap, defensor_cap, multiplicador))

            print(f"   > Tipo {t_cap} cargado.")
        except Exception as e:
            print(f"   ❌ Error tipo {tipo_nombre}: {e}")

def cargar_pokemons(conn, cursor):
    print(f"\n--- 2. CARGANDO {TOTAL_POKEMON} POKÉMON (MODO SOBREESCRITURA TOTAL) ---")
    start_time = time.time()

    for i in range(1, TOTAL_POKEMON + 1):
        try:
            # 1. Llamadas a la API
            p = pb.pokemon(i)
            s = pb.pokemon_species(i)

            p_id = p.id
            nombre = p.name.capitalize()
            peso = p.weight / 10.0
            altura = p.height / 10.0
            stats = {stat.stat.name: stat.base_stat for stat in p.stats}

            # Descripción
            desc = "No description available."
            for entry in s.flavor_text_entries:
                if entry.language.name == "en":
                    desc = entry.flavor_text.replace('\n', ' ').replace('\f', ' ')
                    break

            # 2. INSERTAR/REEMPLAZAR EN PokeEspecie
            cursor.execute("""
                INSERT OR REPLACE INTO PokeEspecie 
                (id_pokedex, name, description, weight, height, ps, attack, defense, special_attack, special_defense, speed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                p_id, nombre, desc, peso, altura,
                stats.get('hp', 0), stats.get('attack', 0), stats.get('defense', 0),
                stats.get('special-attack', 0), stats.get('special-defense', 0), stats.get('speed', 0)
            ))

            # 3. INSERTAR/REEMPLAZAR TIPOS
            tipos_encontrados = [t.type.name.capitalize() for t in p.types]
            type1 = tipos_encontrados[0]
            type2 = tipos_encontrados[1] if len(tipos_encontrados) > 1 else None
            cursor.execute("INSERT OR REPLACE INTO EsTipo (id_pokemon, type1, type2) VALUES (?, ?, ?)",
                           (p_id, type1, type2))

            # 4. INSERTAR HABILIDADES
            for ab in p.abilities:
                ab_name = ab.ability.name.capitalize()
                cursor.execute("INSERT OR IGNORE INTO Habilidad (name, description) VALUES (?, ?)",
                               (ab_name, "Descripción pendiente"))
                cursor.execute("INSERT OR IGNORE INTO HabilidadesPosibles (id_pokemon, ability_name) VALUES (?, ?)",
                               (p_id, ab_name))

            # 5. INSERTAR/REEMPLAZAR EVOLUCIONES (LO QUE FALTABA)
            if s.evolves_from_species:
                id_padre = int(s.evolves_from_species.url.split('/')[-2])
                cursor.execute("""
                    INSERT OR REPLACE INTO Evoluciona (id_base, id_evolution) 
                    VALUES (?, ?)
                """, (id_padre, p_id))
                evo_msg = f" | EVO: {id_padre} -> {p_id}"
            else:
                evo_msg = ""

            print(f"✅ [{i}/{TOTAL_POKEMON}] {nombre}{evo_msg}")

            if i % 10 == 0:
                conn.commit()

        except Exception as e:
            print(f"❌ Error ID {i}: {e}")
            continue

    conn.commit()
    print(f"\n--- CARGA COMPLETADA EN {(time.time() - start_time) / 60:.2f} MINUTOS ---")

def main():
    conn = conectar_bd()
    cursor = conn.cursor()
    cargar_tipos_y_efectividad(cursor)
    conn.commit()
    cargar_pokemons(conn, cursor)
    conn.close()

if __name__ == "__main__":
    main()