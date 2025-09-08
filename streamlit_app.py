# app.py
# Work Order Management - Streamlit only (stockage local JSON dans data/)
# !!! ATTENTION : stockage local sur Streamlit Cloud est éphémère (lire l'avertissement dans le code).

import os
import json
import hashlib
import io
from datetime import datetime, date
from typing import List, Dict, Any, Optional

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from openpyxl.drawing.image import Image as XLImage

# ---------------------------
# Configuration
# ---------------------------
st.set_page_config(page_title="Work Order Management (Streamlit-only)", layout="wide")
st.title("Work Order Management — (Stockage local JSON)")

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)

FILES = {
    "bon_travail": os.path.join(DATA_DIR, "bon_travail.json"),
    "liste_pdr": os.path.join(DATA_DIR, "liste_pdr.json"),
    "users": os.path.join(DATA_DIR, "users.json"),
    "options_description_probleme": os.path.join(DATA_DIR, "options_description_probleme.json"),
    "options_poste_de_charge": os.path.join(DATA_DIR, "options_poste_de_charge.json"),
}

INITIAL_DESCRIPTIONS = [
    'P.M.I.01-Panne au niveau du capos','P.M.I.02-problème d\'éjecteur de moule','P.M.I.03-Blocage  moule',
    'P.M.I.04-Problème de tiroir','P.M.I.05-Cassure vis sortie plaque carotte','P.M.I.06-Blocage de la plaque carotte',
    'P.M.I.07-Vis de noyaux endommagé','P.M.I.08-Problème noyau','P.M.I.09-Problème vis d\'injection','P.M.I.10-Réducteur',
    'P.M.I.11-Roue dentée ','P.M.I.12-PB grenouillère','P.M.I.13-Vis de pied endommagé','P.M.I.14-Colonnes de guidage ',
    'P.M.I.15-Fuite matiére au niveau de la buse d\'injection',
    'P.E.I.01-PB capteur ','P.E.I.02-PB galet (fin de course)','P.E.I.03-PB moteur électrique','P.E.I.04-Capteur linéaire',
    'P.E.I.05-Armoire électrique ','P.E.I.06-Écran/tactile','P.E.I.07-Machine s\'allume pas','P.E.I.08-PB d\'électrovanne',
    'P.E.I.09-PB connecteur ','P.E.I.10-Système magnétique',
    'P.H.I.01-PB flexible','P.H.I.02-PB raccord','P.H.I.03-PB vérin','P.H.I.04-PB distributeur','P.H.I.05-PB pompe',
    'P.H.I.06-PB filtre','P.H.I.07-PB au niveau huile','P.H.I.08-PB fuite huile','P.H.I.09-PB préchauffage',
    'P.H.I.10-PB lubrification du canalisation de grenouillère',
    'P.P.I.01-PB de pression','P.P.I.02-Remplissage matière ','P.P.I.03-Alimentation matiére ',
    'P.P.I.04-Flexible pneumatique','P.P.I.05-PB raccord',
    'P.T.I.01-PB collier chauffante','P.T.I.02-PB de thermocouple','P.T.I.03-Zone de chauffage en arrêt',
    'P.T.I.04-PB refroidisseur','P.T.I.05-PB pression d\'eau','P.T.I.06-PB température sécheur',
    'P.T.I.07-Variation de la température (trop élever/trop bas )'
]

INITIAL_POSTES = [
    'ASL011','ASL021','ASL031','ASL041','ASL051','ASL061','ASL071',
    'ASL012','ASL022','ASL032','ASL042','ASL052','ASL062','ASL072',
    'ACL011','ACL021','ACL031','ACL041','ACL051','ACL061','ACL071','APCL011','APCL021','APCL031',
    'CL350-01 HOUSING','CL350-02 HOUSING','CL350-03 BRAKET ','CL120-01 SUR MOULAGE (LEVIET)','CL120-02 SUR MOULAGE (LEVIET)',
    'M. Shifter Ball', 'M. Knob clip-lever MA','M. Knob clip-lever MB6', 'M. Guides for trigger', 'M. Damper',
    'M. MB6-HIGH HOUSING', 'M. MB6-LOW HOUSING','M. MA-HIGH HOUSING', 'M. MA-LOW HOUSING', 'M. BRAKET MA'
]

