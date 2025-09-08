# app.py
# Version corrigée / esthétique — fidèle à la "Version final"
import os
import json
import io
import hashlib
from datetime import datetime, date
from typing import List, Dict, Any, Optional

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from openpyxl.drawing.image import Image as XLImage

# ---------------------------
# Configuration & constantes
# ---------------------------
st.set_page_config(page_title="Work Order Management", layout="wide")
# small CSS for nicer cards / headers
st.markdown(
    """
    <style>
    .app-header {padding:10px 12px; border-radius:10px; color: white; margin-bottom:10px;}
    .card {background: #ffffff; padding:12px; border-radius:10px; box-shadow: 0 6px 18px rgba(0,0,0,0.06); margin-bottom:12px;}
    .small-muted {color: #6c757d; font-size:12px;}
    .center {display:flex; align-items:center; justify-content:center;}
    </style>
    """,
    unsafe_allow_html=True,
)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)

FILES = {
    "bon_travail": os.path.join(DATA_DIR, "bon_travail.json"),
    "liste_pdr": os.path.join(DATA_DIR, "liste_pdr.json"),
    "users": os.path.join(DATA_DIR, "users.json"),
    "options_description_probleme": os.path.join(DATA_DIR, "options_description_probleme.json"),
    "options_poste_de_charge": os.path.join(DATA_DIR, "options_poste_de_charge.json"),
}

# initial lists (copiées depuis ta version)
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

BON_COLUMNS = [
    "code","date","arret_declare_par","poste_de_charge","heure_declaration","machine_arreter",
    "heure_debut_intervention","heure_fin_intervention","technicien","description_probleme",
    "action","pdr_utilisee","observation","resultat","condition_acceptation","dpt_maintenance","dpt_qualite","dpt_production"
]

# UI palettes (used for headers & pareto)
PAGE_PALETTES = {
    "Production": ("#0d6efd","#6f42c1"),
    "Maintenance": ("#fd7e14","#dc3545"),
    "Qualité": ("#198754","#20c997"),
    "default": ("#6c757d","#adb5bd")
}

# ---------------------------
# File helpers
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
# Auth helpers
# ---------------------------
def hash_password(pwd: str) -> str:
    return hashlib.sha256((pwd or "").encode("utf-8")).hexdigest()

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
# Bons CRUD & PDR helpers (unchanged)
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

def read_options(key: str) -> List[str]:
    arr = load_json(FILES[key])
    return arr or []

def write_options(key: str, arr: List[str]):
    atomic_write(FILES[key], arr)

def get_bon_by_code(code: str) -> Optional[Dict[str, Any]]:
    for r in read_bons():
        if str(r.get("code","")) == str(code):
            return r
    return None

def add_bon(bon: Dict[str, Any]) -> None:
    bons = read_bons()
    if get_bon_by_code(bon.get("code")) is not None:
        raise ValueError("Code déjà présent")
    entry = {k: bon.get(k, "") for k in BON_COLUMNS}
    bons.append(entry)
    write_bons(bons)
    # PDR decrement logic preserved (even if no PDR page)
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
# Session helpers for form values (page-scoped keys)
# ---------------------------
def load_bon_into_session(bon: Dict[str, Any], page_name: str):
    """Charge un bon dans st.session_state en préfixant par page_name."""
    for k in BON_COLUMNS:
        st.session_state[f"{page_name}_form_{k}"] = bon.get(k, "")

def clear_form_session(page_name: str):
    for k in BON_COLUMNS:
        st.session_state[f"{page_name}_form_{k}"] = ""

