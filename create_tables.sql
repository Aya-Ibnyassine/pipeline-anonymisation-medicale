-- ==============================================================================
-- Script d'initialisation de la base de données : Pipeline d'Anonymisation
-- ==============================================================================

-- 1. Création de la base de données
CREATE DATABASE IF NOT EXISTS sih_anonymisation;
USE sih_anonymisation;

-- 2. Création de la table de mapping (Gère la correspondance entre les identifiants)
CREATE TABLE IF NOT EXISTS pseudonym_mapping (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patient_hash VARCHAR(64) NOT NULL UNIQUE,
    pseudonym_id VARCHAR(20) NOT NULL UNIQUE,
    hash_version INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Création du coffre-fort des PII (Stocke les données sensibles chiffrées)
CREATE TABLE IF NOT EXISTS patient_pii_vault (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pseudonym_id VARCHAR(20) NOT NULL UNIQUE,
    encrypted_nom TEXT,
    encrypted_cin TEXT,
    encrypted_tel TEXT,
    encrypted_date_naissance TEXT,
    encrypted_dossier TEXT,
    encrypted_ip VARBINARY(255),           -- Stockage binaire pour le chiffrement Fernet
    encrypted_num_couverture VARCHAR(255), 
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pseudonym_id) REFERENCES pseudonym_mapping(pseudonym_id)
);

-- Fin du script d'initialisation