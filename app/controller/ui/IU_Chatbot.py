from flask import Blueprint, render_template, session, redirect, url_for

def iu_chatbot_blueprint(db):
    bp = Blueprint('chatbot', __name__)

    @bp.route('/chatbot')
    def index():
        return render_template('chatbot.html')

    @bp.route('/chatbot/ver_compatibilidad')
    def ver_compatibilidad():
        session['chatbot_mode'] = 'compatibilidad'
        return redirect(url_for('lpokemon.mostrarLista'))

    @bp.route('/chatbot/ver_cadena_evolutiva')
    def ver_cadena_evolutiva():
        session['chatbot_mode'] = 'consulta_evo'
        return redirect(url_for('lpokemon.mostrarLista'))

    @bp.route('/chatbot/ver_habilidades_estadisticas')
    def ver_habilidades_estadisticas():
        session['chatbot_mode'] = 'hab_est'
        return redirect(url_for('iu_equipos.listar_equipos'))

    return bp