# ---------------------------
# Pareto plotting (improved aesthetics)
# ---------------------------
def plot_pareto(df: pd.DataFrame, period: str = "day", top_n_labels: int = 3, palette=("navy","purple")):
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
    if total == 0:
        st.info("Pas assez de données.")
        return
    cum_pct = 100 * counts.cumsum() / total

    # color gradient using viridis
    cmap = plt.get_cmap("viridis")
    colors = cmap(np.linspace(0.15, 0.85, len(counts)))

    fig, ax1 = plt.subplots(figsize=(10,4))
    fig.patch.set_facecolor("#f8fafc")
    ax1.set_facecolor("#ffffff")

    x = np.arange(len(counts))
    bars = ax1.bar(x, counts.values, color=colors, edgecolor="#2b2b2b", linewidth=0.2)
    ax1.set_xticks(x)
    ax1.set_xticklabels(counts.index.tolist(), rotation=45, ha='right', fontsize=9)
    ax1.set_ylabel("Nombre d'interventions")
    ax1.set_xlabel(xlabel)
    ax1.set_title(f"Pareto ({period}) — total = {total}", fontsize=12, weight="bold")
    ax1.grid(axis="y", alpha=0.12)

    ax2 = ax1.twinx()
    ax2.plot(x, cum_pct.values, color=palette[1], marker='o', linewidth=2)
    ax2.set_ylim(0, 110)
    ax2.set_ylabel("Pourcentage cumulé (%)", color=palette[1])
    ax2.tick_params(axis='y', labelcolor=palette[1])
    ax2.axhline(80, color='grey', linestyle='--', alpha=0.6)

    # annotate top N bars
    top = counts.head(top_n_labels)
    for idx, (label, val) in enumerate(counts.items()):
        if idx < top_n_labels:
            pct = val/total*100
            ax1.text(idx, val + max(counts.values)*0.02, f"{val} ({pct:.1f}%)", ha='center', fontsize=9, bbox=dict(boxstyle="round", alpha=0.2))

    plt.tight_layout()
    st.pyplot(fig)

    st.markdown("**Périodes les plus impactées :**")
    for i, (label, val) in enumerate(top.items(), start=1):
        st.write(f"{i}. **{label}** — {val} interventions — {val/total*100:.1f}%")

