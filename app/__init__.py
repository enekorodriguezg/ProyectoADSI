import os.path
import sqlite3
from flask import Flask

# Imports de los controladores
from app.controller.ui.IU_MPrincipal import iu_mprincipal_blueprint
from app.controller.ui.IU_LPokemon import iu_lpokemon_blueprint
from app.controller.ui.IU_Chatbot import iu_chatbot_blueprint
from app.controller.ui.IU_CompatibilidadTipos import iu_compatibilidad_blueprint
from app.controller.ui.IU_CadenaEvolutiva import iu_cadena_evolutiva_blueprint
from app.controller.ui.IU_Equipos import iu_equipos_blueprint
from app.controller.ui.IU_Admin import iu_admin_blueprint
from app.controller.ui.IU_Amigos import iu_amigos_blueprint
from app.controller.ui.IU_Actividad import iu_actividad_blueprint
from app.database.GestorBD import GestorBD
from config import Config


def init_db():
    print("Iniciando la base de datos")
    conn = sqlite3.connect(Config.DB_PATH)
    with open('app/database/schema.sql') as f:
        conn.executescript(f.read())
    conn.close()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    init_db()
    db = GestorBD()

    # Comprobaciones de base de datos (Tu lógica actual)
    res_pokes = db.execSQL("SELECT COUNT(*) as total FROM PokeEspecie")
    total_actual = res_pokes.getInt("total") if res_pokes.next() else 0

    res_evos = db.execSQL("SELECT COUNT(*) as total FROM Evoluciona")
    total_evos = res_evos.getInt("total") if res_evos.next() else 0

    if total_actual < 1025 or total_evos < 484:
        print(f"Base de datos incompleta (Pokes: {total_actual}/1025, Evos: {total_evos}). Reparando...")
        db.cargar_toda_la_base_de_datos()
    else:
        print("Base de datos verificada al 100%. Iniciando web...")

    # Registrar Blueprints
    app.register_blueprint(iu_mprincipal_blueprint(db))
    app.register_blueprint(iu_lpokemon_blueprint(db))
    app.register_blueprint(iu_chatbot_blueprint(db))
    app.register_blueprint(iu_compatibilidad_blueprint(db))
    app.register_blueprint(iu_cadena_evolutiva_blueprint(db))
    app.register_blueprint(iu_equipos_blueprint(db))
    app.register_blueprint(iu_admin_blueprint(db))
    app.register_blueprint(iu_amigos_blueprint(db))
    app.register_blueprint(iu_actividad_blueprint(db))


    return app