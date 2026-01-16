from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from app.controller.model.GestorEquipos import GestorEquipos
from app.controller.model.Catalogo import Catalogo
from datetime import datetime


def iu_equipos_blueprint(db):
    bp = Blueprint('iu_equipos', __name__)
    gestor = GestorEquipos(db)
    catalogo = Catalogo(db)

    def registrar_actividad_equipo(username, mensaje_text):
        """Registra una acción de equipo en la tabla Mensaje"""
        try:
            fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # Escapar comillas en el mensaje
            mensaje_limpio = mensaje_text.replace("'", "''")
            sql = f"INSERT INTO Mensaje (username, message_text, date_hour) VALUES ('{username}', '{mensaje_limpio}', '{fecha_hora}')"
            db.execSQL(sql)
        except Exception as e:
            print(f"Error registrando actividad: {e}")

    @bp.route('/equipos')
    def listar_equipos():
        if 'user' not in session: return redirect(url_for('iu_mprincipal.login'))

        # USAMOS EL MÉTODO DEL DIAGRAMA: getTeams
        equipos_objs = gestor.getTeams(session['user'])
        # Convertimos a diccionarios para Jinja si es necesario, o pasamos objetos
        if session.get('chatbot_mode') == 'eval_mejor':
            return render_template('equipos_estadisticas.html', equipos=equipos_objs)
        return render_template('equipos.html', equipos=equipos_objs)

    @bp.route('/equipos/crear', methods=['POST'])
    def crear_equipo():
        if 'user' not in session: return redirect(url_for('iu_mprincipal.login'))

        nombre = request.form.get('nombre_equipo')
        if nombre:
            # USAMOS EL MÉTODO DEL DIAGRAMA: createTeam
            exito = gestor.createTeam(nombre, session['user'])  # Nota: diagrama orden (name, username)
            if exito:
                flash("Equipo creado con éxito.", 'success')
                mensaje = f"{session['user']} ha creado el equipo '{nombre}'"
                registrar_actividad_equipo(session['user'], mensaje)
            else:
                flash("Error: Nombre duplicado o fallo técnico.", 'error')

        return redirect(url_for('iu_equipos.listar_equipos'))

    @bp.route('/equipos/eliminar/<int:id_team>')
    def eliminar_equipo(id_team):
        if 'user' not in session: return redirect(url_for('iu_mprincipal.login'))

        # USAMOS EL MÉTODO DEL DIAGRAMA: deleteTeam
        if gestor.deleteTeam(id_team):
            flash("Equipo eliminado.", 'success')
        else:
            flash("Error al eliminar el equipo.", 'error')

        return redirect(url_for('iu_equipos.listar_equipos'))

    @bp.route('/equipos/ver/<int:id_team>')
    def ver_equipo(id_team):
        if 'user' not in session: return redirect(url_for('iu_mprincipal.login'))

        # Usamos el auxiliar para obtener detalles completos
        equipo = gestor._rellenarDetallesEquipo(id_team)
        if not equipo:
            return redirect(url_for('iu_equipos.listar_equipos'))

        return render_template('ver_equipo.html', equipo=equipo)

    @bp.route('/equipos/editar/<int:id_team>')
    def editar_equipo(id_team):
        if 'user' not in session: return redirect(url_for('iu_mprincipal.login'))

        equipo = gestor._rellenarDetallesEquipo(id_team)
        session['editando_equipo_id'] = id_team
        return render_template('editar_equipo.html', equipo=equipo)

    @bp.route('/equipos/guardar/<int:id_team>', methods=['POST'])
    def guardar_equipo(id_team):
        """Guarda los cambios finales del equipo y registra el mensaje de actividad"""
        if 'user' not in session:
            return redirect(url_for('iu_mprincipal.login'))

        # Obtener detalles del equipo
        equipo = gestor._rellenarDetallesEquipo(id_team)
        if not equipo:
            return redirect(url_for('iu_equipos.listar_equipos'))

        # Obtener lista de pokémon en el equipo
        pokemones = []
        if equipo.pokemonList:
            for pk in equipo.pokemonList:
                pokemones.append(pk['nombre'])

        # Crear mensaje descriptivo
        if pokemones:
            lista_pokes = ', '.join(pokemones)
            mensaje = f"{session['user']} ha modificado el equipo '{equipo.name}' y ahora lo forman: {lista_pokes}"
        else:
            mensaje = f"{session['user']} ha modificado el equipo '{equipo.name}' (vacío)"

        registrar_actividad_equipo(session['user'], mensaje)
        
        # Limpiar sesión
        if 'editando_equipo_id' in session:
            del session['editando_equipo_id']

        flash("Equipo guardado.", 'success')
        return redirect(url_for('iu_equipos.listar_equipos'))

    @bp.route('/equipos/quitar_pk/<int:id_instancia>')
    def quitar_pokemon(id_instancia):
        if 'user' not in session or 'editando_equipo_id' not in session:
            return redirect(url_for('iu_equipos.listar_equipos'))

        id_team = session['editando_equipo_id']

        # USAMOS EL MÉTODO DEL DIAGRAMA: deletePokemonFromTeam
        if gestor.deletePokemonFromTeam(id_team, id_instancia):
            flash("Pokémon eliminado.", 'success')
        else:
            flash("Error al eliminar.", 'error')

        return redirect(url_for('iu_equipos.editar_equipo', id_team=id_team))

    @bp.route('/equipos/seleccionar_add')
    def seleccionar_add():
        if 'user' not in session: return redirect(url_for('iu_mprincipal.login'))

        # Reutilizamos lógica de Catálogo para mostrar la lista de selección
        page = request.args.get('page', 1, type=int)
        filtros = {
            "nombre": request.args.get('nombre', '').strip(),
            "tipo": request.args.get('tipo', '').strip(),
            "habilidad": request.args.get('habilidad', '').strip()
        }
        lista = catalogo.obtenerListaPokemon(page, filtros)
        total = catalogo.contarPokemonFiltrados(filtros)
        total_pages = (total // 25) + (1 if total % 25 > 0 else 0)

        return render_template('seleccionar_pokemon.html',
                               pokemons=lista, pagina=page, total_p=total_pages,
                               todos_los_tipos=[], todas_las_habilidades=[])

    @bp.route('/equipos/add_pk/<int:id_pokedex>')
    def add_pk_action(id_pokedex):
        if 'user' not in session or 'editando_equipo_id' not in session:
            return redirect(url_for('iu_equipos.listar_equipos'))

        id_team = session['editando_equipo_id']

        # USAMOS EL MÉTODO DEL DIAGRAMA: addPokemonToTeam
        if gestor.addPokemonToTeam(id_team, id_pokedex, session['user']):
            flash("Pokémon añadido.", 'success')
        else:
            flash("Error: El equipo está lleno o fallo técnico.", 'error')

        return redirect(url_for('iu_equipos.editar_equipo', id_team=id_team))

    @bp.route('/equipos/evaluar')
    def evaluar_equipo():
        if 'user' not in session: return redirect(url_for('iu_mprincipal.login'))

        id_team = request.args.get('id_team')
        stat_name = request.args.get('stat')

        if not id_team:
            flash("Debe seleccionar un equipo para evaluar", "error")
            return redirect(url_for('iu_equipos.listar_equipos'))
            
        if not stat_name:
            flash("Debe seleccionar una estadística para evaluar", "error")
            return redirect(url_for('iu_equipos.listar_equipos'))

        # Usamos métodos internos de Gestor para no duplicar lógica
        # Esto podría refactorizarse a un método público getTeamDetailsWithStats
        equipo = gestor._rellenarDetallesEquipo(id_team)

        if not equipo or not equipo.pokemonList:
            flash("El equipo seleccionado está vacío", "error")
            return redirect(url_for('iu_equipos.listar_equipos'))

        # Lógica para encontrar el mejor
        best_pk = None
        max_val = -1

        for pk in equipo.pokemonList:
            # stats es un dict agregado en GestorEquipos
            val = pk['stats'].get(stat_name, 0)
            if val > max_val:
                max_val = val
                best_pk = pk

        if best_pk:
            # Redirigir a detalle
            return redirect(url_for('lpokemon.mostrarDetalle', id_pokemon=best_pk['id_pokedex']))

        flash("No se pudo evaluar.", "error")
        return redirect(url_for('iu_equipos.listar_equipos'))

    return bp