BON_COLUMNS = [
    "code","date","arret_declare_par","poste_de_charge","heure_declaration","machine_arreter",
    "heure_debut_intervention","heure_fin_intervention","technicien","description_probleme",
    "action","pdr_utilisee","observation","resultat","condition_acceptation","dpt_maintenance","dpt_qualite","dpt_production"
]

PDR_COLUMNS = ["code","remplacement","nom_composant","quantite"]

# ---------------------------
# Fichiers utilitaires
# ---------------------------
def atomic_write(path: str, obj: Any) -> None:
    tmp = path + ".tmp"
    with open(tmp,"w",encoding="utf-8") as f:
        json.dump(obj,f,ensure_ascii=False,indent=2)
    os.replace(tmp,path)

def load_json(path: str) -> Any:
    if not os.path.exists(path):
        return None
    with open(path,"r",encoding="utf-8") as f:
        return json.load(f)

def ensure_data_files():
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
# Hash password
# ---------------------------
def hash_password(pwd: str) -> str:
    return hashlib.sha256((pwd or "").encode("utf-8")).hexdigest()

# ---------------------------
# CRUD bons
# ---------------------------
def read_bons() -> List[Dict[str, Any]]:
    arr = load_json(FILES["bon_travail"])
    return arr or []

def write_bons(arr: List[Dict[str, Any]]):
    atomic_write(FILES["bon_travail"], arr)

def get_bon_by_code(code: str) -> Optional[Dict[str, Any]]:
    for r in read_bons():
        if str(r.get("code","")) == str(code):
            return r
    return None

def add_bon(bon: Dict[str, Any]) -> None:
    bons = read_bons()
    if get_bon_by_code(bon.get("code")) is not None:
        raise ValueError("Code déjà présent")
    entry = {k: bon.get(k,"") for k in BON_COLUMNS}
    bons.append(entry)
    write_bons(bons)
    pdr_code = str(entry.get("pdr_utilisee","")).strip()
    if pdr_code:
        pdrs = read_pdr()
        for i,p in enumerate(pdrs):
            if str(p.get("code","")).strip() == pdr_code:
                q = int(p.get("quantite",0) or 0)
                p["quantite"] = max(0, q-1)
                pdrs[i] = p
                write_pdr(pdrs)
                break

def update_bon(code: str, updates: Dict[str, Any]) -> None:
    bons = read_bons()
    found = False
    for i,r in enumerate(bons):
        if str(r.get("code","")) == str(code):
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
    bons = [r for r in read_bons() if str(r.get("code","")) != str(code)]
    write_bons(bons)

# ---------------------------
# CRUD PDR
# ---------------------------
def read_pdr() -> List[Dict[str, Any]]:
    arr = load_json(FILES["liste_pdr"])
    return arr or []

def write_pdr(arr: List[Dict[str, Any]]):
    atomic_write(FILES["liste_pdr"], arr)

def upsert_pdr(rec: Dict[str, Any]):
    pdrs = read_pdr()
    code = str(rec.get("code","")).strip()
    if not code:
        raise ValueError("Code PDR requis")
    for i,p in enumerate(pdrs):
        if str(p.get("code","")).strip() == code:
            pdrs[i] = {"code": code, "remplacement": rec.get("remplacement",""), "nom_composant": rec.get("nom_composant",""), "quantite": int(rec.get("quantite",0))}
            write_pdr(pdrs)
            return
    pdrs.append({"code": code, "remplacement": rec.get("remplacement",""), "nom_composant": rec.get("nom_composant",""), "quantite": int(rec.get("quantite",0))})
    write_pdr(pdrs)

def delete_pdr_by_code(code: str):
    pdrs = [p for p in read_pdr() if str(p.get("code","")).strip() != str(code).strip()]
    write_pdr(pdrs)

# ---------------------------
# Users
# ---------------------------
def read_users() -> List[Dict[str, Any]]:
    arr = load_json(FILES["users"])
    return arr or []

