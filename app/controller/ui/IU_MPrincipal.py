from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from app.database.GestorBD import GestorBD
import hashlib


def iu_mprincipal_blueprint(db):
    bp = Blueprint('iu_mprincipal', __name__)

    @bp.route('/')
    def index():
        return redirect(url_for('iu_mprincipal.menu_principal'))

    @bp.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']

            # Hash de la contraseña para comparar
            hashed_pw = hashlib.sha256(password.encode()).hexdigest()

            # Consulta segura
            res = db.execSQL(f"SELECT * FROM Users WHERE username='{username}' AND password='{hashed_pw}'")

            if res.next():
                role = res.getString('role')

                # Verificamos si la cuenta está pendiente
                if role == 'PENDANT':
                    flash('Tu cuenta aún no ha sido aprobada por un administrador.', 'warning')
                    return render_template('login.html')

                # Login correcto
                session['user'] = res.getString('username')
                session['role'] = role
                return redirect(url_for('iu_mprincipal.menu_principal'))
            else:
                flash('Usuario o contraseña incorrectos', 'error')

        return render_template('login.html')

    @bp.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            name = request.form['name']
            surname = request.form['surname']
            email = request.form['email']
            dni = request.form['dni']

            hashed_pw = hashlib.sha256(password.encode()).hexdigest()

            try:
                # Insertamos con rol PENDANT
                sql = f"INSERT INTO Users (username, password, name, surname, dni, email, role) VALUES ('{username}', '{hashed_pw}', '{name}', '{surname}', '{dni}', '{email}', 'PENDANT')"
                db.connection.execute(sql)
                db.connection.commit()
                flash('Registro exitoso. Espera a que un administrador apruebe tu cuenta.', 'success')
                return redirect(url_for('iu_mprincipal.login'))
            except Exception as e:
                flash(f'Error al registrar: {e}', 'error')

        return render_template('register.html')

    @bp.route('/menu')
    def menu_principal():
        if 'user' not in session:
            return redirect(url_for('iu_mprincipal.login'))
        return render_template('mprincipal.html')

    @bp.route('/logout')
    def logout():
        session.clear()
        flash('Has cerrado sesión correctamente.', 'info')
        return redirect(url_for('iu_mprincipal.login'))

    # --- NUEVA LÓGICA: VER PERFIL ---
    @bp.route('/profile')
    def profile():
        if 'user' not in session:
            return redirect(url_for('iu_mprincipal.login'))

        username = session['user']

        # CORRECCIÓN: Usamos COALESCE(P.id_pokedex, 0)
        # Esto evita el error TypeError: int() argument must be... not 'NoneType'
        sql = f"""
            SELECT U.*, P.name as fav_poke_name, COALESCE(P.id_pokedex, 0) as fav_poke_id
            FROM Users U
            LEFT JOIN PokeEspecie P ON U.fav_pokemon = P.id_pokedex
            WHERE U.username = '{username}'
        """
        res = db.execSQL(sql)

        if res.next():
            datos_usuario = {
                'username': res.getString('username'),
                'name': res.getString('name'),
                'surname': res.getString('surname'),
                'email': res.getString('email'),
                'dni': res.getString('dni'),
                # Si es NULL, ahora vendrá como 0 gracias al COALESCE
                'fav_poke_name': res.getString('fav_poke_name'),
                'fav_poke_id': res.getInt('fav_poke_id')
            }
            return render_template('profile_view.html', user=datos_usuario)
        else:
            return "Error cargando perfil", 404

    # --- NUEVA LÓGICA: EDITAR PERFIL ---
    @bp.route('/profile/edit', methods=['GET', 'POST'])
    def edit_profile():
        if 'user' not in session:
            return redirect(url_for('iu_mprincipal.login'))

        username = session['user']

        if request.method == 'POST':
            # Recogemos datos del formulario
            nombre = request.form['name']
            apellido = request.form['surname']
            email = request.form['email']
            dni = request.form['dni']
            password = request.form['password']

            try:
                if password:  # Si escribió contraseña nueva
                    hashed = hashlib.sha256(password.encode()).hexdigest()
                    sql = f"UPDATE Users SET name='{nombre}', surname='{apellido}', email='{email}', dni='{dni}', password='{hashed}' WHERE username='{username}'"
                else:  # Si la deja en blanco, no la tocamos
                    sql = f"UPDATE Users SET name='{nombre}', surname='{apellido}', email='{email}', dni='{dni}' WHERE username='{username}'"

                db.connection.execute(sql)
                db.connection.commit()
                flash('Perfil actualizado correctamente.', 'success')
                return redirect(url_for('iu_mprincipal.profile'))  # Volvemos a la vista de perfil
            except Exception as e:
                flash(f'Error al actualizar: {e}', 'error')

        # Si es GET, cargamos los datos para rellenar el formulario
        res = db.execSQL(f"SELECT * FROM Users WHERE username='{username}'")
        if res.next():
            datos = {
                'username': res.getString('username'),
                'name': res.getString('name'),
                'surname': res.getString('surname'),
                'email': res.getString('email'),
                'dni': res.getString('dni')
            }
            return render_template('profile_edit.html', user=datos)

        return redirect(url_for('iu_mprincipal.profile'))

    return bp