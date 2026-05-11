import base64
import json
import os
from datetime import datetime

import gspread
import pandas as pd
import streamlit as st

SHEET_ID = os.getenv("SHEET_ID", "16ubX8tkwshnbiqbQKkRdJsO_S_jkBjeui1M6Xu76W7A")

try:
    creds_raw = os.getenv("GOOGLE_CREDENTIALS") or st.secrets.get("GOOGLE_CREDENTIALS")
except Exception:
    creds_raw = os.getenv("GOOGLE_CREDENTIALS")


def _load_creds(text):
    # 1) Try JSON directly
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 2) Try base64 → JSON
    try:
        return json.loads(base64.b64decode(text).decode("utf-8"))
    except Exception:
        pass
    # 3) JSON with newlines inside strings (TOML ate our \n)
    import re
    text = re.sub(
        r'"(?:[^"\\]|\\.)*"',
        lambda m: m.group(0).replace("\n", "\\n"),
        text,
    )
    return json.loads(text)


if creds_raw:
    gc = gspread.service_account_from_dict(_load_creds(creds_raw))
else:
    gc = gspread.service_account(filename="credenciales.json")
sh = gc.open_by_key(SHEET_ID)
ws = sh.worksheet("detalle gastos")


def cargar_datos():
    datos = ws.get_all_values()
    if len(datos) <= 1:
        return pd.DataFrame(columns=["Fecha", "Concepto", "Monto"])
    df = pd.DataFrame(datos[1:], columns=["Fecha", "Concepto", "Monto"])
    df["Monto"] = pd.to_numeric(df["Monto"], errors="coerce")
    return df.dropna(subset=["Monto"]).reset_index(drop=True)


def guardar_todo(df):
    df = df.dropna(subset=["Concepto", "Monto"]).reset_index(drop=True)
    datos = [["Fecha", "Concepto", "Monto"]]
    for _, row in df.iterrows():
        datos.append([str(row["Fecha"]), str(row["Concepto"]), float(row["Monto"])])
    ws.batch_clear([f"A1:C{ws.row_count}"])
    ws.update(range_name="A1", values=datos)


st.set_page_config(page_title="Presupuesto", layout="wide", menu_items=None)

USERS = {"admin": "33kfdk8r", "dawi": "dawi"}

if "auth" not in st.session_state:
    st.session_state.auth = False
    st.session_state.username = ""
    st.session_state.role = ""


