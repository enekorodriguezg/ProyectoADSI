from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from datetime import datetime


def iu_actividad_blueprint(db):
    bp = Blueprint('iu_actividad', __name__, url_prefix='/activity')

    @bp.route('/', methods=['GET'])
    def index():
        if 'user' not in session:
            return redirect(url_for('iu_mprincipal.login'))

        me = session['user']

        # --- OBTENER PARÁMETROS DE FILTRO ---
        usuario_filtro = request.args.get('usuario', '').strip()
        fecha_inicio = request.args.get('fecha_inicio', '').strip()
        fecha_fin = request.args.get('fecha_fin', '').strip()
        busqueda_filtro = request.args.get('busqueda', '').strip()

        # --- 1. OBTENER MIS AMIGOS (Solo aceptados) ---
        sql_amigos = f"""
            SELECT user_receiver as amigo FROM Amigo 
            WHERE user_sender='{me}' AND status=1
            UNION
            SELECT user_sender as amigo FROM Amigo 
            WHERE user_receiver='{me}' AND status=1
        """
        res_amigos = db.execSQL(sql_amigos)
        mis_amigos = []
        while res_amigos.next():
            mis_amigos.append(res_amigos.getString('amigo'))

        # --- 2. OBTENER ACTIVIDAD (Mensajes de mis amigos) ---
        actividad = []
        
        if mis_amigos:
            amigos_list = "', '".join(mis_amigos)
            
            # Construir la query con filtros
            sql_actividad = f"""
                SELECT username, message_text, date_hour 
                FROM Mensaje 
                WHERE username IN ('{amigos_list}')
            """
            
            # Filtro por usuario
            if usuario_filtro:
                sql_actividad += f" AND username = '{usuario_filtro}'"
            
            # Filtro por rango de fechas
            if fecha_inicio and fecha_fin:
                sql_actividad += f" AND DATE(date_hour) BETWEEN '{fecha_inicio}' AND '{fecha_fin}'"
            elif fecha_inicio:
                sql_actividad += f" AND DATE(date_hour) >= '{fecha_inicio}'"
            elif fecha_fin:
                sql_actividad += f" AND DATE(date_hour) <= '{fecha_fin}'"
            
            # Filtro por búsqueda de texto
            if busqueda_filtro:
                sql_actividad += f" AND message_text LIKE '%{busqueda_filtro}%'"
            
            sql_actividad += " ORDER BY date_hour DESC LIMIT 50"
            
            res_actividad = db.execSQL(sql_actividad)
            
            while res_actividad.next():
                actividad.append({
                    'username': res_actividad.getString('username'),
                    'message': res_actividad.getString('message_text'),
                    'fecha': res_actividad.getString('date_hour')
                })

        return render_template('actividad.html',
                               actividad=actividad,
                               amigos_count=len(mis_amigos),
                               mis_amigos=mis_amigos,
                               usuario_filtro=usuario_filtro,
                               fecha_inicio=fecha_inicio,
                               fecha_fin=fecha_fin,
                               busqueda_filtro=busqueda_filtro)

    return bp
