from datetime import datetime


class GestorActividad:
    """
    Gestor centralizado para la funcionalidad de Changelog/Actividad.
    Maneja el registro, recuperación y filtrado de actividades de usuarios.
    """

    def __init__(self, db):
        self.db = db

    def registrar_actividad(self, username, mensaje_text):
        """
        Registra una acción de usuario en la tabla Mensaje.
        
        Args:
            username (str): Usuario que realiza la acción
            mensaje_text (str): Descripción de la acción
            
        Returns:
            bool: True si se registró correctamente, False en caso de error
        """
        try:
            fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # Escapar comillas para evitar SQL injection
            mensaje_limpio = mensaje_text.replace("'", "''")
            
            sql = f"INSERT INTO Mensaje (username, message_text, date_hour) VALUES ('{username}', '{mensaje_limpio}', '{fecha_hora}')"
            self.db.execSQL(sql)
            return True
        except Exception as e:
            print(f"Error registrando actividad: {e}")
            return False

    def obtener_amigos_aceptados(self, username):
        """
        Obtiene la lista de amigos aceptados de un usuario.
        
        Args:
            username (str): Usuario del que obtener amigos
            
        Returns:
            list: Lista de nombres de usuario amigos
        """
        try:
            # Obtener amigos tanto enviados como recibidos (bidireccional)
            sql = f"""
                SELECT user_receiver as amigo FROM Amigo 
                WHERE user_sender='{username}' AND status=1
                UNION
                SELECT user_sender as amigo FROM Amigo 
                WHERE user_receiver='{username}' AND status=1
            """
            res = self.db.execSQL(sql)
            amigos = []
            while res.next():
                amigos.append(res.getString('amigo'))
            return amigos
        except Exception as e:
            print(f"Error obteniendo amigos: {e}")
            return []

    def obtener_actividad_amigos(self, username, usuario_filtro=None, 
                                 fecha_inicio=None, fecha_fin=None, 
                                 busqueda_filtro=None, limite=50):
        """
        Obtiene la actividad de los amigos de un usuario con filtros opcionales.
        
        Args:
            username (str): Usuario del que obtener actividad
            usuario_filtro (str, optional): Filtrar por usuario específico
            fecha_inicio (str, optional): Filtro de fecha inicio (YYYY-MM-DD)
            fecha_fin (str, optional): Filtro de fecha fin (YYYY-MM-DD)
            busqueda_filtro (str, optional): Búsqueda de texto en mensajes
            limite (int): Máximo de resultados (default: 50)
            
        Returns:
            list: Lista de diccionarios con actividad filtrada
        """
        try:
            # 1. Obtener amigos aceptados
            amigos = self.obtener_amigos_aceptados(username)
            
            if not amigos:
                return []
            
            # 2. Construir query de actividad
            amigos_list = "', '".join(amigos)
            sql = f"""
                SELECT username, message_text, date_hour 
                FROM Mensaje 
                WHERE username IN ('{amigos_list}')
            """
            
            # 3. Aplicar filtros
            if usuario_filtro and usuario_filtro in amigos:
                sql += f" AND username = '{usuario_filtro}'"
            
            if fecha_inicio and fecha_fin:
                sql += f" AND DATE(date_hour) BETWEEN '{fecha_inicio}' AND '{fecha_fin}'"
            elif fecha_inicio:
                sql += f" AND DATE(date_hour) >= '{fecha_inicio}'"
            elif fecha_fin:
                sql += f" AND DATE(date_hour) <= '{fecha_fin}'"
            
            if busqueda_filtro:
                # Escapar caracteres especiales en búsqueda
                busqueda_limpia = busqueda_filtro.replace("'", "''")
                sql += f" AND message_text LIKE '%{busqueda_limpia}%'"
            
            # 4. Ordenar y limitar
            sql += f" ORDER BY date_hour DESC LIMIT {limite}"
            
            # 5. Ejecutar query
            res = self.db.execSQL(sql)
            actividad = []
            
            while res.next():
                actividad.append({
                    'username': res.getString('username'),
                    'message': res.getString('message_text'),
                    'fecha': res.getString('date_hour')
                })
            
            return actividad
        except Exception as e:
            print(f"Error obteniendo actividad: {e}")
            return []

    def obtener_actividad_by_amigo(self, username, amigo_username, limite=50):
        """
        Obtiene solo la actividad de un amigo específico.
        
        Args:
            username (str): Usuario que solicita (para validar amistad)
            amigo_username (str): Amigo cuya actividad se desea
            limite (int): Máximo de resultados
            
        Returns:
            list: Actividad del amigo especificado
        """
        return self.obtener_actividad_amigos(
            username, 
            usuario_filtro=amigo_username, 
            limite=limite
        )

    def obtener_amigos_con_actividad(self, username):
        """
        Obtiene lista de amigos que tienen actividad reciente.
        
        Args:
            username (str): Usuario
            
        Returns:
            list: Amigos con al menos un mensaje registrado
        """
        try:
            amigos = self.obtener_amigos_aceptados(username)
            if not amigos:
                return []
            
            amigos_list = "', '".join(amigos)
            sql = f"""
                SELECT DISTINCT username 
                FROM Mensaje 
                WHERE username IN ('{amigos_list}')
                ORDER BY username ASC
            """
            
            res = self.db.execSQL(sql)
            amigos_activos = []
            
            while res.next():
                amigos_activos.append(res.getString('username'))
            
            return amigos_activos
        except Exception as e:
            print(f"Error obteniendo amigos con actividad: {e}")
            return []

    def contar_actividad_amigos(self, username):
        """
        Cuenta el total de mensajes de actividad de los amigos.
        
        Args:
            username (str): Usuario
            
        Returns:
            int: Total de mensajes
        """
        try:
            amigos = self.obtener_amigos_aceptados(username)
            if not amigos:
                return 0
            
            amigos_list = "', '".join(amigos)
            sql = f"""
                SELECT COUNT(*) as total 
                FROM Mensaje 
                WHERE username IN ('{amigos_list}')
            """
            
            res = self.db.execSQL(sql)
            if res.next():
                return res.getInt('total')
            return 0
        except Exception as e:
            print(f"Error contando actividad: {e}")
            return 0
