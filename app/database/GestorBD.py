import sqlite3
import pokebase as pb
from config import Config
from app.database.ResultadoSQL import ResultadoSQL


class GestorBD:
    def __init__(self):
        self.connection = sqlite3.connect(Config.DB_PATH, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        # Al instanciar, nos aseguramos de que las tablas existan
        self.crear_tablas_si_no_existen()

    def crear_tablas_si_no_existen(self):
        """Lee el archivo schema.sql y crea la estructura si alguna tabla falta"""
        print("Verificando integridad de las tablas...")
        try:
            with open('app/database/schema.sql', 'r') as f:
                schema = f.read()
            self.connection.executescript(schema)
            self.connection.commit()
        except Exception as e:
            print(f"Error al verificar/crear tablas: {e}")

    def cargar_toda_la_base_de_datos(self):
        """Carga inteligente: solo descarga campos faltantes de cada Pokémon"""
        print("--- INICIANDO ESCANEO DE REPARACIÓN (1-1025) ---")
        cursor = self.connection.cursor()

        try:
            # 1. Asegurar efectividades (Si la tabla está vacía)
            cursor.execute("SELECT COUNT(*) as total FROM Efectivo")
            if cursor.fetchone()['total'] == 0:
                self.cargar_efectividades()

            for i in range(1, 1026):
                try:
                    # Comprobaciones individuales
                    cursor.execute("SELECT id_pokedex FROM PokeEspecie WHERE id_pokedex = ?", (i,))
                    tiene_esp = cursor.fetchone()

                    cursor.execute("SELECT id_pokemon FROM EsTipo WHERE id_pokemon = ?", (i,))
                    tiene_tipo = cursor.fetchone()

                    cursor.execute("SELECT id_pokemon FROM HabilidadesPosibles WHERE id_pokemon = ?", (i,))
                    tiene_hab = cursor.fetchone()

                    cursor.execute("SELECT id_evolution FROM Evoluciona WHERE id_evolution = ?", (i,))
                    tiene_evo = cursor.fetchone()

                    # Si cada campo está perfecto para este ID, saltar
                    if tiene_esp and tiene_tipo and tiene_hab and tiene_evo:
                        continue

                    # Si falta algo, descargamos de la API
                    print(f"🛠️  Reparando datos faltantes para ID {i}...")
                    p = pb.pokemon(i)
                    s = pb.pokemon_species(i)

                    # Reparar Especie/Stats
                    if not tiene_esp:
                        stats = {st.stat.name: st.base_stat for st in p.stats}
                        desc = next((f.flavor_text for f in s.flavor_text_entries if f.language.name == 'en'),
                                    "No desc.")
                        desc = desc.replace('\n', ' ').replace('\f', ' ')
                        cursor.execute("""
                            INSERT OR REPLACE INTO PokeEspecie 
                            (id_pokedex, name, description, weight, height, ps, attack, defense, special_attack, special_defense, speed)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (p.id, p.name.capitalize(), desc, p.weight / 10, p.height / 10,
                              stats.get('hp'), stats.get('attack'), stats.get('defense'),
                              stats.get('special-attack'), stats.get('special-defense'), stats.get('speed')))

                    # Reparar Tipos
                    if not tiene_tipo:
                        t1 = p.types[0].type.name.capitalize()
                        t2 = p.types[1].type.name.capitalize() if len(p.types) > 1 else None
                        cursor.execute("INSERT OR REPLACE INTO EsTipo (id_pokemon, type1, type2) VALUES (?, ?, ?)",
                                       (p.id, t1, t2))

                    # Reparar Habilidades
                    if not tiene_hab:
                        for a in p.abilities:
                            h_n = a.ability.name.capitalize()
                            cursor.execute("INSERT OR IGNORE INTO Habilidad (name, description) VALUES (?, ?)",
                                           (h_n, "Pending..."))
                            cursor.execute(
                                "INSERT OR IGNORE INTO HabilidadesPosibles (id_pokemon, ability_name) VALUES (?, ?)",
                                (p.id, h_n))

                    # Reparar Evolución
                    if not tiene_evo and s.evolves_from_species:
                        id_p = int(s.evolves_from_species.url.split('/')[-2])
                        cursor.execute("INSERT OR REPLACE INTO Evoluciona (id_base, id_evolution) VALUES (?, ?)",
                                       (id_p, i))

                    self.connection.commit()

                except Exception as e:
                    print(f"Error en ID {i}: {e}")

            print("--- REPARACIÓN FINALIZADA ---")
        except Exception as e:
            print(f"Error crítico: {e}")

    def cargar_efectividades(self):
        """Carga la tabla de tipos y multiplicadores"""
        print("Cargando tabla de efectividades...")
        cursor = self.connection.cursor()
        tipos = ["Normal", "Fire", "Water", "Electric", "Grass", "Ice", "Fighting", "Poison", "Ground", "Flying",
                 "Psychic", "Bug", "Rock", "Ghost", "Dragon", "Dark", "Steel", "Fairy"]
        for t in tipos:
            cursor.execute("INSERT OR IGNORE INTO Tipo (name) VALUES (?)", (t,))
            try:
                res = pb.type_(t.lower())
                for target in res.damage_relations.double_damage_to:
                    cursor.execute("INSERT OR REPLACE INTO Efectivo (attacker, defender, multiplier) VALUES (?, ?, ?)",
                                   (t, target.name.capitalize(), 2.0))
                for target in res.damage_relations.half_damage_to:
                    cursor.execute("INSERT OR REPLACE INTO Efectivo (attacker, defender, multiplier) VALUES (?, ?, ?)",
                                   (t, target.name.capitalize(), 0.5))
                for target in res.damage_relations.no_damage_to:
                    cursor.execute("INSERT OR REPLACE INTO Efectivo (attacker, defender, multiplier) VALUES (?, ?, ?)",
                                   (t, target.name.capitalize(), 0.0))
            except:
                continue
        self.connection.commit()

    def execSQL(self, sql):
        cursor = self.connection.cursor()
        cursor.execute(sql)
        datos = cursor.fetchall()
        return ResultadoSQL(datos)