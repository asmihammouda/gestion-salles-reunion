-- Nouvelle version de init.sql
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_database WHERE datname = 'salle_db') THEN
        CREATE DATABASE salle_db;
    END IF;
END $$;

\c salle_db;

-- Ces commandes peuvent être exécutées plusieurs fois sans erreur
CREATE TABLE IF NOT EXISTS salles (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(80) UNIQUE NOT NULL,
    capacite INTEGER NOT NULL,
    equipements VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS disponibilites (
    id SERIAL PRIMARY KEY,
    salle_id INTEGER REFERENCES salles(id),
    date_debut TIMESTAMP NOT NULL,
    date_fin TIMESTAMP NOT NULL,
    status VARCHAR(20) DEFAULT 'libre'
);
