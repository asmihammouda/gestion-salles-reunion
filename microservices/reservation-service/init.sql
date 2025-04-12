-- Nouvelle version de init.sql
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_database WHERE datname = 'reservation_db') THEN
        CREATE DATABASE reservation_db;
    END IF;
END $$;

\c reservation_db;

CREATE TABLE IF NOT EXISTS reservations (
    id SERIAL PRIMARY KEY,
    salle_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    date_debut TIMESTAMP NOT NULL,
    date_fin TIMESTAMP NOT NULL,
    status VARCHAR(20) DEFAULT 'confirmed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
