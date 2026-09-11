# 🏥 HOSIX - Pipeline d'Anonymisation et Pseudonymisation IA

Ce projet implémente un pipeline complet d'intelligence artificielle pour l'anonymisation et la pseudonymisation sécurisée de comptes rendus médicaux. Il combine des techniques de traitement du langage naturel (NLP) avec spaCy et Microsoft Presidio, l'IA générative (Gemini), et un système de chiffrement robuste (Fernet) couplé à une base de données MySQL.

## 🛠️ Architecture du Projet

Le projet est structuré autour des composants suivants :

* **interface.py** : Application front-end interactive développée avec Streamlit.
* **agent.py** : Logique de détection des données personnelles (PII) utilisant Presidio (Règles + NLP) et validation par le modèle IA Gemini.
* **pseudonymizer.py** : Moteur de hachage, chiffrement des données sensibles, génération de pseudonymes et gestion des connexions SQL.
* **create_tables.sql** : Script de création et d'initialisation de l'architecture de la base de données.

## 📋 Prérequis

Avant de lancer l'application, assurez-vous d'avoir installé les éléments suivants :
* Python 3.9+
* Serveur MySQL (ex: MySQL Workbench, XAMPP, etc.)
* Clé API Google Gemini

## 🚀 Installation et Configuration

### 1. Préparation de la base de données
1. Ouvrez votre gestionnaire de base de données (ex: MySQL Workbench).
2. Chargez et exécutez entièrement le fichier create_tables.sql.
3. Cela créera la base sih_anonymisation ainsi que les tables sécurisées pseudonym_mapping et patient_pii_vault.

### 2. Variables d'environnement
Renommez le fichier .env.template en .env. Ouvrez-le avec un éditeur de texte et remplissez les champs vides avec vos propres identifiants sécurisés :

GEMINI_API_KEY=votre_cle_api_gemini
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=votre_mot_de_passe_mysql
DB_NAME=sih_anonymisation
PSEUDO_PEPPER=une_chaine_secrete_pour_le_hachage
ADMIN_CIPHER_KEY=votre_cle_fernet_generee_en_base64

Attention : Ne modifiez pas les noms des variables, remplacez uniquement les valeurs après le signe =.

### 3. Installation des dépendances Python
Ouvrez votre terminal dans le dossier du projet (là où se trouve le fichier requirements.txt) et exécutez les commandes suivantes :

pip install -r requirements.txt
python -m spacy download fr_core_news_md

## 💡 Guide d'Utilisation

* Saisie Manuelle : Collez directement le texte du compte rendu dans la zone dédiée.
* Traitement de Document Unique : Importez un fichier (TXT, PDF, DOCX) pour une anonymisation individuelle.
* Traitement par Lots : Importez de multiples documents simultanément pour un traitement automatisé en masse.
* Exportation Sécurisée : Téléchargez les documents finaux expurgés des données identifiantes directes, tout en conservant la mise en page d'origine (PDF/Word).

## 💻 Démarrage de l'application
Une fois la configuration terminée, lancez l'interface utilisateur Streamlit avec la commande suivante :

streamlit run interface.py
