import os
import sys
import json
import io
import hashlib
import calendar
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from openpyxl.drawing.image import Image as XLImage

# Configuration de la page et injection de styles CSS pour le thème
st.set_page_config(page_title="Work Order Management (Streamlit-only)", layout="wide")
st.markdown("""
    <style>
    /* Thème bleu/gris pastel pour l'application */
    body, [class*="css-"] {
        color: #1c1e21;
        background-color: #f5f7fa;
        font-family: "sans serif";
    }
    /* Titres */
    h1 { color: #336699; }
    h2, h3, h4 { color: #264d73; }
    /* Boutons principaux */
    button[kind="primary"], button.primary {
        background-color: #4a76a8;
        color: white;
        border: none;
    }
    /* Boutons secondaires */
    button.secondary {
        background-color: #758eb2;
        color: white;
        border: none;
    }
    /* Formulaires et encadrés */
    .stTextInput, .stSelectbox, .stDateInput, .stNumberInput {
        color: #1c1e21;
        background-color: #e6ebf1;
    }
    /* Sidebar */
    .stSidebar { background-color: #dfe4ed; }
    </style>
""", unsafe_allow_html=True)

st.title("Work Order Management — (Stockage local JSON)")

# Répertoire de données local
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)

FILES = {
    "bon_travail": os.path.join(DATA_DIR, "bon_travail.json"),
    "liste_pdr": os.path.join(DATA_DIR, "liste_pdr.json"),
    "users": os.path.join(DATA_DIR, "users.json"),
    "options_description_probleme": os.path.join(DATA_DIR, "options_description_probleme.json"),
    "options_poste_de_charge": os.path.join(DATA_DIR, "options_poste_de_charge.json"),
}

# Listes initiales de descriptions et postes (pour pré-remplir les options)
INITIAL_DESCRIPTIONS = [
    'P.M.I.01-Panne au niveau du capos', "P.M.I.02-problème d'éjecteur de moule", 'P.M.I.03-Blocage moule',
    'P.M.I.04-Problème de tiroir', 'P.M.I.05-Cassure vis sortie plaque carotte', 'P.M.I.06-Blocage de la plaque carotte',
    'P.M.I.07-Vis de noyaux endommagé', 'P.M.I.08-Problème noyau', "P.M.I.09-Problème vis d'injection", 'P.M.I.10-Réducteur',
    'P.M.I.11-Roue dentée', 'P.M.I.12-PB grenouillère', 'P.M.I.13-Vis de pied endommagé', 'P.M.I.14-Colonnes de guidage',
    "P.M.I.15-Fuite matiére au niveau de la buse d'injection",
    'P.E.I.01-PB capteur', 'P.E.I.02-PB galet (fin de course)', 'P.E.I.03-PB moteur électrique', 'P.E.I.04-Capteur linéaire',
    'P.E.I.05-Armoire électrique', 'P.E.I.06-Écran/tactile', "P.E.I.07-Machine s'allume pas", "P.E.I.08-PB d'électrovanne",
    'P.E.I.09-PB connecteur', 'P.E.I.10-Système magnétique',
    'P.H.I.01-PB flexible', 'P.H.I.02-PB raccord', 'P.H.I.03-PB vérin', 'P.H.I.04-PB distributeur', 'P.H.I.05-PB pompe',
    'P.H.I.06-PB filtre', 'P.H.I.07-PB au niveau huile', 'P.H.I.08-PB fuite huile', 'P.H.I.09-PB préchauffage',
    'P.H.I.10-PB lubrification du canalisation de grenouillère',
    'P.P.I.01-PB de pression', 'P.P.I.02-Remplissage matière', 'P.P.I.03-Alimentation matiére',
    'P.P.I.04-Flexible pneumatique', 'P.P.I.05-PB raccord',
    'P.T.I.01-PB collier chauffante', 'P.T.I.02-PB de thermocouple', 'P.T.I.03-Zone de chauffage en arrêt',
    'P.T.I.04-PB refroidisseur', "P.T.I.05-PB pression d'eau", 'P.T.I.06-PB température sécheur',
    'P.T.I.07-Variation de la température (trop élevé/trop bas)'
]
INITIAL_POSTES = [
    'ASL011','ASL021','ASL031','ASL041','ASL051','ASL061','ASL071',
    'ASL012','ASL022','ASL032','ASL042','ASL052','ASL062','ASL072',
    'ACL011','ACL021','ACL031','ACL041','ACL051','ACL061','ACL071','APCL011','APCL021','APCL031',
    'CL350-01 HOUSING','CL350-02 HOUSING','CL350-03 BRAKET', 'CL120-01 SUR MOULAGE (LEVIET)','CL120-02 SUR MOULAGE (LEVIET)',
    'M. Shifter Ball', 'M. Knob clip-lever MA', 'M. Knob clip-lever MB6', 'M. Guides for trigger', 'M. Damper',
    'M. MB6-HIGH HOUSING', 'M. MB6-LOW HOUSING', 'M. MA-HIGH HOUSING', 'M. MA-LOW HOUSING', 'M. BRAKET MA'
]

# ---------------------------
# Utilitaires fichiers (atomiques)
# ---------------------------
def atomic_write(path: str, obj: Any) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

