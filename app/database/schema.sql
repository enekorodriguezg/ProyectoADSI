-- 1. TABLAS MAESTRAS
CREATE TABLE IF NOT EXISTS Tipo (
    name VARCHAR(50) PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS Habilidad (
    name VARCHAR(50) PRIMARY KEY,
    description TEXT
);

-- 2. ESPECIES Y EVOLUCIONES
CREATE TABLE IF NOT EXISTS PokeEspecie (
    id_pokedex INT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description VARCHAR(1000) NOT NULL,
    weight DECIMAL(10,2),
    height DECIMAL(10,2),
    ps INT,
    attack INT,
    defense INT,
    special_attack INT,
    special_defense INT,
    speed INT
);

CREATE TABLE IF NOT EXISTS Evoluciona (
    id_base INT,
    id_evolution INT,
    PRIMARY KEY (id_base, id_evolution),
    FOREIGN KEY (id_base) REFERENCES PokeEspecie(id_pokedex),
    FOREIGN KEY (id_evolution) REFERENCES PokeEspecie(id_pokedex)
);

-- 3. USUARIOS Y COMUNICACIÓN
CREATE TABLE IF NOT EXISTS Users (
    username VARCHAR(50) PRIMARY KEY,
    password VARCHAR(100),
    fav_pokemon INT,
    name VARCHAR(100),
    surname VARCHAR(100),
    dni VARCHAR(20) UNIQUE,
    email VARCHAR(100) UNIQUE,
    role VARCHAR(20),
    FOREIGN KEY (fav_pokemon) REFERENCES PokeEspecie(id_pokedex)
);

CREATE TABLE IF NOT EXISTS Amigo (
    user_sender VARCHAR(50),
    user_receiver VARCHAR(50),
    status INTEGER DEFAULT 0, -- 0: Pendiente, 1: Aceptada
    request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_sender, user_receiver),
    FOREIGN KEY (user_sender) REFERENCES Users(username),
    FOREIGN KEY (user_receiver) REFERENCES Users(username)
);

CREATE TABLE IF NOT EXISTS Mensaje (
    id_message INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50),
    message_text TEXT,
    date_hour TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (username) REFERENCES Users(username)
);

-- 4. EQUIPOS (Referenciando directamente a PokeEspecie)
CREATE TABLE IF NOT EXISTS EquipoPokémon (
    id_team INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50),
    name VARCHAR(100),
    FOREIGN KEY (username) REFERENCES Users(username)
);

CREATE TABLE IF NOT EXISTS PokémonParticipa (
    id_team INT,
    id_pokedex INT,
    PRIMARY KEY (id_team, id_pokedex),
    FOREIGN KEY (id_team) REFERENCES EquipoPokémon(id_team),
    FOREIGN KEY (id_pokedex) REFERENCES PokeEspecie(id_pokedex)
);

-- 5. RELACIONES DE ATRIBUTOS
CREATE TABLE IF NOT EXISTS HabilidadesPosibles (
    id_pokemon INT,
    ability_name VARCHAR(50),
    PRIMARY KEY (id_pokemon, ability_name),
    FOREIGN KEY (id_pokemon) REFERENCES PokeEspecie(id_pokedex),
    FOREIGN KEY (ability_name) REFERENCES Habilidad(name)
);

CREATE TABLE IF NOT EXISTS EsTipo (
    id_pokemon INT,
    type1 VARCHAR(50),
    type2 VARCHAR(50),
    PRIMARY KEY (id_pokemon, type1),
    FOREIGN KEY (id_pokemon) REFERENCES PokeEspecie(id_pokedex),
    FOREIGN KEY (type1) REFERENCES Tipo(name),
    FOREIGN KEY (type2) REFERENCES Tipo(name)
);

CREATE TABLE IF NOT EXISTS Efectivo (
    attacker VARCHAR(50),
    defender VARCHAR(50),
    multiplier DECIMAL(3,2),
    PRIMARY KEY (attacker, defender),
    FOREIGN KEY (attacker) REFERENCES Tipo(name),
    FOREIGN KEY (defender) REFERENCES Tipo(name)
);