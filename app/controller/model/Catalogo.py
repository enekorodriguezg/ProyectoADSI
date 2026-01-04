from app.controller.model.PokeEspecie import PokeEspecie

class Catalogo:
    def __init__(self, db):
        self.db = db

    def obtenerListaPokemon(self, pagina, filtros, order_by='id', direction='ASC'):
        offset = (pagina - 1) * 25
        where_clauses = []
        if filtros.get("nombre"):
            where_clauses.append(f"P.name LIKE '%{filtros['nombre']}%'")
        if filtros.get("tipo"):
            where_clauses.append(f"(E.type1 = '{filtros['tipo']}' OR E.type2 = '{filtros['tipo']}')")

        where_str = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        sql = f"""
            SELECT P.id_pokedex, P.name
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
            tipos_lista = self.getTiposSQL(id_pk)
            # Aquí podrías devolver objetos básicos de PokeEspecie o diccionarios simples
            lista.append({
                "id": id_pk,
                "nombre": res.getString("name"),
                "imagen": f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{id_pk}.png",
                "tipos": " / ".join(tipos_lista)
            })
        return lista

    def contarPokemonFiltrados(self, filtros):
        where_clauses = []
        if filtros.get("nombre"):
            where_clauses.append(f"P.name LIKE '%{filtros['nombre']}%'")

        if filtros.get("tipo"):
            where_clauses.append(f"(E.type1 = '{filtros['tipo']}' OR E.type2 = '{filtros['tipo']}')")
            sql = f"""
                SELECT COUNT(DISTINCT P.id_pokedex) as total 
                FROM PokeEspecie P
                JOIN EsTipo E ON P.id_pokedex = E.id_pokemon
                {" WHERE " + " AND ".join(where_clauses) if where_clauses else ""}
            """
        else:
            where_str = f" WHERE name LIKE '%{filtros['nombre']}%'" if filtros.get("nombre") else ""
            sql = f"SELECT COUNT(*) as total FROM PokeEspecie {where_str}"

        res = self.db.execSQL(sql)
        return res.getInt("total") if res.next() else 0

    def obtenerDetallePokemon(self, id_pokemon):
        sql = f"SELECT * FROM PokeEspecie WHERE id_pokedex = {id_pokemon}"
        res = self.db.execSQL(sql)

        if not res.next():
            return None

        # Recopilación de datos de la tabla principal
        stats = {
            "ps": res.getInt("ps"),
            "attack": res.getInt("attack"),
            "defense": res.getInt("defense"),
            "special_attack": res.getInt("special_attack"),
            "special_defense": res.getInt("special_defense"),
            "speed": res.getInt("speed")
        }

        # Creación de la instancia PokeEspecie con datos de tablas relacionadas
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
        id_raiz = id_pokemon
        # Buscar el origen de la cadena (el primer pokémon)
        while True:
            res_p = self.db.execSQL(f"SELECT id_base FROM Evoluciona WHERE id_evolution = {id_raiz}")
            if res_p.next():
                id_raiz = res_p.getInt("id_base")
            else:
                break

        def get_pk_data(id_pk):
            res = self.db.execSQL(f"SELECT name FROM PokeEspecie WHERE id_pokedex = {id_pk}")
            nombre = res.getString("name") if res.next() else "???"
            return {"id": id_pk, "name": nombre, "types": self.getTiposSQL(id_pk)}

        # Etapa 1
        etapa1 = [get_pk_data(id_raiz)]

        # Etapa 2
        etapa2 = []
        ids_e2 = []
        res_e2 = self.db.execSQL(f"SELECT id_evolution FROM Evoluciona WHERE id_base = {id_raiz}")
        while res_e2.next():
            id_e2 = res_e2.getInt("id_evolution")
            etapa2.append(get_pk_data(id_e2))
            ids_e2.append(str(id_e2))

        # Etapa 3
        etapa3 = []
        if ids_e2:
            res_e3 = self.db.execSQL(
                f"SELECT id_evolution, id_base FROM Evoluciona WHERE id_base IN ({','.join(ids_e2)})")
            while res_e3.next():
                id_ev = res_e3.getInt("id_evolution")
                p_e3 = get_pk_data(id_ev)
                p_e3["id_padre"] = res_e3.getInt("id_base")
                etapa3.append(p_e3)

        return {"e1": etapa1, "e2": etapa2, "e3": etapa3}

    def getTiposSQL(self, id_pokemon):
        res = self.db.execSQL(f"SELECT type1, type2 FROM EsTipo WHERE id_pokemon = {id_pokemon}")
        tipos = []
        if res.next():
            for t in [res.getString("type1"), res.getString("type2")]:
                if t and t.lower() != 'none': tipos.append(t)
        return tipos

    def getHabilidadesSQL(self, id_pokemon):
        res = self.db.execSQL(f"SELECT ability_name FROM HabilidadesPosibles WHERE id_pokemon = {id_pokemon}")
        habs = []
        while res.next():
            h = res.getString("ability_name")
            if h and h.lower() != 'none': habs.append(h)
        return habs