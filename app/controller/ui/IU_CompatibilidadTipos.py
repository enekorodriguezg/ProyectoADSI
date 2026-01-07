from flask import Blueprint, render_template

def iu_compatibilidad_blueprint(db):
    bp = Blueprint('compatibilidad', __name__)

    @bp.route('/compatibilidad/<int:id_pokemon>')
    def mostrarCompatibilidad(id_pokemon):
        # Por ahora es una página en blanco
        return render_template('compatibilidad_tipos.html')

    return bp
