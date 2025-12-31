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
LOGO_FILE = "logo.png"

# --- INITIALISATION MÉMOIRE (SESSION STATE) ---
if 'df_h' not in st.session_state:
    if os.path.exists(HIST_FILE):
        try:
            st.session_state.df_h = pd.read_csv(HIST_FILE, encoding='utf-8-sig')
        except:
            st.session_state.df_h = pd.DataFrame(columns=["Date", "Ref", "Client", "Contact", "Circuit", "Pax", "Total", "Formule", "Options"])
    else:
        st.session_state.df_h = pd.DataFrame(columns=["Date", "Ref", "Client", "Contact", "Circuit", "Pax", "Total", "Formule", "Options"])

def reset_app():
    st.rerun()

# --- Fonctions Fichiers ---
def get_info_df():
    if os.path.exists(INFO_FILE): 
        return pd.read_csv(INFO_FILE, encoding='utf-8-sig')
    return pd.DataFrame([["Nom", "LAKA AM'LAY"], ["Contact", "+261"]], columns=['Champ', 'Valeur'])

def get_rib():
    if os.path.exists(RIB_FILE): 
        return pd.read_csv(RIB_FILE, encoding='utf-8-sig')
    return pd.DataFrame(columns=["Banque", "IBAN/RIB"])

def generate_custom_ref(client_name, prefix="D"):
    count = len(st.session_state.df_h) + 1
    clean_name = "".join(filter(str.isalnum, client_name)).upper()
    return f"{prefix}{count:06d}-{clean_name}"

# --- Génération Ticket ---
def generate_thermal_ticket(type_doc, data, client_name, ref, contact="", options_text=""):
    pdf = FPDF(format=(80, 250))
    pdf.add_page()
    pdf.set_margins(4, 4, 4)
    
    if os.path.exists(LOGO_FILE):
        pdf.image(LOGO_FILE, x=25, y=10, w=30)
        pdf.ln(35)
    
    df_infos = get_info_df()
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(72, 8, str(df_infos.iloc[0]['Valeur']), ln=True, align='C')
    pdf.set_font("Helvetica", '', 8)
    for i in range(1, len(df_infos)):
        pdf.cell(72, 4, f"{df_infos.iloc[i]['Champ']}: {df_infos.iloc[i]['Valeur']}", ln=True, align='C')
    
    pdf.ln(2); pdf.cell(72, 0, "-"*45, ln=True, align='C'); pdf.ln(2)
    
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(72, 6, f"{type_doc.upper()}", ln=True, align='C')
    pdf.set_font("Helvetica", '', 8)
    pdf.set_x(4)
    pdf.cell(72, 5, f"Date: {datetime.now().strftime('%d/%m/%y %H:%M')}", ln=True, align='L')
    pdf.set_x(4)
    pdf.cell(72, 5, f"Ref: {ref}", ln=True, align='L')
    pdf.set_x(4)
    pdf.cell(72, 5, f"Client: {client_name}", ln=True, align='L')
    if contact:
        pdf.set_x(4)
        pdf.cell(72, 5, f"Contact: {contact}", ln=True, align='L')
    
    pdf.ln(2); pdf.cell(72, 0, "-"*45, ln=True, align='C'); pdf.ln(2)
    
    pdf.set_font("Helvetica", 'B', 9)
    pdf.set_x(4)
    pdf.multi_cell(72, 5, f"Circuit: {data.get('Circuit', 'N/A')}", align='L')
    
    pdf.set_font("Helvetica", '', 8)
    pdf.set_x(4)
    pdf.cell(72, 5, f"Pax: {data.get('Pax', 1)} | Formule: {data.get('Formule', '')}", ln=True, align='L')
    
    if options_text and str(options_text) != "nan":
        pdf.set_font("Helvetica", 'I', 7)
        pdf.set_x(4)
        pdf.multi_cell(72, 4, f"Options: {options_text}", align='L')
    
    pdf.ln(2)
    pdf.set_font("Helvetica", 'B', 12)
    pdf.set_x(4)
    pdf.cell(72, 10, f"TOTAL: {float(data.get('Total', 0)):.2f} EUR", ln=True, align='R')
    pdf.ln(2); pdf.cell(72, 0, "-"*45, ln=True, align='C'); pdf.ln(2)
    
    ribs = get_rib()
    if not ribs.empty:
        pdf.set_font("Helvetica", 'B', 7)
        pdf.set_x(4)
        pdf.cell(72, 4, "COORDONNEES BANCAIRES:", ln=True, align='L')
        pdf.set_font("Helvetica", '', 7)
        for _, row in ribs.iterrows():
            pdf.set_x(4)
            pdf.cell(72, 4, f"{row['Banque']}: {row['IBAN/RIB']}", ln=True, align='L')
    
    pdf.ln(5); pdf.set_font("Helvetica", 'I', 8)
    pdf.cell(72, 5, "Merci de votre confiance !", ln=True, align='C')
    
    out = pdf.output()
    return bytes(out) if isinstance(out, (bytes, bytearray)) else str(out).encode('latin-1')

