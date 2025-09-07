# app.py
# Streamlit app - Storage: Google Sheets (suitable for Streamlit Community Cloud)
# - Auth: SHA-256 passwords, manager-only account creation
# - "Autres..." dynamic options (persisted)
# - Pareto chart improved (day/week/month) + annotated top periods
# - Export Excel with insertion of logo (logo REGAL-PNG.png)
#
# Required secrets in Streamlit Cloud:
# st.secrets["gsheet_id"] -> Google Sheet ID (string)
# st.secrets["gcp_service_account"] -> service account JSON (string or dict)
#
# Place images in repo root: logo REGAL-PNG.png, back_button.png, user-icon.png

import os
import sys
import json
import io
import hashlib
import time
import calendar
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import gspread
from google.oauth2.service_account import Credentials
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from openpyxl.drawing.image import Image as XLImage

# ----------------------------
# Configuration & constants
# ----------------------------
st.set_page_config(page_title="Work Order Management", layout="wide")
st.title("Work Order Management — Streamlit (Google Sheets)")
APP_IMAGES = ["logo REGAL-PNG.png", "back_button.png", "user-icon.png"]

DEFAULT_SHEETS = {
    "bon_travail": [
        "code","date","arret_declare_par","poste_de_charge","heure_declaration","machine_arreter",
        "heure_debut_intervention","heure_fin_intervention","technicien","description_probleme",
        "action","pdr_utilisee","observation","resultat","condition_acceptation","dpt_maintenance","dpt_qualite","dpt_production"
    ],
    "liste_pdr": ["code","remplacement","nom_composant","quantite"],
    "users": ["id","username","password_hash","role"],
    "options_description_probleme": ["label"],
    "options_poste_de_charge": ["label"]
}

# Initial values from your Version_Final.docx (kept comprehensive)
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

# ----------------------------
# Helpers: resource path for images (works in dev and Streamlit Cloud)
# ----------------------------
def resource_path(relative_path: str) -> str:
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

# display header logo when available
for img_name in APP_IMAGES:
    if os.path.exists(resource_path(img_name)):
        # show only the main logo at top
        if img_name == "logo REGAL-PNG.png":
            try:
                st.image(resource_path(img_name), width=220)
            except Exception:
                st.write("Work Order Management")
        break

# ----------------------------
# Google Sheets connection helpers
# ----------------------------
def load_service_account_info_from_secrets() -> Dict[str, Any]:
    # st.secrets["gcp_service_account"] may be a dict or string
    sa = st.secrets.get("gcp_service_account", None)
    if sa is None:
        # fallback to local file for dev
        local_fn = "service_account.json"
        if os.path.exists(local_fn):
            with open(local_fn, "r", encoding="utf-8") as f:
                return json.load(f)
        st.error("Aucune credential service account trouvée. Configure st.secrets['gcp_service_account'] (ou ajoute service_account.json pour dev).")
        st.stop()
    if isinstance(sa, dict):
        return sa
    # string
    try:
        return json.loads(sa)
    except Exception as e:
        # maybe it's already a JSON string with newlines -> try eval
        try:
            return json.loads(sa.replace("\n", "\\n"))
        except Exception:
            st.error("Impossible de parser st.secrets['gcp_service_account']. Assure-toi d'avoir collé le JSON exact.")
            st.stop()

def get_gspread_client():
    sa_info = load_service_account_info_from_secrets()
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(sa_info, scopes=scopes)
    return gspread.authorize(creds)

GSHEET_ID = st.secrets.get("gsheet_id", "")
if not GSHEET_ID:
    st.error("Configure st.secrets['gsheet_id'] (Google Sheet ID). Voir README.")
    st.stop()

# connect
try:
    gc = get_gspread_client()
    sh = gc.open_by_key(GSHEET_ID)
except Exception as e:
    st.error(f"Erreur connexion Google Sheets : {e}")
    st.stop()

