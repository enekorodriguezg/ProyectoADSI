from flask import Blueprint, render_template
from app.controller.model.Catalogo import Catalogo

def iu_compatibilidad_blueprint(db):
    bp = Blueprint('compatibilidad', __name__)

    @bp.route('/compatibilidad/<int:id_pokemon>')
    def mostrarCompatibilidad(id_pokemon):
        catalogo = Catalogo(db)
        # 1. Detalles básicos (Sprite + Tipos)
        pokemon_obj = catalogo.obtenerDetallePokemon(id_pokemon)
        
        if not pokemon_obj:
            return "Pokémon no encontrado", 404

        # 2. Tabla de efectividad
        tabla_efectividad = catalogo.obtenerTablaEfectividad(id_pokemon)

        return render_template('compatibilidad_tipos.html', p=pokemon_obj, tabla=tabla_efectividad)

    return bp
