import streamlit as st
import pandas as pd
import uuid
from fpdf import FPDF
import os
from datetime import datetime
import base64

# =========================
# CONFIGURATION
# =========================
st.set_page_config(page_title="Laka Am'lay POS", layout="centered")

st.markdown("""
    <style>
    .stButton>button { width: 100%; height: 3.5em; font-size: 16px !important; border-radius: 10px; margin-top: 10px; }
    iframe { border-radius: 10px; border: 1px solid #ddd; background-color: white; }
    [data-testid="stMetricValue"] { font-size: 32px; color: #1e88e5; }
    </style>
    """, unsafe_allow_html=True)

HIST_FILE = "historique_devis.csv"
INFO_FILE = "infos.csv"
RIB_FILE = "rib_agence.csv"

def reset_app():
    st.rerun()

# --- Fonctions Fichiers ---
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

# --- Génération Ticket Sécurisée ---
def generate_thermal_ticket(type_doc, data, client_name, ref, contact="", options_text=""):
    pdf = FPDF(format=(80, 250))
    pdf.add_page()
    pdf.set_margins(4, 4, 4)
    df_infos = get_info_df()
    
    # En-tête Agence
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 8, str(df_infos.iloc[0]['Valeur']), ln=True, align='C')
    pdf.set_font("Helvetica", '', 8)
    for i in range(1, len(df_infos)):
        pdf.cell(0, 4, f"{df_infos.iloc[i]['Champ']}: {df_infos.iloc[i]['Valeur']}", ln=True, align='C')
    
    pdf.ln(2); pdf.cell(0, 0, "-"*45, ln=True, align='C'); pdf.ln(2)
    
    # Infos Document & Client
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(0, 6, f"{type_doc.upper()}", ln=True, align='C')
    pdf.set_font("Helvetica", '', 8)
    pdf.cell(0, 5, f"Date: {datetime.now().strftime('%d/%m/%y %H:%M')}", ln=True)
    pdf.cell(0, 5, f"Ref: {ref}", ln=True)
    pdf.cell(0, 5, f"Client: {client_name}", ln=True)
    if contact:
        pdf.cell(0, 5, f"Contact: {contact}", ln=True)
    
    pdf.ln(2); pdf.cell(0, 0, "-"*45, ln=True, align='C'); pdf.ln(2)
    
    # Détails Prestation
    pdf.set_font("Helvetica", 'B', 9)
    pdf.multi_cell(0, 5, f"Circuit: {data.get('Circuit', 'N/A')}")
    pdf.set_font("Helvetica", '', 8)
    pdf.cell(0, 5, f"Pax: {data.get('Pax', 1)} | Formule: {data.get('Formule', '')}", ln=True)
    
    if options_text:
        pdf.set_font("Helvetica", 'I', 7)
        pdf.multi_cell(0, 4, f"Options: {options_text}")
    
    pdf.ln(2)
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, f"TOTAL: {float(data.get('Total', 0)):.2f} EUR", ln=True, align='R')
    pdf.ln(2); pdf.cell(0, 0, "-"*45, ln=True, align='C'); pdf.ln(2)
    
    # RIB
    pdf.set_font("Helvetica", 'B', 7)
    pdf.cell(0, 4, "COORDONNEES BANCAIRES:", ln=True)
    pdf.set_font("Helvetica", '', 7)
    ribs = get_rib()
    for _, row in ribs.iterrows():
        pdf.cell(0, 4, f"{row['Banque']}: {row['IBAN/RIB']}", ln=True)
    
    pdf.ln(5); pdf.set_font("Helvetica", 'I', 8)
    pdf.cell(0, 5, "Merci de votre confiance !", ln=True, align='C')
    
    # Sortie en BYTES pour Streamlit
    out = pdf.output()
    if isinstance(out, (bytes, bytearray)):
        return bytes(out)
    return str(out).encode('latin-1')

# =========================
# INTERFACE
# =========================
tab1, tab2, tab3 = st.tabs(["📝 DEVIS", "🧾 FACTURE", "⚙️ CONFIG"])

