from flask import Blueprint, render_template, request
from app.controller.model.Catalogo import Catalogo


def iu_lpokemon_blueprint(db):
    bp = Blueprint('lpokemon', __name__)
    # Una sola instancia del servicio paratodo el blueprint
    catalogo = Catalogo(db)

    @bp.route('/lpokemon')
    def mostrarLista():

        res = db.execSQL("""
            SELECT P.name FROM Evoluciona E 
            JOIN PokeEspecie P ON E.id_evolution = P.id_pokedex 
            WHERE E.id_base = 1
        """)

        # 1. Captura de parámetros (Paginación y Orden)
        page = request.args.get('page', 1, type=int)
        order_by = request.args.get('order_by', 'id')
        direction = request.args.get('direction', 'ASC')

        # 2. Captura de Filtros
        filtros = {
            "nombre": request.args.get('nombre', '').strip(),
            "tipo": request.args.get('tipo', '').strip(),
            "habilidad": request.args.get('habilidad', '').strip()
        }

        # 3. Obtener datos filtrados y ordenados
        lista = catalogo.obtenerListaPokemon(
            pagina=page,
            filtros=filtros,
            order_by=order_by,
            direction=direction
        )

        # 4. Lógica de Paginación Dinámica
        total_filtrados = catalogo.contarPokemonFiltrados(filtros)
        total_paginas = (total_filtrados // 25) + (1 if total_filtrados % 25 > 0 else 0)

        # Ajuste de seguridad: si la página solicitada es mayor al total, ir a la última
        if page > total_paginas and total_paginas > 0:
            page = total_paginas

        rango_paginas = range(max(1, page - 2), min(total_paginas, page + 2) + 1)

        # 5. Cargar listas para los datalists (Sugerencias en el filtro)
        # Optimizamos la lectura de resultados
        res_tipos = db.execSQL("SELECT name FROM Tipo ORDER BY name")
        lista_tipos = []
        while res_tipos.next():
            lista_tipos.append(res_tipos.getString("name"))

        res_habs = db.execSQL("SELECT name FROM Habilidad ORDER BY name")
        lista_habs = []
        while res_habs.next():
            lista_habs.append(res_habs.getString("name"))

        # 6. Renderizado final con todas las variables necesarias
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
        # Paso 2: obtenerDetallePokemon(ID)
        data_json = catalogo.obtenerDetallePokemon(id_pokemon)

        if not data_json:
            return "Pokémon no encontrado", 404

        return render_template('pokemon_detalle.html', p=data_json)

    return bp