# ----------------------------
# Ensure worksheets and headers exist; prefill options
# ----------------------------
def ensure_worksheets_and_headers(spreadsheet):
    existing = {ws.title: ws for ws in spreadsheet.worksheets()}
    for title, headers in DEFAULT_SHEETS.items():
        if title not in existing:
            ws = spreadsheet.add_worksheet(title=title, rows=200, cols=max(10, len(headers)))
            ws.append_row(headers)
            existing[title] = ws
        else:
            ws = existing[title]
            # verify header
            try:
                first = ws.row_values(1)
                if not first:
                    ws.append_row(headers)
            except Exception:
                # recreate header if weird state
                try:
                    ws.append_row(headers)
                except Exception:
                    pass

    # Prefill options if empty
    try:
        od = spreadsheet.worksheet("options_description_probleme")
        if len(od.get_all_records()) == 0:
            for v in INITIAL_DESCRIPTIONS:
                od.append_row([v])
    except Exception:
        pass
    try:
        op = spreadsheet.worksheet("options_poste_de_charge")
        if len(op.get_all_records()) == 0:
            for v in INITIAL_POSTES:
                op.append_row([v])
    except Exception:
        pass

ensure_worksheets_and_headers(sh)

# ----------------------------
# Small utilities for Sheets <-> DataFrame
# ----------------------------
def sheet_to_df(sheet_name: str) -> pd.DataFrame:
    try:
        ws = sh.worksheet(sheet_name)
        data = ws.get_all_records()
        return pd.DataFrame(data)
    except Exception:
        return pd.DataFrame()

def append_row(sheet_name: str, row_values: List[Any]):
    ws = sh.worksheet(sheet_name)
    ws.append_row(row_values, value_input_option="USER_ENTERED")

def find_row_index(ws, key_col_name: str, key_value: str) -> Optional[int]:
    # returns 2..N index (1 is header) or None
    try:
        all_records = ws.get_all_records()
    except Exception:
        return None
    for i, r in enumerate(all_records, start=2):
        if str(r.get(key_col_name, "")).strip() == str(key_value).strip():
            return i
    return None

def update_row_by_key(sheet_name: str, key_col_name: str, key_value: str, values_dict: Dict[str, Any]):
    ws = sh.worksheet(sheet_name)
    headers = ws.row_values(1)
    idx = find_row_index(ws, key_col_name, key_value)
    if idx is None:
        raise KeyError("clé introuvable")
    row = [values_dict.get(h, "") for h in headers]
    ws.update(f"A{idx}", [row], value_input_option="USER_ENTERED")

def delete_row_by_key(sheet_name: str, key_col_name: str, key_value: str):
    ws = sh.worksheet(sheet_name)
    idx = find_row_index(ws, key_col_name, key_value)
    if idx:
        ws.delete_rows(idx)

# ----------------------------
# Auth helpers
# ----------------------------
def hash_password(pwd: str) -> str:
    return hashlib.sha256((pwd or "").encode("utf-8")).hexdigest()

def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    df = sheet_to_df("users")
    if df.empty: return None
    found = df[df["username"].astype(str).str.strip() == str(username).strip()]
    if found.empty: return None
    return found.iloc[0].to_dict()

# If users sheet is empty, provide a one-shot initial manager creation form (safe prompt)
users_df = sheet_to_df("users")
if users_df.empty:
    st.warning("Aucun utilisateur trouvé. Créez un compte manager initial (nécessaire pour la gestion des utilisateurs).")
    with st.form("create_initial_manager"):
        init_user = st.text_input("Nom d'utilisateur manager", value="manager")
        init_pwd = st.text_input("Mot de passe manager (changez-le après)", type="password")
        submit_init = st.form_submit_button("Créer manager initial")
        if submit_init:
            if not init_user or not init_pwd:
                st.error("Remplis les 2 champs.")
            else:
                ws = sh.worksheet("users")
                ws.append_row([1, init_user.strip(), hash_password(init_pwd), "manager"])
                st.success("Manager créé. Reconnecte-toi maintenant.")
                st.experimental_rerun()

# session state for auth
if "user" not in st.session_state:
    st.session_state.user = None
    st.session_state.role = None

# Sidebar: login & user management
st.sidebar.header("Connexion & Utilisateurs")
if st.session_state.user:
    st.sidebar.info(f"Connecté : {st.session_state.user} ({st.session_state.role})")
    if st.sidebar.button("Se déconnecter"):
        st.session_state.user = None
        st.session_state.role = None
        st.experimental_rerun()
