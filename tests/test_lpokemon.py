import unittest
from unittest.mock import MagicMock, patch
from flask import Flask, session
from app.controller.model.Catalogo import Catalogo
from app.controller.ui.IU_LPokemon import iu_lpokemon_blueprint


class TestListaPokemonCajaNegraCompleto(unittest.TestCase):

    def setUp(self):
        """Configuración del entorno: Inicializa el lanzador y resguardos."""
        self.mock_db = MagicMock()
        self.app = Flask(__name__, template_folder=".")
        self.app.secret_key = 'clave_segura_para_pruebas'
        self.app.register_blueprint(iu_lpokemon_blueprint(self.mock_db))
        self.client = self.app.test_client()
        self.catalogo = Catalogo(self.mock_db)

    def login_simulado(self):
        """Simula inicio de sesión para cumplir precondiciones."""
        with self.client.session_transaction() as sess:
            sess['user'] = 'usuario_test'

    # --- PRUEBAS DE CAJA NEGRA (REQUISITOS TABLA) ---

    def test_ListaP_01_acceso_denegado(self):
        """ListaP-01: Redirigir si no hay sesión."""
        response = self.client.get('/lpokemon', follow_redirects=False)
        self.assertEqual(response.status_code, 302)

    def test_ListaP_05_11_filtros_combinados(self):
        """ListaP-05, 11: Verifica búsqueda con datos existentes."""
        self.login_simulado()
        mock_res = MagicMock()
        # Aseguramos retornos para: lista pk, contar, lista tipos, lista habs
        mock_res.next.side_effect = [True, False, True, False, True, False, True, False]
        mock_res.getString.return_value = "Pikachu"
        mock_res.getInt.return_value = 1
        self.mock_db.execSQL.return_value = mock_res

        with patch('app.controller.ui.IU_LPokemon.render_template', return_value="OK"):
            with patch.object(Catalogo, 'getTiposSQL', return_value=["Electric"]):
                response = self.client.get('/lpokemon?nombre=Pika&tipo=Electric')
                self.assertEqual(response.status_code, 200)

    def test_ListaP_13_ver_detalle_existente(self):
        """ListaP-13: Acceder a información detallada."""
        self.login_simulado()
        mock_res = MagicMock()
        mock_res.next.return_value = True
        mock_res.getInt.return_value = 0
        self.mock_db.execSQL.return_value = mock_res

        with patch.object(Catalogo, 'obtenerDetallePokemon', return_value=MagicMock()):
            with patch('app.controller.ui.IU_LPokemon.render_template', return_value="OK"):
                response = self.client.get('/pokemon/25')
                self.assertEqual(response.status_code, 200)

    def test_ListaP_14_ver_detalle_inexistente(self):
        """ListaP-14: Detalle ID inexistente."""
        self.login_simulado()
        with patch.object(Catalogo, 'obtenerDetallePokemon', return_value=None):
            response = self.client.get('/pokemon/9999')
            self.assertEqual(response.status_code, 404)
            self.assertIn("Pokémon no encontrado".encode('utf-8'), response.data)

    def test_ListaP_16_caracteres_frontera(self):
        """ListaP-16: Datos frontera con 'mala idea'."""
        self.login_simulado()
        mock_res = MagicMock()
        mock_res.next.side_effect = [False, False, False, False]
        self.mock_db.execSQL.return_value = mock_res

        with patch('app.controller.ui.IU_LPokemon.render_template', return_value="OK"):
            response = self.client.get('/lpokemon?nombre=$$%//')
            self.assertEqual(response.status_code, 200)

    # --- NUEVAS PRUEBAS: PAGINACIÓN Y ORDENACIÓN (CORREGIDAS) ---

    def test_ListaP_19_paginacion_limite(self):
        """ListaP-19: Acceder a página inexistente."""
        self.login_simulado()
        mock_res = MagicMock()
        # Suficientes retornos para todas las llamadas a next() en el controlador
        mock_res.next.side_effect = [True, False, True, False, True, False, True, False]
        mock_res.getInt.return_value = 10
        self.mock_db.execSQL.return_value = mock_res

        with patch('app.controller.ui.IU_LPokemon.render_template', return_value="OK"):
            with patch.object(Catalogo, 'getTiposSQL', return_value=["Grass"]):
                response = self.client.get('/lpokemon?page=99')
                self.assertEqual(response.status_code, 200)

    def test_ListaP_20_cambio_ordenacion(self):
        """ListaP-20: Cambiar el orden de la lista."""
        self.login_simulado()
        mock_res = MagicMock()
        mock_res.next.side_effect = [False, False, False, False, False]
        self.mock_db.execSQL.return_value = mock_res

        with patch('app.controller.ui.IU_LPokemon.render_template', return_value="OK"):
            self.client.get('/lpokemon?order_by=name&direction=DESC')

            # Buscamos en el historial de llamadas si alguna contiene el ORDER BY esperado
            consultas = [call.args[0] for call in self.mock_db.execSQL.call_args_list]
            found = any("ORDER BY P.name DESC" in c for c in consultas)
            self.assertTrue(found, "No se encontró la consulta con el ordenamiento correcto")


if __name__ == '__main__':
    unittest.main()