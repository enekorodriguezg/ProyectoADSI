-- 1. Tablas Maestras (Sin dependencias)
CREATE TABLE IF NOT EXISTS Tipo (
    name VARCHAR(50) PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS Habilidad (
    name VARCHAR(50) PRIMARY KEY,
    description TEXT
);

-- 2. Especies y Evoluciones
CREATE TABLE IF NOT EXISTS PokeEspecie (
    id_pokedex INT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    weight DECIMAL(10,2),
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

-- 3. Usuarios y sus interacciones
CREATE TABLE IF NOT EXISTS Users (
    username VARCHAR(50) PRIMARY KEY,
    fav_pokemon INT,
    name VARCHAR(100),
    surname VARCHAR(100),
    dni VARCHAR(20) UNIQUE,
    email VARCHAR(100) UNIQUE,
    role VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS Amigo (
    follower VARCHAR(50),
    followed VARCHAR(50),
    PRIMARY KEY (follower, followed),
    FOREIGN KEY (follower) REFERENCES Users(username),
    FOREIGN KEY (followed) REFERENCES Users(username)
);

CREATE TABLE IF NOT EXISTS Mensaje (
    id_message INTEGER PRIMARY KEY AUTOINCREMENT, -- En SQLite SERIAL es INTEGER PRIMARY KEY AUTOINCREMENT
    username VARCHAR(50),
    message_text TEXT,
    date_hour TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (username) REFERENCES Users(username)
);

-- 4. Instancias de Pokémon
CREATE TABLE IF NOT EXISTS Pokémon (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner VARCHAR(50),
    id_pokedex INT,
    ability_name VARCHAR(50),
    species_name VARCHAR(100),
    weight DECIMAL(10,2),
    ps INT,
    attack INT,
    defense INT,
    special_attack INT,
    special_defense INT,
    speed INT,
    FOREIGN KEY (owner) REFERENCES Users(username),
    FOREIGN KEY (id_pokedex) REFERENCES PokeEspecie(id_pokedex),
    FOREIGN KEY (ability_name) REFERENCES Habilidad(name)
);

-- 5. Relaciones complejas y equipos
CREATE TABLE IF NOT EXISTS EquipoPokémon (
    id_team INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50),
    name VARCHAR(100),
    FOREIGN KEY (username) REFERENCES Users(username)
);

CREATE TABLE IF NOT EXISTS PokémonParticipa (
    id_team INT,
    id_pokemon INT,
    PRIMARY KEY (id_team, id_pokemon),
    FOREIGN KEY (id_team) REFERENCES EquipoPokémon(id_team),
    FOREIGN KEY (id_pokemon) REFERENCES Pokémon(id)
);

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