else:
    username = st.sidebar.text_input("Nom d'utilisateur", key="login_user")
    password = st.sidebar.text_input("Mot de passe", type="password", key="login_pwd")
    if st.sidebar.button("Se connecter"):
        user = get_user_by_username(username)
        if not user or user.get("password_hash") != hash_password(password):
            st.sidebar.error("Identifiants invalides.")
        else:
            st.session_state.user = user["username"]
            st.session_state.role = user["role"]
            st.sidebar.success(f"Bienvenue {user['username']} ({user['role']})")

    st.sidebar.markdown("---")
    st.sidebar.write("Créer un compte (nécessite la validation d'un manager existant)")
    mgr_check_user = st.sidebar.text_input("Manager - nom (pour vérif)")
    mgr_check_pwd = st.sidebar.text_input("Manager - mdp (pour vérif)", type="password")
    if st.sidebar.button("Valider manager"):
        mgr = get_user_by_username(mgr_check_user)
        if not mgr or mgr.get("password_hash") != hash_password(mgr_check_pwd) or mgr.get("role") != "manager":
            st.sidebar.error("Vérification manager échouée.")
        else:
            st.sidebar.success("Manager vérifié. Remplir le formulaire de création ci-dessous.")
            # show creation form
            st.sidebar.markdown("**Créer un nouvel utilisateur**")
            new_user = st.sidebar.text_input("Nouveau nom d'utilisateur", key="new_user")
            new_pwd = st.sidebar.text_input("Nouveau mot de passe", type="password", key="new_pwd")
            new_role = st.sidebar.selectbox("Rôle", ["production", "maintenance", "qualite", "manager"], key="new_role")
            if st.sidebar.button("Créer l'utilisateur"):
                if not new_user or not new_pwd:
                    st.sidebar.error("Champs requis.")
                else:
                    # upsert uniqueness
                    u = get_user_by_username(new_user)
                    if u:
                        st.sidebar.error("Nom d'utilisateur déjà pris.")
                    else:
                        ws = sh.worksheet("users")
                        dfu = sheet_to_df("users")
                        new_id = (len(dfu) + 1) if not dfu.empty else 1
                        ws.append_row([new_id, new_user.strip(), hash_password(new_pwd), new_role])
                        st.sidebar.success(f"Utilisateur {new_user} créé.")

# Sidebar quick navigation
menu = st.sidebar.radio("Pages", ["Dashboard", "Production", "Maintenance", "Qualité", "Pièces (PDR)", "Export Excel"])

# helper for role permissions
def role_allows(page_name: str) -> bool:
    role = st.session_state.role
    if role == "manager": return True
    if role == "production" and page_name == "Production": return True
    if role == "maintenance" and page_name == "Maintenance": return True
    if role == "qualite" and page_name == "Qualité": return True
    return False

