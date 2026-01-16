import unittest
import os
import sys
import tempfile
import sqlite3
from unittest.mock import patch

# --- PATH ADJUSTMENT ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from flask import session
from app import create_app
from config import Config

class TestChatbot(unittest.TestCase):
    def setUp(self):
        # BD temporal
        self.db_fd, self.db_path = tempfile.mkstemp()
        
        self.original_db_path = Config.DB_PATH
        Config.DB_PATH = self.db_path

        self.patcher = patch('app.database.GestorBD.GestorBD.cargar_toda_la_base_de_datos')
        self.mock_carga = self.patcher.start()

        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.app.config['SECRET_KEY'] = 'test_key'
        self.client = self.app.test_client()

        schema_path = os.path.join(project_root, 'app', 'database', 'schema.sql')
        conn = sqlite3.connect(self.db_path)
        with open(schema_path, encoding='utf-8') as f:
            conn.executescript(f.read())
            
        cursor = conn.cursor()
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

        cursor.execute("DROP TABLE IF EXISTS PokémonParticipa")
        cursor.execute("""
                       CREATE TABLE PokémonParticipa
                       (
                           id_team    INT,
                           id_pokemon INT,
                           PRIMARY KEY (id_team, id_pokemon)
                       )
                       """)

        conn.commit()
        conn.close()

    def tearDown(self):
        self.patcher.stop()
        os.close(self.db_fd)
        try:
            os.unlink(self.db_path)
        except PermissionError:
            pass
        Config.DB_PATH = self.original_db_path

    def aprobar_usuario(self, username):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE Users SET role='USER' WHERE username=?", (username,))
        conn.commit()
        conn.close()

    # --- PRUEBAS DE CAJA NEGRA ---

    def test_chatbot_01(self):
        """
        Chatbot-01: Intentar acceder a “Consultar ChatBot” sin haber iniciado sesión.
        Resultado esperado: Se redirige a la pantalla de inicio de sesión (acceso no permitido).
        """
        response = self.client.get('/chatbot')
        self.assertEqual(response.status_code, 302)
        self.assertTrue('/login' in response.location)

    def test_chatbot_02(self):
        """
        Chatbot-02: Acceder a "Consultar con ChatBot" desde el menú principal.
        Resultado esperado: Se muestra la interfaz del ChatBot con las cuatro opciones de consulta.
        """
        # Registro
        self.client.post('/registro', data={
            'username': 'chatuser',
            'password': 'password123',
            'name': 'Chat',
            'surname': 'User',
            'email': 'chat@example.com',
            'dni': '12345678A',
            'fav_pokemon': 25
        })
        
        self.aprobar_usuario('chatuser')

        # Login
        self.client.post('/login', data={
            'username': 'chatuser',
            'password': 'password123'
        })

        # Acceso al chatbot
        response = self.client.get('/chatbot')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(b'chatbot' in response.data.lower() or b'html' in response.data.lower()) # Check for some content--

    def test_chatbot_03(self):
        """
        Chatbot-03: Redirect a /equipos al pulsar evaluar el mejor pokemon del equipo.
        Resultado esperado: Se muestra la interfaz para seleccionar un equipo y una estadística.
        """
        # Registro & Login
        self.client.post('/registro', data={
            'username': 'user3', 'password': 'pw', 'name': 'U3', 'surname': 'S',
            'email': 'u3@ex.com', 'dni': '33333333C', 'fav_pokemon': 25
        })
        self.aprobar_usuario('user3')
        self.client.post('/login', data={'username': 'user3', 'password': 'pw'})

        # Acceso al chatbot
        response = self.client.get('/chatbot/evaluar_mejor_pokemon', follow_redirects=True)
        
        # Verificación
        self.assertEqual(response.status_code, 200)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get('chatbot_mode'), 'eval_mejor')
        
    def test_chatbot_04(self):
        """
        Chatbot-04: Seleccionar un equipo válido y una estadística (ej. "Ataque").
        Resultado esperado: El ChatBot responde indicando el Pokémon de ese equipo con el valor más alto en "Ataque".
        """
        # Registro & Login
        self.client.post('/registro', data={
            'username': 'user4', 'password': 'pw', 'name': 'U4', 'surname': 'S',
            'email': 'u4@ex.com', 'dni': '44444444D', 'fav_pokemon': 25
        })
        self.aprobar_usuario('user4')
        self.client.post('/login', data={'username': 'user4', 'password': 'pw'})

        # Setup del Equipo: Machamp (68) y Charizard (6)
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT INTO EquipoPokémon (name, username) VALUES ('TeamAlpha', 'user4')")
        team_id = c.lastrowid
        
        c.execute("""
                       INSERT INTO Pokémon (id_pokedex, species_name, ps, attack, defense, special_attack,
                                            special_defense, speed)
                       VALUES (6, 'Charizard', 78, 84, 78, 109, 85, 100)
                       """)
        charizard_inst_id = c.lastrowid
        c.execute("""
                       INSERT INTO Pokémon (id_pokedex, species_name, ps, attack, defense, special_attack,
                                            special_defense, speed)
                       VALUES (68, 'Machamp', 90, 130, 80, 65, 85, 55)
                       """)
        machamp_inst_id = c.lastrowid

        c.execute("INSERT OR IGNORE INTO PokeEspecie (id_pokedex, name, description, ps, attack, defense, special_attack, special_defense, speed) VALUES (6, 'Charizard', 'Fire Dragon', 78, 84, 78, 109, 85, 100)")
        c.execute("INSERT OR IGNORE INTO PokeEspecie (id_pokedex, name, description, ps, attack, defense, special_attack, special_defense, speed) VALUES (68, 'Machamp', 'Strong', 90, 130, 80, 65, 85, 55)")
        c.execute(f"INSERT INTO PokémonParticipa (id_team, id_pokemon) VALUES ({team_id}, {charizard_inst_id})")
        c.execute(f"INSERT INTO PokémonParticipa (id_team, id_pokemon) VALUES ({team_id}, {machamp_inst_id})")
        conn.commit()
        conn.close()

        response = self.client.get(f'/equipos/evaluar?id_team={team_id}&stat=attack', follow_redirects=True)

        # Verificar Redirect a Machamp (130 > 84)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(b'Machamp' in response.data)
    
    def test_chatbot_05(self):
        """
        Chatbot-05: Seleccionar "Evaluar..." pero con un equipo que está vacío.
        Resultado esperado: El ChatBot muestra un mensaje: "El equipo seleccionado está vacío".
        """
        # Registro & Login
        self.client.post('/registro', data={
            'username': 'user5', 'password': 'pw', 'name': 'U5', 'surname': 'S',
            'email': 'u5@ex.com', 'dni': '55555555E', 'fav_pokemon': 25
        })
        self.aprobar_usuario('user5')
        self.client.post('/login', data={'username': 'user5', 'password': 'pw'})

        # Setup Equipo Vacío
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT INTO EquipoPokémon (name, username) VALUES ('EmptyTeam', 'user5')")
        team_id = c.lastrowid
        conn.commit()
        conn.close()

        response = self.client.get(f'/equipos/evaluar?id_team={team_id}&stat=attack', follow_redirects=True)

        self.assertTrue(b'El equipo seleccionado est\xc3\xa1 vac\xc3\xado' in response.data)
    
    def test_chatbot_06(self):
        """
        Chatbot-06: Intentar evaluar sin seleccionar un equipo.
        Resultado esperado: Mensaje de error: "Debe seleccionar un equipo para evaluar". 
        """
        # Registro & Login
        self.client.post('/registro', data={
            'username': 'user6', 'password': 'pw', 'name': 'U6', 'surname': 'S',
            'email': 'u6@ex.com', 'dni': '66666666F', 'fav_pokemon': 25
        })
        self.aprobar_usuario('user6')
        self.client.post('/login', data={'username': 'user6', 'password': 'pw'})

        # Evaluar sin equipo
        response = self.client.get('/equipos/evaluar?stat=attack', follow_redirects=True)
        self.assertTrue(b'Debe seleccionar un equipo para evaluar' in response.data)

    
    def test_chatbot_07(self):
        """
        Chatbot-07: Intentar evaluar sin seleccionar una estadística.
        Resultado esperado: Mensaje de error: "Debe seleccionar una estadística para evaluar".
        """
        # Registro & Login
        self.client.post('/registro', data={
            'username': 'user7', 'password': 'pw', 'name': 'U7', 'surname': 'S',
            'email': 'u7@ex.com', 'dni': '77777777G', 'fav_pokemon': 25
        })
        self.aprobar_usuario('user7')
        self.client.post('/login', data={'username': 'user7', 'password': 'pw'})

        # Setup Equipo
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT INTO EquipoPokémon (name, username) VALUES ('TeamX', 'user7')")
        team_id = c.lastrowid
        conn.commit()
        conn.close()

        # Evaluar sin estadística
        response = self.client.get(f'/equipos/evaluar?id_team={team_id}', follow_redirects=True)
        self.assertTrue(b'Debe seleccionar una estad\xc3\xadstica para evaluar' in response.data)

    
    def test_chatbot_08(self):
        """
        Chatbot-08: Seleccionar la opción "Mostrar compatibilidad de tipos".
        Resultado esperado: Se muestra la lista completa de Pokémon para la selección.
        """
        # Registro & Login
        self.client.post('/registro', data={
            'username': 'user8', 'password': 'pw', 'name': 'U8', 'surname': 'S',
            'email': 'u8@ex.com', 'dni': '88888888H', 'fav_pokemon': 25
        })
        self.aprobar_usuario('user8')
        self.client.post('/login', data={'username': 'user8', 'password': 'pw'})

        response = self.client.get('/chatbot/ver_compatibilidad', follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        # Verifica que redirige a lpokemon (lista) y session mode
        self.assertTrue(b'lpokemon' in response.data)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get('chatbot_mode'), 'compatibilidad')
    
    def test_chatbot_09(self):
        """
        Chatbot-09: Seleccionar un Pokémon de un solo tipo (ej. "Machamp").
        Resultado esperado: El ChatBot responde con las debilidades y resistencias correctas.
        """
        # Registro & Login
        self.client.post('/registro', data={
            'username': 'user9', 'password': 'pw', 'name': 'U9', 'surname': 'S',
            'email': 'u9@ex.com', 'dni': '99999999I', 'fav_pokemon': 25
        })
        self.aprobar_usuario('user9')
        self.client.post('/login', data={'username': 'user9', 'password': 'pw'})
        
        # Aplicamos el modo manualmente por que no hacemos click en la opción.
        with self.client.session_transaction() as sess:
            sess['chatbot_mode'] = 'compatibilidad'

        # Setup Machamp
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO PokeEspecie (id_pokedex, name, description, ps, attack, defense, special_attack, special_defense, speed) VALUES (68, 'Machamp', 'Strong', 90, 130, 80, 65, 85, 55)")
        types = ['Bug', 'Dark', 'Dragon', 'Electric', 'Fairy', 'Fighting', 'Fire', 'Flying', 'Ghost', 'Grass', 'Ground', 'Ice', 'Normal', 'Poison', 'Psychic', 'Rock', 'Steel', 'Water']
        for t in types:
            c.execute(f"INSERT OR IGNORE INTO Tipo (name) VALUES ('{t}')")

        c.execute("INSERT OR IGNORE INTO EsTipo (id_pokemon, type1, type2) VALUES (68, 'Fighting', NULL)")
        
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Bug', 'Fighting', 0.5)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Dark', 'Fighting', 0.5)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Dragon', 'Fighting', 1)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Electric', 'Fighting', 1)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Fairy', 'Fighting', 2)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Fighting', 'Fighting', 1)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Fire', 'Fighting', 1)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Flying', 'Fighting', 2)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Ghost', 'Fighting', 1)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Grass', 'Fighting', 1)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Ground', 'Fighting', 1)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Ice', 'Fighting', 1)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Normal', 'Fighting', 1)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Poison', 'Fighting', 1)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Psychic', 'Fighting', 2)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Rock', 'Fighting', 1)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Steel', 'Fighting', 1)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Water', 'Fighting', 1)")
        
        conn.commit()
        conn.close()

        response = self.client.get(f'/compatibilidad/68', follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        self.assertIn(b'Bug', response.data)
        self.assertIn(b'x1/2', response.data)
        self.assertIn(b'Dark', response.data)
        self.assertIn(b'x1/2', response.data)
        self.assertIn(b'Dragon', response.data)
        self.assertIn(b'x1', response.data)
        self.assertIn(b'Electric', response.data)
        self.assertIn(b'x1', response.data)
        self.assertIn(b'Fairy', response.data)
        self.assertIn(b'x2', response.data)
        self.assertIn(b'Fighting', response.data)
        self.assertIn(b'x1', response.data)
        self.assertIn(b'Fire', response.data)
        self.assertIn(b'x1', response.data)
        self.assertIn(b'Flying', response.data)
        self.assertIn(b'x2', response.data)
        self.assertIn(b'Ghost', response.data)
        self.assertIn(b'x1', response.data)
        self.assertIn(b'Grass', response.data)
        self.assertIn(b'x1', response.data)
        self.assertIn(b'Ground', response.data)
        self.assertIn(b'x1', response.data)
        self.assertIn(b'Ice', response.data)
        self.assertIn(b'x1', response.data)
        self.assertIn(b'Normal', response.data)
        self.assertIn(b'x1', response.data)
        self.assertIn(b'Poison', response.data)
        self.assertIn(b'x1', response.data)
        self.assertIn(b'Psychic', response.data)
        self.assertIn(b'x2', response.data)
        self.assertIn(b'Rock', response.data)
        self.assertIn(b'x1/2', response.data)
        self.assertIn(b'Steel', response.data)
        self.assertIn(b'x1', response.data)
        self.assertIn(b'Water', response.data)
        self.assertIn(b'x1', response.data)

    def test_chatbot_10(self):
        """
        Chatbot-10: Seleccionar un Pokémon de doble tipo (ej. "Charizard").
        Resultado esperado: El ChatBot responde con las debilidades combinadas.
        """
        # Registro & Login
        self.client.post('/registro', data={
            'username': 'user10', 'password': 'pw', 'name': 'U10', 'surname': 'S',
            'email': 'u10@ex.com', 'dni': '10101010J', 'fav_pokemon': 25
        })
        self.aprobar_usuario('user10')
        self.client.post('/login', data={'username': 'user10', 'password': 'pw'})
        
        # Aplicamos el modo manualmente por que no hacemos click en la opción.
        with self.client.session_transaction() as sess:
            sess['chatbot_mode'] = 'compatibilidad'

        # Setup Charizard
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO PokeEspecie (id_pokedex, name, description, ps, attack, defense, special_attack, special_defense, speed) VALUES (6, 'Charizard', 'Fire Dragon', 90, 130, 80, 65, 85, 55)")
        types = ['Bug', 'Dark', 'Dragon', 'Electric', 'Fairy', 'Fighting', 'Fire', 'Flying', 'Ghost', 'Grass', 'Ground', 'Ice', 'Normal', 'Poison', 'Psychic', 'Rock', 'Steel', 'Water']
        for t in types:
            c.execute(f"INSERT OR IGNORE INTO Tipo (name) VALUES ('{t}')")

        c.execute("INSERT OR IGNORE INTO EsTipo (id_pokemon, type1, type2) VALUES (6, 'Fire', 'Flying')")
        
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Bug', 'Fire', 0.5)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Dark', 'Fire', 1)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Dragon', 'Fire', 1)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Electric', 'Fire', 1)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Fairy', 'Fire', 0.5)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Fighting', 'Fire', 1)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Fire', 'Fire', 0.5)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Flying', 'Fire', 1)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Ghost', 'Fire', 1)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Grass', 'Fire', 0.5)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Ground', 'Fire', 2)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Ice', 'Fire', 0.5)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Normal', 'Fire', 1)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Poison', 'Fire', 1)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Psychic', 'Fire', 1)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Rock', 'Fire', 2)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Steel', 'Fire', 0.5)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Water', 'Fire', 2)")

        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Bug', 'Flying', 0.5)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Dark', 'Flying', 1)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Dragon', 'Flying', 1)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Electric', 'Flying', 2)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Fairy', 'Flying', 1)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Fighting', 'Flying', 0.5)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Fire', 'Flying', 1)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Flying', 'Flying', 1)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Ghost', 'Flying', 1)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Grass', 'Flying', 0.5)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Ground', 'Flying', 0.5)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Ice', 'Flying', 2)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Normal', 'Flying', 1)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Poison', 'Flying', 1)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Psychic', 'Flying', 1)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Rock', 'Flying', 2)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Steel', 'Flying', 1)")
        c.execute("INSERT OR IGNORE INTO Efectivo (attacker, defender, multiplier) VALUES ('Water', 'Flying', 1)")
        
        conn.commit()
        conn.close()

        response = self.client.get(f'/compatibilidad/6', follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        self.assertIn(b'Bug', response.data)
        self.assertIn(b'x1/4', response.data)
        self.assertIn(b'Dark', response.data)
        self.assertIn(b'x1', response.data)
        self.assertIn(b'Dragon', response.data)
        self.assertIn(b'x1', response.data)
        self.assertIn(b'Electric', response.data)
        self.assertIn(b'x2', response.data)
        self.assertIn(b'Fairy', response.data)
        self.assertIn(b'x1/2', response.data)
        self.assertIn(b'Fighting', response.data)
        self.assertIn(b'x1/2', response.data)
        self.assertIn(b'Fire', response.data)
        self.assertIn(b'x1/2', response.data)
        self.assertIn(b'Flying', response.data)
        self.assertIn(b'x1', response.data)
        self.assertIn(b'Ghost', response.data)
        self.assertIn(b'x1', response.data)
        self.assertIn(b'Grass', response.data)
        self.assertIn(b'x1/4', response.data)
        self.assertIn(b'Ground', response.data)
        self.assertIn(b'x0', response.data)
        self.assertIn(b'Ice', response.data)
        self.assertIn(b'x1', response.data)
        self.assertIn(b'Normal', response.data)
        self.assertIn(b'x1', response.data)
        self.assertIn(b'Poison', response.data)
        self.assertIn(b'x1', response.data)
        self.assertIn(b'Psychic', response.data)
        self.assertIn(b'x1', response.data)
        self.assertIn(b'Rock', response.data)
        self.assertIn(b'x4', response.data)
        self.assertIn(b'Steel', response.data)
        self.assertIn(b'x1/2', response.data)
        self.assertIn(b'Water', response.data)
        self.assertIn(b'x2', response.data)

    def test_chatbot_11(self):
        """
        Chatbot-11: Seleccionar la opción "Consultar habilidades y estadísticas".
        Resultado esperado: Se muestra la lista completa de equipos para la selección.
        """
        # Registro & Login
        self.client.post('/registro', data={
            'username': 'user11', 'password': 'pw', 'name': 'U11', 'surname': 'S',
            'email': 'u11@ex.com', 'dni': '11111111J', 'fav_pokemon': 25
        })
        self.aprobar_usuario('user11')
        self.client.post('/login', data={'username': 'user11', 'password': 'pw'})
        
        response = self.client.get('/chatbot/ver_habilidades_estadisticas', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        # Verifica que redirige a equipos y session mode
        self.assertTrue(b'equipos' in response.data)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get('chatbot_mode'), 'hab_est')

    def test_chatbot_12(self):
        """ 
        Chatbot-12: Seleccionar un Pokémon válido (ej. "Pikachu").
        Resultado esperado: El ChatBot responde mostrando la habilidad (ej. "Electricidad Estática") y las estadísticas base (PS, Ataque, Defensa, etc.).
        """
        # Registro & Login
        self.client.post('/registro', data={
            'username': 'user12', 'password': 'pw', 'name': 'U12', 'surname': 'S',
            'email': 'u12@ex.com', 'dni': '12121212J', 'fav_pokemon': 25
        })
        self.aprobar_usuario('user12')
        self.client.post('/login', data={'username': 'user12', 'password': 'pw'})

        # Setup del Equipo: Machamp (68) y Charizard (6)
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT INTO EquipoPokémon (name, username) VALUES ('TeamAlpha', 'user4')")
        team_id = c.lastrowid
        
        c.execute("""
                       INSERT INTO Pokémon (id_pokedex, species_name, ps, attack, defense, special_attack,
                                            special_defense, speed)
                       VALUES (6, 'Charizard', 78, 84, 78, 109, 85, 100)
                       """)
        charizard_inst_id = c.lastrowid
        c.execute("""
                       INSERT INTO Pokémon (id_pokedex, species_name, ps, attack, defense, special_attack,
                                            special_defense, speed)
                       VALUES (68, 'Machamp', 90, 130, 80, 65, 85, 55)
                       """)
        machamp_inst_id = c.lastrowid

        c.execute("INSERT OR IGNORE INTO PokeEspecie (id_pokedex, name, description, ps, attack, defense, special_attack, special_defense, speed) VALUES (6, 'Charizard', 'Fire Dragon', 78, 84, 78, 109, 85, 100)")
        c.execute("INSERT OR IGNORE INTO PokeEspecie (id_pokedex, name, description, ps, attack, defense, special_attack, special_defense, speed) VALUES (68, 'Machamp', 'Strong', 90, 130, 80, 65, 85, 55)")
        c.execute(f"INSERT INTO PokémonParticipa (id_team, id_pokemon) VALUES ({team_id}, {charizard_inst_id})")
        c.execute(f"INSERT INTO PokémonParticipa (id_team, id_pokemon) VALUES ({team_id}, {machamp_inst_id})")
        conn.commit()
        conn.close()

        response = self.client.get(f'/equipos/ver/{team_id}', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(b'Machamp' in response.data)
        self.assertTrue(b'Charizard' in response.data)
        response = self.client.get(f'/pokemon/6', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(b'Charizard' in response.data)
        
        

    def test_chatbot_13(self):
        """
        Chatbot-13: Seleccionar la opción "Consultar cadena evolutiva".
        Resultado esperado: Se muestra la lista completa de Pokémon para la selección.
        """
        # Registro & Login
        self.client.post('/registro', data={
            'username': 'user13', 'password': 'pw', 'name': 'U13', 'surname': 'S',
            'email': 'u13@ex.com', 'dni': '13131313J', 'fav_pokemon': 25
        })
        self.aprobar_usuario('user13')
        self.client.post('/login', data={'username': 'user13', 'password': 'pw'})
        
        response = self.client.get('/chatbot/ver_cadena_evolutiva', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(b'lpokemon' in response.data)
    
    def test_chatbot_14(self):
        """
        Chatbot-14: Seleccionar un Pokémon con cadena evolutiva lineal (ej. "Pichu").
        Resultado esperado: El ChatBot muestra la cadena evolutiva en forma lineal.
        """
        # Registro & Login
        self.client.post('/registro', data={
            'username': 'user14', 'password': 'pw', 'name': 'U14', 'surname': 'S',
            'email': 'u14@ex.com', 'dni': '14141414J', 'fav_pokemon': 25
        })
        self.aprobar_usuario('user14')
        self.client.post('/login', data={'username': 'user14', 'password': 'pw'})
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
                       INSERT INTO PokeEspecie (id_pokedex, name, description, ps, attack, defense, special_attack,
                                                special_defense, speed)
                       VALUES (25, 'Pikachu', 'Ratón eléctrico', 35, 55, 40, 50, 50, 90)
                       """)
        conn.commit()
        conn.close()
        
        response = self.client.get('/cadena_evolutiva/25', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(b'Cadena Evolutiva de Pikachu' in response.data)
    
    def test_chatbot_15(self):
        """
        Chatbot-15: Seleccionar un Pokémon con cadena evolutiva ramificada (ej. "Ralts").
        Resultado esperado: El ChatBot muestra la cadena evolutiva con todas sus ramas.
        """
        # Registro & Login
        self.client.post('/registro', data={
            'username': 'user15', 'password': 'pw', 'name': 'U15', 'surname': 'S',
            'email': 'u15@ex.com', 'dni': '15151515J', 'fav_pokemon': 25
        })
        self.aprobar_usuario('user15')
        self.client.post('/login', data={'username': 'user15', 'password': 'pw'})
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
                       INSERT INTO PokeEspecie (id_pokedex, name, description, ps, attack, defense, special_attack,
                                                special_defense, speed)
                       VALUES (280, 'Ralts', 'Ralts', 28, 25, 25, 45, 35, 40)
                       """)
        conn.commit()
        conn.close()
        
        response = self.client.get('/cadena_evolutiva/280', follow_redirects=True)
        print(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(b'Cadena Evolutiva de Ralts' in response.data)
        

    def test_chatbot_16(self):
        """ 
        Chatbot-16: Seleccionar un Pokémon con varias evoluciones posibles (ej. “Hitmontop”).
        Resultado esperado: El ChatBot muestra todas las evoluciones posibles.
        """
        # Registro & Login
        self.client.post('/registro', data={
            'username': 'user16', 'password': 'pw', 'name': 'U16', 'surname': 'S',
            'email': 'u16@ex.com', 'dni': '16161616J', 'fav_pokemon': 25
        })
        self.aprobar_usuario('user16')
        self.client.post('/login', data={'username': 'user16', 'password': 'pw'})
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
                       INSERT INTO PokeEspecie (id_pokedex, name, description, ps, attack, defense, special_attack,
                                                special_defense, speed)
                       VALUES (237, 'Hitmontop', 'Hitmontop', 50, 95, 95, 35, 110, 70)
                       """)
        conn.commit()
        conn.close()
        
        response = self.client.get('/cadena_evolutiva/237', follow_redirects=True)
        print(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(b'Cadena Evolutiva de Hitmontop' in response.data)
    
    def test_chatbot_17(self):
        """ 
        Chatbot-17: Seleccionar un Pokémon que no tenga línea evolutiva (ej. "Tauros").
        Resultado esperado: El ChatBot muestra solo al Pokémon seleccionado.
        """
        # Registro & Login
        self.client.post('/registro', data={
            'username': 'user17', 'password': 'pw', 'name': 'U17', 'surname': 'S',
            'email': 'u17@ex.com', 'dni': '17171717J', 'fav_pokemon': 25
        })
        self.aprobar_usuario('user17')
        self.client.post('/login', data={'username': 'user17', 'password': 'pw'})
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
                       INSERT INTO PokeEspecie (id_pokedex, name, description, ps, attack, defense, special_attack,
                                                special_defense, speed)
                       VALUES (128, 'Tauros', 'Tauros', 75, 100, 95, 40, 70, 110)
                       """)
        conn.commit()
        conn.close()
        
        response = self.client.get('/cadena_evolutiva/128', follow_redirects=True)
        print(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(b'Cadena Evolutiva de Tauros' in response.data)
    
    def test_chatbot_18(self):
        """ 
        Chatbot-18: Salir de la interfaz del ChatBot.
        Resultado esperado: Vuelve correctamente al menú principal.
        """
        self.client.post('/registro', data={
            'username': 'user18', 'password': 'pw', 'name': 'U18', 'surname': 'S',
            'email': 'u18@ex.com', 'dni': '18181818J', 'fav_pokemon': 25
        })
        self.aprobar_usuario('user18')
        self.client.post('/login', data={'username': 'user18', 'password': 'pw'})
        
        self.client.post('/chatbot/menu', follow_redirects=True)
        response = self.client.get('/menu', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(b'menu' in response.data)
    
    
if __name__ == '__main__':
    unittest.main()