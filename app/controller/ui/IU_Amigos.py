from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from app.database.GestorBD import GestorBD


def iu_amigos_blueprint(db):
    bp = Blueprint('iu_amigos', __name__, url_prefix='/friends')

    @bp.route('/', methods=['GET', 'POST'])
    def index():
        if 'user' not in session:
            return redirect(url_for('iu_mprincipal.login'))

        me = session['user']
        gestor = GestorBD()

        # --- 1. CARGAR MIS AMIGOS (Con Pokémon Favorito) ---
        # Seleccionamos Nombre y Pokémon Favorito de todos los usuarios que estén en mi lista de amigos
        sql_amigos = f"""
            SELECT U.username, P.name as fav_poke_name
            FROM Users U
            LEFT JOIN PokeEspecie P ON U.fav_pokemon = P.id_pokedex
            WHERE U.username IN (
                SELECT user_receiver FROM Amigo WHERE user_sender='{me}' AND status=1
                UNION
                SELECT user_sender FROM Amigo WHERE user_receiver='{me}' AND status=1
            )
        """
        res_amigos = gestor.execSQL(sql_amigos)
        mis_amigos = []
        while res_amigos.next():
            mis_amigos.append({
                'username': res_amigos.getString('username'),
                'fav_poke': res_amigos.getString('fav_poke_name')
            })

        # --- 2. CARGAR SOLICITUDES PENDIENTES ---
        sql_solicitudes = f"SELECT user_sender FROM Amigo WHERE user_receiver='{me}' AND status=0"
        res_soli = gestor.execSQL(sql_solicitudes)
        mis_solicitudes = []
        while res_soli.next():
            mis_solicitudes.append({'username': res_soli.getString('user_sender')})

        # --- 3. BÚSQUEDA ---
        resultados_busqueda = []
        search_query = request.args.get('q')

        if search_query:
            sql_search = f"""
                SELECT username FROM Users 
                WHERE username LIKE '%{search_query}%' 
                AND username != '{me}' 
                AND role != 'ADMIN'
            """
            res_search = gestor.execSQL(sql_search)

            while res_search.next():
                candidato = res_search.getString('username')

                # Comprobar estado
                sql_check = f"""
                    SELECT status FROM Amigo 
                    WHERE (user_sender='{me}' AND user_receiver='{candidato}')
                       OR (user_sender='{candidato}' AND user_receiver='{me}')
                """
                res_check = gestor.execSQL(sql_check)

                estado = "NADA"
                if res_check.next():
                    st = res_check.getInt('status')
                    estado = "AMIGOS" if st == 1 else "PENDIENTE"

                resultados_busqueda.append({
                    'username': candidato,
                    'estado_relacion': estado
                })

        return render_template('amigos.html',
                               amigos=mis_amigos,
                               solicitudes=mis_solicitudes,
                               busqueda=resultados_busqueda,
                               query=search_query)

    # --- NUEVA RUTA: VER EQUIPOS DE UN AMIGO ---
    @bp.route('/teams/<username>')
    def ver_equipos_amigo(username):
        if 'user' not in session: return redirect(url_for('iu_mprincipal.login'))

        # Seguridad: Verificar si realmente son amigos antes de cotillear
        me = session['user']
        gestor = GestorBD()

        check_sql = f"""
            SELECT status FROM Amigo 
            WHERE (user_sender='{me}' AND user_receiver='{username}' AND status=1)
               OR (user_sender='{username}' AND user_receiver='{me}' AND status=1)
        """
        if not gestor.execSQL(check_sql).next():
            flash('Solo puedes ver los equipos de tus amigos.', 'error')
            return redirect(url_for('iu_amigos.index'))

        # Obtener los equipos del amigo
        sql_equipos = f"SELECT id_team, name FROM EquipoPokémon WHERE username='{username}'"
        res = gestor.execSQL(sql_equipos)

        equipos = []
        while res.next():
            equipos.append({
                'id': res.getInt('id_team'),
                'nombre': res.getString('name')
            })

        return render_template('amigo_equipos.html', amigo=username, equipos=equipos)

    # --- ACCIONES (Igual que antes) ---
    @bp.route('/add/<target>')
    def send_request(target):
        if 'user' not in session: return redirect(url_for('iu_mprincipal.login'))
        me = session['user']
        gestor = GestorBD()
        try:
            gestor.connection.execute(
                f"INSERT INTO Amigo (user_sender, user_receiver, status) VALUES ('{me}', '{target}', 0)")
            gestor.connection.commit()
            flash(f'Solicitud enviada a {target}', 'success')
        except:
            flash('Error al enviar solicitud.', 'error')
        return redirect(url_for('iu_amigos.index', q=request.args.get('last_query')))

    @bp.route('/accept/<sender>')
    def accept_request(sender):
        if 'user' not in session: return redirect(url_for('iu_mprincipal.login'))
        me = session['user']
        gestor = GestorBD()
        gestor.connection.execute(f"UPDATE Amigo SET status=1 WHERE user_sender='{sender}' AND user_receiver='{me}'")
        gestor.connection.commit()
        flash(f'¡Ahora eres amigo de {sender}!', 'success')
        return redirect(url_for('iu_amigos.index'))

    @bp.route('/reject/<sender>')
    def reject_request(sender):
        if 'user' not in session: return redirect(url_for('iu_mprincipal.login'))
        me = session['user']
        gestor = GestorBD()
        gestor.connection.execute(f"DELETE FROM Amigo WHERE user_sender='{sender}' AND user_receiver='{me}'")
        gestor.connection.commit()
        flash(f'Solicitud de {sender} rechazada.', 'info')
        return redirect(url_for('iu_amigos.index'))

    @bp.route('/delete/<friend>')
    def delete_friend(friend):
        if 'user' not in session: return redirect(url_for('iu_mprincipal.login'))
        me = session['user']
        gestor = GestorBD()
        gestor.connection.execute(f"""
            DELETE FROM Amigo 
            WHERE (user_sender='{me}' AND user_receiver='{friend}') 
               OR (user_sender='{friend}' AND user_receiver='{me}')
        """)
        gestor.connection.commit()
        flash(f'{friend} eliminado de tus amigos.', 'info')
        return redirect(url_for('iu_amigos.index'))

    return bp