# ----------------------------
# Pareto plotting helper (improved)
# ----------------------------
def plot_pareto(df: pd.DataFrame, period: str = "day", top_n_labels: int = 3, show_max_categories: int = 30):
    """
    df must contain 'date' column (strings). period: 'day', 'week', 'month'.
    """
    try:
        dates = pd.to_datetime(df["date"], errors="coerce").dropna()
    except Exception:
        st.info("Aucune date valide.")
        return

    if dates.empty:
        st.info("Aucune date valide.")
        return

    if period == "day":
        groups = dates.dt.strftime("%Y-%m-%d")
        xlabel = "Jour"
    elif period == "week":
        groups = dates.dt.strftime("%Y-W%U")
        xlabel = "Semaine (YYYY-WWW)"
    else:
        groups = dates.dt.strftime("%Y-%m")
        xlabel = "Mois (YYYY-MM)"

    counts = groups.value_counts().sort_values(ascending=False)
    total = counts.sum()
    if counts.empty:
        st.info("Aucune intervention pour la période.")
        return

    # Limit categories for readability
    if len(counts) > show_max_categories:
        counts = counts.head(show_max_categories)
        # optionally, add an "Autres" aggregation at the end
        # but Pareto usually focuses on top categories.

    cum = counts.cumsum()
    cum_pct = 100 * cum / total

    # Plot
    fig, ax1 = plt.subplots(figsize=(10, 4))
    x = range(len(counts))
    bars = ax1.bar(x, counts.values, alpha=0.85)
    ax1.set_xticks(x)
    ax1.set_xticklabels(counts.index.tolist(), rotation=45, ha="right", fontsize=9)
    ax1.set_ylabel("Nombre d'interventions")
    ax1.set_xlabel(xlabel)
    ax1.set_title(f"Pareto ({period}) — total = {total}")
    ax1.grid(axis="y", alpha=0.25)

    # cumulative line
    ax2 = ax1.twinx()
    ax2.plot(x, cum_pct.values, marker="o", linestyle="-", linewidth=2, label="Cumul (%)")
    ax2.set_ylim(0, 110)
    ax2.set_ylabel("Pourcentage cumulé (%)")
    # threshold line at 80%
    ax2.axhline(80, color="red", linestyle="--", alpha=0.6)
    ax2.text(len(counts)-1, 82, "80% threshold", color="red", ha="right", va="bottom", fontsize=9)

    # annotate top N
    top = counts.head(top_n_labels)
    for label, val in top.items():
        idx = counts.index.tolist().index(label)
        pct = val / total * 100
        ax1.annotate(f"{val} ({pct:.1f}%)", xy=(idx, val), xytext=(0, 6), textcoords="offset points",
                     ha="center", fontsize=9, fontweight="bold", bbox=dict(boxstyle="round,pad=0.2", alpha=0.18))

    st.pyplot(fig)

    # textual top periods
    st.markdown("**Périodes les plus impactées :**")
    for i, (label, val) in enumerate(top.items(), start=1):
        st.write(f"{i}. **{label}** — {val} interventions — {val/total*100:.1f}% du total")

# ----------------------------
# CRUD for bon_travail and PDR
# ----------------------------
def fetch_bons_df() -> pd.DataFrame:
    return sheet_to_df("bon_travail")

def add_or_update_bon(row: Dict[str, Any]):
    df = fetch_bons_df()
    code = str(row.get("code", "")).strip()
    headers = DEFAULT_SHEETS["bon_travail"]
    if code == "":
        raise ValueError("Code requis")
    if not df.empty and code in df["code"].astype(str).tolist():
        # update
        update_row_by_key("bon_travail", "code", code, row)
    else:
        append_row("bon_travail", [row.get(h, "") for h in headers])

        # decrement PDR quantity if exists
        pdr_code = str(row.get("pdr_utilisee", "")).strip()
        if pdr_code:
            try:
                ws_pdr = sh.worksheet("liste_pdr")
                idx = find_row_index(ws_pdr, "code", pdr_code)
                if idx:
                    hdrs = ws_pdr.row_values(1)
                    # find quantite col
                    qcol = None
                    for i, h in enumerate(hdrs, start=1):
                        if h.lower() == "quantite":
                            qcol = i
                            break
                    if qcol:
                        # gspread row_values returns strings
                        row_vals = ws_pdr.row_values(idx)
                        q_val = 0
                        if len(row_vals) >= qcol:
                            try:
                                q_val = int(row_vals[qcol-1])
                            except Exception:
                                q_val = 0
                        q_val = max(0, q_val - 1)
                        # update that cell
                        # build range like D{idx} (col letter)
                        letter = gspread.utils.rowcol_to_a1(1, qcol)[0]  # this trick is not direct; simpler compute letter:
                        # compute column letter properly:
                        def colnum_to_letters(n):
                            string = ""
                            while n > 0:
                                n, remainder = divmod(n-1, 26)
                                string = chr(65 + remainder) + string
                            return string
                        col_letter = colnum_to_letters(qcol)
                        ws_pdr.update(f"{col_letter}{idx}", q_val, value_input_option="USER_ENTERED")
            except Exception:
                pass

def delete_bon(code: str):
    delete_row_by_key("bon_travail", "code", code)

def fetch_pdr_df() -> pd.DataFrame:
    return sheet_to_df("liste_pdr")

