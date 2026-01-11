from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from app.database.GestorBD import GestorBD


def iu_admin_blueprint(db):
    bp = Blueprint('iu_admin', __name__, url_prefix='/admin')

    # --- 1. PANEL PRINCIPAL ---
    @bp.route('/')
    def panel():
        if 'user' not in session or session.get('role') != 'ADMIN':
            return redirect(url_for('iu_mprincipal.login'))
        return render_template('admin_panel.html')

    # --- 2. GESTIÓN DE SOLICITUDES (Ya lo tenías) ---
    @bp.route('/requests')
    def requests_list():
        if 'user' not in session or session.get('role') != 'ADMIN':
            return redirect(url_for('iu_mprincipal.login'))

        gestor = GestorBD()
        res = gestor.execSQL("SELECT * FROM Users WHERE role = 'PENDANT'")
        lista = []
        while res.next():
            lista.append({
                'username': res.getString('username'),
                'name': res.getString('name'),
                'surname': res.getString('surname'),
                'dni': res.getString('dni'),
                'email': res.getString('email')
            })
        return render_template('admin_requests.html', usuarios=lista)

    # Rutas de aprobar/rechazar solicitudes (abreviadas aquí, mantén las tuyas)
    @bp.route('/approve/<username>')
    def approve_user(username):
        # ... (Tu código de aprobar) ...
        gestor = GestorBD()
        gestor.connection.execute(f"UPDATE Users SET role='USER' WHERE username='{username}'")
        gestor.connection.commit()
        flash(f'Usuario {username} aprobado.', 'success')
        return redirect(url_for('iu_admin.requests_list'))

    @bp.route('/reject/<username>')
    def reject_user(username):
        # ... (Tu código de rechazar) ...
        gestor = GestorBD()
        gestor.connection.execute(f"DELETE FROM Users WHERE username='{username}'")
        gestor.connection.commit()
        flash(f'Solicitud de {username} rechazada.', 'info')
        return redirect(url_for('iu_admin.requests_list'))

    # --- 3. GESTIÓN DE USUARIOS (NUEVO) ---
    @bp.route('/users', methods=['GET'])
    def users_list():
        if 'user' not in session or session.get('role') != 'ADMIN':
            return redirect(url_for('iu_mprincipal.login'))

        gestor = GestorBD()

        # BUSCADOR: Si envían ?q=pepe, filtramos
        query = request.args.get('q')
        if query:
            sql = f"SELECT * FROM Users WHERE role = 'USER' AND username LIKE '%{query}%'"
        else:
            sql = "SELECT * FROM Users WHERE role = 'USER'"

        res = gestor.execSQL(sql)

        lista_usuarios = []
        while res.next():
            lista_usuarios.append({
                'username': res.getString('username'),
                'name': res.getString('name'),
                'surname': res.getString('surname'),
                'dni': res.getString('dni'),
                'email': res.getString('email')
            })

        return render_template('admin_users.html', usuarios=lista_usuarios, search_query=query)

    # ACCIÓN 1: MODIFICAR DATOS
    @bp.route('/edit_user/<username>', methods=['GET', 'POST'])
    def edit_user(username):
        if 'user' not in session or session.get('role') != 'ADMIN':
            return redirect(url_for('iu_mprincipal.login'))

        gestor = GestorBD()

        if request.method == 'POST':
            nombre = request.form['name']
            apellido = request.form['surname']
            dni = request.form['dni']
            email = request.form['email']
            # Opcional: Cambiar contraseña si se escribe algo
            nueva_clave = request.form['password']

            try:
                if nueva_clave:
                    sql = f"UPDATE Users SET name='{nombre}', surname='{apellido}', dni='{dni}', email='{email}', password='{nueva_clave}' WHERE username='{username}'"
                else:
                    sql = f"UPDATE Users SET name='{nombre}', surname='{apellido}', dni='{dni}', email='{email}' WHERE username='{username}'"

                gestor.connection.execute(sql)
                gestor.connection.commit()
                flash(f'Datos de {username} actualizados.', 'success')
                return redirect(url_for('iu_admin.users_list'))
            except Exception as e:
                flash(f'Error al editar: {e}', 'error')

        # Cargar datos actuales
        res = gestor.execSQL(f"SELECT * FROM Users WHERE username='{username}'")
        datos = {}
        if res.next():
            datos = {
                'username': res.getString('username'),
                'name': res.getString('name'),
                'surname': res.getString('surname'),
                'dni': res.getString('dni'),
                'email': res.getString('email')
            }

        return render_template('admin_edit_user.html', usuario=datos)

    # ACCIÓN 2: CONVERTIR EN ADMIN
    @bp.route('/make_admin/<username>')
    def make_admin(username):
        if 'user' not in session or session.get('role') != 'ADMIN':
            return redirect(url_for('iu_mprincipal.login'))

        gestor = GestorBD()
        gestor.connection.execute(f"UPDATE Users SET role='ADMIN' WHERE username='{username}'")
        gestor.connection.commit()
        flash(f'¡{username} ahora es Administrador!', 'success')
        return redirect(url_for('iu_admin.users_list'))

    # ACCIÓN 3: ELIMINAR CUENTA
    @bp.route('/delete_user/<username>')
    def delete_user(username):
        if 'user' not in session or session.get('role') != 'ADMIN':
            return redirect(url_for('iu_mprincipal.login'))

        gestor = GestorBD()
        gestor.connection.execute(f"DELETE FROM Users WHERE username='{username}'")
        gestor.connection.commit()
        flash(f'El usuario {username} ha sido eliminado permanentemente.', 'info')
        return redirect(url_for('iu_admin.users_list'))

    return bp