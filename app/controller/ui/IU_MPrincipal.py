from flask import Blueprint, render_template, redirect, url_for, session


def iu_mprincipal_blueprint(db):
    bp = Blueprint('principal', __name__)

    @bp.route('/')
    def index():
        # Limpiar modo chatbot si se vuelve al inicio
        session.pop('chatbot_mode', None)
        # Renderiza la interfaz principal (el menú de botones)
        return render_template('mprincipal.html')

    @bp.route('/go_to/<section>')
    def redirect_to(section):
        # Lógica de redirección basada en el botón presionado
        # Asumiendo que tendrás otros Blueprints llamados 'lista', 'equipos', etc.
        if section == 'lista':
            return redirect(url_for('lpokemon.mostrarLista'))
        elif section == 'equipos':
            return redirect(url_for('equipos.index'))
        elif section == 'chatbot':
            return redirect(url_for('chatbot.index'))
        elif section == 'amigos':
            return redirect(url_for('amigos.index'))

        return redirect(url_for('principal.index'))

    return bp