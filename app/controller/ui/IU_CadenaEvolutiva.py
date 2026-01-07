from flask import Blueprint, render_template
from app.controller.model.Catalogo import Catalogo

def iu_cadena_evolutiva_blueprint(db):
    bp = Blueprint('cadena_evolutiva', __name__)

    @bp.route('/cadena_evolutiva/<int:id_pokemon>')
    def mostrarCadena(id_pokemon):
        catalogo = Catalogo(db)
        # Reutilizamos la lógica de obtener detalle que ya trae la cadena evolutiva
        pokemon_obj = catalogo.obtenerDetallePokemon(id_pokemon)
        
        if not pokemon_obj:
            return "Pokémon no encontrado", 404

        # Transformar datos planos (e1, e2, e3) en estructura de árbol para la vista
        evo_tree = None
        if pokemon_obj.evolution:
            evo_data = pokemon_obj.evolution
            
            # Raíz (Etapa 1)
            # e1 es una lista, tomamos el primero
            root_node = {**evo_data['e1'][0], 'children': []}
            
            # Map para encontrar nodos de etapa 2 rápidamente por ID
            # Esto permitirá asignar los de etapa 3 a su padre correcto
            e2_map = {}

            # Procesar Etapa 2
            if 'e2' in evo_data:
                for p2 in evo_data['e2']:
                    node_e2 = {**p2, 'children': []}
                    root_node['children'].append(node_e2)
                    e2_map[p2['id']] = node_e2
            
            # Procesar Etapa 3
            if 'e3' in evo_data:
                for p3 in evo_data['e3']:
                    id_padre = p3.get('id_padre')
                    if id_padre in e2_map:
                        node_e3 = {**p3, 'children': []}
                        e2_map[id_padre]['children'].append(node_e3)
            
            evo_tree = root_node

        return render_template('cadena_evolutiva.html', p=pokemon_obj, evo_tree=evo_tree)

    return bp
