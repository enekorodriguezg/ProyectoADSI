from app.database.GestorBD import GestorBD
from app.controller.model.EquipoPokemon import EquipoPokemon


class GestorEquipos:
    # Según el diagrama, implementa patrón Singleton implícito o gestión centralizada
    def __init__(self, db):
        self.db = db
        # self.listaEquipos = [] # Según diagrama existe, pero en web se suele consultar a BD directamente

    # Método del diagrama: + getTeams(usuario: String): Collection<EquipoPokémon>
    def getTeams(self, usuario):
        sql = f"SELECT * FROM EquipoPokémon WHERE username = '{usuario}' ORDER BY id_team ASC"
        res = self.db.execSQL(sql)

        collection_equipos = []
        while res.next():
            # Creamos el objeto tal cual pide el diagrama
            equipo = EquipoPokemon(
                id_team=res.getInt("id_team"),
                name=res.getString("name")
            )
            collection_equipos.append(equipo)

        return collection_equipos

    # Método del diagrama: + createTeam(name: String, username: String): boolean
    def createTeam(self, name, username):
        # 1. Validar duplicados
        check_sql = f"SELECT id_team FROM EquipoPokémon WHERE username = '{username}' AND name = '{name}'"
        if self.db.execSQL(check_sql).next():
            return False  # Ya existe

        # 2. Insertar
        sql = f"INSERT INTO EquipoPokémon (username, name) VALUES ('{username}', '{name}')"
        try:
            self.db.connection.execute(sql)
            self.db.connection.commit()
            return True
        except Exception as e:
            print(f"Error createTeam: {e}")
            return False

    # Método del diagrama: + deleteTeam(idTeam: int): boolean
    def deleteTeam(self, idTeam):
        try:
            # Primero borramos los pokémon que participan en ese equipo (Integridad referencial)
            self.db.connection.execute(f"DELETE FROM PokémonParticipa WHERE id_team = {idTeam}")
            # Luego borramos el equipo
            self.db.connection.execute(f"DELETE FROM EquipoPokémon WHERE id_team = {idTeam}")
            self.db.connection.commit()
            return True
        except Exception as e:
            print(f"Error deleteTeam: {e}")
            return False

    # Método del diagrama: + addPokémonToTeam(idEquipo: int, idPokemon: int, usuario: String)
    # NOTA: idPokemon aquí refiere al ID de la Pokédex (especie) que seleccionamos para crear la instancia.
    def addPokemonToTeam(self, idEquipo, idPokemon, usuario):
        # 1. Verificar límite de 6 Pokémon
        res_count = self.db.execSQL(f"SELECT COUNT(*) as total FROM PokémonParticipa WHERE id_team = {idEquipo}")
        if res_count.next() and res_count.getInt("total") >= 6:
            return False  # Equipo lleno

        try:
            # 2. Crear instancia en la tabla 'Pokémon' (Instancia concreta)
            # Obtenemos datos base de la especie
            res_esp = self.db.execSQL(f"SELECT * FROM PokeEspecie WHERE id_pokedex = {idPokemon}")
            if not res_esp.next():
                return False

            cursor = self.db.connection.cursor()
            cursor.execute("""
                           INSERT INTO Pokémon (owner, id_pokedex, species_name, ps, attack, defense, special_attack,
                                                special_defense, speed)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                           """, (usuario, idPokemon, res_esp.getString("name"),
                                 res_esp.getInt("ps"), res_esp.getInt("attack"), res_esp.getInt("defense"),
                                 res_esp.getInt("special_attack"), res_esp.getInt("special_defense"),
                                 res_esp.getInt("speed")))

            id_nueva_instancia = cursor.lastrowid

            # 3. Vincular en 'PokémonParticipa'
            cursor.execute("INSERT INTO PokémonParticipa (id_team, id_pokemon) VALUES (?, ?)",
                           (idEquipo, id_nueva_instancia))
            self.db.connection.commit()
            return True

        except Exception as e:
            print(f"Error addPokemonToTeam: {e}")
            return False

    # Método del diagrama: + deletePokémonFromTeam(idEquipo: int, idPokemon: int): boolean
    # NOTA: idPokemon aquí es el ID de la instancia (tabla Pokémon), no de la especie.
    def deletePokemonFromTeam(self, idEquipo, idPokemon):
        try:
            # Eliminar vínculo
            self.db.connection.execute(
                f"DELETE FROM PokémonParticipa WHERE id_team = {idEquipo} AND id_pokemon = {idPokemon}")
            # Eliminar instancia (opcional, limpieza de BD)
            self.db.connection.execute(f"DELETE FROM Pokémon WHERE id = {idPokemon}")
            self.db.connection.commit()
            return True
        except Exception as e:
            print(f"Error deletePokemonFromTeam: {e}")
            return False

    # Método auxiliar para obtener el detalle completo (necesario para la vista 'Ver Equipo')
    # Aunque no esté explícito en el diagrama como público, es necesario para llenar 'pokemonList'
    def _rellenarDetallesEquipo(self, idTeam):
        sql = f"SELECT * FROM EquipoPokémon WHERE id_team = {idTeam}"
        res_eq = self.db.execSQL(sql)
        if not res_eq.next():
            return None

        equipo = EquipoPokemon(res_eq.getInt("id_team"), res_eq.getString("name"))

        # Recuperar pokémon
        # Agregamos ps, attack, etc. de la tabla Pokémon (instancia)
        sql_miembros = f"""
            SELECT P_Inst.id, P_Esp.id_pokedex, P_Esp.name, E1.type1, E1.type2,
                   P_Inst.ps, P_Inst.attack, P_Inst.defense, P_Inst.special_attack, 
                   P_Inst.special_defense, P_Inst.speed
            FROM PokémonParticipa PP
            JOIN Pokémon P_Inst ON PP.id_pokemon = P_Inst.id
            JOIN PokeEspecie P_Esp ON P_Inst.id_pokedex = P_Esp.id_pokedex
            LEFT JOIN EsTipo E1 ON P_Esp.id_pokedex = E1.id_pokemon
            WHERE PP.id_team = {idTeam}
        """
        res_miembros = self.db.execSQL(sql_miembros)

        while res_miembros.next():
            # Construimos un diccionario o un objeto Pokémon simple para la vista
            tipos = [res_miembros.getString("type1")]
            if res_miembros.getString("type2") and res_miembros.getString("type2") != 'None':
                tipos.append(res_miembros.getString("type2"))

            equipo.pokemonList.append({
                "id_instancia": res_miembros.getInt("id"),
                "id_pokedex": res_miembros.getInt("id_pokedex"),
                "nombre": res_miembros.getString("name"),
                "tipos": tipos,
                "imagen": f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{res_miembros.getInt('id_pokedex')}.png",
                "stats": {
                    "ps": res_miembros.getInt("ps"),
                    "attack": res_miembros.getInt("attack"),
                    "defense": res_miembros.getInt("defense"),
                    "special_attack": res_miembros.getInt("special_attack"),
                    "special_defense": res_miembros.getInt("special_defense"),
                    "speed": res_miembros.getInt("speed")
                }
            })

        return equipo