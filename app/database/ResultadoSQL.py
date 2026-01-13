class ResultadoSQL:
    def __init__(self, datos):
        """
        Constructor que recibe la lista de filas (objetos Row de sqlite3).
        """
        self.datos = datos  # Lista de registros devuelta por fetchall()
        self.indice = -1    # Empezamos en -1 para que al primer next() se mueva al índice 0

    def next(self):
        """
        Mueve el puntero a la siguiente fila.
        Devuelve True si existe la fila, o False si hemos llegado al final.
        """
        self.indice += 1
        return self.indice < len(self.datos)

    def getInt(self, columna):
        """
        Obtiene el valor de una columna y lo convierte a entero.
        'columna' puede ser el nombre del campo (gracias a sqlite3.Row).
        """
        return int(self.datos[self.indice][columna])

    def getFloat(self, columna):
        """
        Obtiene el valor de una columna y lo convierte a float.
        Incluye manejo de errores para valores nulos o tipos incompatibles.
        """
        try:
            valor = self.datos[self.indice][columna]
            # Si el valor es None, devolvemos 0.0 para evitar errores en cálculos
            return float(valor) if valor is not None else 0.0
        except (ValueError, TypeError, KeyError):
            return 0.0

    def getString(self, columna):
        """
        Obtiene el valor de una columna convertido a texto.
        """
        return str(self.datos[self.indice][columna])