# =========================
# INTERFACE
# =========================
tab1, tab2, tab3 = st.tabs(["📝 DEVIS", "🧾 FACTURE", "⚙️ CONFIG"])

with tab1:
    try:
        df_excu = pd.read_csv("data.csv", encoding='utf-8-sig')
        nom_c = st.text_input("👤 Nom du Client", key="n_cl")
        cont_c = st.text_input("📱 WhatsApp / Email", key="c_cl")
        
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
                    visite = st.checkbox("🎫 Visite Sites (+5€/site)")
                    if visite:
                        nb_sites = st.number_input("Nombre de sites", min_value=1, value=1)
                        supplements += (5 * nb_sites)
                        opts_list.append(f"Visite ({nb_sites} sites)")
                if repas: supplements += 10; opts_list.append("Repas")
                if guide: supplements += 15; opts_list.append("Guide")
            else:
                opts_list.append("Sortie Mer")

            nb_pax = st.number_input("👥 Pax", min_value=1, value=1)
            marge = st.slider("📈 Marge %", 0, 100, 20)
            total_ttc = ((float(row_d['Prix']) + supplements) * nb_pax) * (1 + marge/100)
            st.metric("TOTAL", f"{total_ttc:.2f} €")

            if st.button("🔥 GENERER LE TICKET"):
                if not nom_c: st.error("Nom obligatoire")
                else:
                    ref_d = generate_custom_ref(nom_c, "D")
                    opts_txt = ", ".join(opts_list)
                    
                    # --- SAUVEGARDE EN MÉMOIRE ET SUR DISQUE ---
                    new_row = {
                        "Date": datetime.now().strftime("%Y-%m-%d"),
                        "Ref": ref_d,
                        "Client": nom_c,
                        "Contact": cont_c,
                        "Circuit": circuit,
                        "Pax": nb_pax,
                        "Total": round(total_ttc, 2),
                        "Formule": formule,
                        "Options": opts_txt
                    }
                    st.session_state.df_h = pd.concat([st.session_state.df_h, pd.DataFrame([new_row])], ignore_index=True)
                    st.session_state.df_h.to_csv(HIST_FILE, index=False, encoding='utf-8-sig')
                    
                    st.success(f"Devis {ref_d} enregistré !")
                    
                    # Génération PDF
                    pdf_bytes = generate_thermal_ticket("Devis", new_row, nom_c, ref_d, cont_c, opts_txt)
                    b64 = base64.b64encode(pdf_bytes).decode('utf-8')
                    st.markdown(f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="400"></iframe>', unsafe_allow_html=True)
                    st.download_button("🖨️ TELECHARGER", data=pdf_bytes, file_name=f"{ref_d}.pdf", mime="application/pdf")
            
            if st.button("➕ NOUVEAU DEVIS"): reset_app()
    except Exception as e: st.info("Saisie en cours...")

with tab2:
    if not st.session_state.df_h.empty:
        df_h = st.session_state.df_h
        devis_list = [r for r in df_h['Ref'].unique() if str(r).startswith("D")]
        sel_ref = st.selectbox("Choisir Devis à facturer", [""] + devis_list[::-1]) # Inversé pour voir le plus récent
        
        if sel_ref:
            f_data = df_h[df_h['Ref'] == sel_ref].iloc[0]
            ref_f = sel_ref.replace("D", "F", 1)
            c_val = str(f_data['Contact']) if 'Contact' in f_data else ""
            opt_val = str(f_data['Options']) if 'Options' in f_data else ""
            
            if st.button("📄 GENERER FACTURE"):
                pdf_f = generate_thermal_ticket("Facture", f_data.to_dict(), f_data['Client'], ref_f, c_val, opt_val)
                b64_f = base64.b64encode(pdf_f).decode('utf-8')
                st.markdown(f'<iframe src="data:application/pdf;base64,{b64_f}" width="100%" height="400"></iframe>', unsafe_allow_html=True)
                st.download_button("🖨️ TELECHARGER FACTURE", data=pdf_f, file_name=f"{ref_f}.pdf", mime="application/pdf")
    else:
        st.info("Aucun historique trouvé.")

with tab3:
    if st.button("🗑️ RESET HISTORIQUE"):
        if os.path.exists(HIST_FILE): os.remove(HIST_FILE)
        st.session_state.df_h = pd.DataFrame(columns=["Date", "Ref", "Client", "Contact", "Circuit", "Pax", "Total", "Formule", "Options"])
        st.rerun()
    st.divider()
    df_i = get_info_df(); new_i = st.data_editor(df_i, num_rows="dynamic")
    if st.button("Sauver Infos"): new_i.to_csv(INFO_FILE, index=False, encoding='utf-8-sig')
    st.divider()
    df_r = get_rib(); new_r = st.data_editor(df_r, num_rows="dynamic")
    if st.button("Sauver RIB"): new_r.to_csv(RIB_FILE, index=False, encoding='utf-8-sig')
