from flask import Blueprint, render_template

def iu_chatbot_blueprint(db):
    bp = Blueprint('chatbot', __name__)

    @bp.route('/chatbot')
    def index():
        return render_template('chatbot.html')

    return bp
