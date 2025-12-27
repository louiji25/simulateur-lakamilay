import streamlit as st
import pandas as pd
import uuid
from fpdf import FPDF
import os
from datetime import datetime
import base64
import urllib.parse

# =========================
# CONFIGURATION MOBILE
# =========================
st.set_page_config(page_title="Laka Am'lay POS", layout="centered")

# Style CSS pour les boutons
st.markdown("""
    <style>
    .stButton>button { width: 100%; height: 3.5em; font-size: 16px !important; border-radius: 10px; margin-top: 10px; }
    .btn-print { background-color: #FF4B4B !important; color: white !important; }
    .btn-new { background-color: #f0f2f6 !important; color: black !important; }
    .btn-whatsapp { background-color: #25D366 !important; color: white !important; }
    iframe { border-radius: 10px; border: 1px solid #ddd; }
    </style>
    """, unsafe_allow_html=True)

HIST_FILE = "historique_devis.csv"
INFO_FILE = "infos.csv"
RIB_FILE = "rib_agence.csv"

def reset_app():
    for key in st.session_state.keys():
        del st.session_state[key]
    st.rerun()

# --- Fonctions Fichiers ---
def get_info_df():
    if os.path.exists(INFO_FILE):
        return pd.read_csv(INFO_FILE)
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

# --- Génération Ticket ---
def generate_thermal_ticket(type_doc, data, client_name, ref, options_text=""):
    pdf = FPDF(format=(80, 250))
    pdf.add_page()
    pdf.set_margins(4, 4, 4)
    df_infos = get_info_df()
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, str(df_infos.iloc[0]['Valeur']), ln=True, align='C')
    pdf.set_font("Arial", '', 8)
    for i in range(1, len(df_infos)):
        pdf.cell(0, 4, f"{df_infos.iloc[i]['Champ']}: {df_infos.iloc[i]['Valeur']}", ln=True, align='C')
    pdf.ln(2); pdf.cell(0, 0, "-"*45, ln=True, align='C'); pdf.ln(2)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 6, f"{type_doc.upper()}", ln=True, align='C')
    pdf.set_font("Arial", '', 8)
    pdf.cell(0, 5, f"Date: {datetime.now().strftime('%d/%m/%y %H:%M')}", ln=True)
    pdf.cell(0, 5, f"Ref: {ref}", ln=True)
    pdf.cell(0, 5, f"Client: {client_name}", ln=True)
    pdf.ln(2); pdf.cell(0, 0, "-"*45, ln=True, align='C'); pdf.ln(2)
    pdf.set_font("Arial", 'B', 9)
    pdf.multi_cell(0, 5, f"Circuit: {data.get('Circuit', 'N/A')}")
    pdf.set_font("Arial", '', 8)
    pdf.cell(0, 5, f"Pax: {data.get('Pax', 1)} | Formule: {data.get('Formule', '')}", ln=True)
    if options_text:
        pdf.set_font("Arial", 'I', 7)
        pdf.multi_cell(0, 4, f"Détails: {options_text}")
    pdf.ln(2)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"TOTAL: {float(data.get('Total', 0)):.2f} EUR", ln=True, align='R')
    pdf.ln(2); pdf.cell(0, 0, "-"*45, ln=True, align='C'); pdf.ln(2)
    pdf.set_font("Arial", 'B', 7)
    pdf.cell(0, 4, "COORDONNEES BANCAIRES:", ln=True)
    pdf.set_font("Arial", '', 7)
    ribs = get_rib()
    for _, row in ribs.iterrows():
        pdf.cell(0, 4, f"{row['Banque']}: {row['IBAN/RIB']}", ln=True)
    pdf.ln(5); pdf.set_font("Arial", 'I', 8)
    pdf.cell(0, 5, "Merci de votre confiance !", ln=True, align='C')
    return pdf.output(dest='S').encode('latin-1')

# =========================
# INTERFACE
# =========================
tab1, tab2, tab3 = st.tabs(["📝 DEVIS", "🧾 FACTURE", "⚙️ CONFIG"])

