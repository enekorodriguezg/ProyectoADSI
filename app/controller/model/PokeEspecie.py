class PokeEspecie:
    def __init__(self, id_pokedex, name, description, weight, height, stats, types, abilities, evolution):
        self.id = id_pokedex
        self.name = name
        self.description = description
        self.weight = weight
        self.height = height
        # stats es un dict: {'ps': int, 'attack': int, ...}
        self.stats = stats
        self.types = types
        self.abilities = abilities
        self.evolution = evolution

    def __repr__(self):
        return f"PokeEspecie(id={self.id}, name='{self.name}')"

    def to_dict(self):
        """Convierte la instancia en un diccionario (útil para JSON)"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "weight": self.weight,
            "height": self.height,
            "stats": self.stats,
            "types": self.types,
            "abilities": self.abilities,
            "evolution": self.evolution
        }