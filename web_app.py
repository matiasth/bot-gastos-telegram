import json
import os
from datetime import datetime

import gspread
import pandas as pd
import streamlit as st

SHEET_ID = os.getenv("SHEET_ID", "16ubX8tkwshnbiqbQKkRdJsO_S_jkBjeui1M6Xu76W7A")

creds_json = os.getenv("GOOGLE_CREDENTIALS") or st.secrets.get("GOOGLE_CREDENTIALS")
if creds_json:
    gc = gspread.service_account_from_dict(json.loads(creds_json))
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


st.set_page_config(page_title="Panel de Gastos", layout="wide", menu_items=None)
st.title("Panel de Gastos")

df = cargar_datos()

col_izq, col_der = st.columns(2)

with col_izq:
    st.metric("Total Gastos", f"${df['Monto'].sum():,.0f}")
    st.metric("Cantidad de Gastos", len(df))

with col_der:
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

st.divider()
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

if st.button("Guardar cambios"):
    guardar_todo(edit_df)
    st.success("Cambios guardados en Google Sheets.")
    st.rerun()
