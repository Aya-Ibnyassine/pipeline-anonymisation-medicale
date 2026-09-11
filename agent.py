import os
import json
import pandas as pd

from google import genai
from google.genai import types

from presidio_analyzer import (
    AnalyzerEngine,
    Pattern,
    PatternRecognizer,
    RecognizerResult
)

from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine

from dotenv import load_dotenv
load_dotenv()


class AnonymizationAgent:
    def __init__(self):
        
        # Configuration Gemini
      
        API_KEY = os.getenv("GEMINI_API_KEY")

        if API_KEY is None:
            raise ValueError("La variable d'environnement GEMINI_API_KEY n'a pas été trouvée.")

        self.client = genai.Client(api_key=API_KEY)
        self.MODEL_NAME = "gemini-2.5-flash"

      
        # Configuration de spaCy
       
        provider_config = {
            "nlp_engine_name": "spacy",
            "models": [
                {
                    "lang_code": "fr",
                    "model_name": "fr_core_news_md"
                }
            ]
        }

        provider = NlpEngineProvider(
            nlp_configuration=provider_config
        )

        nlp_engine = provider.create_engine()

        
        # Création du moteur Presidio
        
        self.analyzer = AnalyzerEngine(
            nlp_engine=nlp_engine,
            supported_languages=["fr"]
        )

        self.anonymizer = AnonymizerEngine()

       
        # Ajout des règles Regex
        
        self._create_regex_recognizers()

    def _create_regex_recognizers(self):

        # IP / IPP (Identifiant Patient)
        ip_pattern = Pattern(
            name="ip_pattern",
            regex=r"\b(?:IP|IPP)[\s:\-]*[*]?[\d\s]{5,15}[*]?\b",
            score=0.95
        )

        ip_recognizer = PatternRecognizer(
            supported_entity="OTHER_ID",
            patterns=[ip_pattern],
            context=["ip", "ipp", "identification"]
        )
        self.analyzer.registry.add_recognizer(ip_recognizer)

        # Dossier médical
        dossier_pattern = Pattern(
            name="dossier_pattern",
            regex=r"\bDM[\s\-]?\d{3,10}\b",
            score=0.95
        )

        dossier_recognizer = PatternRecognizer(
            supported_entity="DOSSIER_MED",
            patterns=[dossier_pattern],
            context=["dossier", "dm"]
        )

        # Téléphone Maroc
        tel_pattern = Pattern(
            name="telephone_maroc",
            regex=r"\b0[5-7](?:\s*\d{2}){4}\b",
            score=0.95
        )

        tel_recognizer = PatternRecognizer(
            supported_entity="PHONE_NUMBER_MA",
            patterns=[tel_pattern],
            context=["telephone", "portable", "tél"]
        )

        # CIN marocain
        cin_pattern = Pattern(
            name="cin_maroc",
            regex=r"\b[A-Z]{1,2}\d{5,7}\b",
            score=0.95
        )

        cin_recognizer = PatternRecognizer(
            supported_entity="CIN",
            patterns=[cin_pattern],
            context=["cin"]
        )

        # Date de naissance
        date_naissance_pattern = Pattern(
            name="date_naissance_pattern",
            regex=r"\b(?:né|née|ne|nee)\s+(?:le\s+)?\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
            score=0.90
        )

        date_naissance_recognizer = PatternRecognizer(
            supported_entity="DATE_NAISSANCE",
            patterns=[date_naissance_pattern],
            context=["né", "née", "naissance"]
        )

        # Assurance / AMO / CNSS / RAMED
        assurance_pattern = Pattern(
            name="assurance_pattern",
            regex=r"\b(?:AMO|CNSS|CNOPS|RAMED)[\s:-]*[A-Z0-9]{4,15}\b",
            score=0.90
        )

        assurance_recognizer = PatternRecognizer(
            supported_entity="ASSURANCE_MEDICALE",
            patterns=[assurance_pattern],
            context=["amo", "cnss", "cnops", "ramed", "assurance"]
        )

        # Médecin
        medecin_pattern = Pattern(
            name="medecin_pattern",
            regex=r"\b(?:Dr|Pr|Docteur|Professeur)\s+[A-ZÀ-Ÿ][a-zà-ÿ\-]+\s+[A-ZÀ-Ÿ][a-zà-ÿ\-]+\b",
            score=0.90
        )

        medecin_recognizer = PatternRecognizer(
            supported_entity="MEDECIN",
            patterns=[medecin_pattern],
            context=["dr", "pr", "docteur", "professeur"]
        )

        # Adresse marocaine
        adresse_pattern = Pattern(
          name="adresse_maroc_pattern",
          regex=r"\b\d{1,4}\s*,?\s*(?:rue|avenue|av\.?|boulevard|bd\.?|quartier|hay|résidence|residence)\s+[^.\n]+",
          score=0.97
        )

        adresse_recognizer = PatternRecognizer(
            supported_entity="ADRESSE_MA",
            patterns=[adresse_pattern],
            context=["adresse", "habite", "résidence", "rue", "avenue"]
        )

        # Nom patient simple
        patient_pattern = Pattern(
            name="patient_name_pattern",
            regex=r"\b(?:M\.|Mme|Monsieur|Madame)?\s*[A-ZÀ-Ÿ][a-zà-ÿ\-]+\s+[A-ZÀ-Ÿ][a-zà-ÿ\-]+,\s*\d{1,3}\s*ans\b",
            score=0.85
        )

        patient_recognizer = PatternRecognizer(
            supported_entity="PATIENT_NAME",
            patterns=[patient_pattern],
            context=["patient", "patiente", "monsieur", "madame", "mme"]
        )

        # Ajout de toutes les règles au moteur Presidio
        self.analyzer.registry.add_recognizer(dossier_recognizer)
        self.analyzer.registry.add_recognizer(tel_recognizer)
        self.analyzer.registry.add_recognizer(cin_recognizer)
        self.analyzer.registry.add_recognizer(date_naissance_recognizer)
        self.analyzer.registry.add_recognizer(assurance_recognizer)
        self.analyzer.registry.add_recognizer(medecin_recognizer)
        self.analyzer.registry.add_recognizer(adresse_recognizer)
        self.analyzer.registry.add_recognizer(patient_recognizer)


    def ajouter_regex_direct(self, text, resultats):
      import re

      regex_rules = [
        {
            "type": "PATIENT_NAME",
            "regex": r"\b(?:M\.|Mme|Monsieur|Madame)\s+[A-ZÀ-Ÿ][a-zà-ÿ\-']+(?:\s+[A-ZÀ-Ÿ][a-zà-ÿ\-']+){1,3}(?=\s*,\s*\d{1,3}\s*ans\b)",
            "score": 0.99
        },
        {
            "type": "PHONE_NUMBER_MA",
            "regex": r"\b0[5-7](?:[\s.-]?\d{2}){4}\b",
            "score": 0.99
        },
        {
            "type": "CIN",
            "regex": r"\b[A-Z]{1,2}\d{5,7}\b",
            "score": 0.99
        },
        {
            "type": "DOSSIER_MED",
            "regex": r"\bDM[\s\-:]?\d{3,10}\b",
            "score": 0.99
        },
        
        {
            "type": "MEDECIN",
            "regex": r"\b(?:Dr|Pr|Docteur|Professeur)\.?\s+[A-ZÀ-Ÿ][a-zà-ÿ\-']+(?:\s+[A-ZÀ-Ÿ][a-zà-ÿ\-']+){0,3}",
            "score": 0.99
        },
        {
            "type": "ADRESSE_MA",
            "regex": r"\b\d{1,4}\s*,?\s*(?:rue|avenue|av\.?|boulevard|bd\.?|quartier|hay|résidence|residence)\s+[^.\n]+",
            "score": 0.99
        },
        {
            "type": "ASSURANCE_MEDICALE",
            "regex": r"\b(?:AMO|CNSS|CNOPS|RAMED)[\s:-]*[A-Z0-9]{4,15}\b",
            "score": 0.99
        },
        {
            "type": "OTHER_ID",
            "regex": r"\b(?:IP|IPP)[\s:\-]*[*]?[\d\s]{5,15}[*]?\b",
            "score": 0.99
        },
    ]

      for rule in regex_rules:
        for match in re.finditer(rule["regex"], text, flags=re.IGNORECASE):
            resultats.append(
                RecognizerResult(
                    entity_type=rule["type"],
                    start=match.start(),
                    end=match.end(),
                    score=rule["score"]
                )
            )

      return resultats

    def detect_presidio(self, text):
     entities = [
        "PERSON",
        "LOCATION",
        #"DATE_TIME",
        "EMAIL_ADDRESS",
        "PHONE_NUMBER",
        "ORGANIZATION",

        "PATIENT_NAME",
        "PHONE_NUMBER_MA",
        "DOSSIER_MED",
        "CIN",
        "DATE_NAISSANCE",
        "ASSURANCE_MEDICALE",
        "MEDECIN",
        "ADRESSE_MA"
    ]

     resultats = self.analyzer.analyze(
        text=text,
        language="fr",
        entities=entities
     )

    # Ajouter tes regex fortes
     resultats = self.ajouter_regex_direct(text, resultats)

    # Supprimer les faux positifs comme "Consultation" détecté comme LOCATION
     resultats = self.filtrer_faux_positifs(text, resultats)

     return resultats

    def afficher_entites_detectees(self, text, resultats):
        print("===== ENTITES DETECTEES =====\n")

        for r in resultats:
            texte = text[r.start:r.end]

            print(f"""
Texte      : {texte}
Type       : {r.entity_type}
Score      : {r.score:.2f}
Début      : {r.start}
Fin        : {r.end}
-------------------------------
""")

    def anonymiser_presidio_simple(self, text, resultats):
        texte_anonymise = self.anonymizer.anonymize(
            text=text,
            analyzer_results=resultats
        )

        return texte_anonymise.text

    def compter_types_entites(self, resultats):
        types = {}

        for r in resultats:
            types[r.entity_type] = types.get(r.entity_type, 0) + 1

        return pd.DataFrame(
            types.items(),
            columns=["Type", "Nombre"]
        )

    def fusionner_entites(self, resultats):
     priorite = {
        "PATIENT_NAME": 100,
        "MEDECIN": 95,
        "CIN": 95,
        "DOSSIER_MED": 95,
        "PHONE_NUMBER_MA": 95,
        "ADRESSE_MA": 95,
        "ASSURANCE_MEDICALE": 90,
        "DATE_NAISSANCE": 90,

        "PHONE_NUMBER": 80,
        "EMAIL_ADDRESS": 80,
        "PERSON": 60,
        "LOCATION": 50,
        "ORGANIZATION": 45,
        "DATE_TIME": 40
     }

     entites = sorted(
        resultats,
        key=lambda x: (x.start, -(x.end - x.start))
     )

     fusion = []

     for entite in entites:
        ajouter = True

        for existante in fusion[:]:
            chevauche = not (
                entite.end <= existante.start or
                entite.start >= existante.end
            )

            if chevauche:
                score_entite = (
                    priorite.get(entite.entity_type, 10),
                    entite.score,
                    entite.end - entite.start
                )

                score_existante = (
                    priorite.get(existante.entity_type, 10),
                    existante.score,
                    existante.end - existante.start
                )

                if score_entite > score_existante:
                    fusion.remove(existante)
                else:
                    ajouter = False

        if ajouter:
            fusion.append(entite)

     return sorted(fusion, key=lambda x: x.start)
    
    def filtrer_faux_positifs(self, text, resultats):
     faux_location = {
        "consultation",
        "compte rendu",
        "dossier",
        "dossier médical",
        "patiente",
        "patient",
        "service",
        "oncologie",
        "radiothérapie",
        "chimiothérapie"
    }

     resultats_filtres = []

     for r in resultats:
        extrait = text[r.start:r.end].strip()
        extrait_normalise = extrait.lower()

        # Supprimer les faux LOCATION
        if r.entity_type == "LOCATION" and extrait_normalise in faux_location:
            continue

        resultats_filtres.append(r)

     return resultats_filtres

    def anonymiser_texte(self, text, entites):
        mapping_remplacement = {
        "PERSON": "[PATIENT]",
        "PATIENT_NAME": "[PATIENT]",
        "PHONE_NUMBER": "[TELEPHONE]",
        "PHONE_NUMBER_MA": "[TELEPHONE]",
        "DOSSIER_MED": "[DOSSIER_MEDICAL]",
        "CIN_MA": "[CIN]",
        "CIN": "[CIN]",
        "DATE_TIME": "[DATE]",
        "DATE_NAISSANCE": "[DATE]",
        "LOCATION": "[LIEU]",
        "ADRESSE_MA": "[ADRESSE]",
        "MEDECIN": "[MEDECIN]",
        "EMAIL_ADDRESS": "[EMAIL]",
        "ASSURANCE_MEDICALE": "[NUM_COUVERTURE]",
        "ORGANIZATION": "[ORGANISATION]"
    }

        texte_final = text

        for entite in sorted(entites, key=lambda x: x.start, reverse=True):
            remplacement = mapping_remplacement.get(
                entite.entity_type,
                f"[{entite.entity_type}]"
            )

            texte_final = (
                texte_final[:entite.start]
                + remplacement
                + texte_final[entite.end:]
            )

        return texte_final

    def generer_rapport_presidio(self, text, entites_fusionnees):
        rapport = []

        for entite in entites_fusionnees:
            rapport.append({
                "texte": text[entite.start:entite.end],
                "type": entite.entity_type,
                "score": round(entite.score, 2),
                "start": entite.start,
                "end": entite.end
            })

        return rapport

    def presidio_to_list(self, text, resultats):
        entities = []

        for r in resultats:
            entities.append({
                "text": text[r.start:r.end],
                "type": r.entity_type,
                "score": round(r.score, 2),
                "start": r.start,
                "end": r.end
            })

        return entities

    def build_llm_prompt(self, text, presidio_entities):
        return f"""
Tu es un agent d'anonymisation médicale pour des comptes rendus hospitaliers marocains.

Ta mission :
1. Vérifier les PII déjà détectées par Presidio/Regex.
2. Détecter les PII oubliées (Nom, Prénom, CIN, Téléphone, Adresse exacte, Email).
3. Corriger les mauvaises classifications.
4. Retourner uniquement un JSON valide.

⚠️ RÈGLES STRICTES DE FORMATAGE (TRÈS IMPORTANT) :
1. FERMETURE DES BALISES : Toute balise de remplacement DOIT SE TERMINER par un crochet fermant `]`. (ex: `[NOM_DOCTEUR]`)
2. EXACTITUDE DU TEXTE CIBLE : La clé "text" doit contenir EXACTEMENT le mot à masquer, sans les mots de liaison (le, la, au, du, etc.).
3. TYPES DE PII AUTORISÉS (Utilise UNIQUEMENT ces types exacts dans ton JSON, AUCUN AUTRE n'est permis) :
   - PATIENT_NAME (pour le nom du patient)
   - MEDECIN (pour le nom du docteur)
   - CIN
   - PHONE
   - DATE_NAISSANCE
   - DATE_CONSULTATION
   - DOSSIER_MEDICAL
   - ASSURANCE_MEDICALE
   - IP
   - ADRESSE

⚠️ RÈGLES STRICTES :
-ÂGE DU PATIENT : Tu ne dois JAMAIS masquer ou extraire l'âge du patient (ex: "59 ans", "patiente de 59 ans"). L'âge est une donnée clinique cruciale qui doit rester INTACTE dans le texte.
- Ne masque JAMAIS les noms de villes (ex: Fès, Casablanca, Rabat).
- Ne masque JAMAIS les assurances médicales (ex: AMO, CNSS, RAMED, CNOPS).
- L'adresse exacte (rue, numéro) doit être masquée, mais la ville doit rester visible.
- DIFFÉRENCE IP / DOSSIER MÉDICAL : 
  * Le code-barres (les numéros encadrés par des astérisques, ex: "*188 231*") représente l'Identifiant Patient. Tu dois STRICTEMENT le classer sous le type "IP".
  * Un numéro à côté de "IP:" ou "IPP:" est STRICTEMENT de type "IP".
  * Le "DOSSIER_MEDICAL" est complètement différent. Il est souvent précédé de "Dossier" ou "DM". Ne classe JAMAIS le code-barres sous DOSSIER_MEDICAL.

⚠️ RÈGLES STRICTES CONCERNANT LES DATES :
- Tu dois MASQUER UNIQUEMENT la "Date de Naissance" et la "Date de Consultation".
- TOUTES LES AUTRES DATES DOIVENT RESTER 100% INTACTES. Ne masque jamais les dates liées aux traitements, aux chimiothérapies, aux irradiations, aux chirurgies (ex: "étalé du 11/2019 au 12/2019", "fin d'irradiation le...").
- Dates de consultation, d'hospitalisation ou d'examen : Tu NE DOIS PAS masquer l'intégralité de la date. Masque uniquement le jour et l'heure (si présente). Garde le mois et l'année au format MM/AAAA.
  Exemple de remplacement attendu : "Consultation du [DATE_CONSULTATION: 02/2020]" ou "Examen du [DATE_CONSULTATION: 05/2026]".
-Pour la Date de naissance : Garde uniquement l'année (ex: [ANNEE_NAISSANCE: 1971]).

⚠️ RÈGLES STRICTES DE MASQUAGE PARTIEL :
- Assurance médicale (AMO, CNSS, RAMED, CNOPS) : Tu NE DOIS PAS masquer le nom de l'organisme. Masque uniquement le numéro d'immatriculation. 
  Exemple de remplacement attendu : "AMO [NUM_COUVERTURE]" ou "CNSS [NUM_COUVERTURE]".

Types de PII à détecter :
- NOM_PATIENT
- NOM_DOCTEUR
- CIN
- PHONE
- EMAIL
- ADRESSE (Rue/Quartier uniquement, pas la ville)
- DATE_NAISSANCE
- DOSSIER_MEDICAL
- ASSURANCE_MEDICALE
- AUTRE_ID

Entités déjà détectées par Presidio/Regex :
{json.dumps(presidio_entities, ensure_ascii=False, indent=2)}

Compte rendu :
{text}

Format obligatoire :
{{
  "pii_detected": [
    {{
      "text": "...",
      "type": "...",
      "replacement": "la balise de remplacement selon les règles"
    }}
  ]
}}
"""

    def call_gemini_agent(self, text, presidio_entities, fichier_bytes=None, mime_type=None):
        prompt = self.build_llm_prompt(text, presidio_entities)

        # Si un document visuel (PDF ou Image) est fourni, on l'ajoute !
        contents = []
        if fichier_bytes and mime_type in ['application/pdf', 'image/jpeg', 'image/png']:
            contents.append(
                types.Part.from_bytes(data=fichier_bytes, mime_type=mime_type)
            )
        
        # On ajoute le texte du prompt à la suite
        contents.append(prompt)

        response = self.client.models.generate_content(
            model=self.MODEL_NAME,
            contents=contents
        )

        return response.text

    def parse_llm_json(self, response_text):
        response_text = response_text.strip()

        if response_text.startswith("```json"):
            response_text = (
                response_text
                .replace("```json", "")
                .replace("```", "")
                .strip()
            )

        elif response_text.startswith("```"):
            response_text = (
                response_text
                .replace("```", "")
                .strip()
            )

        return json.loads(response_text)

    def anonymiser_avec_llm(self, text, pii_list):
        texte = text

        # Trier par longueur décroissante pour éviter les remplacements partiels
        pii_list = sorted(
            pii_list,
            key=lambda x: len(x["text"]),
            reverse=True
        )

        for pii in pii_list:
            original = pii["text"]
            replacement = pii["replacement"]

            texte = texte.replace(original, replacement)

        return texte

    def run(self, text, fichier_bytes=None, mime_type=None, afficher=False):
     
        # 1. Détection Presidio + Regex
     
        resultats = self.detect_presidio(text)

        if afficher:
            self.afficher_entites_detectees(text, resultats)

        
        # 2. Anonymisation Presidio simple
        
        texte_anonymise_presidio_simple = self.anonymiser_presidio_simple(
            text,
            resultats
        )

       
        # 3. Fusion des entités
       
        entites_fusionnees = self.fusionner_entites(resultats)

        
        # 4. Anonymisation custom Presidio + Regex
       
        texte_final_presidio = self.anonymiser_texte(
            text,
            entites_fusionnees
        )

        
        # 5. Rapport Presidio
        
        rapport_presidio = self.generer_rapport_presidio(
            text,
            entites_fusionnees
        )

        
        # 6. Conversion résultats Presidio pour Gemini
        
        presidio_entities = self.presidio_to_list(
            text,
            resultats
        )

      
        # 7. Appel Gemini
      
        # 7. Appel Gemini (On lui passe maintenant les informations du fichier)
        llm_response = self.call_gemini_agent(
            text,
            presidio_entities,
            fichier_bytes,
            mime_type
        )

       
        # 8. Parser JSON Gemini
        
        llm_json = self.parse_llm_json(llm_response)

        
        # 9. Anonymisation avec LLM
       
        texte_final_llm = self.anonymiser_avec_llm(
            text,
            llm_json["pii_detected"]
        )

       
        # 10. Sortie finale
        
        return {
            "original_text": text,
            "resultats_presidio": resultats,
            "texte_anonymise_presidio_simple": texte_anonymise_presidio_simple,
            "entites_fusionnees": entites_fusionnees,
            "texte_anonymise_presidio_custom": texte_final_presidio,
            "rapport_presidio": rapport_presidio,
            "presidio_entities_for_llm": presidio_entities,
            "llm_raw_response": llm_response,
            "llm_json": llm_json,
            "texte_anonymise_llm": texte_final_llm
        }
    