def load_json(path: str) -> Any:
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def ensure_data_files():
    # Initialise les fichiers JSON vides ou avec valeurs par défaut
    if load_json(FILES["bon_travail"]) is None:
        atomic_write(FILES["bon_travail"], [])
    if load_json(FILES["liste_pdr"]) is None:
        atomic_write(FILES["liste_pdr"], [])
    if load_json(FILES["users"]) is None:
        atomic_write(FILES["users"], [])
    if load_json(FILES["options_description_probleme"]) is None:
        atomic_write(FILES["options_description_probleme"], INITIAL_DESCRIPTIONS.copy())
    if load_json(FILES["options_poste_de_charge"]) is None:
        atomic_write(FILES["options_poste_de_charge"], INITIAL_POSTES.copy())

ensure_data_files()

# ---------------------------
# Hashage du mot de passe
# ---------------------------
def hash_password(pwd: str) -> str:
    return hashlib.sha256((pwd or "").encode("utf-8")).hexdigest()

# ---------------------------
# Opérations CRUD pour les bons, PDR, utilisateurs
# ---------------------------
BON_COLUMNS = ["code", "date", "arret_declare_par", "poste_de_charge", "heure_declaration",
               "machine_arreter", "description_probleme", "dpt_production",
               "pdr_utilisee", "resultat", "condition_acceptation"]

PDR_COLUMNS = ["code", "remplacement", "nom_composant", "quantite"]

def read_bons() -> List[Dict[str, Any]]:
    arr = load_json(FILES["bon_travail"])
    return arr if arr else []

def write_bons(arr: List[Dict[str, Any]]) -> None:
    atomic_write(FILES["bon_travail"], arr)

def get_bon_by_code(code: str) -> Optional[Dict[str, Any]]:
    for r in read_bons():
        if str(r.get("code", "")) == str(code):
            return r
    return None

def add_bon(bon: Dict[str, Any]) -> None:
    bons = read_bons()
    if get_bon_by_code(bon.get("code")) is not None:
        raise ValueError("Code déjà présent")
    # assure chaque colonne existe
    entry = {k: bon.get(k, "") for k in BON_COLUMNS}
    bons.append(entry)
    write_bons(bons)
    # décrémenter PDR si fourni
    pdr_code = str(entry.get("pdr_utilisee", "")).strip()
    if pdr_code:
        pdrs = read_pdr()
        for i, p in enumerate(pdrs):
            if str(p.get("code", "")).strip() == pdr_code:
                q = int(p.get("quantite", 0) or 0)
                p["quantite"] = max(0, q - 1)
                pdrs[i] = p
                write_pdr(pdrs)
                break

def update_bon(code: str, updates: Dict[str, Any]) -> None:
    bons = read_bons()
    found = False
    for i, r in enumerate(bons):
        if str(r.get("code", "")) == str(code):
            for k in BON_COLUMNS:
                if k in updates:
                    r[k] = updates[k]
            bons[i] = r
            found = True
            break
    if not found:
        raise KeyError("Code introuvable")
    write_bons(bons)

def delete_bon(code: str) -> None:
    bons = read_bons()
    bons = [r for r in bons if str(r.get("code", "")) != str(code)]
    write_bons(bons)

def read_pdr() -> List[Dict[str, Any]]:
    arr = load_json(FILES["liste_pdr"])
    return arr if arr else []

def write_pdr(arr: List[Dict[str, Any]]) -> None:
    atomic_write(FILES["liste_pdr"], arr)

def upsert_pdr(rec: Dict[str, Any]) -> None:
    pdrs = read_pdr()
    code = str(rec.get("code", "")).strip()
    if not code:
        raise ValueError("Code PDR requis")
    for i, p in enumerate(pdrs):
        if str(p.get("code", "")).strip() == code:
            pdrs[i] = {
                "code": code,
                "remplacement": rec.get("remplacement", ""),
                "nom_composant": rec.get("nom_composant", ""),
                "quantite": int(rec.get("quantite", 0))
            }
            write_pdr(pdrs)
            return
    pdrs.append({
        "code": code,
        "remplacement": rec.get("remplacement", ""),
        "nom_composant": rec.get("nom_composant", ""),
        "quantite": int(rec.get("quantite", 0))
    })
    write_pdr(pdrs)

def delete_pdr_by_code(code: str) -> None:
    pdrs = read_pdr()
    pdrs = [p for p in pdrs if str(p.get("code", "")).strip() != str(code).strip()]
    write_pdr(pdrs)

def read_users() -> List[Dict[str, Any]]:
    arr = load_json(FILES["users"])
    return arr if arr else []

def write_users(arr: List[Dict[str, Any]]) -> None:
    atomic_write(FILES["users"], arr)

def get_user(username: str) -> Optional[Dict[str, Any]]:
    for u in read_users():
        if u.get("username", "") == username:
            return u
    return None

def create_user(username: str, password: str, role: str) -> None:
    users = read_users()
    if get_user(username) is not None:
        raise ValueError("Nom d'utilisateur déjà existant")
    users.append({"username": username, "password_hash": hash_password(password), "role": role})
    write_users(users)
