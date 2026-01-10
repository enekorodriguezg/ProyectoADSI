from flask import Blueprint, render_template, redirect, url_for, session, request, flash
from app.database.GestorBD import GestorBD

def iu_mprincipal_blueprint(db):
    bp = Blueprint('iu_mprincipal', __name__)

    # --- RUTA 1: LANDING PAGE (RAÍZ) ---
    # ¡ESTA ES LA QUE FALTABA Y DABA ERROR 404!
    @bp.route('/')
    def index():
        # Si ya está logueado, lo mandamos al menú
        if 'user' in session:
            session['chatbot_mode'] = None
            return redirect(url_for('iu_mprincipal.menu_principal'))
        # Si no, mostramos la portada bonita
        return render_template('index.html')

    # --- RUTA 2: LOGIN ---
    @bp.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            usuario = request.form['username']
            clave = request.form['password']

            gestor = GestorBD()

            # 1. Buscamos al usuario en la BD
            sql = f"SELECT * FROM Users WHERE username = '{usuario}'"
            res = gestor.execSQL(sql)

            if res.next():
                db_password = res.getString('password')
                db_role = res.getString('role')

                # 2. Verificamos la contraseña
                if clave == db_password:
                    # Lógica de PENDANT
                    if db_role == 'PENDANT':
                        flash('Su cuenta está pendiente de aprobar.','info')
                        return render_template('login.html')

                    # Login correcto
                    session['user'] = usuario
                    session['role'] = db_role
                    session.pop('chatbot_mode', None)

                    return redirect(url_for('iu_mprincipal.menu_principal'))

                else:
                    flash('Usuario o contraseña incorrectos.','error') # Mensaje genérico por seguridad
            else:
                flash('Usuario o contraseña incorrectos.','error')

        return render_template('login.html')

    # --- RUTA 3: REGISTRO ---
    @bp.route('/register', methods=['GET', 'POST'])
    def registro():
        if request.method == 'POST':
            usuario = request.form['username']
            clave = request.form['password']
            nombre = request.form['name']
            apellido = request.form['surname']
            dni = request.form['dni']
            email = request.form['email']

            gestor = GestorBD()

            try:
                # Comprobar duplicados
                check_user = gestor.execSQL(f"SELECT username FROM Users WHERE username = '{usuario}'")
                if check_user.next():
                    flash('¡Ese nombre de usuario ya está cogido! Elige otro.','error')
                    return render_template('register.html')

                check_dni = gestor.execSQL(f"SELECT dni FROM Users WHERE dni = '{dni}'")
                if check_dni.next():
                    flash('Ya existe una cuenta con este DNI.','error')
                    return render_template('register.html')

                # Insertar como PENDANT
                sql = f"""
                    INSERT INTO Users (username, password, name, surname, dni, email, role)
                    VALUES ('{usuario}', '{clave}', '{nombre}', '{apellido}', '{dni}', '{email}', 'PENDANT')
                """
                gestor.connection.execute(sql)
                gestor.connection.commit()

                flash('¡Cuenta creada con éxito! Ahora inicia sesión.','success')
                return redirect(url_for('iu_mprincipal.login'))

            except Exception as e:
                error_msg = str(e)
                if "UNIQUE constraint failed" in error_msg:
                    if "email" in error_msg:
                        flash("Ese correo electrónico ya está registrado.",'error')
                    else:
                        flash("Error: Datos duplicados.",'error')
                else:
                    flash(f"Error técnico: {error_msg}")

                return render_template('register.html')

        return render_template('register.html')

    # --- RUTA 4: MENÚ PRINCIPAL ---
    @bp.route('/menu')
    def menu_principal():
        if 'user' not in session:
            return redirect(url_for('iu_mprincipal.login'))
        return render_template('mprincipal.html')

    # --- RUTA 5: LOGOUT ---
    @bp.route('/logout')
    def logout():
        session.clear()
        return redirect(url_for('iu_mprincipal.index'))

    # --- RUTA 6: PERFIL / MODIFICAR DATOS ---
    @bp.route('/profile', methods=['GET', 'POST'])
    def profile():
        # Seguridad: Si no está logueado, fuera
        if 'user' not in session:
            return redirect(url_for('iu_mprincipal.login'))

        usuario_actual = session['user']
        gestor = GestorBD()

        if request.method == 'POST':
            # 1. Recoger datos nuevos del formulario
            nombre = request.form['name']
            apellido = request.form['surname']
            dni = request.form['dni']
            email = request.form['email']
            nueva_clave = request.form['password']  # Puede venir vacía

            try:
                # 2. Construir la SQL de actualización
                # Si escribió contraseña nueva, actualizamos todo.
                if nueva_clave:
                    sql = f"""
                        UPDATE Users 
                        SET name='{nombre}', surname='{apellido}', dni='{dni}', email='{email}', password='{nueva_clave}'
                        WHERE username='{usuario_actual}'
                    """
                else:
                    # Si NO escribió contraseña, actualizamos todo MENOS la contraseña
                    sql = f"""
                        UPDATE Users 
                        SET name='{nombre}', surname='{apellido}', dni='{dni}', email='{email}'
                        WHERE username='{usuario_actual}'
                    """

                gestor.connection.execute(sql)
                gestor.connection.commit()

                flash('¡Datos actualizados correctamente!', 'success')  # Verde
                return redirect(url_for('iu_mprincipal.menu_principal'))

            except Exception as e:
                flash(f'Error al actualizar: {e}', 'error')  # Rojo
                return redirect(url_for('iu_mprincipal.profile'))

        # --- Lógica GET (Cargar datos) ---
        # Buscamos los datos actuales para rellenar el formulario
        sql = f"SELECT * FROM Users WHERE username = '{usuario_actual}'"
        res = gestor.execSQL(sql)

        datos_usuario = {}
        if res.next():
            datos_usuario = {
                'name': res.getString('name'),
                'surname': res.getString('surname'),
                'dni': res.getString('dni'),
                'email': res.getString('email')
                # La contraseña no la enviamos por seguridad
            }

        return render_template('profile.html', datos=datos_usuario)
    return bp