def write_users(arr: List[Dict[str, Any]]):
    atomic_write(FILES["users"], arr)

def get_user(username: str) -> Optional[Dict[str, Any]]:
    for u in read_users():
        if u.get("username","") == username:
            return u
    return None

def create_user(username: str, password: str, role: str):
    users = read_users()
    if get_user(username):
        raise ValueError("Utilisateur existe déjà")
    new_id = (len(users) + 1) if users else 1
    users.append({"id": new_id, "username": username, "password_hash": hash_password(password), "role": role})
    write_users(users)

# ---------------------------
# Options
# ---------------------------
def read_options(key: str) -> List[str]:
    arr = load_json(FILES[key])
    return arr or []

def write_options(key: str, arr: List[str]):
    atomic_write(FILES[key], arr)

# ---------------------------
# Pareto plotting
# ---------------------------
def plot_pareto(df: pd.DataFrame, period: str = "day", top_n_labels: int = 3):
    s = pd.to_datetime(df['date'], errors='coerce').dropna()
    if s.empty:
        st.info("Aucune date valide pour tracer le Pareto.")
        return
    if period == "day":
        groups = s.dt.strftime("%Y-%m-%d")
        xlabel = "Jour"
    elif period == "week":
        groups = s.dt.strftime("%Y-W%U")
        xlabel = "Semaine"
    else:
        groups = s.dt.strftime("%Y-%m")
        xlabel = "Mois"
    counts = groups.value_counts().sort_values(ascending=False)
    total = counts.sum()
    cum_pct = counts.cumsum()/total*100
    fig, ax1 = plt.subplots(figsize=(10,4))
    x = range(len(counts))
    ax1.bar(x, counts.values, alpha=0.85)
    ax1.set_xticks(x)
    ax1.set_xticklabels(counts.index.tolist(), rotation=45, ha='right', fontsize=9)
    ax1.set_ylabel("Nombre d'interventions")
    ax1.set_xlabel(xlabel)
    ax1.set_title(f"Pareto ({period}) - total = {total}")
    ax2 = ax1.twinx()
    ax2.plot(x, cum_pct.values, color='red', marker='o')
    ax2.set_ylim(0, 110)
    ax2.set_ylabel("Pourcentage cumulé (%)")
    ax2.axhline(80, color='grey', linestyle='--')
    st.pyplot(fig)

