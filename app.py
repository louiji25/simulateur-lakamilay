import streamlit as st
import pandas as pd
import uuid
from fpdf import FPDF
import os
from datetime import datetime
import base64
import urllib.parse

# CONFIGURATION
st.set_page_config(page_title="Laka Am'lay POS", layout="centered")

HIST_FILE = "historique_devis.csv"
INFO_FILE = "infos.csv"
RIB_FILE = "rib_agence.csv"

# --- Fonctions Utilitaires ---
def get_info_df():
    if os.path.exists(INFO_FILE): return pd.read_csv(INFO_FILE)
    return pd.DataFrame([["Nom", "LAKA AM'LAY"], ["Contact", "+261"]], columns=['Champ', 'Valeur'])

def get_rib():
    if os.path.exists(RIB_FILE): return pd.read_csv(RIB_FILE)
    return pd.DataFrame(columns=["Banque", "IBAN/RIB"])

def generate_custom_ref(client_name, prefix="D"):
    count = 1
    if os.path.exists(HIST_FILE):
        try:
            df = pd.read_csv(HIST_FILE)
            count = len(df) + 1
        except: count = 1
    clean_name = "".join(filter(str.isalnum, client_name)).upper()
    return f"{prefix}{count:06d}-{clean_name}"

def generate_thermal_ticket(type_doc, data, client_name, ref, options_text=""):
    pdf = FPDF(format=(80, 250))
    pdf.add_page()
    pdf.set_margins(4, 4, 4)
    df_infos = get_info_df()
    
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 8, str(df_infos.iloc[0]['Valeur']), ln=True, align='C')
    pdf.set_font("Helvetica", '', 8)
    for i in range(1, len(df_infos)):
        pdf.cell(0, 4, f"{df_infos.iloc[i]['Champ']}: {df_infos.iloc[i]['Valeur']}", ln=True, align='C')
    
    pdf.ln(2); pdf.cell(0, 0, "-"*45, ln=True, align='C'); pdf.ln(2)
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(0, 6, f"{type_doc.upper()}", ln=True, align='C')
    pdf.set_font("Helvetica", '', 8)
    pdf.cell(0, 5, f"Date: {datetime.now().strftime('%d/%m/%y %H:%M')}", ln=True)
    pdf.cell(0, 5, f"Ref: {ref}", ln=True)
    pdf.cell(0, 5, f"Client: {client_name}", ln=True)
    
    pdf.ln(2); pdf.cell(0, 0, "-"*45, ln=True, align='C'); pdf.ln(2)
    pdf.set_font("Helvetica", 'B', 9)
    pdf.multi_cell(0, 5, f"Circuit: {data.get('Circuit', 'N/A')}")
    pdf.set_font("Helvetica", '', 8)
    pdf.cell(0, 5, f"Pax: {data.get('Pax', 1)} | Formule: {data.get('Formule', '')}", ln=True)
    
    if options_text:
        pdf.set_font("Helvetica", 'I', 7)
        pdf.multi_cell(0, 4, f"Details: {options_text}")
    
    pdf.ln(2)
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, f"TOTAL: {float(data.get('Total', 0)):.2f} EUR", ln=True, align='R')
    pdf.ln(2); pdf.cell(0, 0, "-"*45, ln=True, align='C'); pdf.ln(2)
    
    ribs = get_rib()
    for _, row in ribs.iterrows():
        pdf.cell(0, 4, f"{row['Banque']}: {row['IBAN/RIB']}", ln=True)
    
    # Conversion finale sécurisée en bytes
    out = pdf.output()
    return bytes(out) if isinstance(out, (bytearray, bytes)) else str(out).encode('latin-1')

# --- Interface ---
tab1, tab2, tab3 = st.tabs(["📝 DEVIS", "🧾 FACTURE", "⚙️ CONFIG"])

with tab1:
    df_excu = pd.read_csv("data.csv")
    nom_c = st.text_input("👤 Client", key="nom_devis")
    type_e = st.selectbox("🌍 Type", [""] + sorted(df_excu["Type"].unique().tolist()))
    
    if type_e:
        df_f = df_excu[df_excu["Type"] == type_e]
        circuit = st.selectbox("📍 Circuit", sorted(df_f["Circuit"].unique().tolist()))
        row_d = df_f[df_f["Circuit"] == circuit].iloc[0]
        
        nb_pax = st.number_input("👥 Pax", min_value=1, value=1)
        total_ttc = (row_d['Prix'] * nb_pax) # Simplifié pour le test
        
        if st.button("🔥 GENERER LE DEVIS"):
            ref = generate_custom_ref(nom_c, "D")
            pdf_bytes = generate_thermal_ticket("Devis", {"Circuit": circuit, "Pax": nb_pax, "Total": total_ttc}, nom_c, ref)
            
            # Sauvegarde historique
            pd.DataFrame([{"Ref": ref, "Client": nom_c, "Total": total_ttc}]).to_csv(HIST_FILE, mode='a', header=not os.path.exists(HIST_FILE), index=False)
            
            # APERÇU
            base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
            st.markdown(f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="400"></iframe>', unsafe_allow_html=True)
            
            # TÉLÉCHARGEMENT
            st.download_button("🖨️ TELECHARGER PDF", data=pdf_bytes, file_name=f"{ref}.pdf", mime="application/pdf")

with tab2:
    if os.path.exists(HIST_FILE):
        df_h = pd.read_csv(HIST_FILE)
        sel_ref = st.selectbox("Devis à convertir", df_h['Ref'].tolist())
        if st.button("📄 GENERER FACTURE"):
            f_data = df_h[df_h['Ref'] == sel_ref].iloc[0]
            ref_f = sel_ref.replace("D", "F")
            pdf_f = generate_thermal_ticket("Facture", {"Circuit": "Excursion", "Pax": 1, "Total": f_data['Total']}, f_data['Client'], ref_f)
            
            base64_f = base64.b64encode(pdf_f).decode('utf-8')
            st.markdown(f'<iframe src="data:application/pdf;base64,{base64_f}" width="100%" height="400"></iframe>', unsafe_allow_html=True)
            st.download_button("🖨️ TELECHARGER FACTURE", data=pdf_f, file_name=f"{ref_f}.pdf", mime="application/pdf")

with tab3:
    if st.button("🗑️ RESET COMPTEURS"):
        if os.path.exists(HIST_FILE): os.remove(HIST_FILE)
        st.rerun()