def upsert_pdr_record(code: str, remplacement: str, nom_composant: str, quantite: int):
    ws = sh.worksheet("liste_pdr")
    dfp = fetch_pdr_df()
    code = code.strip()
    if not code:
        raise ValueError("Code PDR requis")
    if not dfp.empty and code in dfp["code"].astype(str).tolist():
        update_row_by_key("liste_pdr", "code", code, {
            "code": code, "remplacement": remplacement, "nom_composant": nom_composant, "quantite": int(quantite)
        })
    else:
        append_row("liste_pdr", [code, remplacement, nom_composant, int(quantite)])

def delete_pdr(code: str):
    delete_row_by_key("liste_pdr", "code", code)

# ----------------------------
# Export Excel (with insertion of logo if available)
# ----------------------------
def export_bons_to_excel_bytes(df: pd.DataFrame) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Bon de travail"

    # Try add logo
    logo_path = resource_path("logo REGAL-PNG.png")
    try:
        if os.path.exists(logo_path):
            img = XLImage(logo_path)
            img.anchor = 'A1'
            ws.add_image(img)
            # adjust heading area
            ws.merge_cells('C1:Q4')
            ws['C1'].alignment = Alignment(horizontal='center', vertical='center')
            ws['C1'].font = Font(bold=True, size=18)
    except Exception:
        pass

    headers = DEFAULT_SHEETS["bon_travail"]
    # write header starting row 6 to give space for logo
    start_row = 6
    for col_idx, h in enumerate(headers, start=1):
        ws.cell(row=start_row, column=col_idx, value=h).font = Font(bold=True)
    row_num = start_row + 1
    for _, r in df.iterrows():
        for col_idx, h in enumerate(headers, start=1):
            ws.cell(row=row_num, column=col_idx, value=r.get(h))
        row_num += 1

    bio = io.BytesIO()
    wb.save(bio)
    return bio.getvalue()

# ----------------------------
# Pages: Dashboard, Management, PDR, Export
# ----------------------------
def page_dashboard():
    st.header("Tableau de bord — Pareto & résumé")
    df = fetch_bons_df()
    if df.empty:
        st.info("Aucun enregistrement (bon_travail vide).")
        return

    # Controls for Pareto
    c1, c2 = st.columns([3,1])
    period = c1.selectbox("Période pour Pareto", ["day", "week", "month"], index=0)
    top_n = c2.number_input("Top N labels", min_value=1, max_value=10, value=3)
    max_cat = c2.number_input("Max catégories affichées", min_value=5, max_value=100, value=30)

    plot_pareto(df, period=period, top_n_labels=top_n, show_max_categories=max_cat)

    st.markdown("---")
    st.subheader("Aperçu des bons (derniers en premier)")
    st.dataframe(df.sort_values(by="date", ascending=False), height=320)