def login():
    st.markdown("""
    <style>
        .stApp { background: #f5f5f5; }
        .main > .block-container { max-width: 400px; margin: auto; padding-top: 4rem; }
        h1 { text-align: center; font-size: 1.75rem !important; font-weight: 700 !important; color: #1a1a2e !important; }
        .login-card {
            background: #fff; border-radius: 20px; padding: 2rem;
            box-shadow: 0 4px 20px rgba(0,0,0,.1);
        }
        .stTextInput input {
            border-radius: 12px !important; border: 1.5px solid #e0e0e0 !important;
            padding: 0.7rem 0.75rem !important; font-size: 1rem !important;
        }
        .stTextInput input:focus { border-color: #6c63ff !important; box-shadow: 0 0 0 3px rgba(108,99,255,.15) !important; }
        .stButton button {
            border-radius: 12px !important; font-weight: 600 !important;
            height: 48px; border: none !important;
            background: linear-gradient(135deg, #6c63ff, #5a52d5) !important;
            color: #fff !important; box-shadow: 0 4px 12px rgba(108,99,255,.3) !important;
        }
        .stButton button:active { transform: scale(.97); }
        .error { color: #e74c3c; text-align: center; font-size: 0.9rem; margin-top: 0.5rem; }
    </style>
    """, unsafe_allow_html=True)
    st.title("Presupuesto")
    st.markdown("<div class='login-card'>", unsafe_allow_html=True)
    usuario = st.text_input("Usuario", placeholder="Ingresá tu usuario", label_visibility="collapsed", key="login_user")
    clave = st.text_input("Contraseña", type="password", placeholder="Ingresá tu contraseña", label_visibility="collapsed", key="login_pass")
    if st.button("Ingresar", use_container_width=True):
        if usuario in USERS and USERS[usuario] == clave:
            st.session_state.auth = True
            st.session_state.username = usuario
            st.session_state.role = "admin" if usuario == "admin" else "viewer"
            st.rerun()
        else:
            st.markdown("<div class='error'>Usuario o contraseña incorrectos</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


if not st.session_state.auth:
    login()
    st.stop()

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    * { font-family: 'Inter', sans-serif; }

    .stApp { background: #f5f5f5; }
    .main > .block-container {
        padding: 1rem 0.75rem;
        max-width: 100%;
    }

    h1 {
        font-size: 1.5rem !important;
        font-weight: 700 !important;
        color: #1a1a2e !important;
        padding-bottom: 0.25rem !important;
        border-bottom: 3px solid #6c63ff;
        display: inline-block;
    }

    .stMetric {
        background: #fff;
        border-radius: 16px;
        padding: 1rem 1.25rem;
        box-shadow: 0 2px 8px rgba(0,0,0,.08);
        margin-bottom: 0.75rem;
    }
    .stMetric label {
        font-size: 0.8rem !important;
        font-weight: 500 !important;
        color: #888 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .stMetric [data-testid="stMetricValue"] {
        font-size: 1.75rem !important;
        font-weight: 700 !important;
        color: #1a1a2e !important;
    }

    [data-testid="stForm"] {
        background: #fff;
        border-radius: 16px;
        padding: 1.25rem;
        box-shadow: 0 2px 8px rgba(0,0,0,.08);
        border: none;
    }
    [data-testid="stForm"] [data-testid="stForm"] { box-shadow: none; padding: 0; }
    [data-testid="stForm"] h3 {
        font-size: 1rem;
        font-weight: 600;
        color: #1a1a2e;
        margin-bottom: 0.75rem;
    }

    .stTextInput input, .stNumberInput input {
        border-radius: 12px !important;
        border: 1.5px solid #e0e0e0 !important;
        padding: 0.6rem 0.75rem !important;
        font-size: 0.95rem !important;
        background: #fafafa !important;
        transition: border .2s, box-shadow .2s;
    }
    .stTextInput input:focus, .stNumberInput input:focus {
        border-color: #6c63ff !important;
        box-shadow: 0 0 0 3px rgba(108,99,255,.15) !important;
    }
    .stDateInput input { border-radius: 12px !important; }

    .stButton button {
        border-radius: 12px !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        padding: 0.5rem 1rem !important;
        transition: transform .15s, box-shadow .15s !important;
        border: none !important;
    }
    .stButton button:active { transform: scale(.97); }
    button[kind="primary"] {
        background: linear-gradient(135deg, #6c63ff, #5a52d5) !important;
        color: #fff !important;
        box-shadow: 0 4px 12px rgba(108,99,255,.3) !important;
    }
    button[kind="primary"]:hover {
        box-shadow: 0 6px 18px rgba(108,99,255,.4) !important;
    }

    [data-testid="stDataFrame"] {
        border-radius: 16px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0,0,0,.08);
    }
    [data-testid="stDataFrame"] thead tr th {
        background: #6c63ff !important;
        color: #fff !important;
        font-weight: 600 !important;
        font-size: 0.8rem !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    [data-testid="stDataFrame"] tbody tr td {
        font-size: 0.9rem !important;
        padding: 0.5rem 0.75rem !important;
    }
    [data-testid="stDataFrame"] tbody tr:nth-child(even) td {
        background: #fafafa !important;
    }

    hr { margin: 1.25rem 0 !important; border-color: #e0e0e0 !important; }
    h2 {
        font-size: 1.15rem !important;
        font-weight: 600 !important;
        color: #1a1a2e !important;
    }

    .stAlert {
        border-radius: 12px !important;
        border: none !important;
        font-weight: 500 !important;
    }

    .user-badge {
        display: inline-flex; align-items: center; gap: 6px;
        background: #eef; padding: 4px 14px; border-radius: 20px;
        font-size: 0.85rem; font-weight: 500; color: #6c63ff;
        float: right; margin-top: 8px;
    }
    .user-badge .dot {
        width: 8px; height: 8px; border-radius: 50%; display: inline-block;
    }
    .user-badge .dot.admin { background: #6c63ff; }
    .user-badge .dot.viewer { background: #f39c12; }

    @media (min-width: 768px) {
        .main > .block-container { padding: 2rem 3rem; max-width: 1100px; margin: 0 auto; }
        h1 { font-size: 2rem !important; }
        .stMetric [data-testid="stMetricValue"] { font-size: 2.25rem !important; }
        [data-testid="stForm"] { padding: 1.5rem; }
    }

    @media (max-width: 639px) {
        div[data-testid="column"] {
            min-width: 100% !important;
            flex: 0 0 100% !important;
            width: 100% !important;
        }
        section[data-testid="stSidebar"] + div .main div[data-testid="columns"] {
            flex-direction: column !important;
            gap: 0.5rem !important;
        }
        .stMetric { padding: 0.75rem 1rem; }
        .stMetric [data-testid="stMetricValue"] { font-size: 1.5rem !important; }
    }
</style>
""", unsafe_allow_html=True)

es_admin = st.session_state.role == "admin"

user_label = "Admin" if es_admin else "Dawi (solo lectura)"
dot_class = "admin" if es_admin else "viewer"
st.markdown(f"<div class='user-badge'><span class='dot {dot_class}'></span>{user_label}</div>", unsafe_allow_html=True)
st.title("Presupuesto")

df = cargar_datos()

col_izq, col_der = st.columns(2)

with col_izq:
    st.metric("Total Gastos", f"${df['Monto'].sum():,.0f}")
    st.metric("Cantidad de Gastos", len(df))

with col_der:
    if es_admin:
        with st.form("nuevo_gasto", clear_on_submit=True):
            st.subheader("Agregar gasto")
            i1, i2, i3 = st.columns([2, 1, 1])
            with i1:
                concepto = st.text_input("Concepto", label_visibility="collapsed", placeholder="Concepto")
            with i2:
                monto = st.number_input("Monto", min_value=0.0, step=100.0, format="%.0f", label_visibility="collapsed", placeholder="Monto")
            with i3:
                fecha = st.date_input("Fecha", value=datetime.today(), label_visibility="collapsed")
            if st.form_submit_button("Agregar", use_container_width=True):
                if concepto and monto > 0:
                    ws.append_row([str(fecha), concepto.capitalize(), monto])
                    st.rerun()
    else:
        st.info("Modo solo lectura", icon="👁️")

st.divider()

if es_admin:
    st.subheader("Editar / Eliminar")
    edit_df = st.data_editor(
        df,
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "Fecha": st.column_config.TextColumn("Fecha"),
            "Concepto": st.column_config.TextColumn("Concepto"),
            "Monto": st.column_config.NumberColumn("Monto", format="$%.0f"),
        },
        key="editor",
    )
    if st.button("Guardar cambios", type="primary"):
        guardar_todo(edit_df)
        st.success("Cambios guardados en Google Sheets.")
        st.rerun()
else:
    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "Fecha": st.column_config.TextColumn("Fecha"),
            "Concepto": st.column_config.TextColumn("Concepto"),
            "Monto": st.column_config.NumberColumn("Monto", format="$%.0f"),
        },
    )

st.divider()
if st.button("Cerrar sesión"):
    for k in ["auth", "username", "role"]:
        st.session_state.pop(k, None)
    st.rerun()