# ---------------------------
# Small Excel exporter (kept but no UI page)
# ---------------------------
def export_excel(bons: List[Dict[str,Any]]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Bon de travail"
    start_row = 1
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
# UI: login (central card) + main menu (visible après connexion)
# ---------------------------
# Load logo if available
logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo REGAL-PNG.png")
def show_login_card():
    st.markdown('<div class="center">', unsafe_allow_html=True)
    col1, col2 = st.columns([1,2], gap="large")
    with col1:
        if os.path.exists(logo_path):
            st.image(logo_path, width=160)
        else:
            st.markdown("<h3>Work Order</h3>", unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<h3 style="margin:4px 0 2px 0">Connexion</h3>', unsafe_allow_html=True)
        st.markdown('<div class="small-muted">Entrez vos identifiants pour accéder à l’application</div>', unsafe_allow_html=True)
        username = st.text_input("Nom d'utilisateur", key="login_user_main")
        pwd = st.text_input("Mot de passe", type="password", key="login_pwd_main")
        if st.button("Se connecter", key="login_btn_main"):
            u = get_user(username)
            if not u or u.get("password_hash") != hash_password(pwd):
                st.error("Identifiants invalides.")
            else:
                st.session_state.user = u["username"]
                st.session_state.role = u["role"]
                st.success(f"Bienvenue {u['username']} — ({u['role']})")
                st.experimental_rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# If no user exists, small manager creation form
if "user" not in st.session_state:
    st.session_state.user = None
if "role" not in st.session_state:
    st.session_state.role = None

users = read_users()
if not users:
    st.warning("Aucun utilisateur trouvé — créez un manager initial ci-dessous.")
    with st.form("init_manager_form"):
        m_user = st.text_input("Manager username", value="manager", key="init_mgr_user")
        m_pwd = st.text_input("Manager password", type="password", key="init_mgr_pwd")
        submitted = st.form_submit_button("Créer manager initial")
        if submitted:
            if not m_user or not m_pwd:
                st.error("Remplis les champs.")
            else:
                try:
                    create_user(m_user.strip(), m_pwd, "manager")
                    st.success("Manager initial créé — connecte-toi.")
                    st.experimental_rerun()
                except Exception as e:
                    st.error(str(e))

# If not logged in -> show login card and stop
if not st.session_state.get("user"):
    show_login_card()
    st.stop()

# After login: sidebar menu and logout
st.sidebar.success(f"Connecté: {st.session_state.user} ({st.session_state.role})")
if st.sidebar.button("Se déconnecter", key="logout_btn"):
    st.session_state.user = None
    st.session_state.role = None
    st.experimental_rerun()

# Sidebar menu (PDR and Export pages removed)
menu = st.sidebar.radio("Pages", ["Dashboard","Production","Maintenance","Qualité"])

# permission helper
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

# ---------------------------
# Dashboard page
# ---------------------------
def page_dashboard():
    st.markdown(f'<div class="app-header" style="background: linear-gradient(90deg, {PAGE_PALETTES.get("default")[0]}, {PAGE_PALETTES.get("default")[1]});"><h3 style="margin:6px 0">Tableau de bord — Pareto & résumé</h3></div>', unsafe_allow_html=True)
    bons = read_bons()
    if not bons:
        st.info("Aucun bon enregistré.")
        return
    df = pd.DataFrame(bons)
    c1, c2 = st.columns([3,1])
    period = c1.selectbox("Période pour Pareto", ["day","week","month"], key="dashboard_period")
    topn = c2.number_input("Top N", min_value=1, max_value=10, value=3, key="dashboard_topn")
    # choose palette for pareto: use default accent
    plot_pareto(df, period=period, top_n_labels=topn, palette=PAGE_PALETTES.get("default"))
    st.markdown("---")
    st.subheader("Aperçu (derniers d'abord)")
    st.dataframe(df.sort_values(by="date", ascending=False), height=320)

# ---------------------------
# Page: Bons — unique, cleaned, with keys
# ---------------------------
def page_bons(page_name: str):
    # colored header (page-specific palette)
    p1, p2 = PAGE_PALETTES.get(page_name, PAGE_PALETTES["default"])
    st.markdown(f'<div class="app-header" style="background: linear-gradient(90deg, {p1}, {p2});"><h3 style="margin:6px 0">{page_name} — Gestion des bons</h3></div>', unsafe_allow_html=True)
    if not allowed(page_name):
        st.warning("Vous n'avez pas la permission pour cette page.")
        return

    bons = read_bons()
    df = pd.DataFrame(bons) if bons else pd.DataFrame(columns=BON_COLUMNS)
    codes = df["code"].astype(str).tolist() if not df.empty else []

    # Charger / Nouveau
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Charger / Nouveau")
    col_load1, col_load2 = st.columns([3,1])
    sel_code_key = f"sel_{page_name}"
    sel_code = col_load1.selectbox("Charger un bon existant (optionnel)", options=[""] + codes, key=sel_code_key)
    if col_load2.button("Charger", key=f"btn_load_{page_name}") and sel_code:
        bon = get_bon_by_code(sel_code)
        if bon:
            load_bon_into_session(bon, page_name)
            st.experimental_rerun()
    if col_load2.button("Nouveau", key=f"btn_new_{page_name}"):
        clear_form_session(page_name)
        st.experimental_rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # editable fields sets
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
        editable_set = set()

    # init session keys for this page
    for k in BON_COLUMNS:
        session_key = f"{page_name}_form_{k}"
        if session_key not in st.session_state:
            st.session_state[session_key] = ""

    # Form (unique id per page)
    form_id = f"form_bon_{page_name}"
    st.markdown('<div class="card">', unsafe_allow_html=True)
    with st.form(form_id, clear_on_submit=False):
        c1, c2, c3 = st.columns(3)

        # Code
        code_key = f"{page_name}_form_code"
        code = c1.text_input("Code", value=st.session_state.get(code_key, ""), key=code_key, disabled=("code" not in editable_set))

        # Date
        date_key = f"{page_name}_form_date"
        date_default = st.session_state.get(date_key, date.today().strftime("%Y-%m-%d"))
        try:
            default_date_obj = datetime.strptime(date_default, "%Y-%m-%d").date()
        except Exception:
            default_date_obj = date.today()
        date_input = c1.date_input("Date", value=default_date_obj, key=date_key, disabled=("date" not in editable_set))

        # Arrêt déclaré par
        arret_key = f"{page_name}_form_arret_declare_par"
        arret = c1.text_input("Arrêt déclaré par", value=st.session_state.get(arret_key, ""), key=arret_key, disabled=("arret_declare_par" not in editable_set))

        # Poste de charge
        poste_key = f"{page_name}_form_poste_de_charge"
        postes = read_options("options_poste_de_charge")
        poste_default = st.session_state.get(poste_key, "")
        if "poste_de_charge" in editable_set:
            poste = c2.selectbox("Poste de charge", [""] + postes + ["Autres..."], index=([""] + postes + ["Autres..."]).index(poste_default) if poste_default in ([""]+postes+["Autres..."]) else 0, key=poste_key)
            if poste == "Autres...":
                new_poste = c2.text_input("Ajouter nouveau poste", key=f"{page_name}_new_poste")
                if new_poste:
                    opts = read_options("options_poste_de_charge")
                    opts.append(new_poste.strip())
                    write_options("options_poste_de_charge", opts)
                    st.session_state[poste_key] = new_poste.strip()
                    poste = new_poste.strip()
        else:
            # read-only representation (disabled)
            _idx = ([""] + postes).index(poste_default) if poste_default in ([""]+postes) else 0
            c2.selectbox("Poste de charge", [""] + postes, index=_idx, disabled=True, key=f"{poste_key}_ro")
            poste = poste_default

        # Heure déclaration
        heure_key = f"{page_name}_form_heure_declaration"
        heure_declaration = c2.text_input("Heure de déclaration", value=st.session_state.get(heure_key, ""), key=heure_key, disabled=("heure_declaration" not in editable_set))

        # Machine arrêtée
        machine_key = f"{page_name}_form_machine_arreter"
        machine = c2.selectbox("Machine arrêtée?", ["","Oui","Non"], index=(["","Oui","Non"].index(st.session_state.get(machine_key,"")) if st.session_state.get(machine_key,"") in ["","Oui","Non"] else 0), key=machine_key, disabled=("machine_arreter" not in editable_set))

        # Heures intervention
        debut_key = f"{page_name}_form_heure_debut_intervention"
        fin_key = f"{page_name}_form_heure_fin_intervention"
        debut = c3.text_input("Heure début", value=st.session_state.get(debut_key, ""), key=debut_key, disabled=("heure_debut_intervention" not in editable_set))
        fin = c3.text_input("Heure fin", value=st.session_state.get(fin_key, ""), key=fin_key, disabled=("heure_fin_intervention" not in editable_set))

        # Technicien
        tech_key = f"{page_name}_form_technicien"
        technicien = c3.text_input("Technicien", value=st.session_state.get(tech_key, ""), key=tech_key, disabled=("technicien" not in editable_set))

        # Description problème
        desc_key = f"{page_name}_form_description_probleme"
        descs = read_options("options_description_probleme")
        desc_default = st.session_state.get(desc_key, "")
        if "description_probleme" in editable_set:
            description = st.selectbox("Description", [""] + descs + ["Autres..."], index=([""]+descs+["Autres..."]).index(desc_default) if desc_default in ([""]+descs+["Autres..."]) else 0, key=desc_key)
            if st.session_state.get(desc_key) == "Autres...":
                new_desc = st.text_input("Ajouter nouvelle description", key=f"{page_name}_new_desc")
                if new_desc:
                    optsd = read_options("options_description_probleme")
                    optsd.append(new_desc.strip())
                    write_options("options_description_probleme", optsd)
                    st.session_state[desc_key] = new_desc.strip()
                    description = new_desc.strip()
        else:
            # read-only
            _idx = ([""]+descs).index(desc_default) if desc_default in ([""]+descs) else 0
            st.selectbox("Description", [""] + descs, index=_idx, disabled=True, key=f"{desc_key}_ro")
            description = desc_default

        # Action
        action_key = f"{page_name}_form_action"
        action = st.text_input("Action", value=st.session_state.get(action_key, ""), key=action_key, disabled=("action" not in editable_set))

        # PDR utilisée (readonly or editable)
        pdr_key = f"{page_name}_form_pdr_utilisee"
        pdr_used = st.text_input("PDR utilisée (code)", value=st.session_state.get(pdr_key, ""), key=pdr_key, disabled=("pdr_utilisee" not in editable_set))

        # Observation
        obs_key = f"{page_name}_form_observation"
        observation = st.text_input("Observation", value=st.session_state.get(obs_key, ""), key=obs_key, disabled=("observation" not in editable_set))

        # Résultat
        res_key = f"{page_name}_form_resultat"
        resultat = st.selectbox("Résultat", ["","Accepter","Refuser","Accepter avec condition"], index=(["","Accepter","Refuser","Accepter avec condition"].index(st.session_state.get(res_key,"")) if st.session_state.get(res_key,"") in ["","Accepter","Refuser","Accepter avec condition"] else 0), key=res_key, disabled=("resultat" not in editable_set))

        # Condition
        cond_key = f"{page_name}_form_condition_acceptation"
        cond = st.text_input("Condition d'acceptation", value=st.session_state.get(cond_key, ""), key=cond_key, disabled=("condition_acceptation" not in editable_set))

        # Dpts
        dpt_m_key = f"{page_name}_form_dpt_maintenance"
        dpt_q_key = f"{page_name}_form_dpt_qualite"
        dpt_p_key = f"{page_name}_form_dpt_production"
        dpt_m = st.selectbox("Dpt Maintenance", ["","Valider","Non Valider"], index=(["","Valider","Non Valider"].index(st.session_state.get(dpt_m_key,"")) if st.session_state.get(dpt_m_key,"") in ["","Valider","Non Valider"] else 0), key=dpt_m_key, disabled=("dpt_maintenance" not in editable_set))
        dpt_q = st.selectbox("Dpt Qualité", ["","Valider","Non Valider"], index=(["","Valider","Non Valider"].index(st.session_state.get(dpt_q_key,"")) if st.session_state.get(dpt_q_key,"") in ["","Valider","Non Valider"] else 0), key=dpt_q_key, disabled=("dpt_qualite" not in editable_set))
        dpt_p = st.selectbox("Dpt Production", ["","Valider","Non Valider"], index=(["","Valider","Non Valider"].index(st.session_state.get(dpt_p_key,"")) if st.session_state.get(dpt_p_key,"") in ["","Valider","Non Valider"] else 0), key=dpt_p_key, disabled=("dpt_production" not in editable_set))

        submit_key = f"submit_{page_name}"
        submitted = st.form_submit_button("Ajouter / Mettre à jour", key=submit_key)

        if submitted:
            code_v = st.session_state.get(code_key, "").strip()
            date_v = st.session_state.get(date_key, default_date_obj.strftime("%Y-%m-%d"))
            row = {k: "" for k in BON_COLUMNS}
            row.update({
                "code": code_v,
                "date": date_v,
                "arret_declare_par": st.session_state.get(arret_key, ""),
                "poste_de_charge": st.session_state.get(poste_key, ""),
                "heure_declaration": st.session_state.get(heure_key, ""),
                "machine_arreter": st.session_state.get(machine_key, ""),
                "heure_debut_intervention": st.session_state.get(debut_key, ""),
                "heure_fin_intervention": st.session_state.get(fin_key, ""),
                "technicien": st.session_state.get(tech_key, ""),
                "description_probleme": st.session_state.get(desc_key, ""),
                "action": st.session_state.get(action_key, ""),
                "pdr_utilisee": st.session_state.get(pdr_key, ""),
                "observation": st.session_state.get(obs_key, ""),
                "resultat": st.session_state.get(res_key, ""),
                "condition_acceptation": st.session_state.get(cond_key, ""),
                "dpt_maintenance": st.session_state.get(dpt_m_key, ""),
                "dpt_qualite": st.session_state.get(dpt_q_key, ""),
                "dpt_production": st.session_state.get(dpt_p_key, "")
            })
            try:
                if code_v == "":
                    st.error("Le champ Code est requis.")
                else:
                    if any(c.get("code","") == code_v for c in read_bons()):
                        update_bon(code_v, row)
                        st.success("Bon mis à jour.")
                    else:
                        add_bon(row)
                        st.success("Bon ajouté.")
                    # keep values visible
                    load_bon_into_session(row, page_name)
                    st.experimental_rerun()
            except Exception as e:
                st.error(str(e))
    st.markdown('</div>', unsafe_allow_html=True)  # card close

    # --------------------------
    # Recherche & Liste (single, with unique keys)
    # --------------------------
    st.markdown('')  # spacing
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Recherche & Liste")
    search_by_key = f"{page_name}_search_by"
    term_key = f"{page_name}_term"
    search_by = st.selectbox("Rechercher par", ["Code","Date","Poste de charge","Dpt"], key=search_by_key)
    term = st.text_input("Terme de recherche", key=term_key)
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
        sel_key = f"{page_name}_sel_code"
        sel = st.selectbox("Sélectionner un code", options=[""] + all_df["code"].astype(str).tolist(), key=sel_key)
        if sel:
            if st.button("Afficher JSON", key=f"showjson_{page_name}"):
                st.json(get_bon_by_code(sel))
            if st.button("Supprimer", key=f"del_{page_name}"):
                delete_bon(sel)
                st.success("Supprimé")
                st.experimental_rerun()
    else:
        st.info("Aucun bon à afficher.")
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------
# Router
# ---------------------------
if menu == "Dashboard":
    page_dashboard()
elif menu == "Production":
    page_bons("Production")
elif menu == "Maintenance":
    page_bons("Maintenance")
elif menu == "Qualité":
    page_bons("Qualité")

# Footer note
st.sidebar.markdown("---")
st.sidebar.caption("⚠️ Données stockées localement sur l'instance. Elles peuvent disparaître après redémarrage / redeploy.")