def page_bons(page_name: str):
    st.header(f"{page_name} — Gestion des bons de travail")
    if not role_allows(page_name):
        st.warning("Vous n'avez pas la permission d'accéder à cette page.")
        return

    df = fetch_bons_df()
    codes = df["code"].astype(str).tolist() if not df.empty else []

    with st.form("form_bon"):
        col1, col2, col3 = st.columns(3)
        code = col1.text_input("Code")
        date_input = col1.date_input("Date", value=date.today())
        arret = col1.text_input("Arrêt déclaré par")
        # Poste de charge (dynamic)
        postes_df = sheet_to_df("options_poste_de_charge")
        postes = postes_df["label"].astype(str).tolist() if not postes_df.empty else []
        poste = col2.selectbox("Poste de charge", options=[""] + postes + ["Autres..."])
        if poste == "Autres...":
            new_poste = col2.text_input("Ajouter nouveau poste")
            if new_poste:
                sh.worksheet("options_poste_de_charge").append_row([new_poste.strip()])
                poste = new_poste.strip()
        heure_declaration = col2.text_input("Heure de déclaration (HH:MM)")
        machine = col2.selectbox("Machine arrêtée ?", ["", "Oui", "Non"])
        debut = col3.text_input("Heure début")
        fin = col3.text_input("Heure fin")
        technicien = col3.text_input("Technicien")
        # Description (dynamic)
        descs_df = sheet_to_df("options_description_probleme")
        descs = descs_df["label"].astype(str).tolist() if not descs_df.empty else []
        description = st.selectbox("Description du problème", options=[""] + descs + ["Autres..."])
        if description == "Autres...":
            new_desc = st.text_input("Ajouter nouvelle description")
            if new_desc:
                sh.worksheet("options_description_probleme").append_row([new_desc.strip()])
                description = new_desc.strip()
        action = st.text_input("Action")
        pdr_used = st.text_input("PDR utilisée (code)")
        observation = st.text_input("Observation")
        resultat = st.selectbox("Résultat", ["", "Accepter", "Refuser", "Accepter avec condition"])
        cond = st.text_input("Condition d'acceptation")
        dpt_m = st.selectbox("Dpt Maintenance", ["", "Valider", "Non Valider"])
        dpt_q = st.selectbox("Dpt Qualité", ["", "Valider", "Non Valider"])
        dpt_p = st.selectbox("Dpt Production", ["", "Valider", "Non Valider"])

        submit = st.form_submit_button("Ajouter / Mettre à jour")
        if submit:
            code_v = code.strip()
            date_v = date_input.strftime("%Y-%m-%d")
            row = {
                "code": code_v, "date": date_v, "arret_declare_par": arret, "poste_de_charge": poste,
                "heure_declaration": heure_declaration, "machine_arreter": machine,
                "heure_debut_intervention": debut, "heure_fin_intervention": fin,
                "technicien": technicien, "description_probleme": description,
                "action": action, "pdr_utilisee": pdr_used, "observation": observation,
                "resultat": resultat, "condition_acceptation": cond,
                "dpt_maintenance": dpt_m, "dpt_qualite": dpt_q, "dpt_production": dpt_p
            }
            try:
                add_or_update_bon(row)
                st.success("Bon ajouté / mis à jour.")
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Erreur add/update: {e}")

    st.markdown("---")
    st.subheader("Liste & actions")
    df_all = fetch_bons_df()
    if df_all.empty:
        st.info("Aucun bon.")
        return
    st.dataframe(df_all.sort_values(by="date", ascending=False), height=300)

    sel_code = st.selectbox("Sélectionner un code", options=[""] + df_all["code"].astype(str).tolist())
    if sel_code:
        if st.button("Afficher détails (JSON)"):
            row = df_all[df_all["code"].astype(str) == sel_code].iloc[0].to_dict()
            st.json(row)
        if st.button("Supprimer cet enregistrement"):
            try:
                delete_bon(sel_code)
                st.success("Supprimé.")
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Erreur suppression: {e}")

def page_pdr():
    st.header("Gestion des pièces - PDR (liste_pdr)")
    df = fetch_pdr_df()
    st.dataframe(df, height=240)
    with st.form("form_pdr"):
        code = st.text_input("Code PDR")
        remplacement = st.text_input("Remplacement")
        nom = st.text_input("Nom composant")
        quantite = st.number_input("Quantité", min_value=0, value=0)
        submit = st.form_submit_button("Enregistrer PDR")
        if submit:
            try:
                upsert_pdr_record(code, remplacement, nom, int(quantite))
                st.success("PDR enregistrée.")
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Erreur PDR: {e}")
    del_code = st.text_input("Code à supprimer")
    if st.button("Supprimer PDR"):
        try:
            delete_pdr(del_code.strip())
            st.success("PDR supprimée.")
            st.experimental_rerun()
        except Exception as e:
            st.error(f"Erreur suppression PDR: {e}")

def page_export():
    st.header("Export Excel (tous les bons)")
    df = fetch_bons_df()
    if df.empty:
        st.info("Aucun enregistrement pour l'export.")
        return
    if st.button("Générer et télécharger Excel"):
        try:
            excel_bytes = export_bons_to_excel_bytes(df)
            st.download_button("Télécharger bon_travail_export.xlsx", data=excel_bytes,
                               file_name="bon_travail_export.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        except Exception as e:
            st.error(f"Erreur export Excel: {e}")

# ----------------------------
# Router pages
# ----------------------------
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
st.sidebar.caption("Déployée sur Streamlit Community Cloud. Utilise l'URL de l'app pour accéder depuis plusieurs PC.")
