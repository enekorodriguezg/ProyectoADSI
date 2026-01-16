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

from flask import session
from app import create_app
from config import Config


class TestGestionUsuarios(unittest.TestCase):
    def setUp(self):
        """Configuración rápida con Mocking."""
        # 1. Crear BD temporal
        self.db_fd, self.db_path = tempfile.mkstemp()

        # 2. Configurar app
        self.original_db_path = Config.DB_PATH
        Config.DB_PATH = self.db_path

        # 3. MOCK: Evitar carga masiva de PokeAPI
        self.patcher = patch('app.database.GestorBD.GestorBD.cargar_toda_la_base_de_datos')
        self.mock_carga = self.patcher.start()

        # 4. Iniciar app
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.app.config['SECRET_KEY'] = 'test_key'
        self.client = self.app.test_client()

        # 5. Crear tablas e insertar datos mínimos
        schema_path = os.path.join(project_root, 'app', 'database', 'schema.sql')
        conn = sqlite3.connect(self.db_path)
        with open(schema_path, encoding='utf-8') as f:
            conn.executescript(f.read())

        cursor = conn.cursor()
        # Datos mínimos de Pokémon
        cursor.execute("INSERT INTO PokeEspecie (id_pokedex, name, description) VALUES (25, 'Pikachu', 'Mouse')")
        cursor.execute("INSERT INTO PokeEspecie (id_pokedex, name, description) VALUES (175, 'Togepi', 'Egg')")
        conn.commit()
        conn.close()

    def tearDown(self):
        """Limpieza."""
        self.patcher.stop()
        os.close(self.db_fd)
        try:
            os.unlink(self.db_path)
        except PermissionError:
            pass
        Config.DB_PATH = self.original_db_path

    # --- HELPER: Aprobar usuario manualmente ---
    def aprobar_usuario(self, username):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE Users SET role='USER' WHERE username=?", (username,))
        conn.commit()
        conn.close()

    # ==========================================
    # TESTS
    # ==========================================

    def test_registro_usuario_exitoso(self):
        response = self.client.post('/registro', data={
            'username': 'testuser',
            'password': 'password123',
            'name': 'Test',
            'surname': 'User',
            'email': 'test@example.com',
            'dni': '12345678A',
            'fav_pokemon': 25
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Users WHERE username = ?", ('testuser',))
        user = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(user, "El usuario no se ha creado en la BD")
        self.assertEqual(user[3], 'Test')
        # Por defecto debe ser PENDANT
        self.assertEqual(user[7], 'PENDANT')

    def test_registro_usuario_duplicado(self):
        # 1. Crear usuario inicial
        self.client.post('/registro', data={
            'username': 'uniqueuser',
            'password': 'password123',
            'name': 'User1',
            'surname': 'Test',
            'email': 'u1@example.com',
            'dni': '11111111A',
            'fav_pokemon': 25
        })

        # 2. Intentar duplicar
        self.client.post('/registro', data={
            'username': 'uniqueuser',
            'password': 'password456',
            'name': 'User2',
            'surname': 'Test',
            'email': 'u2@example.com',
            'dni': '22222222B',
            'fav_pokemon': 25
        }, follow_redirects=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Users WHERE username = ?", ('uniqueuser',))
        count = cursor.fetchone()[0]
        conn.close()

        self.assertEqual(count, 1)

    def test_login_exitoso(self):
        # 1. Registrar
        self.client.post('/registro', data={
            'username': 'loginuser',
            'password': 'mypassword',
            'name': 'Login',
            'surname': 'User',
            'email': 'login@example.com',
            'dni': '99999999Z',
            'fav_pokemon': 25
        })

        # 2. IMPORTANTE: Aprobar usuario manualmente (simular Admin)
        self.aprobar_usuario('loginuser')

        # 3. Intentar login
        response = self.client.post('/login', data={
            'username': 'loginuser',
            'password': 'mypassword'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)

        with self.client.session_transaction() as sess:
            self.assertTrue('user' in sess, "Fallo al iniciar sesión: ¿El usuario sigue PENDANT?")
            self.assertEqual(sess['user'], 'loginuser')

    def test_flujo_completo_amistad(self):
        # 1. Registrar usuarios
        self.client.post('/registro', data={
            'username': 'ash', 'password': 'pika', 'name': 'Ash', 'surname': 'K',
            'email': 'ash@poke.com', 'dni': '00000001A', 'fav_pokemon': 25
        })
        self.client.post('/registro', data={
            'username': 'misty', 'password': 'toge', 'name': 'Misty', 'surname': 'W',
            'email': 'misty@poke.com', 'dni': '00000002B', 'fav_pokemon': 175
        })

        # 2. Aprobar ambos usuarios
        self.aprobar_usuario('ash')
        self.aprobar_usuario('misty')

        # 3. Ash envía solicitud
        self.client.post('/login', data={'username': 'ash', 'password': 'pika'})
        self.client.get('/friends/add/misty', follow_redirects=True)

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT status FROM Amigo WHERE user_sender='ash' AND user_receiver='misty'")
        row = c.fetchone()
        self.assertIsNotNone(row, "No se encontró la solicitud")
        self.assertEqual(row[0], 0)
        conn.close()

        self.client.get('/logout')

        # 4. Misty acepta
        self.client.post('/login', data={'username': 'misty', 'password': 'toge'})
        self.client.get('/friends/accept/ash', follow_redirects=True)

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT status FROM Amigo WHERE user_sender='ash' AND user_receiver='misty'")
        row = c.fetchone()
        conn.close()

        self.assertEqual(row[0], 1)


if __name__ == '__main__':
    unittest.main()