import unittest
import os
import sys
import tempfile
import sqlite3
from unittest.mock import patch

# --- AJUSTE DE RUTAS ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from config import Config
from app.database.GestorBD import GestorBD
from app.controller.model.GestorEquipos import GestorEquipos


class TestGestionEquipos(unittest.TestCase):

    def setUp(self):
        """Configuración con Base de Datos Temporal"""
        # 1. Crear BD temporal
        self.db_fd, self.db_path = tempfile.mkstemp()

        # 2. Configurar la ruta de la BD para que el Gestor use la temporal
        self.original_db_path = Config.DB_PATH
        Config.DB_PATH = self.db_path

        # 3. MOCK: Evitar carga masiva de PokeAPI
        self.patcher = patch('app.database.GestorBD.GestorBD.cargar_toda_la_base_de_datos')
        self.mock_carga = self.patcher.start()

        # 4. Crear el esquema base (tablas del schema.sql)
        schema_path = os.path.join(project_root, 'app', 'database', 'schema.sql')
        conn = sqlite3.connect(self.db_path)
        with open(schema_path, encoding='utf-8') as f:
            conn.executescript(f.read())

        cursor = conn.cursor()

        # --- PARCHE PARA QUE EL TEST FUNCIONE CON TU GESTOREQUIPOS.PY ---
        # El código Python intenta usar la tabla 'Pokémon' que no está en schema.sql
        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS Pokémon
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           owner
                           VARCHAR
                       (
                           50
                       ),
                           id_pokedex INT,
                           species_name VARCHAR
                       (
                           100
                       ),
                           ps INT, attack INT, defense INT,
                           special_attack INT, special_defense INT, speed INT
                           )
                       """)

        # El código Python usa 'id_pokemon' en PokémonParticipa, pero schema.sql tiene 'id_pokedex'.
        # Recreamos la tabla para que coincida con la lógica de tu controlador.
        cursor.execute("DROP TABLE IF EXISTS PokémonParticipa")
        cursor.execute("""
                       CREATE TABLE PokémonParticipa
                       (
                           id_team    INT,
                           id_pokemon INT,
                           PRIMARY KEY (id_team, id_pokemon)
                       )
                       """)
        # ----------------------------------------------------------------

        # 5. Insertar datos de prueba (Pikachu) con TODOS los campos necesarios
        cursor.execute("""
                       INSERT INTO PokeEspecie (id_pokedex, name, description, ps, attack, defense, special_attack,
                                                special_defense, speed)
                       VALUES (25, 'Pikachu', 'Ratón eléctrico', 35, 55, 40, 50, 50, 90)
                       """)
        conn.commit()
        conn.close()

        # 6. Instanciar el Gestor con la BD temporal
        self.gestor_bd = GestorBD()
        self.gestor_equipos = GestorEquipos(self.gestor_bd)

    def tearDown(self):
        """Limpieza al terminar cada test"""
        self.patcher.stop()
        os.close(self.db_fd)
        try:
            os.unlink(self.db_path)
        except PermissionError:
            pass
        Config.DB_PATH = self.original_db_path

    # ==========================================
    # TESTS PARA CREAR EQUIPO
    # ==========================================

    def test_cp_01_crear_equipo_valido(self):
        """CP_01: Crear un equipo nuevo correctamente."""
        username = "ash"
        team_name = "Equipo Rojo"

        # Ejecutar
        resultado = self.gestor_equipos.createTeam(team_name, username)

        # Verificar que devuelve True
        self.assertTrue(resultado, "Debería devolver True al crear un equipo válido")

        # Verificar en base de datos
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT name FROM EquipoPokémon WHERE username=? AND name=?", (username, team_name))
        row = c.fetchone()
        conn.close()

        self.assertIsNotNone(row, "El equipo debería existir en la BD")
        self.assertEqual(row[0], team_name)

    def test_cp_02_crear_equipo_duplicado(self):
        """CP_02: No permitir crear dos equipos con el mismo nombre para el mismo usuario."""
        username = "ash"
        team_name = "Equipo Duplicado"

        # 1. Crear el primero
        self.gestor_equipos.createTeam(team_name, username)

        # 2. Intentar crear el segundo (debe fallar)
        resultado = self.gestor_equipos.createTeam(team_name, username)

        self.assertFalse(resultado, "No debería permitir crear un equipo con nombre duplicado")

    def test_cp_03_anadir_pokemon_al_equipo(self):
        """CP_03: Añadir un Pokémon (Pikachu) a un equipo existente."""
        username = "ash"
        team_name = "Equipo Trueno"
        self.gestor_equipos.createTeam(team_name, username)

        # Recuperar ID del equipo recién creado
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT id_team FROM EquipoPokémon WHERE name=?", (team_name,))
        id_team = c.fetchone()[0]
        conn.close()

        # Ejecutar: Añadir Pikachu (ID 25)
        # Nota: GestorEquipos.py asume que le pasas el ID de la especie (25)
        # y él crea la instancia en la tabla 'Pokémon'.
        resultado = self.gestor_equipos.addPokemonToTeam(id_team, 25, username)

        self.assertTrue(resultado, "Debería dejar añadir un Pokémon válido")

        # Verificar en tabla 'PokémonParticipa'
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM PokémonParticipa WHERE id_team=?", (id_team,))
        count = c.fetchone()[0]
        conn.close()
        self.assertEqual(count, 1, "Debería haber 1 pokémon en el equipo")

    def test_cp_04_limite_6_pokemons(self):
        """CP_04: Verificar que no se pueden añadir más de 6 pokémons."""
        username = "ash"
        team_name = "Equipo Lleno"
        self.gestor_equipos.createTeam(team_name, username)

        # Recuperar ID
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT id_team FROM EquipoPokémon WHERE name=?", (team_name,))
        id_team = c.fetchone()[0]
        conn.close()

        # Añadir 6 Pikachus
        for i in range(6):
            self.gestor_equipos.addPokemonToTeam(id_team, 25, username)

        # Intentar añadir el 7º
        resultado = self.gestor_equipos.addPokemonToTeam(id_team, 25, username)

        self.assertFalse(resultado, "No debería permitir añadir un 7º Pokémon")


if __name__ == '__main__':
    unittest.main()