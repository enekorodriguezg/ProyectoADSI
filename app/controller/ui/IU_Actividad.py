from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from app.controller.model.GestorActividad import GestorActividad


def iu_actividad_blueprint(db):
    bp = Blueprint('iu_actividad', __name__, url_prefix='/activity')
    gestor_actividad = GestorActividad(db)

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

        # --- OBTENER ACTIVIDAD USANDO EL MODELO ---
        actividad = gestor_actividad.obtener_actividad_amigos(
            me,
            usuario_filtro=usuario_filtro if usuario_filtro else None,
            fecha_inicio=fecha_inicio if fecha_inicio else None,
            fecha_fin=fecha_fin if fecha_fin else None,
            busqueda_filtro=busqueda_filtro if busqueda_filtro else None
        )

        # --- OBTENER AMIGOS PARA EL SELECTOR DE FILTROS ---
        mis_amigos = gestor_actividad.obtener_amigos_aceptados(me)

        return render_template('actividad.html',
                               actividad=actividad,
                               amigos_count=len(mis_amigos),
                               mis_amigos=mis_amigos,
                               usuario_filtro=usuario_filtro,
                               fecha_inicio=fecha_inicio,
                               fecha_fin=fecha_fin,
                               busqueda_filtro=busqueda_filtro)

    return bp
