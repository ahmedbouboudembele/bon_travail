# ====================================================
# Work Order Management - Version finale (corrigée)
# ====================================================
import os
import json
import hashlib
from datetime import datetime, date
from typing import List, Dict, Any, Optional

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# ====================================================
# CONFIGURATION
# ====================================================
st.set_page_config(page_title="Work Order Management", layout="wide")

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)

FILES = {
    "bon_travail": os.path.join(DATA_DIR, "bon_travail.json"),
    "users": os.path.join(DATA_DIR, "users.json"),
    "options_description_probleme": os.path.join(DATA_DIR, "options_description_probleme.json"),
    "options_poste_de_charge": os.path.join(DATA_DIR, "options_poste_de_charge.json"),
}

INITIAL_DESCRIPTIONS = [
    "P.M.I.01-Panne au niveau du capos","P.M.I.02-problème d'éjecteur de moule","P.M.I.03-Blocage moule",
    "P.M.I.04-Problème de tiroir","P.M.I.05-Cassure vis sortie plaque carotte","P.M.I.06-Blocage de la plaque carotte",
    "P.M.I.07-Vis de noyaux endommagé","P.M.I.08-Problème noyau","P.M.I.09-Problème vis d'injection","P.M.I.10-Réducteur",
    "P.M.I.11-Roue dentée","P.M.I.12-PB grenouillère","P.M.I.13-Vis de pied endommagé","P.M.I.14-Colonnes de guidage",
    "P.M.I.15-Fuite matière au niveau de la buse d'injection",
    "P.E.I.01-PB capteur","P.E.I.02-PB galet (fin de course)","P.E.I.03-PB moteur électrique","P.E.I.04-Capteur linéaire",
    "P.E.I.05-Armoire électrique","P.E.I.06-Écran/tactile","P.E.I.07-Machine s'allume pas","P.E.I.08-PB d'électrovanne",
    "P.E.I.09-PB connecteur","P.E.I.10-Système magnétique",
]

INITIAL_POSTES = ["ASL011","ASL021","ASL031","ASL041","ASL051","ASL061","ASL071"]

# ====================================================
# UTILITAIRES
# ====================================================
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
    if load_json(FILES["bon_travail"]) is None:
        atomic_write(FILES["bon_travail"], [])
    if load_json(FILES["users"]) is None:
        atomic_write(FILES["users"], [])
    if load_json(FILES["options_description_probleme"]) is None:
        atomic_write(FILES["options_description_probleme"], INITIAL_DESCRIPTIONS)
    if load_json(FILES["options_poste_de_charge"]) is None:
        atomic_write(FILES["options_poste_de_charge"], INITIAL_POSTES)

ensure_data_files()

def hash_password(pwd: str) -> str:
    return hashlib.sha256((pwd or "").encode("utf-8")).hexdigest()

# ====================================================
# DONNÉES
# ====================================================
BON_COLUMNS = [
    "code","date","arret_declare_par","poste_de_charge","heure_declaration","machine_arreter",
    "heure_debut_intervention","heure_fin_intervention","technicien","description_probleme",
    "action","pdr_utilisee","observation","resultat","condition_acceptation",
    "dpt_maintenance","dpt_qualite","dpt_production"
]

def read_bons() -> List[Dict[str, Any]]:
    return load_json(FILES["bon_travail"]) or []

def write_bons(arr: List[Dict[str, Any]]):
    atomic_write(FILES["bon_travail"], arr)

def get_bon_by_code(code: str) -> Optional[Dict[str, Any]]:
    for r in read_bons():
        if str(r.get("code","")) == str(code):
            return r
    return None

def add_bon(bon: Dict[str, Any]) -> None:
    bons = read_bons()
    entry = {k: bon.get(k, "") for k in BON_COLUMNS}
    bons.append(entry)
    write_bons(bons)

def update_bon(code: str, updates: Dict[str, Any]) -> None:
    bons = read_bons()
    for i, r in enumerate(bons):
        if str(r.get("code","")) == str(code):
            for k in BON_COLUMNS:
                if k in updates:
                    r[k] = updates[k]
            bons[i] = r
            break
    write_bons(bons)

def delete_bon(code: str) -> None:
    bons = read_bons()
    bons = [r for r in bons if str(r.get("code","")) != str(code)]
    write_bons(bons)

