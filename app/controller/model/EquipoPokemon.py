class EquipoPokemon:
    def __init__(self, id_team, name, pokemonList=None):
        self.id = id_team          # Coincide con diagrama "- id: int"
        self.name = name           # Coincide con diagrama "- name: String"
        self.pokemonList = pokemonList if pokemonList else [] # Coincide con "- pokémonList: Collection<Pokémon>"

    def to_dict(self):
        """Ayuda para pasarlo a la vista HTML fácilmente"""
        return {
            "id": self.id,
            "name": self.name,
            "miembros": [p for p in self.pokemonList] # Asumiendo que los Pokémon son diccionarios u objetos
        }