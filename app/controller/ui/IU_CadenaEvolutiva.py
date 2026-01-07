from flask import Blueprint, render_template

def iu_cadena_evolutiva_blueprint(db):
    bp = Blueprint('cadena_evolutiva', __name__)

    @bp.route('/cadena_evolutiva/<int:id_pokemon>')
    def mostrarCadena(id_pokemon):
        # Por ahora es una página en blanco
        return render_template('cadena_evolutiva.html')

    return bp
