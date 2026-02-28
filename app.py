import streamlit as st
import sqlite3
import pandas as pd
from fpdf import FPDF
from datetime import datetime

# Deve essere sempre il primo comando Streamlit
st.set_page_config(page_title="App Plicometria", layout="wide")

# --- INIZIALIZZAZIONE MESSAGGI DI SUCCESSO ---
if 'success_msg' not in st.session_state:
    st.session_state.success_msg = ""

# --- 1. CONFIGURAZIONE DATABASE LOCALE ---
# Usiamo v4 per includere la nuova colonna bf_media senza far crashare i vecchi db
conn = sqlite3.connect('db_plicometria_v4.db', check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS clienti (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT UNIQUE,
    eta INTEGER,
    sesso TEXT,
    altezza REAL
)''')

c.execute('''CREATE TABLE IF NOT EXISTS misurazioni (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER,
    data TEXT,
    peso REAL,
    polpaccio_circ REAL, polpaccio_plico REAL,
    coscia_circ REAL, coscia_plico REAL,
    vita_circ REAL, vita_plico REAL,
    spalle_circ REAL, spalle_plico REAL,
    schiena_circ REAL, schiena_plico REAL,
    braccio_circ REAL, braccio_plico REAL,
    bf_media REAL,
    FOREIGN KEY(cliente_id) REFERENCES clienti(id)
)''')
conn.commit()

# --- 2. FUNZIONE PER GENERARE IL PDF ---
def genera_pdf(dati_cliente, df_storico):
    pdf = FPDF()
    pdf.add_page()
    
    pdf.set_font("Arial", style="B", size=16)
    pdf.cell(200, 10, txt=f"Report Completo: {dati_cliente['nome']}", ln=True, align="C")
    pdf.ln(5)
    
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 8, txt=f"Eta: {dati_cliente['eta']} anni | Sesso: {dati_cliente['sesso']} | Altezza: {dati_cliente['altezza']} cm", ln=True)
    pdf.ln(5)
    
    if not df_storico.empty:
        ultimi_dati = df_storico.iloc[-1]
        pdf.set_font("Arial", style="B", size=14)
        pdf.cell(200, 10, txt=f"Situazione Attuale (Data: {ultimi_dati['data']})", ln=True)
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 8, txt=f"Peso: {ultimi_dati['peso']} kg", ln=True)
        
        # Aggiungiamo il dato saliente in evidenza!
        pdf.set_font("Arial", style="B", size=12)
        pdf.set_text_color(0, 100, 0) # Verde scuro
        pdf.cell(200, 8, txt=f"BF Totale Media: {ultimi_dati['bf_media']:.1f} %", ln=True)
        pdf.set_text_color(0, 0, 0) # Ritorna nero
        pdf.ln(2)
        
        pdf.set_font("Arial", style="B", size=10)
        pdf.cell(50, 8, "Parte del corpo", border=1)
        pdf.cell(50, 8, "Circonferenza (cm)", border=1)
        pdf.cell(50, 8, "BF / Plico (mm)", border=1, ln=True)
        
        pdf.set_font("Arial", size=10)
        parti = ['polpaccio', 'coscia', 'vita', 'spalle', 'schiena', 'braccio']
        for p in parti:
            circ = ultimi_dati[f"{p}_circ"]
            plico = ultimi_dati[f"{p}_plico"]
            pdf.cell(50, 8, p.capitalize(), border=1)
            pdf.cell(50, 8, str(circ), border=1)
            pdf.cell(50, 8, str(plico), border=1, ln=True)
            
        pdf.ln(10)
        
        pdf.set_font("Arial", style="B", size=14)
        pdf.cell(200, 10, txt="Storico Registrazioni:", ln=True)
        pdf.set_font("Arial", size=10)
        for index, row in df_storico.iterrows():
            pdf.cell(200, 6, txt=f"Data: {row['data']} | Peso: {row['peso']}kg | BF Media: {row['bf_media']:.1f}%", ln=True)
    else:
        pdf.cell(200, 10, txt="Nessuna misurazione presente.", ln=True)
        
    return bytes(pdf.output())

# --- 3. INTERFACCIA WEB (STREAMLIT) ---
st.title("Plicometria 📊")

if st.session_state.success_msg != "":
    st.success(st.session_state.success_msg)
    st.session_state.success_msg = ""

df_clienti = pd.read_sql_query("SELECT * FROM clienti", conn)

tab1, tab2, tab3 = st.tabs(["➕ Nuovo Cliente", "📝 Aggiungi Misurazione", "📈 Storico e Stampa"])

# --- SCHEDA 1: NUOVO CLIENTE ---
with tab1:
    st.subheader("Registra una nuova persona")
    nuovo_nome = st.text_input("Nome e Cognome (o Nickname)")
    
    col1, col2, col3 = st.columns(3)
    eta = col1.number_input("Età", min_value=1, max_value=120, step=1)
    sesso = col2.selectbox("Sesso", ["M", "F"])
    altezza = col3.number_input("Altezza (cm)", min_value=50.0, max_value=250.0, format="%.1f")
    
    if st.button("Salva Cliente"):
        if nuovo_nome.strip() == "":
            st.warning("Devi inserire un nome!")
        else:
            try:
                c.execute("INSERT INTO clienti (nome, eta, sesso, altezza) VALUES (?, ?, ?, ?)", 
                          (nuovo_nome.strip(), int(eta), sesso, float(altezza)))
                conn.commit()
                st.session_state.success_msg = f"✅ Cliente '{nuovo_nome}' registrato con successo!"
                st.rerun()
            except sqlite3.IntegrityError:
                st.error("⚠️ ERRORE: Questa persona è già presente nel database! Vai nelle altre schede per aggiungere misurazioni.")

# --- SCHEDA 2: MISURAZIONI ---
with tab2:
    st.subheader("Inserisci le misure correnti")
    if not df_clienti.empty:
        cliente_scelto = st.selectbox("Seleziona Cliente", df_clienti['nome'].tolist(), key="sel_misure")
        cliente_id = int(df_clienti.loc[df_clienti['nome'] == cliente_scelto, 'id'].values[0])
        
        peso = st.number_input("Peso attuale (kg)", min_value=0.0, format="%.1f")
        
        st.write("---")
        st.write("### Circonferenze e BF (Pliche)")
        
        parti_del_corpo = ['polpaccio', 'coscia', 'vita', 'spalle', 'schiena', 'braccio']
        misure_input = {}
        
        for p in parti_del_corpo:
            st.write(f"**{p.capitalize()}**")
            c1, c2 = st.columns(2)
            circ = c1.number_input(f"Circonferenza (cm) - {p}", min_value=0.0, format="%.1f", key=f"c_{p}")
            plico = c2.number_input(f"BF / Plico - {p}", min_value=0.0, format="%.1f", key=f"p_{p}")
            misure_input[p] = (circ, plico)
        
        if st.button("Salva Misurazione"):
            data_oggi = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # --- CALCOLO DELLA BF MEDIA ARITMETICA ---
            somma_bf = sum([misure_input[p][1] for p in parti_del_corpo])
            bf_media = somma_bf / 6.0
            
            c.execute('''INSERT INTO misurazioni (
                cliente_id, data, peso, 
                polpaccio_circ, polpaccio_plico, coscia_circ, coscia_plico, 
                vita_circ, vita_plico, spalle_circ, spalle_plico, 
                schiena_circ, schiena_plico, braccio_circ, braccio_plico, bf_media
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (
                cliente_id, data_oggi, float(peso),
                float(misure_input['polpaccio'][0]), float(misure_input['polpaccio'][1]),
                float(misure_input['coscia'][0]), float(misure_input['coscia'][1]),
                float(misure_input['vita'][0]), float(misure_input['vita'][1]),
                float(misure_input['spalle'][0]), float(misure_input['spalle'][1]),
                float(misure_input['schiena'][0]), float(misure_input['schiena'][1]),
                float(misure_input['braccio'][0]), float(misure_input['braccio'][1]),
                float(bf_media) # Salviamo la media!
            ))
            conn.commit()
            
            st.session_state.success_msg = f"✅ Misure salvate! BF Media calcolata: {bf_media:.1f}%"
            st.rerun()
    else:
        st.info("Nessun cliente registrato.")

# --- SCHEDA 3: STORICO, GRAFICI E STAMPA ---
with tab3:
    st.subheader("Analisi Andamento e PDF")
    if not df_clienti.empty:
        cliente_stampa = st.selectbox("Seleziona Cliente", df_clienti['nome'].tolist(), key="sel_stampa")
        dati_cliente = df_clienti[df_clienti['nome'] == cliente_stampa].iloc[0]
        cliente_id_stampa = int(dati_cliente['id'])
        
        df_storico = pd.read_sql_query(f"SELECT * FROM misurazioni WHERE cliente_id = {cliente_id_stampa} ORDER BY data ASC", conn)
        
        if not df_storico.empty:
            # --- CALCOLI AVANZATI PER IL GRAFICO ---
            # Calcoliamo la massa muscolare (Massa Magra) sottraendo la % di BF media dal peso
            df_storico['massa_magra_kg'] = df_storico['peso'] * (1 - (df_storico['bf_media'] / 100))
            
            # Calcoliamo il rapporto richiesto (Massa Muscolare / BF). Evitiamo divisioni per zero.
            df_storico['rapporto_muscolo_bf'] = df_storico.apply(
                lambda row: row['massa_magra_kg'] / row['bf_media'] if row['bf_media'] > 0 else 0, axis=1
            )
            
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.write("### Andamento BF Totale Media (%)")
                df_grafico_bf = df_storico.set_index('data')
                st.line_chart(df_grafico_bf[['bf_media']])
                
            with col_g2:
                st.write("### Rapporto Massa Muscolare / BF")
                st.caption("Se il grafico sale = stai mettendo muscolo e perdendo grasso! 💪")
                df_grafico_rapporto = df_storico.set_index('data')
                st.line_chart(df_grafico_rapporto[['rapporto_muscolo_bf']])
            
            st.write("### Tabella Completa Dati")
            # Mostriamo solo le colonne più utili per non intasare la vista
            colonne_da_mostrare = ['data', 'peso', 'bf_media', 'massa_magra_kg', 'rapporto_muscolo_bf']
            st.dataframe(df_storico[colonne_da_mostrare], use_container_width=True)
            
            pdf_bytes = genera_pdf(dati_cliente, df_storico)
            st.download_button(
                label="🖨️ Scarica PDF Completo",
                data=pdf_bytes,
                file_name=f"Report_{cliente_stampa}.pdf",
                mime="application/pdf"
            )
        else:
            st.info("⚠️ Nessuna misurazione presente per questo cliente.")