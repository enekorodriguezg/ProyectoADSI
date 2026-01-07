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

    return bp
