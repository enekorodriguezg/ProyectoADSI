class Catalogo:
    def __init__(self, db):
        self.db = db

    def obtenerListaPokemon(self, pagina, filtros, order_by='id', direction='ASC'):
        offset = (pagina - 1) * 25

        # 1. Definimos las cláusulas WHERE basándonos en los filtros
        where_clauses = []
        if filtros.get("nombre"):
            where_clauses.append(f"P.name LIKE '%{filtros['nombre']}%'")

        # Filtro por tipo requiere buscar en la tabla EsTipo
        if filtros.get("tipo"):
            where_clauses.append(f"(E.type1 = '{filtros['tipo']}' OR E.type2 = '{filtros['tipo']}')")

        where_str = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        # 2. SQL con JOIN para obtener los tipos junto a la especie
        # Usamos alias P para PokeEspecie y E para EsTipo
        sql = f"""
            SELECT P.id_pokedex, P.name, E.type1, E.type2 
            FROM PokeEspecie P
            LEFT JOIN EsTipo E ON P.id_pokedex = E.id_pokemon
            {where_str} 
            ORDER BY {"P.id_pokedex" if order_by == 'id' else "P.name"} {direction} 
            LIMIT 25 OFFSET {offset}
        """

        res = self.db.execSQL(sql)
        lista = []
        while res.next():
            id_pk = res.getInt("id_pokedex")
            t1 = res.getString("type1")
            t2 = res.getString("type2")

            # Formateamos el string de tipos para la tabla
            tipos_str = t1 if t1 else "Normal"
            if t2:
                tipos_str += f" / {t2}"

            lista.append({
                "id": id_pk,
                "nombre": res.getString("name"),
                "imagen": f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{id_pk}.png",
                "tipos": tipos_str
            })
        return lista

    def contarPokemonFiltrados(self, filtros):
        if not filtros.get("tipo"):
            # Si no hay filtro de tipo, conteo simple en PokeEspecie
            where = f"WHERE name LIKE '%{filtros['nombre']}%'" if filtros.get("nombre") else ""
            res = self.db.execSQL(f"SELECT COUNT(*) as total FROM PokeEspecie {where}")
        else:
            # Si hay filtro de tipo, necesitamos unir las tablas
            res = self.db.execSQL(f"""
                SELECT COUNT(*) as total FROM PokeEspecie P
                JOIN EsTipo E ON P.id_pokedex = E.id_pokemon
                WHERE (E.type1 = '{filtros['tipo']}' OR E.type2 = '{filtros['tipo']}')
                {"AND P.name LIKE '%" + filtros['nombre'] + "%'" if filtros.get('nombre') else ""}
            """)
        return res.getInt("total") if res.next() else 0

    def obtenerDetallePokemon(self, id_pokemon):
        sql = f"""
            SELECT id_pokedex, name, weight, ps, attack, defense, 
                   special_attack, special_defense, speed
            FROM PokeEspecie 
            WHERE id_pokedex = {id_pokemon}
        """
        res = self.db.execSQL(sql)
        if not res.next(): return None

        return {
            "id": res.getInt("id_pokedex"),
            "name": res.getString("name"),
            "weight": res.getFloat("weight"),
            "stats": {
                "ps": res.getInt("ps"),
                "attack": res.getInt("attack"),
                "defense": res.getInt("defense"),
                "special_attack": res.getInt("special_attack"),
                "special_defense": res.getInt("special_defense"),
                "speed": res.getInt("speed")
            },
            "types": self.getTiposSQL(id_pokemon),
            "abilities": self.getHabilidadesSQL(id_pokemon),
            "evolution": self.getCadenaEvolutivaSQL(id_pokemon)
        }

    def getCadenaEvolutivaSQL(self, id_pokemon):
        """Busca la raíz de la familia y devuelve todos sus miembros"""
        # 1. Encontrar la base de la familia (recursivo hacia atrás)
        id_raiz = id_pokemon
        while True:
            res_padre = self.db.execSQL(f"SELECT id_base FROM Evoluciona WHERE id_evolution = {id_raiz}")
            if res_padre.next():
                id_raiz = res_padre.getInt("id_base")
            else:
                break

        # 2. Obtener toda la familia en orden
        sql_familia = f"""
            SELECT id_pokedex, name FROM PokeEspecie 
            WHERE id_pokedex = {id_raiz}
            OR id_pokedex IN (SELECT id_evolution FROM Evoluciona WHERE id_base = {id_raiz})
            OR id_pokedex IN (SELECT id_evolution FROM Evoluciona WHERE id_base IN 
                (SELECT id_evolution FROM Evoluciona WHERE id_base = {id_raiz}))
            ORDER BY id_pokedex ASC
        """
        res_fam = self.db.execSQL(sql_familia)
        cadena = []
        while res_fam.next():
            cadena.append({
                "id": res_fam.getInt("id_pokedex"),
                "name": res_fam.getString("name")
            })
        return cadena

    def getTiposSQL(self, id_pokemon):
        """2.4.1: Obtiene lista de tipos desde EsTipo"""
        sql = f"SELECT type1, type2 FROM EsTipo WHERE id_pokemon = {id_pokemon}"
        res = self.db.execSQL(sql)
        tipos = []
        if res.next():
            tipos.append(res.getString("type1"))
            t2 = res.getString("type2")
            if t2: tipos.append(t2)
        return tipos

    def getHabilidadesSQL(self, id_pokemon):
        """Obtiene las habilidades desde HabilidadesPosibles"""
        sql = f"SELECT ability_name FROM HabilidadesPosibles WHERE id_pokemon = {id_pokemon}"
        res = self.db.execSQL(sql)
        habs = []
        while res.next():
            habs.append(res.getString("ability_name"))
        return habs