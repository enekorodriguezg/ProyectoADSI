from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from app.controller.model.Catalogo import Catalogo
from datetime import datetime


def iu_lpokemon_blueprint(db):
    bp = Blueprint('lpokemon', __name__)
    catalogo = Catalogo(db)

    def registrar_actividad_pokemon(username, mensaje_text):
        """Registra una acción de pokémon en la tabla Mensaje"""
        try:
            fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # Escapar comillas en el mensaje
            mensaje_limpio = mensaje_text.replace("'", "''")
            sql = f"INSERT INTO Mensaje (username, message_text, date_hour) VALUES ('{username}', '{mensaje_limpio}', '{fecha_hora}')"
            db.execSQL(sql)
        except Exception as e:
            print(f"Error registrando actividad: {e}")

    @bp.route('/lpokemon')
    def mostrarLista():
        # --- (Tu código original de lista se mantiene igual) ---
        res = db.execSQL("""
                         SELECT P.name
                         FROM Evoluciona E
                                  JOIN PokeEspecie P ON E.id_evolution = P.id_pokedex
                         WHERE E.id_base = 1
                         """)

        page = request.args.get('page', 1, type=int)
        order_by = request.args.get('order_by', 'id')
        direction = request.args.get('direction', 'ASC')

        filtros = {
            "nombre": request.args.get('nombre', '').strip(),
            "tipo": request.args.get('tipo', '').strip(),
            "habilidad": request.args.get('habilidad', '').strip()
        }

        lista = catalogo.obtenerListaPokemon(
            pagina=page,
            filtros=filtros,
            order_by=order_by,
            direction=direction
        )

        total_filtrados = catalogo.contarPokemonFiltrados(filtros)
        total_paginas = (total_filtrados // 25) + (1 if total_filtrados % 25 > 0 else 0)

        if page > total_paginas and total_paginas > 0:
            page = total_paginas

        rango_paginas = range(max(1, page - 2), min(total_paginas, page + 2) + 1)

        res_tipos = db.execSQL("SELECT name FROM Tipo ORDER BY name")
        lista_tipos = []
        while res_tipos.next():
            lista_tipos.append(res_tipos.getString("name"))

        res_habs = db.execSQL("SELECT name FROM Habilidad ORDER BY name")
        lista_habs = []
        while res_habs.next():
            lista_habs.append(res_habs.getString("name"))

        session['last_pokedex_url'] = request.full_path

        return render_template('lpokemon.html',
                               pokemons=lista,
                               order_by=order_by,
                               direction=direction,
                               todos_los_tipos=lista_tipos,
                               todas_las_habilidades=lista_habs,
                               pagina=page,
                               rango=rango_paginas,
                               total_p=total_paginas)

    @bp.route('/pokemon/<int:id_pokemon>')
    def mostrarDetalle(id_pokemon):
        catalogo = Catalogo(db)
        pokemon_detalles = catalogo.obtenerDetallePokemon(id_pokemon)

        if not pokemon_detalles:
            return "Pokémon no encontrado", 404

        return_url = session.get('last_pokedex_url', '/lpokemon')
        if session.get('chatbot_mode') == 'hab_est':
             return_url = url_for('chatbot.index')
        elif session.get('chatbot_mode') == 'eval_mejor':
             return_url = url_for('iu_equipos.listar_equipos')

        # --- NUEVO: Averiguar el favorito actual del usuario ---
        # --- NUEVO: Averiguar el favorito actual del usuario ---
        id_fav_actual = -1
        if 'user' in session:
            # CORRECCIÓN: Usamos COALESCE(fav_pokemon, 0)
            # Esto le dice a la base de datos: "Si es NULL, devuélveme un 0".
            sql = f"SELECT COALESCE(fav_pokemon, 0) as fav_pokemon FROM Users WHERE username = '{session['user']}'"
            res_fav = db.execSQL(sql)

            if res_fav.next():
                val = res_fav.getInt('fav_pokemon')  # Ahora 'val' será 0, nunca None
                if val and val > 0:
                    id_fav_actual = val
        # -------------------------------------------------------
        # -------------------------------------------------------

        # Pasamos 'fav_id' a la plantilla
        return render_template('pokemon_detalle.html',
                               p=pokemon_detalles,
                               return_url=return_url,
                               fav_id=id_fav_actual)

    # --- NUEVA RUTA: FIJAR FAVORITO ---
    @bp.route('/set_favorite/<int:id_pokemon>')
    def set_favorite(id_pokemon):
        # 1. Seguridad
        if 'user' not in session:
            flash('Debes iniciar sesión para tener un favorito.', 'error')
            return redirect(url_for('iu_mprincipal.login'))

        usuario = session['user']

        try:
            # 2. Actualizar BD
            sql = f"UPDATE Users SET fav_pokemon = {id_pokemon} WHERE username = '{usuario}'"
            db.execSQL(sql)

            # 3. Obtener nombre para el mensaje (estético)
            res = db.execSQL(f"SELECT name FROM PokeEspecie WHERE id_pokedex = {id_pokemon}")
            poke_name = res.getString('name') if res.next() else "Pokémon"

            # 4. Registrar actividad
            mensaje = f"{usuario} ha establecido a {poke_name} como su Pokémon favorito"
            registrar_actividad_pokemon(usuario, mensaje)

            flash(f'¡{poke_name} es ahora tu Pokémon favorito!', 'success')
        except Exception as e:
            flash(f'Error al guardar favorito: {e}', 'error')

        # 4. Volver a la ficha del Pokémon
        return redirect(url_for('lpokemon.mostrarDetalle', id_pokemon=id_pokemon))

    return bp