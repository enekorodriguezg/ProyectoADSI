# app/database/resultado_sql.py

class ResultadoSQL:
    def __init__(self, datos):
        self.datos = datos  # Aquí guardamos lo que fetchall() nos dio
        self.indice = -1    # Empezamos antes de la primera fila

    def next(self):
        self.indice += 1
        return self.indice < len(self.datos)

    def getInt(self, columna):
        return int(self.datos[self.indice][columna])

    def getFloat(self, columna):
        try:
            valor = self.datos[self.indice][columna]
            return float(valor) if valor is not None else 0.0
        except (ValueError, TypeError, KeyError):
            return 0.0

    def getString(self, columna):
        return str(self.datos[self.indice][columna])