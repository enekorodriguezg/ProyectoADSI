from app.controller.model.PokeEspecie import PokeEspecie


class Catalogo:
    def __init__(self, db):
        # Inicializamos con la conexión a la base de datos
        self.db = db

    def obtenerListaPokemon(self, pagina, filtros, order_by='id', direction='ASC'):
        """
        Obtiene una lista paginada de Pokémon aplicando filtros de nombre, tipo y habilidad.
        """
        # Calculamos cuántos registros saltar (25 por página)
        offset = (pagina - 1) * 25
        where_clauses = []

        # Construcción dinámica de la cláusula WHERE según los filtros recibidos
        if filtros.get("nombre"):
            where_clauses.append(f"P.name LIKE '%{filtros['nombre']}%'")
        if filtros.get("tipo"):
            # Filtra si el tipo coincide con el slot 1 o el slot 2
            where_clauses.append(f"(E.type1 = '{filtros['tipo']}' OR E.type2 = '{filtros['tipo']}')")
        if filtros.get("habilidad"):
            where_clauses.append(f"H.ability_name = '{filtros['habilidad']}'")

        # Unimos los filtros con 'AND' si existen
        where_str = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        # Definimos el criterio de ordenación (ID o Nombre)
        columna_orden = "P.id_pokedex" if order_by == 'id' else "P.name"

        # Consulta principal con JOINs para acceder a tipos y habilidades en la misma búsqueda
        sql = f"""
            SELECT DISTINCT P.id_pokedex, P.name
            FROM PokeEspecie P
            LEFT JOIN EsTipo E ON P.id_pokedex = E.id_pokemon
            LEFT JOIN HabilidadesPosibles H ON P.id_pokedex = H.id_pokemon
            {where_str} 
            ORDER BY {columna_orden} {direction} 
            LIMIT 25 OFFSET {offset}
        """

        res = self.db.execSQL(sql)
        lista = []

        # Procesamos los resultados del cursor
        while res.next():
            id_pk = res.getInt("id_pokedex")
            # Obtenemos los tipos llamando a la función auxiliar
            tipos_lista = self.getTiposSQL(id_pk)

            # Construimos el diccionario con la info básica y la URL de la imagen (PokeAPI)
            lista.append({
                "id": id_pk,
                "nombre": res.getString("name"),
                "imagen": f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{id_pk}.png",
                "tipos": " / ".join(tipos_lista)
            })
        return lista

    def contarPokemonFiltrados(self, filtros):
        """
        Cuenta el total de Pokémon que coinciden con los filtros para gestionar la paginación.
        """
        where_clauses = []
        if filtros.get("nombre"):
            where_clauses.append(f"P.name LIKE '%{filtros['nombre']}%'")
        if filtros.get("tipo"):
            where_clauses.append(f"(E.type1 = '{filtros['tipo']}' OR E.type2 = '{filtros['tipo']}')")
        if filtros.get("habilidad"):
            where_clauses.append(f"H.ability_name = '{filtros['habilidad']}'")

        # Optimización: Si hay filtros de tablas relacionadas, usamos JOINs
        if filtros.get("tipo") or filtros.get("habilidad"):
            sql = f"""
                SELECT COUNT(DISTINCT P.id_pokedex) as total 
                FROM PokeEspecie P
                LEFT JOIN EsTipo E ON P.id_pokedex = E.id_pokemon
                LEFT JOIN HabilidadesPosibles H ON P.id_pokedex = H.id_pokemon
                {" WHERE " + " AND ".join(where_clauses) if where_clauses else ""}
            """
        else:
            # Si solo filtramos por nombre, la consulta es mucho más ligera
            where_str = f" WHERE name LIKE '%{filtros['nombre']}%'" if filtros.get("nombre") else ""
            sql = f"SELECT COUNT(*) as total FROM PokeEspecie {where_str}"

        res = self.db.execSQL(sql)
        return res.getInt("total") if res.next() else 0

    def obtenerDetallePokemon(self, id_pokemon):
        """
        Recupera toda la información detallada de un Pokémon por su ID único.
        """
        sql = f"SELECT * FROM PokeEspecie WHERE id_pokedex = {id_pokemon}"
        res = self.db.execSQL(sql)

        if not res.next():
            return None

        # Mapeamos las estadísticas base a un diccionario
        stats = {
            "ps": res.getInt("ps"),
            "attack": res.getInt("attack"),
            "defense": res.getInt("defense"),
            "special_attack": res.getInt("special_attack"),
            "special_defense": res.getInt("special_defense"),
            "speed": res.getInt("speed")
        }

        # Creamos y devolvemos un objeto de la clase PokeEspecie con toda la info relacionada
        pokemon_obj = PokeEspecie(
            id_pokedex=res.getInt("id_pokedex"),
            name=res.getString("name"),
            description=res.getString("description"),
            weight=res.getFloat("weight"),
            height=res.getFloat("height"),
            stats=stats,
            types=self.getTiposSQL(id_pokemon),
            abilities=self.getHabilidadesSQL(id_pokemon),
            evolution=self.getCadenaEvolutivaSQL(id_pokemon)
        )

        return pokemon_obj

    def getCadenaEvolutivaSQL(self, id_pokemon):
        """
        Construye el árbol genealógico del Pokémon (forma base -> evoluciones -> mega-evoluciones/etapa 3).
        """
        id_raiz = id_pokemon
        encontrado = False

        # Bucle para encontrar al 'ancestro' original (el que no evoluciona de nadie)
        while not encontrado:
            res_p = self.db.execSQL(f"SELECT id_base FROM Evoluciona WHERE id_evolution = {id_raiz}")
            if res_p.next():
                id_raiz = res_p.getInt("id_base")
            else:
                encontrado = True

        # Función interna para obtener datos rápidos de un Pokémon en la cadena
        def get_pk_data(id_pk):
            res = self.db.execSQL(f"SELECT name FROM PokeEspecie WHERE id_pokedex = {id_pk}")
            nombre = res.getString("name") if res.next() else "???"
            return {"id": id_pk, "name": nombre, "types": self.getTiposSQL(id_pk)}

        # Etapa 1: El Pokémon inicial
        etapa1 = [get_pk_data(id_raiz)]

        # Etapa 2: Evoluciones directas del inicial
        etapa2 = []
        ids_e2 = []
        res_e2 = self.db.execSQL(f"SELECT id_evolution FROM Evoluciona WHERE id_base = {id_raiz}")
        while res_e2.next():
            id_e2 = res_e2.getInt("id_evolution")
            etapa2.append(get_pk_data(id_e2))
            ids_e2.append(str(id_e2))  # Guardamos los IDs para buscar la siguiente etapa

        # Etapa 3: Evoluciones de las evoluciones
        etapa3 = []
        if ids_e2:
            # Buscamos quién evoluciona de cualquiera de los Pokémon de la etapa 2
            res_e3 = self.db.execSQL(
                f"SELECT id_evolution, id_base FROM Evoluciona WHERE id_base IN ({','.join(ids_e2)})")
            while res_e3.next():
                id_ev = res_e3.getInt("id_evolution")
                p_e3 = get_pk_data(id_ev)
                p_e3["id_padre"] = res_e3.getInt("id_base")  # Para saber de quién viene
                etapa3.append(p_e3)

        return {"e1": etapa1, "e2": etapa2, "e3": etapa3}

    def getTiposSQL(self, id_pokemon):
        """
        Obtiene los tipos (uno o dos) asociados a un Pokémon.
        """
        res = self.db.execSQL(f"SELECT type1, type2 FROM EsTipo WHERE id_pokemon = {id_pokemon}")
        tipos = []
        if res.next():
            # Comprobamos ambos campos y evitamos valores nulos o 'none'
            for t in [res.getString("type1"), res.getString("type2")]:
                if t and t.lower() != 'none': tipos.append(t)
        return tipos

    def getHabilidadesSQL(self, id_pokemon):
        """
        Obtiene la lista de habilidades posibles para un Pokémon.
        """
        res = self.db.execSQL(f"SELECT ability_name FROM HabilidadesPosibles WHERE id_pokemon = {id_pokemon}")
        habs = []
        while res.next():
            h = res.getString("ability_name")
            if h and h.lower() != 'none': habs.append(h)
        return habs

    def obtenerTablaEfectividad(self, id_pokemon):
        """
        Calcula cómo afectan todos los tipos de ataque al Pokémon defensor (debilidades y resistencias).
        """
        # 1. Obtenemos los tipos del defensor (ej: Charizard -> ['Fire', 'Flying'])
        tipos_defensor = self.getTiposSQL(id_pokemon)

        # 2. Obtenemos la lista de todos los tipos existentes (Fuego, Agua, etc.)
        res_tipos = self.db.execSQL("SELECT name FROM Tipo ORDER BY name")
        todos_tipos = []
        while res_tipos.next():
            todos_tipos.append(res_tipos.getString("name"))

        tabla_resultados = []

        # 3. Calculamos el multiplicador final combinando los tipos del defensor
        for tipo_atacante in todos_tipos:
            mult_total = 1.0  # Empezamos con daño neutro

            for tipo_def in tipos_defensor:
                # Consultamos la tabla de efectividad para ver la relación Atacante vs Defensor
                sql = f"""
                    SELECT multiplier FROM Efectivo 
                    WHERE attacker = '{tipo_atacante}' AND defender = '{tipo_def}'
                """
                res = self.db.execSQL(sql)
                if res.next():
                    # El daño se multiplica (ej: 2.0 * 2.0 = 4.0 si es doble debilidad)
                    mult_total *= res.getFloat("multiplier")

            # Guardamos el resultado final para este tipo de ataque
            tabla_resultados.append({
                "type": tipo_atacante,
                "multiplier": mult_total
            })

        return tabla_resultados