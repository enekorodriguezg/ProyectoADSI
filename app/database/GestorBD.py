import sqlite3
import pokebase as pb
from config import Config
from app.database.ResultadoSQL import ResultadoSQL


class GestorBD:
    def __init__(self):
        self.connection = sqlite3.connect(
            Config.DB_PATH,
            check_same_thread=False
        )
        self.connection.row_factory = sqlite3.Row

    def cargar_toda_la_base_de_datos(self):
        """Carga masiva de datos optimizada"""
        print("--- INICIANDO CARGA TOTAL ---")
        cursor = self.connection.cursor()

        try:
            # 1. Cargar tipos y efectividades
            self.cargar_efectividades()

            for i in range(1, 1026):
                try:
                    # Comprobamos si ya existe el Pokémon
                    cursor.execute("SELECT id_pokedex FROM PokeEspecie WHERE id_pokedex = ?", (i,))
                    # Si descomentas 'continue', saltará los ya descargados para ir más rápido
                    if cursor.fetchone():
                        continue

                    p = pb.pokemon(i)
                    print(f"Sincronizando ID {i}: {p.name.capitalize()}...")

                    # 3. PokeEspecie (Datos Base)
                    stats = {s.stat.name: s.base_stat for s in p.stats}
                    cursor.execute("""
                        INSERT OR IGNORE INTO PokeEspecie 
                        (id_pokedex, name, weight, ps, attack, defense, special_attack, special_defense, speed)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (p.id, p.name.capitalize(), p.weight / 10,
                          stats.get('hp'), stats.get('attack'), stats.get('defense'),
                          stats.get('special-attack'), stats.get('special-defense'), stats.get('speed')))

                    # 4. Tipos
                    t1 = p.types[0].type.name.capitalize()
                    t2 = p.types[1].type.name.capitalize() if len(p.types) > 1 else None
                    cursor.execute("INSERT OR IGNORE INTO Tipo (name) VALUES (?)", (t1,))
                    if t2:
                        cursor.execute("INSERT OR IGNORE INTO Tipo (name) VALUES (?)", (t2,))
                    cursor.execute("INSERT OR IGNORE INTO EsTipo (id_pokemon, type1, type2) VALUES (?, ?, ?)",
                                   (p.id, t1, t2))

                    # 5. Habilidades
                    for a in p.abilities:
                        hab_nombre = a.ability.name.capitalize()
                        cursor.execute("SELECT name FROM Habilidad WHERE name = ?", (hab_nombre,))
                        if not cursor.fetchone():
                            try:
                                res_hab = pb.ability(a.ability.name)
                                desc = next(
                                    (en.short_effect for en in res_hab.effect_entries if en.language.name == 'en'),
                                    "No description.")
                                cursor.execute("INSERT INTO Habilidad (name, description) VALUES (?, ?)",
                                               (hab_nombre, desc))
                            except:
                                cursor.execute("INSERT OR IGNORE INTO Habilidad (name, description) VALUES (?, ?)",
                                               (hab_nombre, "No description available."))
                        cursor.execute(
                            "INSERT OR IGNORE INTO HabilidadesPosibles (id_pokemon, ability_name) VALUES (?, ?)",
                            (p.id, hab_nombre))

                    # 6. Evoluciones
                    try:
                        especie = pb.pokemon_species(i)
                        if especie.evolves_from_species:
                            url_padre = especie.evolves_from_species.url
                            id_padre = int(url_padre.split('/')[-2])
                            cursor.execute("INSERT OR IGNORE INTO Evoluciona (id_base, id_evolution) VALUES (?, ?)",
                                           (id_padre, i))
                            print(f"   [EVO] Relación guardada: {id_padre} -> {i}")
                    except:
                        pass

                    self.connection.commit()
                    if i % 10 == 0:
                        print(f"--- Hito: {i}/1025 alcanzado ---")

                except Exception as e:
                    print(f"Error procesando ID {i}: {e}")

            print("--- CARGA TOTAL FINALIZADA CON ÉXITO ---")
        except Exception as e:
            print(f"Error crítico en la carga: {e}")

    def cargar_efectividades(self):
        """Rellena la tabla Efectivo y Tipo con las relaciones de daño de la API"""
        print("Calculando tabla de tipos y efectividades...")
        cursor = self.connection.cursor()

        tipos_maestros = ["Normal", "Fire", "Water", "Electric", "Grass", "Ice", "Fighting", "Poison", "Ground",
                          "Flying", "Psychic", "Bug", "Rock", "Ghost", "Dragon", "Dark", "Steel", "Fairy"]

        for t_name in tipos_maestros:
            cursor.execute("INSERT OR IGNORE INTO Tipo (name) VALUES (?)", (t_name,))
            try:
                res_type = pb.type_(t_name.lower())
                rels = [(res_type.damage_relations.double_damage_to, 2.0),
                        (res_type.damage_relations.half_damage_to, 0.5), (res_type.damage_relations.no_damage_to, 0.0)]
                for target_list, mult in rels:
                    for target in target_list:
                        target_name = target.name.capitalize()
                        cursor.execute("INSERT OR IGNORE INTO Tipo (name) VALUES (?)", (target_name,))
                        cursor.execute(
                            "INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES (?, ?, ?)",
                            (t_name, target_name, mult))
            except:
                continue
        self.connection.commit()
        print("Tabla de tipos lista.")

    def execSQL(self, sql):
        cursor = self.connection.cursor()
        cursor.execute(sql)
        datos = cursor.fetchall()
        return ResultadoSQL(datos)