with tab1:
    try:
        df_excu = pd.read_csv("data.csv")
        nom_c = st.text_input("👤 Nom du Client", key="nom_devis")
        contact_c = st.text_input("📱 WhatsApp ou Email", key="contact_devis")
        
        type_e = st.selectbox("🌍 Type d'excursion", [""] + sorted(df_excu["Type"].unique().tolist()))
        
        if type_e:
            df_f = df_excu[df_excu["Type"] == type_e]
            formule = st.selectbox("💎 Formule", sorted(df_f["Formule"].unique().tolist()))
            transport = st.selectbox("🚗 Transport", sorted(df_f[df_f["Formule"] == formule]["Transport"].unique().tolist()))
            circuit = st.selectbox("📍 Circuit", sorted(df_f[(df_f["Formule"] == formule) & (df_f["Transport"] == transport)]["Circuit"].unique().tolist()))
            row_d = df_f[df_f["Circuit"] == circuit].iloc[0]
            
            # Gestion des Options
            supplements = 0
            opts_list = [f"Transp: {transport}"]
            if type_e.lower() == "terrestre":
                col1, col2 = st.columns(2)
                with col1:
                    repas = st.checkbox("🍽️ Repas (+10€)")
                    guide = st.checkbox("🧭 Guide (+15€)")
                with col2:
                    visite = st.checkbox("🎫 Visite Sites (+5€/site)")
                    nb_sites = 1
                    if visite:
                        nb_sites = st.number_input("Nombre de sites", min_value=1, value=1)
                        supplements += (5 * nb_sites)
                        opts_list.append(f"Visite ({nb_sites} sites)")
                if repas: supplements += 10; opts_list.append("Repas")
                if guide: supplements += 15; opts_list.append("Guide")
            else:
                st.success("✅ Pack Mer Tout Inclus")
                opts_list.append("Sortie Mer")

            nb_pax = st.number_input("👥 Nombre de Pax", min_value=1, value=1)
            marge = st.slider("📈 Marge Agence %", 0, 100, 20)
            
            total_ttc = ((row_d['Prix'] + supplements) * nb_pax) * (1 + marge/100)
            st.metric("TOTAL À PAYER", f"{total_ttc:.2f} €")

            if st.button("🔥 GENERER LE TICKET DEVIS"):
                if not nom_c:
                    st.error("Veuillez saisir le nom du client")
                else:
                    ref_d = generate_custom_ref(nom_c, "D")
                    opts_text = ", ".join(opts_list)
                    pdf_bytes = generate_thermal_ticket("Devis", {"Circuit": circuit, "Pax": nb_pax, "Formule": formule, "Total": total_ttc}, nom_c, ref_d, contact_c, opts_text)
                    
                    # Sauvegarde historique
                    new_entry = {"Date": datetime.now().strftime("%Y-%m-%d"), "Ref": ref_d, "Client": nom_c, "Contact": contact_c, "Circuit": circuit, "Pax": nb_pax, "Total": round(total_ttc, 2), "Formule": formule, "Options": opts_text}
                    pd.DataFrame([new_entry]).to_csv(HIST_FILE, mode='a', header=not os.path.exists(HIST_FILE), index=False, encoding='utf-8-sig')
                    
                    # Aperçu
                    b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
                    st.markdown(f'<iframe src="data:application/pdf;base64,{b64_pdf}" width="100%" height="400"></iframe>', unsafe_allow_html=True)
                    
                    # Bouton Télécharger
                    st.download_button(label="🖨️ TELECHARGER LE DEVIS", data=pdf_bytes, file_name=f"{ref_d}.pdf", mime="application/pdf")
            
            if st.button("➕ NOUVEAU DEVIS"): reset_app()
    except Exception as e:
        st.info("Sélectionnez les options pour calculer.")

with tab2:
    if os.path.exists(HIST_FILE):
        df_h = pd.read_csv(HIST_FILE)
        devis_list = [r for r in df_h['Ref'].unique() if r.startswith("D")]
        sel_ref = st.selectbox("Convertir un devis en facture", [""] + devis_list)
        
        if sel_ref:
            f_data = df_h[df_h['Ref'] == sel_ref].iloc[0]
            ref_f = sel_ref.replace("D", "F", 1)
            
            if st.button("📄 GENERER LA FACTURE"):
                pdf_fact = generate_thermal_ticket("Facture", f_data.to_dict(), f_data['Client'], ref_f, f_data.get('Contact', ''), f_data.get('Options', ''))
                
                b64_f = base64.b64encode(pdf_fact).decode('utf-8')
                st.markdown(f'<iframe src="data:application/pdf;base64,{b64_f}" width="100%" height="400"></iframe>', unsafe_allow_html=True)
                st.download_button(label="🖨️ TELECHARGER LA FACTURE", data=pdf_fact, file_name=f"{ref_f}.pdf", mime="application/pdf")
            
            if st.button("➕ NOUVELLE FACTURE"): reset_app()
    else:
        st.info("Aucun devis disponible.")

with tab3:
    st.subheader("Configuration")
    if st.button("🗑️ REMISE À ZÉRO (Prochain = D000001)"):
        if os.path.exists(HIST_FILE): os.remove(HIST_FILE)
        st.success("Historique effacé !")
    st.divider()
    df_i = get_info_df(); new_i = st.data_editor(df_i, num_rows="dynamic")
    if st.button("Sauver En-tête"): new_i.to_csv(INFO_FILE, index=False)
