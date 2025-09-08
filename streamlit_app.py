# app.py
# Work Order Management - Streamlit only (stockage local JSON dans data/)
# !!! ATTENTION : stockage local sur Streamlit Cloud est éphémère (lire l'avertissement dans le code).
#
# Requirements (requirements.txt):
# streamlit
# pandas
# openpyxl
# matplotlib
# pillow
#
# Place images (optional but recommended) in same repo:
# - logo REGAL-PNG.png
# - back_button.png
# - user-icon.png

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

# matplotlib used for Pareto plotting
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

# Initial lists (copiées depuis ton Version_Final)
INITIAL_DESCRIPTIONS = [
    'P.M.I.01-Panne au niveau du capos',"P.M.I.02-problème d'éjecteur de moule",'P.M.I.03-Blocage  moule',
    'P.M.I.04-Problème de tiroir','P.M.I.05-Cassure vis sortie plaque carotte','P.M.I.06-Blocage de la plaque carotte',
    'P.M.I.07-Vis de noyaux endommagé','P.M.I.08-Problème noyau',"P.M.I.09-Problème vis d'injection",'P.M.I.10-Réducteur',
    'P.M.I.11-Roue dentée ','P.M.I.12-PB grenouillère','P.M.I.13-Vis de pied endommagé','P.M.I.14-Colonnes de guidage ',
    "P.M.I.15-Fuite matiére au niveau de la buse d'injection",
    'P.E.I.01-PB capteur ','P.E.I.02-PB galet (fin de course)','P.E.I.03-PB moteur électrique','P.E.I.04-Capteur linéaire',
    'P.E.I.05-Armoire électrique ','P.E.I.06-Écran/tactile',"P.E.I.07-Machine s'allume pas","P.E.I.08-PB d'électrovanne",
    'P.E.I.09-PB connecteur ','P.E.I.10-Système magnétique',
    'P.H.I.01-PB flexible','P.H.I.02-PB raccord','P.H.I.03-PB vérin','P.H.I.04-PB distributeur','P.H.I.05-PB pompe',
    'P.H.I.06-PB filtre','P.H.I.07-PB au niveau huile','P.H.I.08-PB fuite huile','P.H.I.09-PB préchauffage',
    'P.H.I.10-PB lubrification du canalisation de grenouillère',
    'P.P.I.01-PB de pression','P.P.I.02-Remplissage matière ','P.P.I.03-Alimentation matiére ',
    'P.P.I.04-Flexible pneumatique','P.P.I.05-PB raccord',
    'P.T.I.01-PB collier chauffante','P.T.I.02-PB de thermocouple','P.T.I.03-Zone de chauffage en arrêt',
    'P.T.I.04-PB refroidisseur',"P.T.I.05-PB pression d'eau",'P.T.I.06-PB température sécheur',
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
    # bon_travail as list
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
# Data operations
# ---------------------------
def read_bons() -> List[Dict[str, Any]]:
    arr = load_json(FILES["bon_travail"])
    return arr or []

def write_bons(arr: List[Dict[str, Any]]):
    atomic_write(FILES["bon_travail"], arr)

def read_pdr() -> List[Dict[str, Any]]:
    arr = load_json(FILES["liste_pdr"])
    return arr or []

def write_pdr(arr: List[Dict[str, Any]]):
    atomic_write(FILES["liste_pdr"], arr)

def read_users() -> List[Dict[str, Any]]:
    arr = load_json(FILES["users"])
    return arr or []

def write_users(arr: List[Dict[str, Any]]):
    atomic_write(FILES["users"], arr)

def read_options(key: str) -> List[str]:
    arr = load_json(FILES[key])
    return arr or []

def write_options(key: str, arr: List[str]):
    atomic_write(FILES[key], arr)

# ---------------------------
# Helpers: CRUD bon_travail
# ---------------------------
BON_COLUMNS = [
    "code","date","arret_declare_par","poste_de_charge","heure_declaration","machine_arreter",
    "heure_debut_intervention","heure_fin_intervention","technicien","description_probleme",
    "action","pdr_utilisee","observation","resultat","condition_acceptation","dpt_maintenance","dpt_qualite","dpt_production"
]

def get_bon_by_code(code: str) -> Optional[Dict[str, Any]]:
    for r in read_bons():
        if str(r.get("code","")) == str(code):
            return r
    return None

def add_bon(bon: Dict[str, Any]) -> None:
    bons = read_bons()
    if get_bon_by_code(bon.get("code")) is not None:
        raise ValueError("Code déjà présent")
    # assure every column exists
    entry = {k: bon.get(k, "") for k in BON_COLUMNS}
    bons.append(entry)
    write_bons(bons)
    # décrémenter PDR si fourni
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
    for i, r in enumerate(bons):
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
    bons = read_bons()
    bons = [r for r in bons if str(r.get("code","")) != str(code)]
    write_bons(bons)

# ---------------------------
# PDR CRUD
# ---------------------------
PDR_COLUMNS = ["code","remplacement","nom_composant","quantite"]

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
    pdrs = read_pdr()
    pdrs = [p for p in pdrs if str(p.get("code","")).strip() != str(code).strip()]
    write_pdr(pdrs)

# ---------------------------
# Users helpers
# ---------------------------
def get_user(username: str) -> Optional[Dict[str,Any]]:
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
# Pareto plotting helper
# ---------------------------
def plot_pareto(df: pd.DataFrame, period: str = "day", top_n_labels: int = 3):
    # df must contain 'date'
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
    cum = counts.cumsum()
    cum_pct = 100 * cum / total

    # Tracé
    fig, ax1 = plt.subplots(figsize=(10,4))
    x = range(len(counts))
    ax1.bar(x, counts.values, alpha=0.85)
    ax1.set_xticks(x)
    ax1.set_xticklabels(counts.index.tolist(), rotation=45, ha='right', fontsize=9)
    ax1.set_ylabel("Nombre d'interventions")
    ax1.set_xlabel(xlabel)
    ax1.set_title(f"Pareto ({period}) - total = {total}")
    ax1.grid(axis="y", alpha=0.25)

    ax2 = ax1.twinx()
    ax2.plot(x, cum_pct.values, color='red', marker='o')
    ax2.set_ylim(0, 110)
    ax2.set_ylabel("Pourcentage cumulé (%)")
    ax2.axhline(80, color='grey', linestyle='--', alpha=0.6)
    ax2.text(len(counts)-1, 82, "80% threshold", color="grey", ha="right")

    # annotate top
    top = counts.head(top_n_labels)
    for label, val in top.items():
        idx = list(counts.index).index(label)
        pct = val/total*100
        ax1.annotate(f"{val} ({pct:.1f}%)", xy=(idx, val), xytext=(0,7), textcoords="offset points", ha='center', fontsize=9, bbox=dict(boxstyle="round", alpha=0.2))
    st.pyplot(fig)

    st.markdown("**Périodes les plus impactées :**")
    for i, (label, val) in enumerate(top.items(), start=1):
        st.write(f"{i}. **{label}** — {val} interventions — {val/total*100:.1f}%")

# ---------------------------
# Excel export with logo
# ---------------------------
def export_excel(bons: List[Dict[str,Any]]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Bon de travail"

    # insert logo if exists
    logo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo REGAL-PNG.png")
    try:
        if os.path.exists(logo):
            img = XLImage(logo)
            img.anchor = 'A1'
            ws.add_image(img)
            ws.merge_cells('C1:Q4')
            ws['C1'].alignment = Alignment(horizontal='center', vertical='center')
            ws['C1'].font = Font(bold=True, size=16)
    except Exception:
        pass

    start_row = 6
    for col_idx, h in enumerate(BON_COLUMNS, start=1):
        ws.cell(row=start_row, column=col_idx).value = h
        ws.cell(row=start_row, column=col_idx).font = Font(bold=True)
    rownum = start_row + 1
    for r in bons:
        for col_idx, h in enumerate(BON_COLUMNS, start=1):
            ws.cell(row=rownum, column=col_idx).value = r.get(h, "")
        rownum += 1

    bio = io.BytesIO()
    wb.save(bio)
    return bio.getvalue()

# ---------------------------
# UI / Pages
# ---------------------------
# Header image
logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo REGAL-PNG.png")
if os.path.exists(logo_path):
    try:
        st.image(logo_path, width=220)
    except Exception:
        pass

# Session state for user
if "user" not in st.session_state:
    st.session_state.user = None
if "role" not in st.session_state:
    st.session_state.role = None

st.sidebar.title("Connexion")
users = read_users()
if st.session_state.user:
    st.sidebar.success(f"Connecté: {st.session_state.user} ({st.session_state.role})")
    if st.sidebar.button("Se déconnecter"):
        st.session_state.user = None
        st.session_state.role = None
        st.experimental_rerun()
else:
    # Login form
    login_user = st.sidebar.text_input("Nom d'utilisateur", key="login_user")
    login_pwd = st.sidebar.text_input("Mot de passe", key="login_pwd", type="password")
    if st.sidebar.button("Se connecter"):
        u = get_user(login_user)
        if not u or u.get("password_hash") != hash_password(login_pwd):
            st.sidebar.error("Identifiants invalides.")
        else:
            st.session_state.user = u["username"]
            st.session_state.role = u["role"]
            st.sidebar.success(f"Bienvenue {u['username']} ({u['role']})")

    # Create account (manager verification)
    st.sidebar.markdown("---")
    st.sidebar.write("Créer un compte (nécessite validation manager)")
    mgr_name = st.sidebar.text_input("Manager (pour vérif)", key="mgr_name")
    mgr_pwd = st.sidebar.text_input("Manager - mdp", type="password", key="mgr_pwd")
    if st.sidebar.button("Vérifier manager"):
        mgr = get_user(mgr_name)
        if not mgr or mgr.get("password_hash") != hash_password(mgr_pwd) or mgr.get("role") != "manager":
            st.sidebar.error("Vérification échouée.")
        else:
            st.sidebar.success("Manager vérifié — complétez la création.")
            new_user = st.sidebar.text_input("Nouveau utilisateur", key="new_user")
            new_pwd = st.sidebar.text_input("Nouveau mdp", key="new_pwd", type="password")
            new_role = st.sidebar.selectbox("Rôle", ["production","maintenance","qualite","manager"], key="new_role")
            if st.sidebar.button("Créer utilisateur"):
                try:
                    create_user(new_user.strip(), new_pwd, new_role)
                    st.sidebar.success("Utilisateur créé.")
                except Exception as e:
                    st.sidebar.error(str(e))

# If no user exists, provide initial manager creation (one-shot)
if not users:
    st.warning("Aucun utilisateur trouvé — créez un manager initial.")
    with st.form("init_mgr"):
        mgru = st.text_input("Manager username", value="manager")
        mgrp = st.text_input("Manager password", type="password")
        if st.form_submit_button("Créer manager initial"):
            if not mgru or not mgrp:
                st.error("Remplis les champs.")
            else:
                create_user(mgru.strip(), mgrp, "manager")
                st.success("Manager initial créé — connecte-toi.")
                st.experimental_rerun()

# Sidebar menu
menu = st.sidebar.radio("Pages", ["Dashboard","Production","Maintenance","Qualité","Pièces (PDR)","Export Excel"])

# Helper permissions
def allowed(page: str) -> bool:
    role = st.session_state.role
    if role == "manager":
        return True
    if role == "production" and page == "Production":
        return True
    if role == "maintenance" and page == "Maintenance":
        return True
    if role == "qualite" and page == "Qualité":
        return True
    return False

# Dashboard
def page_dashboard():
    st.header("Tableau de bord — Pareto & résumé")
    bons = read_bons()
    if not bons:
        st.info("Aucun bon enregistré.")
        return
    df = pd.DataFrame(bons)
    c1, c2 = st.columns([3,1])
    period = c1.selectbox("Période pour Pareto", ["day","week","month"])
    topn = c2.number_input("Top N", min_value=1, max_value=10, value=3)
    plot_pareto(df, period=period, top_n_labels=topn)
    st.markdown("---")
    st.subheader("Aperçu (derniers d'abord)")
    st.dataframe(df.sort_values(by="date", ascending=False), height=320)

# --------------------------
# Page: Bons (production/maintenance/qualité)
# --------------------------
def page_bons(page_name: str):
    st.header(f"{page_name} — Gestion des bons")
    if not allowed(page_name):
        st.warning("Vous n'avez pas la permission pour cette page.")
        return

    bons = read_bons()
    df = pd.DataFrame(bons) if bons else pd.DataFrame(columns=BON_COLUMNS)
    codes = df["code"].astype(str).tolist() if not df.empty else []

    st.subheader("Charger / Nouveau")
    col_load1, col_load2 = st.columns([3,1])
    sel_code = col_load1.selectbox("Charger un bon existant (optionnel)", options=[""] + codes, key=f"sel_{page_name}")
    if col_load2.button("Charger") and sel_code:
        bon = get_bon_by_code(sel_code)
        if bon:
            load_bon_into_session(bon)
            st.experimental_rerun()
    if col_load2.button("Nouveau"):
        clear_form_session()
        st.experimental_rerun()

    # --------------------------
    # Définition des champs éditables par fenêtre
    # --------------------------
    # Champs autorisés (editable) selon la demande :
    production_allowed = {
        "code", "heure_declaration", "description_probleme", "arret_declare_par",
        "poste_de_charge", "machine_arreter", "resultat", "condition_acceptation", "dpt_production"
    }
    maintenance_allowed = {
        "heure_debut_intervention", "heure_fin_intervention", "technicien", "observation", "dpt_maintenance"
    }
    qualite_allowed = {
        "heure_debut_intervention", "heure_fin_intervention", "technicien", "observation", "dpt_qualite"
    }

    if page_name.lower().startswith("production"):
        editable_set = production_allowed
    elif page_name.lower().startswith("maintenance"):
        editable_set = maintenance_allowed
    elif page_name.lower().startswith("qualit") or page_name.lower().startswith("qualité"):
        editable_set = qualite_allowed
    else:
        editable_set = set()  # par défaut tout grisé

    # Initialiser session state pour le formulaire si pas présent
    for k in BON_COLUMNS:
        sk = f"form_{k}"
        if sk not in st.session_state:
            st.session_state[sk] = ""

    # --------------------------
    # Le formulaire
    # --------------------------
    with st.form("form_bon", clear_on_submit=False):
        c1,c2,c3 = st.columns(3)

        # Code
        code_val = st.session_state.get("form_code","")
        code = c1.text_input("Code", value=code_val, disabled=("code" not in editable_set))

        # Date
        date_default = st.session_state.get("form_date", date.today().strftime("%Y-%m-%d"))
        try:
            # convert to date for date_input default
            default_date_obj = datetime.strptime(date_default, "%Y-%m-%d").date()
        except Exception:
            default_date_obj = date.today()
        date_input = c1.date_input("Date", value=default_date_obj, disabled=("date" not in editable_set))

        # Arrêt déclaré par
        arret_val = st.session_state.get("form_arret_declare_par","")
        arret = c1.text_input("Arrêt déclaré par", value=arret_val, disabled=("arret_declare_par" not in editable_set))

        # Poste de charge
        postes = read_options("options_poste_de_charge")
        poste_default = st.session_state.get("form_poste_de_charge","")
        if "poste_de_charge" in editable_set:
            poste = c2.selectbox("Poste de charge", [""] + postes + ["Autres..."], index=( [""] + postes + ["Autres..."]).index(poste_default) if poste_default in ([""]+postes+["Autres..."]) else 0)
            if poste == "Autres...":
                new_poste = c2.text_input("Ajouter nouveau poste")
                if new_poste:
                    opts = read_options("options_poste_de_charge")
                    opts.append(new_poste.strip())
                    write_options("options_poste_de_charge", opts)
                    poste = new_poste.strip()
        else:
            # lecture seule -> afficher valeur (si vide afficher '')
            c2.selectbox("Poste de charge", [""] + postes, index=([""]+postes).index(poste_default) if poste_default in ([""]+postes) else 0, disabled=True)
            poste = poste_default

        # Heure de déclaration
        heure_decl_val = st.session_state.get("form_heure_declaration","")
        heure_declaration = c2.text_input("Heure de déclaration", value=heure_decl_val, disabled=("heure_declaration" not in editable_set))

        # Machine arrêtée?
        machine_val = st.session_state.get("form_machine_arreter","")
        machine = c2.selectbox("Machine arrêtée?", ["","Oui","Non"], index=(["","Oui","Non"].index(machine_val) if machine_val in ["","Oui","Non"] else 0), disabled=("machine_arreter" not in editable_set))

        # Heures intervention
        debut_val = st.session_state.get("form_heure_debut_intervention","")
        debut = c3.text_input("Heure début", value=debut_val, disabled=("heure_debut_intervention" not in editable_set))
        fin_val = st.session_state.get("form_heure_fin_intervention","")
        fin = c3.text_input("Heure fin", value=fin_val, disabled=("heure_fin_intervention" not in editable_set))

        # Technicien
        techn_val = st.session_state.get("form_technicien","")
        technicien = c3.text_input("Technicien", value=techn_val, disabled=("technicien" not in editable_set))

        # Description problème
        descs = read_options("options_description_probleme")
        desc_default = st.session_state.get("form_description_probleme","")
        if "description_probleme" in editable_set:
            description = st.selectbox("Description", [""] + descs + ["Autres..."], index=([""]+descs+["Autres..."]).index(desc_default) if desc_default in ([""]+descs+["Autres..."]) else 0)
            if description == "Autres...":
                new_desc = st.text_input("Ajouter nouvelle description")
                if new_desc:
                    optsd = read_options("options_description_probleme")
                    optsd.append(new_desc.strip())
                    write_options("options_description_probleme", optsd)
                    description = new_desc.strip()
        else:
            # lecture seule
            st.selectbox("Description", [""] + descs, index=([""]+descs).index(desc_default) if desc_default in ([""]+descs) else 0, disabled=True)
            description = desc_default

        # Action
        action_val = st.session_state.get("form_action","")
        action = st.text_input("Action", value=action_val, disabled=("action" not in editable_set))

        # PDR utilisée
        pdr_val = st.session_state.get("form_pdr_utilisee","")
        pdr_used = st.text_input("PDR utilisée (code)", value=pdr_val, disabled=("pdr_utilisee" not in editable_set))

        # Observation
        obs_val = st.session_state.get("form_observation","")
        observation = st.text_input("Observation", value=obs_val, disabled=("observation" not in editable_set))

        # Résultat
        result_val = st.session_state.get("form_resultat","")
        resultat = st.selectbox("Résultat", ["","Accepter","Refuser","Accepter avec condition"], index=(["","Accepter","Refuser","Accepter avec condition"].index(result_val) if result_val in ["","Accepter","Refuser","Accepter avec condition"] else 0), disabled=("resultat" not in editable_set))

        # Condition d'acceptation
        cond_val = st.session_state.get("form_condition_acceptation","")
        cond = st.text_input("Condition d'acceptation", value=cond_val, disabled=("condition_acceptation" not in editable_set))

        # Dpts
        dpt_m_val = st.session_state.get("form_dpt_maintenance","")
        dpt_m = st.selectbox("Dpt Maintenance", ["","Valider","Non Valider"], index=(["","Valider","Non Valider"].index(dpt_m_val) if dpt_m_val in ["","Valider","Non Valider"] else 0), disabled=("dpt_maintenance" not in editable_set))
        dpt_q_val = st.session_state.get("form_dpt_qualite","")
        dpt_q = st.selectbox("Dpt Qualité", ["","Valider","Non Valider"], index=(["","Valider","Non Valider"].index(dpt_q_val) if dpt_q_val in ["","Valider","Non Valider"] else 0), disabled=("dpt_qualite" not in editable_set))
        dpt_p_val = st.session_state.get("form_dpt_production","")
        dpt_p = st.selectbox("Dpt Production", ["","Valider","Non Valider"], index=(["","Valider","Non Valider"].index(dpt_p_val) if dpt_p_val in ["","Valider","Non Valider"] else 0), disabled=("dpt_production" not in editable_set))

        submitted = st.form_submit_button("Ajouter / Mettre à jour")

        if submitted:
            code_v = code.strip()
            date_v = date_input.strftime("%Y-%m-%d")
            row = {k: "" for k in BON_COLUMNS}
            row.update({
                "code": code_v,
                "date": date_v,
                "arret_declare_par": arret,
                "poste_de_charge": poste,
                "heure_declaration": heure_declaration,
                "machine_arreter": machine,
                "heure_debut_intervention": debut,
                "heure_fin_intervention": fin,
                "technicien": technicien,
                "description_probleme": description,
                "action": action,
                "pdr_utilisee": pdr_used,
                "observation": observation,
                "resultat": resultat,
                "condition_acceptation": cond,
                "dpt_maintenance": dpt_m,
                "dpt_qualite": dpt_q,
                "dpt_production": dpt_p
            })
            try:
                if code_v == "":
                    st.error("Le champ Code est requis pour ajouter ou mettre à jour un bon.")
                else:
                    if any(c.get("code","") == code_v for c in read_bons()):
                        update_bon(code_v, row)
                        st.success("Bon mis à jour.")
                    else:
                        add_bon(row)
                        st.success("Bon ajouté.")
                    # mise à jour session pour garder valeurs visibles
                    load_bon_into_session(row)
                    st.experimental_rerun()
            except Exception as e:
                st.error(str(e))

    # --------------------------
    # Recherche & Liste
    # --------------------------
    st.markdown("---")
    st.subheader("Recherche & Liste")
    search_by = st.selectbox("Rechercher par", ["Code","Date","Poste de charge","Dpt"])
    term = st.text_input("Terme de recherche", key=f"search_{page_name}")
    if st.button("Rechercher", key=f"btn_search_{page_name}"):
        res = []
        for r in read_bons():
            col = ""
            if search_by == "Code":
                col = r.get("code","")
            elif search_by == "Date":
                col = r.get("date","")
            elif search_by == "Poste de charge":
                col = r.get("poste_de_charge","")
            else:
                col = r.get("dpt_production","") + r.get("dpt_maintenance","") + r.get("dpt_qualite","")
            if term.lower() in str(col).lower():
                res.append(r)
        if not res:
            st.info("Aucun enregistrement trouvé.")
        else:
            st.dataframe(pd.DataFrame(res), height=250)

    st.subheader("Tous les bons")
    all_df = pd.DataFrame(read_bons())
    if not all_df.empty:
        st.dataframe(all_df.sort_values(by="date", ascending=False), height=300)
        sel = st.selectbox("Sélectionner un code", options=[""] + all_df["code"].astype(str).tolist(), key=f"sel2_{page_name}")
        if sel:
            if st.button("Afficher JSON", key=f"showjson_{page_name}"):
                st.json(get_bon_by_code(sel))
            if st.button("Supprimer", key=f"del_{page_name}"):
                delete_bon(sel)
                st.success("Supprimé")
                st.experimental_rerun()
    else:
        st.info("Aucun bon à afficher.")

    st.markdown("---")
    st.subheader("Recherche & Liste")
    search_by = st.selectbox("Rechercher par", ["Code","Date","Poste de charge","Dpt"])
    term = st.text_input("Terme de recherche")
    if st.button("Rechercher"):
        res = []
        for r in read_bons():
            col = None
            if search_by == "Code":
                col = r.get("code","")
            elif search_by == "Date":
                col = r.get("date","")
            elif search_by == "Poste de charge":
                col = r.get("poste_de_charge","")
            else:
                col = r.get("dpt_production","") + r.get("dpt_maintenance","") + r.get("dpt_qualite","")
            if term.lower() in str(col).lower():
                res.append(r)
        if not res:
            st.info("Aucun enregistrement trouvé.")
        else:
            st.dataframe(pd.DataFrame(res), height=250)

    st.subheader("Tous les bons")
    all_df = pd.DataFrame(read_bons())
    if not all_df.empty:
        st.dataframe(all_df.sort_values(by="date", ascending=False), height=300)
        sel = st.selectbox("Sélectionner un code", options=[""] + all_df["code"].astype(str).tolist())
        if sel:
            if st.button("Afficher JSON"):
                st.json(get_bon_by_code(sel))
            if st.button("Supprimer"):
                delete_bon(sel)
                st.success("Supprimé")
                st.experimental_rerun()
    else:
        st.info("Aucun bon à afficher.")

# PDR page
def page_pdr():
    st.header("Pièces - PDR (liste_pdr)")
    pdrs = read_pdr()
    df = pd.DataFrame(pdrs) if pdrs else pd.DataFrame(columns=PDR_COLUMNS)
    st.dataframe(df, height=250)
    with st.form("form_pdr"):
        code = st.text_input("Code PDR")
        remplacement = st.text_input("Remplacement")
        nom = st.text_input("Nom composant")
        quantite = st.number_input("Quantité", min_value=0, value=0)
        if st.form_submit_button("Enregistrer PDR"):
            try:
                upsert_pdr({"code": code, "remplacement": remplacement, "nom_composant": nom, "quantite": int(quantite)})
                st.success("PDR enregistrée.")
                st.experimental_rerun()
            except Exception as e:
                st.error(str(e))
    delcode = st.text_input("Code à supprimer")
    if st.button("Supprimer PDR"):
        delete_pdr_by_code(delcode.strip())
        st.success("PDR supprimée.")
        st.experimental_rerun()

# Export page
def page_export():
    st.header("Export Excel")
    bons = read_bons()
    if not bons:
        st.info("Aucun bon à exporter.")
        return
    if st.button("Générer & télécharger Excel"):
        try:
            excel_bytes = export_excel(bons)
            st.download_button("Télécharger bon_travail_export.xlsx", data=excel_bytes, file_name="bon_travail_export.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        except Exception as e:
            st.error(str(e))

# Router
if menu == "Dashboard":
    page_dashboard()
elif menu == "Production":
    page_bons("Production")
elif menu == "Maintenance":
    page_bons("Maintenance")
elif menu == "Qualité":
    page_bons("Qualité")
elif menu == "Pièces (PDR)":
    page_pdr()
elif menu == "Export Excel":
    page_export()

# Footer
st.sidebar.markdown("---")
st.sidebar.caption("⚠️ Données stockées localement sur l'instance Streamlit. Elles peuvent disparaître après redémarrage/redeploy.")
