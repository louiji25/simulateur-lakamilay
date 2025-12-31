import streamlit as st
import pandas as pd
import os
from fpdf import FPDF
from datetime import datetime
import base64

# =========================
# CONFIGURATION
# =========================
st.set_page_config(page_title="Laka Am'lay POS", layout="centered")

HIST_FILE = "historique_devis.csv"
LOGO_FILE = "logo.png"

# --- INITIALISATION DE LA MÉMOIRE (SESSION STATE) ---
if 'df_h' not in st.session_state:
    if os.path.exists(HIST_FILE):
        st.session_state.df_h = pd.read_csv(HIST_FILE, encoding='utf-8-sig')
    else:
        st.session_state.df_h = pd.DataFrame(columns=["Date", "Ref", "Client", "Contact", "Circuit", "Pax", "Total", "Formule", "Options"])

def save_devis(new_row):
    # 1. Ajouter à la mémoire vive
    st.session_state.df_h = pd.concat([st.session_state.df_h, pd.DataFrame([new_row])], ignore_index=True)
    # 2. Sauvegarder sur le disque
    st.session_state.df_h.to_csv(HIST_FILE, index=False, encoding='utf-8-sig')

def generate_custom_ref(client_name):
    count = len(st.session_state.df_h) + 1
    clean_name = "".join(filter(str.isalnum, client_name)).upper()
    return f"D{count:06d}-{clean_name}"

# --- FONCTION PDF (Simplifiée pour test) ---
def generate_thermal_ticket(type_doc, data, client_name, ref, contact="", options_text=""):
    pdf = FPDF(format=(80, 200))
    pdf.add_page()
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(72, 8, "LAKA AM'LAY", ln=True, align='C')
    pdf.ln(5)
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(72, 6, f"{type_doc.upper()} : {ref}", ln=True)
    pdf.set_font("Helvetica", '', 9)
    pdf.cell(72, 5, f"Client: {client_name}", ln=True)
    pdf.cell(72, 5, f"Contact: {contact}", ln=True)
    pdf.ln(2)
    pdf.multi_cell(72, 5, f"Circuit: {data.get('Circuit')}")
    pdf.cell(72, 5, f"Pax: {data.get('Pax')} | {data.get('Formule')}", ln=True)
    pdf.ln(2)
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(72, 10, f"TOTAL: {data.get('Total'):.2f} EUR", ln=True, align='R')
    return bytes(pdf.output())

# =========================
# INTERFACE
# =========================
tab1, tab2, tab3 = st.tabs(["📝 DEVIS", "🧾 FACTURE", "⚙️ CONFIG"])

with tab1:
    try:
        df_excu = pd.read_csv("data.csv", encoding='utf-8-sig')
        nom_c = st.text_input("👤 Nom du Client")
        cont_c = st.text_input("📱 Contact")
        
        circuit = st.selectbox("📍 Circuit", df_excu["Circuit"].unique())
        row_d = df_excu[df_excu["Circuit"] == circuit].iloc[0]
        nb_pax = st.number_input("👥 Pax", min_value=1, value=1)
        total_ttc = float(row_d['Prix']) * nb_pax
        
        if st.button("🔥 GENERER ET ENREGISTRER"):
            if nom_c:
                ref_d = generate_custom_ref(nom_c)
                
                # DONNÉES À SAUVER
                new_data = {
                    "Date": datetime.now().strftime("%Y-%m-%d"),
                    "Ref": ref_d,
                    "Client": nom_c,
                    "Contact": cont_c,
                    "Circuit": circuit,
                    "Pax": nb_pax,
                    "Total": total_ttc,
                    "Formule": "Standard",
                    "Options": ""
                }
                
                # APPEL DE LA SAUVEGARDE
                save_devis(new_data)
                
                st.success(f"Enregistré sous la référence {ref_d}")
                
                # GENERATION PDF
                pdf_bytes = generate_thermal_ticket("Devis", new_data, nom_c, ref_d, cont_c)
                b64 = base64.b64encode(pdf_bytes).decode('utf-8')
                st.markdown(f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="400"></iframe>', unsafe_allow_html=True)
            else:
                st.error("Entrez le nom du client")
    except:
        st.error("Vérifiez votre fichier data.csv")

with tab2:
    st.subheader("Historique des Devis")
    # On utilise directement la mémoire vive (st.session_state)
    if not st.session_state.df_h.empty:
        df_display = st.session_state.df_h.copy()
        # On n'affiche que les Devis
        devis_only = df_display[df_display['Ref'].str.startswith("D", na=False)]
        
        sel_ref = st.selectbox("Sélectionner un devis pour facture", [""] + devis_only['Ref'].tolist())
        
        if sel_ref:
            f_data = devis_only[devis_only['Ref'] == sel_ref].iloc[0]
            if st.button("📄 Créer la Facture"):
                pdf_f = generate_thermal_ticket("Facture", f_data.to_dict(), f_data['Client'], sel_ref.replace("D", "F"), f_data['Contact'])
                b64_f = base64.b64encode(pdf_f).decode('utf-8')
                st.markdown(f'<iframe src="data:application/pdf;base64,{b64_f}" width="100%" height="400"></iframe>', unsafe_allow_html=True)
        
        st.divider()
        st.write("Derniers enregistrements :")
        st.table(st.session_state.df_h.tail(5))
    else:
        st.info("L'historique est vide.")

with tab3:
    if st.button("🗑️ RESET TOUT"):
        if os.path.exists(HIST_FILE): os.remove(HIST_FILE)
        st.session_state.df_h = pd.DataFrame(columns=["Date", "Ref", "Client", "Contact", "Circuit", "Pax", "Total", "Formule", "Options"])
        st.rerun()
