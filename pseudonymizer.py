import hmac
import hashlib
import re
import os
import mysql.connector
from cryptography.fernet import Fernet

class PatientPseudonymizer:
    def __init__(self):
        # Sécurité stricte : aucune valeur par défaut dans le code source
        self.pepper = os.getenv("PSEUDO_PEPPER")
        if not self.pepper:
            raise ValueError("Erreur de configuration : 'PSEUDO_PEPPER' est introuvable dans le fichier .env")
        
        cle_chiffrement = os.getenv("ADMIN_CIPHER_KEY")
        if not cle_chiffrement:
            raise ValueError("Erreur de configuration : 'ADMIN_CIPHER_KEY' est introuvable dans le fichier .env")
        
        self.cipher = Fernet(cle_chiffrement.encode())

        # Configuration MySQL
        self.db_host = os.getenv("DB_HOST")
        self.db_user = os.getenv("DB_USER")
        self.db_password = os.getenv("DB_PASSWORD")
        self.db_name = os.getenv("DB_NAME")

    def get_db_connection(self):
        try:
            return mysql.connector.connect(
                host=self.db_host,
                user=self.db_user,
                password=self.db_password,
                database=self.db_name
            )
        except mysql.connector.Error as e:
            print(f"Erreur de connexion MySQL : {e}")
            return None

    def normaliser_pii(self, texte):
        if not texte:
            return ""
        texte = str(texte).upper()
        return re.sub(r"[^\w\d]", "", texte)

    def construire_cle_patient(self, pii_list):
        ip_val, cin, nom, tel, date_naissance, dossier = "", "", "", "", "", ""

        for pii in pii_list:
            type_pii = pii.get("type", "").upper()
            valeur = self.normaliser_pii(pii.get("text", ""))

            # CORRECTION : On extrait les chiffres et on garde toujours la version la plus longue de l'IP
            if type_pii in ["OTHER_ID", "IP", "IPP", "IDENTIFIANT"]: 
                val_clean = "".join(filter(str.isdigit, pii.get("text", "")))
                if len(val_clean) > len(ip_val): 
                    ip_val = val_clean
            elif type_pii in ["CIN", "CIN_MA"]: 
                cin = valeur
            # CORRECTION : On accepte les caprices de l'IA comme "NOM_PATIENT"
            elif type_pii in ["PATIENT_NAME", "PERSON", "NOM_PATIENT", "NOM"]: 
                nom = valeur
            elif type_pii in ["PHONE", "PHONE_NUMBER_MA", "PHONE_NUMBER", "TELEPHONE"]: 
                tel = valeur
            elif type_pii in ["DATE_BIRTH", "DATE_NAISSANCE", "AGE"]: 
                date_naissance = valeur
            elif type_pii in ["DOSSIER_MEDICAL", "DOSSIER_MED", "DM"]: 
                dossier = valeur

        if cin: 
            return f"ID-CIN-{cin}"
        elif ip_val:
            return f"ID-IP-{ip_val}"
        elif nom and date_naissance and tel: 
            return f"ID-NDT-{nom}-{date_naissance}-{tel}"
        elif nom and date_naissance: 
            return f"ID-ND-{nom}-{date_naissance}"
        elif nom and tel: 
            return f"ID-NT-{nom}-{tel}"
        elif nom: 
            return f"ID-NOM-{nom}"
        elif dossier: 
            return f"ID-DOS-{dossier}"
        
        return None

    def chiffrer_valeur(self, valeur_originale):
      if valeur_originale and str(valeur_originale).strip() != "":
        # Ajout du .decode('utf-8') pour transformer les bytes en texte
        return self.cipher.encrypt(str(valeur_originale).encode('utf-8')).decode('utf-8')
      return None

    def generer_pseudonyme(self, cle_patient, pii_list):
        if not cle_patient:
            return None, None, "Aucune PII trouvée pour construire la clé."

        hash_obj = hmac.new(self.pepper.encode('utf-8'), cle_patient.encode('utf-8'), hashlib.sha256)
        hash_complet = hash_obj.hexdigest()
        pseudonyme_court = f"PAT-{hash_complet[:8].upper()}"

        cin, nom, tel, date_naissance, dossier, num_couverture, ip_val = "", "", "", "", "", "", ""
        
        for pii in pii_list:
            type_pii = pii.get("type", "").upper()
            valeur = pii.get("text", "")
            
            if type_pii in ["CIN", "CIN_MA"]: 
                cin = valeur
            # CORRECTION : Tolérance sur le type "Nom"
            elif type_pii in ["PATIENT_NAME", "PERSON", "NOM_PATIENT", "NOM"]: 
                nom = valeur
            elif type_pii in ["PHONE", "PHONE_NUMBER_MA", "PHONE_NUMBER", "TELEPHONE"]: 
                tel = valeur
            elif type_pii in ["DATE_BIRTH", "DATE_NAISSANCE", "AGE"]: 
                date_naissance = valeur
            elif type_pii in ["DOSSIER_MEDICAL", "DOSSIER_MED", "DM"]: 
                dossier = valeur
            elif type_pii in ["ASSURANCE_MEDICALE", "NUM_ASSURANCE", "ASSURANCE", "AMO", "CNSS"]: 
                num_couverture = valeur
            # CORRECTION : On garde l'IP la plus longue (188231 au lieu de 231)
            elif type_pii in ["OTHER_ID", "IP", "IPP", "IDENTIFIANT"]: 
                val_clean = "".join(filter(str.isdigit, valeur))
                if len(val_clean) > len(ip_val): 
                    ip_val = val_clean

        conn = self.get_db_connection()
        db_status = ""
        
        if conn:
            try:
                cursor = conn.cursor(dictionary=True)
                
                cursor.execute("SELECT pseudonym_id FROM pseudonym_mapping WHERE patient_hash = %s", (hash_complet,))
                resultat = cursor.fetchone()

                if resultat:
                    pseudonyme_court = resultat['pseudonym_id']
                    
                    enc_nom = self.chiffrer_valeur(nom)
                    enc_cin = self.chiffrer_valeur(cin)
                    enc_tel = self.chiffrer_valeur(tel)
                    enc_date = self.chiffrer_valeur(date_naissance)
                    enc_dossier = self.chiffrer_valeur(dossier)
                    enc_ip = self.chiffrer_valeur(ip_val) 
                    enc_num_couverture = self.chiffrer_valeur(num_couverture)
                    
                    query_update = '''
                        UPDATE patient_pii_vault 
                        SET encrypted_nom = COALESCE(%s, encrypted_nom),
                            encrypted_cin = COALESCE(%s, encrypted_cin),
                            encrypted_tel = COALESCE(%s, encrypted_tel),
                            encrypted_date_naissance = COALESCE(%s, encrypted_date_naissance),
                            encrypted_dossier = COALESCE(%s, encrypted_dossier),
                            encrypted_ip = COALESCE(%s, encrypted_ip),
                            encrypted_num_couverture = COALESCE(%s, encrypted_num_couverture)
                        WHERE pseudonym_id = %s
                    '''
                    cursor.execute(query_update, (enc_nom, enc_cin, enc_tel, enc_date, enc_dossier, enc_ip, enc_num_couverture, pseudonyme_court))
                    conn.commit()
                    db_status = "Succès : Patient existant récupéré et données mises à jour."
                    
                else:
                    cursor.execute(
                        "INSERT INTO pseudonym_mapping (patient_hash, pseudonym_id) VALUES (%s, %s)", 
                        (hash_complet, pseudonyme_court)
                    )
                    
                    enc_nom = self.chiffrer_valeur(nom)
                    enc_cin = self.chiffrer_valeur(cin)
                    enc_tel = self.chiffrer_valeur(tel)
                    enc_date = self.chiffrer_valeur(date_naissance)
                    enc_dossier = self.chiffrer_valeur(dossier)
                    enc_ip = self.chiffrer_valeur(ip_val)
                    enc_num_couverture = self.chiffrer_valeur(num_couverture)
                    
                    query_vault = '''
                        INSERT INTO patient_pii_vault 
                        (pseudonym_id, encrypted_nom, encrypted_cin, encrypted_tel, encrypted_date_naissance, encrypted_dossier, encrypted_ip, encrypted_num_couverture) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    '''
                    cursor.execute(query_vault, (pseudonyme_court, enc_nom, enc_cin, enc_tel, enc_date, enc_dossier, enc_ip, enc_num_couverture))
                    
                    conn.commit()
                    db_status = "Succès : Nouveau patient et PII chiffrées insérés."

            except mysql.connector.Error as e:
                db_status = f"Erreur SQL : {e}"
            finally:
                if conn.is_connected():
                    cursor.close()
                    conn.close()
        else:
            db_status = "Échec de la connexion à MySQL."

        return hash_complet, pseudonyme_court, db_status