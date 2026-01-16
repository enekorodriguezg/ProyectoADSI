import unittest
import os
import sys
import tempfile
import sqlite3
import gc
import time
from unittest.mock import patch
from datetime import datetime, timedelta

# --- AJUSTE DE RUTAS ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from app import create_app
from config import Config


class TestChangelogAcceso(unittest.TestCase):
    """Acceso-01 y Acceso-02: Control de acceso al changelog"""

    def setUp(self):
        """Configuración inicial para cada test"""
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.original_db_path = Config.DB_PATH
        Config.DB_PATH = self.db_path

        self.patcher = patch('app.database.GestorBD.GestorBD.cargar_toda_la_base_de_datos')
        self.mock_carga = self.patcher.start()

        # Crear schema ANTES de create_app
        schema_path = os.path.join(project_root, 'app', 'database', 'schema.sql')
        conn = sqlite3.connect(self.db_path)
        with open(schema_path, encoding='utf-8') as f:
            conn.executescript(f.read())

        cursor = conn.cursor()
        cursor.execute("INSERT INTO Users (username, password, name, surname, dni, email, role) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                      ("testuser1", "hashed_pwd", "Test", "User1", "12345678A", "test1@test.com", "user"))
        cursor.execute("INSERT INTO Users (username, password, name, surname, dni, email, role) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                      ("testuser2", "hashed_pwd", "Test", "User2", "87654321B", "test2@test.com", "user"))
        conn.commit()
        conn.close()

        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.app.config['SECRET_KEY'] = 'test_key'
        self.client = self.app.test_client()

    def tearDown(self):
        """Limpieza después de cada test"""
        self.patcher.stop()
        gc.collect()
        time.sleep(0.1)
        try:
            os.close(self.db_fd)
        except:
            pass
        try:
            os.unlink(self.db_path)
        except:
            pass
        Config.DB_PATH = self.original_db_path

    def test_acceso_01_visitante_redirige_login(self):
        """Acceso-01: Visitante intenta acceder a changelog, debe redirigir a login"""
        response = self.client.get('/activity/', follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', str(response.location).lower())

    def test_acceso_02_usuario_accede_changelog(self):
        """Acceso-02: Usuario autenticado puede acceder al changelog"""
        with self.client.session_transaction() as sess:
            sess['user'] = 'testuser1'
            sess['user_id'] = 1

        response = self.client.get('/activity/', follow_redirects=True)
        self.assertEqual(response.status_code, 200)


class TestChangelogFeed(unittest.TestCase):
    """Changelog-01 a Changelog-03: Contenido del feed"""

    def setUp(self):
        """Configuración inicial para cada test"""
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.original_db_path = Config.DB_PATH
        Config.DB_PATH = self.db_path

        self.patcher = patch('app.database.GestorBD.GestorBD.cargar_toda_la_base_de_datos')
        self.mock_carga = self.patcher.start()

        schema_path = os.path.join(project_root, 'app', 'database', 'schema.sql')
        conn = sqlite3.connect(self.db_path)
        with open(schema_path, encoding='utf-8') as f:
            conn.executescript(f.read())

        cursor = conn.cursor()
        cursor.execute("INSERT INTO Users (username, password, name, surname, dni, email, role) VALUES (?, ?, ?, ?, ?, ?, ?)", ('user1', 'pass', 'User', 'One', '11111111A', 'user1@test.com', 'user'))
        cursor.execute("INSERT INTO Users (username, password, name, surname, dni, email, role) VALUES (?, ?, ?, ?, ?, ?, ?)", ('user2', 'pass', 'User', 'Two', '22222222B', 'user2@test.com', 'user'))
        cursor.execute("INSERT INTO Users (username, password, name, surname, dni, email, role) VALUES (?, ?, ?, ?, ?, ?, ?)", ('user3', 'pass', 'User', 'Three', '33333333C', 'user3@test.com', 'user'))
        cursor.execute("INSERT INTO Amigo (user_sender, user_receiver, status) VALUES ('user1', 'user2', 1)")
        conn.commit()
        conn.close()

        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.app.config['SECRET_KEY'] = 'test_key'
        self.client = self.app.test_client()

    def tearDown(self):
        """Limpieza después de cada test"""
        self.patcher.stop()
        gc.collect()
        time.sleep(0.1)
        try:
            os.close(self.db_fd)
        except:
            pass
        try:
            os.unlink(self.db_path)
        except:
            pass
        Config.DB_PATH = self.original_db_path

    def test_changelog_01_feed_vacio(self):
        """Changelog-01: Feed vacío muestra pantalla sin mensajes"""
        with self.client.session_transaction() as sess:
            sess['user'] = 'user1'

        response = self.client.get('/activity/', follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def test_changelog_02_feed_solo_amigos(self):
        """Changelog-02: Feed muestra solo actividad de los amigos del usuario"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("INSERT INTO Mensaje (username, message_text, date_hour) VALUES (?, ?, ?)", ('user2', 'Mensaje de amigo', ahora))
        cursor.execute("INSERT INTO Mensaje (username, message_text, date_hour) VALUES (?, ?, ?)", ('user3', 'Mensaje de no-amigo', ahora))
        conn.commit()
        conn.close()

        with self.client.session_transaction() as sess:
            sess['user'] = 'user1'

        response = self.client.get('/activity/', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Mensaje de amigo', response.data)

    def test_changelog_03_mensajes_duplicados_con_timestamps(self):
        """Changelog-03: Mensajes duplicados se diferencian por fecha/hora en orden cronologico"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        timestamp1 = (datetime.now() - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
        timestamp2 = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        cursor.execute("INSERT INTO Mensaje (username, message_text, date_hour) VALUES (?, ?, ?)", ('user2', 'Cambio 1', timestamp1))
        cursor.execute("INSERT INTO Mensaje (username, message_text, date_hour) VALUES (?, ?, ?)", ('user2', 'Cambio 2', timestamp2))
        conn.commit()
        conn.close()

        with self.client.session_transaction() as sess:
            sess['user'] = 'user1'

        response = self.client.get('/activity/', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Cambio 1', response.data)
        self.assertIn(b'Cambio 2', response.data)


class TestChangelogFiltros(unittest.TestCase):
    """Filtros-01 a Filtros-04: Sistema de filtros"""

    def setUp(self):
        """Configuración inicial para cada test"""
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.original_db_path = Config.DB_PATH
        Config.DB_PATH = self.db_path

        self.patcher = patch('app.database.GestorBD.GestorBD.cargar_toda_la_base_de_datos')
        self.mock_carga = self.patcher.start()

        schema_path = os.path.join(project_root, 'app', 'database', 'schema.sql')
        conn = sqlite3.connect(self.db_path)
        with open(schema_path, encoding='utf-8') as f:
            conn.executescript(f.read())

        cursor = conn.cursor()
        cursor.execute("INSERT INTO Users (username, password, name, surname, dni, email, role) VALUES (?, ?, ?, ?, ?, ?, ?)", ('user1', 'pass', 'User', 'One', '11111111A', 'user1@test.com', 'user'))
        cursor.execute("INSERT INTO Users (username, password, name, surname, dni, email, role) VALUES (?, ?, ?, ?, ?, ?, ?)", ('amigo1', 'pass', 'Friend', 'One', '44444444D', 'amigo1@test.com', 'user'))
        cursor.execute("INSERT INTO Users (username, password, name, surname, dni, email, role) VALUES (?, ?, ?, ?, ?, ?, ?)", ('amigo2', 'pass', 'Friend', 'Two', '55555555E', 'amigo2@test.com', 'user'))
        cursor.execute("INSERT INTO Amigo (user_sender, user_receiver, status) VALUES ('user1', 'amigo1', 1)")
        cursor.execute("INSERT INTO Amigo (user_sender, user_receiver, status) VALUES ('user1', 'amigo2', 1)")

        ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("INSERT INTO Mensaje (username, message_text, date_hour) VALUES (?, ?, ?)", ('amigo1', 'Cambio de amigo1', ahora))
        cursor.execute("INSERT INTO Mensaje (username, message_text, date_hour) VALUES (?, ?, ?)", ('amigo2', 'Cambio de amigo2', ahora))
        conn.commit()
        conn.close()

        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.app.config['SECRET_KEY'] = 'test_key'
        self.client = self.app.test_client()

    def tearDown(self):
        """Limpieza después de cada test"""
        self.patcher.stop()
        gc.collect()
        time.sleep(0.1)
        try:
            os.close(self.db_fd)
        except:
            pass
        try:
            os.unlink(self.db_path)
        except:
            pass
        Config.DB_PATH = self.original_db_path

    def test_filtros_01_acceso_seleccion_usuarios(self):
        """Filtros-01: Acceso a filtros redirige a seleccion de usuarios"""
        with self.client.session_transaction() as sess:
            sess['user'] = 'user1'

        response = self.client.get('/activity/?usuario=amigo1', follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def test_filtros_02_selector_solo_amigos(self):
        """Filtros-02: El selector de usuarios muestra solo los amigos"""
        with self.client.session_transaction() as sess:
            sess['user'] = 'user1'

        response = self.client.get('/activity/', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'amigo', response.data.lower())

    def test_filtros_03_usuario_A_seleccionado(self):
        """Filtros-03: Usuario A seleccionado muestra solo su actividad"""
        with self.client.session_transaction() as sess:
            sess['user'] = 'user1'

        response = self.client.get('/activity/?usuario=amigo1', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Cambio de amigo1', response.data)

    def test_filtros_04_sin_filtro_todos_amigos(self):
        """Filtros-04: Sin usuarios seleccionados muestra actividad de todos los amigos"""
        with self.client.session_transaction() as sess:
            sess['user'] = 'user1'

        response = self.client.get('/activity/', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Cambio de amigo1', response.data)
        self.assertIn(b'Cambio de amigo2', response.data)


class TestChangelogCambios(unittest.TestCase):
    """Cambios-01: Propagacion de cambios al changelog de amigos"""

    def setUp(self):
        """Configuración inicial para cada test"""
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.original_db_path = Config.DB_PATH
        Config.DB_PATH = self.db_path

        self.patcher = patch('app.database.GestorBD.GestorBD.cargar_toda_la_base_de_datos')
        self.mock_carga = self.patcher.start()

        schema_path = os.path.join(project_root, 'app', 'database', 'schema.sql')
        conn = sqlite3.connect(self.db_path)
        with open(schema_path, encoding='utf-8') as f:
            conn.executescript(f.read())

        cursor = conn.cursor()
        cursor.execute("INSERT INTO Users (username, password, name, surname, dni, email, role) VALUES (?, ?, ?, ?, ?, ?, ?)", ('user1', 'pass', 'User', 'One', '11111111A', 'user1@test.com', 'user'))
        cursor.execute("INSERT INTO Users (username, password, name, surname, dni, email, role) VALUES (?, ?, ?, ?, ?, ?, ?)", ('user2', 'pass', 'User', 'Two', '22222222B', 'user2@test.com', 'user'))
        cursor.execute("INSERT INTO Users (username, password, name, surname, dni, email, role) VALUES (?, ?, ?, ?, ?, ?, ?)", ('user3', 'pass', 'User', 'Three', '33333333C', 'user3@test.com', 'user'))
        cursor.execute("INSERT INTO Amigo (user_sender, user_receiver, status) VALUES ('user1', 'user2', 1)")
        cursor.execute("INSERT INTO Amigo (user_sender, user_receiver, status) VALUES ('user2', 'user3', 1)")
        conn.commit()
        conn.close()

        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.app.config['SECRET_KEY'] = 'test_key'
        self.client = self.app.test_client()

    def tearDown(self):
        """Limpieza después de cada test"""
        self.patcher.stop()
        gc.collect()
        time.sleep(0.1)
        try:
            os.close(self.db_fd)
        except:
            pass
        try:
            os.unlink(self.db_path)
        except:
            pass
        Config.DB_PATH = self.original_db_path

    def test_cambios_01_cambio_aparece_en_amigos(self):
        """Cambios-01: Un usuario realiza un cambio, aparece en changelog de sus amigos"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("INSERT INTO Mensaje (username, message_text, date_hour) VALUES (?, ?, ?)", ('user2', 'Capture un Pokemon', ahora))
        conn.commit()
        conn.close()

        # user1 consulta su changelog (es amigo de user2)
        with self.client.session_transaction() as sess:
            sess['user'] = 'user1'

        response = self.client.get('/activity/', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Capture un Pokemon', response.data)

        # user3 consulta su changelog (tambien es amigo de user2)
        with self.client.session_transaction() as sess:
            sess['user'] = 'user3'

        response = self.client.get('/activity/', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Capture un Pokemon', response.data)


if __name__ == '__main__':
    unittest.main()