# USERS
def read_users() -> List[Dict[str, Any]]:
    return load_json(FILES["users"]) or []

def write_users(arr: List[Dict[str, Any]]):
    atomic_write(FILES["users"], arr)

def get_user(username: str) -> Optional[Dict[str,Any]]:
    for u in read_users():
        if u.get("username","") == username:
            return u
    return None

def create_user(username: str, password: str, role: str):
    users = read_users()
    if get_user(username):
        raise ValueError("Utilisateur existe déjà")
    users.append({"username": username, "password_hash": hash_password(password), "role": role})
    write_users(users)

# ====================================================
# PARETO
# ====================================================
def plot_pareto(df: pd.DataFrame, period: str = "day", top_n_labels: int = 3):
    s = pd.to_datetime(df['date'], errors='coerce').dropna()
    if s.empty:
        st.info("Aucune date valide.")
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
    cum_pct = 100 * counts.cumsum() / total

    fig, ax1 = plt.subplots(figsize=(10,4))
    x = range(len(counts))
    ax1.bar(x, counts.values, color="#1f77b4", alpha=0.85)
    ax1.set_xticks(x)
    ax1.set_xticklabels(counts.index.tolist(), rotation=45, ha='right', fontsize=9)
    ax1.set_ylabel("Nombre d'interventions")
    ax1.set_xlabel(xlabel)
    ax1.set_title(f"Pareto ({period})", color="#1f77b4")

    ax2 = ax1.twinx()
    ax2.plot(x, cum_pct.values, color='#ff7f0e', marker='o')
    ax2.set_ylim(0, 110)
    ax2.set_ylabel("Pourcentage cumulé (%)")

    st.pyplot(fig)

# ====================================================
# LOGIN TEMPLATE
# ====================================================
def show_login_card():
    st.markdown(
        """
        <style>
        .login-card {
            background-color: #f0f2f6;
            padding: 2em;
            border-radius: 15px;
            box-shadow: 2px 2px 10px rgba(0,0,0,0.2);
            text-align: center;
        }
        </style>
        """, unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.subheader("🔑 Connexion")
        username = st.text_input("Nom d'utilisateur", key="login_user")
        pwd = st.text_input("Mot de passe", type="password", key="login_pwd")
        if st.button("Se connecter", key="login_btn_main"):
            u = get_user(username)
            if not u or u.get("password_hash") != hash_password(pwd):
                st.error("Identifiants invalides.")
            else:
                st.session_state.user = u["username"]
                st.session_state.role = u["role"]
                st.success(f"Bienvenue {u['username']} — ({u['role']})")
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ====================================================
# PAGES
# ====================================================
def page_dashboard():
    st.header("📊 Tableau de bord")
    bons = read_bons()
    if not bons:
        st.info("Aucun bon enregistré.")
        return
    df = pd.DataFrame(bons)
    c1, c2 = st.columns([3,1])
    period = c1.selectbox("Période", ["day","week","month"])
    topn = c2.number_input("Top N", min_value=1, max_value=10, value=3)
    plot_pareto(df, period=period, top_n_labels=topn)
    st.markdown("---")
    st.subheader("Aperçu")
    st.dataframe(df.sort_values(by="date", ascending=False), height=300)

# ====================================================
# MAIN
# ====================================================
if "user" not in st.session_state:
    st.session_state.user = None
if "role" not in st.session_state:
    st.session_state.role = None

if not read_users():
    st.warning("Aucun utilisateur trouvé — créez un manager initial.")
    with st.form("init_mgr"):
        mgru = st.text_input("Nom Manager")
        mgrp = st.text_input("Mot de passe", type="password")
        if st.form_submit_button("Créer"):
            create_user(mgru.strip(), mgrp, "manager")
            st.success("Manager créé.")
            st.rerun()

if not st.session_state.user:
    show_login_card()
else:
    menu = st.sidebar.radio("Menu", ["Dashboard","Production","Maintenance","Qualité"])
    if menu == "Dashboard":
        page_dashboard()
    elif menu == "Production":
        st.info("👉 Fenêtre Production (formulaire bons)")
    elif menu == "Maintenance":
        st.info("👉 Fenêtre Maintenance (formulaire bons)")
    elif menu == "Qualité":
        st.info("👉 Fenêtre Qualité (formulaire bons)")

