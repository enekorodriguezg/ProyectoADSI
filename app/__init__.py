import os.path
import sqlite3

from flask import Flask

from app.controller.ui.IU_MPrincipal import iu_mprincipal_blueprint
from app.controller.ui.IU_LPokemon import iu_lpokemon_blueprint
from app.controller.ui.IU_Chatbot import iu_chatbot_blueprint
from app.controller.ui.IU_CompatibilidadTipos import iu_compatibilidad_blueprint
from app.controller.ui.IU_CadenaEvolutiva import iu_cadena_evolutiva_blueprint
from app.database.GestorBD import GestorBD
from config import Config


def init_db():
    print("Iniciando la base de datos")
    if os.path.exists(Config.DB_PATH):
        print("La base de datos existe")
        conn = sqlite3.connect(Config.DB_PATH)
        with open('app/database/schema.sql') as f:
            conn.executescript(f.read())
        conn.close()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    init_db()
    db = GestorBD()

    # Comprobamos cuántos Pokémon tenemos en la tabla
    res_pokes = db.execSQL("SELECT COUNT(*) as total FROM PokeEspecie")
    total_actual = res_pokes.getInt("total") if res_pokes.next() else 0

    # CAMBIO: Solo entra si realmente faltan datos.
    # Si total_actual es 1025, el programa saltará directamente a los Blueprints.
    if total_actual < 1025:
        print(f"Base de datos incompleta ({total_actual}/1025). Completando descarga...")
        db.cargar_toda_la_base_de_datos()
    else:
        print("Base de datos verificada: 1025 Pokémon detectados. Iniciando web...")

    # Registrar Blueprints
    app.register_blueprint(iu_mprincipal_blueprint(db))
    app.register_blueprint(iu_lpokemon_blueprint(db))
    app.register_blueprint(iu_chatbot_blueprint(db))
    app.register_blueprint(iu_compatibilidad_blueprint(db))
    app.register_blueprint(iu_cadena_evolutiva_blueprint(db))

    return app