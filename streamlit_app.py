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

st.title("Work Order Management")

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

#===========================================================================================

# Initialisation de l'état de session
if "user" not in st.session_state:
    st.session_state.user = None
    st.session_state.role = None

# Si l'utilisateur est déjà connecté, proposer de se déconnecter
if st.session_state.user:
    st.sidebar.write(f"Connecté en tant que **{st.session_state.user}** ({st.session_state.role})")
    if st.sidebar.button("Se déconnecter"):
        st.session_state.user = None
        st.session_state.role = None
        st.rerun()  # Remplace st.experimental_rerun()

else:
    # Formulaire de connexion
    st.sidebar.header("Connexion")
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

# Création de compte (après vérification du manager)
st.sidebar.markdown("---")
st.sidebar.write("Créer un compte (nécessite vérification manager)")

mgr_name = st.sidebar.text_input("Manager (username)", key="mgr_name")
mgr_pwd = st.sidebar.text_input("Manager (mdp)", key="mgr_pwd", type="password")

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

# Si aucun utilisateur (premier lancement), création manager initial
users = read_users()
if not users:
    st.warning("Aucun utilisateur trouvé — créez un manager initial.")
    with st.form("init_mgr"):
        mgru = st.text_input("Manager username", value="manager")
        mgrp = st.text_input("Manager password", type="password")
        if st.form_submit_button("Créer manager initial"):
            if not mgru or not mgrp:
                st.error("Remplissez les champs.")
            else:
                create_user(mgru.strip(), mgrp, "manager")
                st.success("Manager initial créé — connectez-vous.")
                st.rerun()
#==============================================================================================================

# Menu latéral pour naviguer entre les pages
st.sidebar.markdown("---")
menu = st.sidebar.radio("Pages", ["Dashboard", "Production", "Maintenance", "Qualité", "Pièces (PDR)", "Export Excel"])
#==============================================================================================================

def page_dashboard():
    st.header("Tableau de bord — Pareto & résumé")
    bons = read_bons()
    if not bons:
        st.info("Aucun bon enregistré.")
        return
    df = pd.DataFrame(bons)
    c1, c2 = st.columns([3, 1])
    period = c1.selectbox("Période pour Pareto", ["day", "week", "month"])
    topn = c2.number_input("Top N", min_value=1, max_value=10, value=3)
    # Génère et affiche le Pareto en utilisant matplotlib
    plot_pareto(df, period=period, top_n_labels=topn)
    st.markdown("---")
    st.subheader("Aperçu (derniers d'abord)")
    st.dataframe(df.sort_values(by="date", ascending=False), height=320)
#==========================================================================================================================

# Fonction utilitaire de permission
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

def page_bons(page_name: str):
    st.header(f"{page_name} — Gestion des bons")
    if not allowed(page_name):
        st.warning("Vous n'avez pas la permission pour cette page.")
        return

    bons = read_bons()
    df = pd.DataFrame(bons) if bons else pd.DataFrame(columns=BON_COLUMNS)
    codes = df["code"].astype(str).tolist() if not df.empty else []

    st.subheader("Charger / Nouveau")
    col_load1, col_load2 = st.columns([3, 1])
    sel_code = col_load1.selectbox("Charger un bon existant (optionnel)",
                                   options=[""] + codes, key=f"sel_{page_name}")
    if col_load2.button("Charger") and sel_code:
        bon = get_bon_by_code(sel_code)
        if bon:
            # Charger dans st.session_state
            for k, v in bon.items():
                st.session_state[f"form_{k}"] = v
            st.rerun()
    if col_load2.button("Nouveau"):
        # Réinitialiser le formulaire
        for k in BON_COLUMNS:
            st.session_state[f"form_{k}"] = ""
        st.rerun()

    # Création ou modification d'un bon
    st.subheader("Bon de travail")
    with st.form(f"bon_form_{page_name}", clear_on_submit=False):
        st.text_input("Code du bon", key="form_code")
        st.date_input("Date", key="form_date")
        st.text_input("Déclaré par (arrêt déclaré par)", key="form_arret_declare_par")
        st.selectbox("Poste de charge", options=read_json(FILES["options_poste_de_charge"]),
                     key="form_poste_de_charge")
        st.number_input("Heure de déclaration", min_value=0, max_value=24, step=1, key="form_heure_declaration")
        st.text_input("Machine arrêtée", key="form_machine_arreter")
        st.selectbox("Description problème", options=read_json(FILES["options_description_probleme"]),
                     key="form_description_probleme")
        st.text_input("Département production", key="form_dpt_production")
        st.text_input("PDR utilisée (code)", key="form_pdr_utilisee")
        st.selectbox("Résultat", options=["Réparé", "BKO", "Aucune action"], key="form_resultat")
        st.selectbox("Condition d'acceptation", options=["Réparé", "BKO", "Aucune action"], key="form_condition_acceptation")
        submitted = st.form_submit_button("Enregistrer bon")
        if submitted:
            try:
                bon_data = {k[5:]: st.session_state[k] for k in st.session_state if k.startswith("form_")}
                if get_bon_by_code(bon_data["code"]):
                    update_bon(bon_data["code"], bon_data)
                    st.success("Bon mis à jour.")
                else:
                    add_bon(bon_data)
                    st.success("Nouveau bon créé.")
            except Exception as e:
                st.error(str(e))
#=======================================================================================================================

def page_pdr():
    st.header("Gestion des pièces de rechange (PDR)")
    pdrs = read_pdr()
    df_pdr = pd.DataFrame(pdrs) if pdrs else pd.DataFrame(columns=PDR_COLUMNS)
    codes = df_pdr["code"].astype(str).tolist() if not df_pdr.empty else []

    st.subheader("Ajouter / Modifier une pièce")
    with st.form("pdr_form"):
        code = st.text_input("Code", key="pdr_code")
        remplacement = st.text_input("Remplacement", key="pdr_remplacement")
        nom = st.text_input("Nom du composant", key="pdr_nom_composant")
        quantite = st.number_input("Quantité", min_value=0, value=0, key="pdr_quantite")
        submitted_pdr = st.form_submit_button("Enregistrer PDR")
        if submitted_pdr:
            try:
                upsert_pdr({
                    "code": code,
                    "remplacement": remplacement,
                    "nom_composant": nom,
                    "quantite": quantite
                })
                st.success("PDR enregistrée.")
            except Exception as e:
                st.error(str(e))

    st.subheader("Liste des pièces")
    if df_pdr.empty:
        st.info("Aucune pièce de rechange enregistrée.")
    else:
        st.dataframe(df_pdr, height=200)
    # Suppression d'une pièce
    st.subheader("Supprimer une pièce")
    code_suppr = st.selectbox("Sélectionner le code à supprimer", options=[""] + codes)
    if st.button("Supprimer"):
        if code_suppr:
            delete_pdr_by_code(code_suppr)
            st.success(f"PDR {code_suppr} supprimée.")
            st.rerun()
#==========================================================================================================

def page_export():
    st.header("Export Excel des bons")
    bons = read_bons()
    if not bons:
        st.info("Aucun bon à exporter.")
        return
    try:
        excel_bytes = export_excel(bons)
        st.download_button("Télécharger bon_travail_export.xlsx",
                           data=excel_bytes,
                           file_name="bon_travail_export.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        st.error(str(e))
#========================================================================================================

# Affichage de la page active selon le menu
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

# Footer / note de bas de page
st.sidebar.markdown("---")
st.sidebar.caption("⚠️ Données stockées localement sur l'instance Streamlit. Elles peuvent disparaître après redémarrage/redeploy.")
#======================================================================================================================================