# ---------------------------
# Export Excel
# ---------------------------
def export_bons_to_excel(bons: List[Dict[str, Any]]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Bons de Travail"
    for i, col in enumerate(BON_COLUMNS, start=1):
        c = ws.cell(row=1, column=i, value=col)
        c.font = Font(bold=True)
        c.alignment = Alignment(horizontal='center')
    for r_idx, r in enumerate(bons, start=2):
        for c_idx, col in enumerate(BON_COLUMNS, start=1):
            ws.cell(row=r_idx, column=c_idx, value=r.get(col,""))
    bio = io.BytesIO()
    wb.save(bio)
    return bio.getvalue()

# ---------------------------
# Login & main app
# ---------------------------
st.sidebar.title("Navigation")
page = st.sidebar.selectbox("Choisir la page", ["Login","Dashboard","Bons de Travail","PDR","Pareto","Export Excel"])

if "login_state" not in st.session_state:
    st.session_state["login_state"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""
if "role" not in st.session_state:
    st.session_state["role"] = ""

if page == "Login":
    st.subheader("Connexion")
    username = st.text_input("Utilisateur")
    password = st.text_input("Mot de passe", type="password")
    if st.button("Se connecter"):
        user = get_user(username)
        if user and hash_password(password) == user["password_hash"]:
            st.session_state["login_state"] = True
            st.session_state["username"] = username
            st.session_state["role"] = user["role"]
            st.success("Connecté avec succès !")
            st.experimental_rerun()
        else:
            st.error("Utilisateur ou mot de passe incorrect")
    if st.button("Créer un manager initial") and not read_users():
        create_user("manager","manager123","manager")
        st.success("Manager initial créé: username=manager, pwd=manager123")

elif st.session_state["login_state"]:
    st.sidebar.write(f"Utilisateur connecté: {st.session_state['username']} ({st.session_state['role']})")

    if page == "Bons de Travail":
        st.subheader("Gestion des Bons de Travail")
        bons = read_bons()
        df = pd.DataFrame(bons)
        st.dataframe(df, use_container_width=True)
        st.write("Ajouter / Modifier un bon")
        with st.form("form_bon"):
            code = st.text_input("Code")
            date_val = st.date_input("Date", value=date.today())
            arret_declare_par = st.text_input("Arrêt déclaré par")
            poste_de_charge = st.selectbox("Poste de charge", read_options("options_poste_de_charge"))
            heure_declaration = st.time_input("Heure déclaration")
            machine_arreter = st.text_input("Machine arrêtée")
            heure_debut_intervention = st.time_input("Début intervention")
            heure_fin_intervention = st.time_input("Fin intervention")
            technicien = st.text_input("Technicien")
            description_probleme = st.selectbox("Description problème", read_options("options_description_probleme"))
            action = st.text_area("Action")
            pdr_utilisee = st.text_input("PDR utilisée")
            observation = st.text_area("Observation")
            resultat = st.text_area("Résultat")
            condition_acceptation = st.text_input("Condition d'acceptation")
            dpt_maintenance = st.text_input("Département maintenance")
            dpt_qualite = st.text_input("Département qualité")
            dpt_production = st.text_input("Département production")
            submit = st.form_submit_button("Ajouter / Mettre à jour")
            if submit:
                try:
                    add_bon({
                        "code": code,"date": str(date_val),"arret_declare_par": arret_declare_par,
                        "poste_de_charge": poste_de_charge,"heure_declaration": str(heure_declaration),
                        "machine_arreter": machine_arreter,"heure_debut_intervention": str(heure_debut_intervention),
                        "heure_fin_intervention": str(heure_fin_intervention),"technicien": technicien,
                        "description_probleme": description_probleme,"action": action,"pdr_utilisee": pdr_utilisee,
                        "observation": observation,"resultat": resultat,"condition_acceptation": condition_acceptation,
                        "dpt_maintenance": dpt_maintenance,"dpt_qualite": dpt_qualite,"dpt_production": dpt_production
                    })
                    st.success("Bon ajouté avec succès")
                    st.experimental_rerun()
                except ValueError as e:
                    st.warning(str(e))

    elif page == "PDR":
        st.subheader("Gestion des PDR")
        pdrs = read_pdr()
        df = pd.DataFrame(pdrs)
        st.dataframe(df, use_container_width=True)
        with st.form("form_pdr"):
            code_pdr = st.text_input("Code PDR")
            remplacement = st.text_input("Remplacement")
            nom_composant = st.text_input("Nom composant")
            quantite = st.number_input("Quantité", min_value=0, value=0)
            submit_pdr = st.form_submit_button("Ajouter / Modifier PDR")
            if submit_pdr:
                upsert_pdr({"code": code_pdr, "remplacement": remplacement, "nom_composant": nom_composant, "quantite": quantite})
                st.success("PDR ajouté / modifié")
                st.experimental_rerun()

    elif page == "Pareto":
        st.subheader("Dashboard Pareto")
        bons = read_bons()
        if bons:
            df = pd.DataFrame(bons)
            period = st.selectbox("Période", ["day","week","month"])
            plot_pareto(df, period=period)
        else:
            st.info("Aucun bon enregistré")

    elif page == "Export Excel":
        st.subheader("Exporter les Bons en Excel")
        bons = read_bons()
        if bons:
            excel_bytes = export_bons_to_excel(bons)
            st.download_button("Télécharger Excel", excel_bytes, "bons_travail.xlsx")
        else:
            st.info("Aucun bon à exporter")

    elif page == "Dashboard":
        st.subheader("Tableau de bord")
        st.write("Fonctionnalités futures à implémenter ici...")

else:
    st.warning("Veuillez vous connecter pour accéder à l'application.")