with tab1:
    try:
        df_excu = pd.read_csv("data.csv")
        nom_c = st.text_input("👤 Client", key="nom_client_devis")
        tel_c = st.text_input("📱 WhatsApp (ex: 26132...)", key="tel_client_devis")
        type_e = st.selectbox("🌍 Type", [""] + sorted(df_excu["Type"].unique().tolist()))
        
        if type_e:
            df_f = df_excu[df_excu["Type"] == type_e]
            formule = st.selectbox("💎 Formule", sorted(df_f["Formule"].unique().tolist()))
            transport = st.selectbox("🚗 Transport", sorted(df_f[df_f["Formule"] == formule]["Transport"].unique().tolist()))
            circuit = st.selectbox("📍 Circuit", sorted(df_f[(df_f["Formule"] == formule) & (df_f["Transport"] == transport)]["Circuit"].unique().tolist()))
            row_d = df_f[df_f["Circuit"] == circuit].iloc[0]
            
            supplements = 0
            opts_list = [f"Transp: {transport}"]
            if type_e.lower() == "terrestre":
                col1, col2 = st.columns(2)
                with col1:
                    repas = st.checkbox("🍽️ Repas (+10€)")
                    guide = st.checkbox("🧭 Guide (+15€)")
                with col2:
                    visite = st.checkbox("🎫 Visite (+5€/site)")
                    if visite:
                        nb_sites = st.number_input("Nombre de sites", min_value=1, value=1)
                        supplements += (5 * nb_sites)
                        opts_list.append(f"Visite ({nb_sites} sites)")
                if repas: supplements += 10; opts_list.append("Repas")
                if guide: supplements += 15; opts_list.append("Guide")

            nb_pax = st.number_input("👥 Pax", min_value=1, value=1)
            marge = st.slider("📈 Marge %", 0, 100, 20)
            total_ttc = ((row_d['Prix'] + supplements) * nb_pax) * (1 + marge/100)
            st.metric("TOTAL TTC", f"{total_ttc:.2f} €")

            if st.button("🔥 GENERER LE DEVIS"):
                if not nom_c: st.error("Nom client obligatoire")
                else:
                    ref_final = generate_custom_ref(nom_c, "D")
                    opts_text = ", ".join(opts_list)
                    ticket_bytes = generate_thermal_ticket("Devis", {"Circuit": circuit, "Pax": nb_pax, "Formule": formule, "Total": total_ttc}, nom_c, ref_final, opts_text)
                    
                    # Sauvegarde
                    new_entry = {"Date": datetime.now().strftime("%Y-%m-%d"), "Ref": ref_final, "Client": nom_c, "Circuit": circuit, "Pax": nb_pax, "Total": round(total_ttc, 2), "Formule": formule, "Options": opts_text}
                    pd.DataFrame([new_entry]).to_csv(HIST_FILE, mode='a', header=not os.path.exists(HIST_FILE), index=False, encoding='utf-8-sig')
                    
                    # Affichage
                    base64_pdf = base64.b64encode(ticket_bytes).decode('utf-8')
                    st.markdown(f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="400"></iframe>', unsafe_allow_html=True)
                    
                    # Bouton Télécharger/Imprimer (Plus compatible mobile)
                    st.download_button(label="🖨️ TELECHARGER & IMPRIMER", data=ticket_bytes, file_name=f"{ref_final}.pdf", mime="application/pdf")
                    
                    # Bouton Nouveau
                    if st.button("➕ NOUVEAU DEVIS", key="btn_reset_devis"): reset_app()
    except Exception as e: st.info("Prêt pour un nouveau devis")

with tab2:
    st.subheader("Facturation")
    if os.path.exists(HIST_FILE):
        df_h = pd.read_csv(HIST_FILE)
        devis_list = [r for r in df_h['Ref'].unique() if r.startswith("D")]
        sel_ref = st.selectbox("Devis à convertir", [""] + devis_list)
        
        if sel_ref:
            f_data = df_h[df_h['Ref'] == sel_ref].iloc[0]
            ref_f = sel_ref.replace("D", "F", 1)
            
            if st.button("📄 GENERER LA FACTURE"):
                ticket_f = generate_thermal_ticket("Facture", f_data, f_data['Client'], ref_f, f_data.get('Options', ''))
                base64_f = base64.b64encode(ticket_f).decode('utf-8')
                st.markdown(f'<iframe src="data:application/pdf;base64,{base64_f}" width="100%" height="400"></iframe>', unsafe_allow_html=True)
                
                st.download_button(label="🖨️ TELECHARGER & IMPRIMER", data=ticket_f, file_name=f"{ref_f}.pdf", mime="application/pdf")
                
                if st.button("➕ NOUVELLE FACTURE"): reset_app()
    else: st.info("Aucun historique")

with tab3:
    st.subheader("Configuration")
    if st.button("🔄 RESET COMPLET"): reset_app()
    df_i = get_info_df()
    new_i = st.data_editor(df_i, num_rows="dynamic")
    if st.button("Sauver En-tête"): new_i.to_csv(INFO_FILE, index=False)