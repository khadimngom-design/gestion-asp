import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
from fpdf import FPDF
import io
import hashlib
import qrcode

# Configuration du fuseau horaire Africa/Dakar
DAKAR_TZ = ZoneInfo("Africa/Dakar")

st.set_page_config(page_title="Système National ASP Sénégal", layout="wide")

st.title("🇸🇳 Système Intégré de Gestion des Volontaires ASP")
st.markdown("### Direction des Ressources Humaines et de la Solde - Sénégal")

# --- DICTIONNAIRE OFFICIEL DES 14 RÉGIONS ET LEUR DÉPARTEMENT ---
regions_departements = {
    'Dakar': ['Dakar', 'Guédiawaye', 'Pikine', 'Rufisque', 'Keur Massar'],
    'Diourbel': ['Bambey', 'Diourbel', 'Mbacké'],
    'Fatick': ['Fatick', 'Foundiougne', 'Gossas'],
    'Kaffrine': ['Birkelane', 'Kaffrine', 'Koungheul', 'Malem Hodar'],
    'Kaolack': ['Guinguinéo', 'Kaolack', 'Nioro du Rip'],
    'Kédougou': ['Kédougou', 'Salémata', 'Saraya'],
    'Kolda': ['Kolda', 'Médina Yoro Foulah', 'Vélingara'],
    'Louga': ['Kébémer', 'Lingueré', 'Louga'],
    'Matam': ['Kanel', 'Matam', 'Ranérou-Ferlo'],
    'Saint-Louis': ['Dagana', 'Podor', 'Saint-Louis'],
    'Sédhiou': ['Bounkiling', 'Goudomp', 'Sédhiou'],
    'Tambacounda': ['Bakel', 'Goudiry', 'Koumpentoum', 'Tambacounda'],
    'Thiès': ['Mbour', 'Thiès', 'Tivaouane'],
    'Ziguinchor': ['Bignona', 'Oussouye', 'Ziguinchor']
}

regions_list = list(regions_departements.keys())

# --- 1. CHARGEMENT OPTIMISÉ DU FICHIER EXCEL (AVEC CACHE) ---
@st.cache_data
def charger_base_excel(nom_fichier):
    df_init = pd.read_excel(nom_fichier)
    df_init.columns = df_init.columns.str.strip()
    return df_init

if 'df_asp' not in st.session_state:
    nom_fichier_excel = "base_asp.xlsx"  # ⚠️ Mettez ici le nom exact de votre fichier Excel
    
    try:
        df_init = charger_base_excel(nom_fichier_excel)
        
        # --- MAPPINGS DES COLONNES VERS L'APPLICATION ---
        rennomages = {
            'Date Naissance': 'Date_Naissance',
            'Lieu Naissance': 'Lieu_Naissance',
            'Date Intégration': 'Date_Engagement',
            'État Agent': 'Statut_Agent',
            'Téléphone': 'Telephone',
            'Site': 'Lieu_Affectation'
        }
        df_init = df_init.rename(columns=rennomages)
        
        # Identification de la colonne CNI / Matricule réelle dans votre Excel
        colonnes_cni_possibles = ['CNI', 'Matricule_CNI', 'Matricule', 'Numéro CNI', 'Numero CNI', 'N_CNI']
        colonne_cni_trouvee = None
        for col in colonnes_cni_possibles:
            if col in df_init.columns:
                colonne_cni_trouvee = col
                break
                
        if colonne_cni_trouvee and colonne_cni_trouvee != 'Matricule_CNI':
            df_init['Matricule_CNI'] = df_init[colonne_cni_trouvee].astype(str)
        elif 'Matricule_CNI' not in df_init.columns:
            # Recherche d'une colonne contenant 'cni' ou 'identite' par défaut
            candidats = [c for c in df_init.columns if 'cni' in c.lower() or 'identite' in c.lower() or 'matricule' in c.lower()]
            if candidats:
                df_init['Matricule_CNI'] = df_init[candidats[0]].astype(str)
            else:
                st.error("🛑 Erreur critique : Aucune colonne de CNI ou de Matricule n'a été trouvée dans votre fichier Excel.")
                
        # Sécurité pour les autres colonnes obligatoires si absentes
        if 'Nom' not in df_init.columns:
            df_init['Nom'] = "Non renseigné"
        if 'Prénom' not in df_init.columns and 'Prenom' in df_init.columns:
            df_init['Prénom'] = df_init['Prenom']
        elif 'Prénom' not in df_init.columns:
            df_init['Prénom'] = "Non renseigné"
            
        if 'Région' not in df_init.columns:
            df_init['Région'] = 'Dakar'
        if 'Département' not in df_init.columns:
            df_init['Département'] = 'Dakar'

        # --- AJOUT DES COLONNES TECHNIQUES & FINANCIÈRES ---
        colonnes_techniques = {
            'Pécule_Base': 90000,
            'Beneficie_Prime': True,
            'Prime': 15000,
            'Cotisation_Mutuelle': 2500,
            'Retenue_Pret': 0,
            'Sanction_Discipline': 0,
            'Nombre_Avertissements': 0,
            'Historique_Discipline': "Aucun antécédent",
            'Motif_Action': "RAS",
            'Conges_Restants': 30,
            'Dernier_Conge_Debut': "-",
            'Dernier_Conge_Fin': "-",
            'Dernier_Conge_Jours': 0,
            'Canal_Paiement': 'Orange Money'
        }
        
        for col, val_defaut in colonnes_techniques.items():
            if col not in df_init.columns:
                df_init[col] = val_defaut
                
        def calculer_net(row):
            if str(row.get('Statut', 'Actif')) in ['Radié', 'Démissionnaire']:
                return 0
            prime_effective = row['Prime'] if row['Beneficie_Prime'] else 0
            net = row['Pécule_Base'] + prime_effective - row['Cotisation_Mutuelle'] - row['Retenue_Pret'] - row['Sanction_Discipline']
            return max(0, net)
            
        df_init['Net_A_Payer'] = df_init.apply(calculer_net, axis=1)
        st.session_state.df_asp = df_init
        st.success(f"✅ Base de données chargée avec succès : {len(df_init):,} agents importés.")

    except FileNotFoundError:
        st.error(f"🛑 Fichier introuvable : Le fichier **'{nom_fichier_excel}'** est introuvable. Veuillez le placer dans le même dossier.")
        st.session_state.df_asp = pd.DataFrame(columns=['Matricule_CNI', 'Nom', 'Prénom', 'Région', 'Département', 'Statut', 'Net_A_Payer'])

# --- 2. INITIALISATION DES ÉTATS DE SESSION & SÉCURITÉ ---
now_dakar = datetime.now(DAKAR_TZ)
current_session_id = f"PECULE-{now_dakar.year}-{now_dakar.month:02d}"

if 'sessions_db' not in st.session_state:
    st.session_state.sessions_db = {
        current_session_id: {
            "id": current_session_id, "annee": now_dakar.year, "mois": now_dakar.month,
            "statut": "OUVERTE", "date_ouverture": now_dakar.strftime("%Y-%m-%d %H:%M"),
            "date_cloture": None, "type_cloture": None, "archives_donnees": None
        }
    }

if 'session_active_id' not in st.session_state:
    st.session_state.session_active_id = current_session_id

if 'journal_audit' not in st.session_state:
    st.session_state.journal_audit = [{
        "Timestamp": now_dakar.strftime("%Y-%m-%d %H:%M:%S"),
        "Utilisateur": "Système Automatisé", "Action": "Ouverture session",
        "Session": current_session_id, "Détails": "Ouverture automatique session mensuelle"
    }]

if 'notifications_emails' not in st.session_state:
    st.session_state.notifications_emails = []

if 'user_role' not in st.session_state:
    st.session_state.user_role = "Gestionnaire RH"

if 'sanction_soumise_id' not in st.session_state:
    st.session_state.sanction_soumise_id = None

# --- 3. FONCTIONS UTILITAIRES ---
def enregistrer_audit(utilisateur, action, session_id, details):
    st.session_state.journal_audit.insert(0, {
        "Timestamp": datetime.now(DAKAR_TZ).strftime("%Y-%m-%d %H:%M:%S"),
        "Utilisateur": utilisateur, "Action": action, "Session": session_id, "Détails": details
    })

def calculer_jours_ouvres(date_debut, date_fin):
    if date_debut > date_fin:
        return 0
    feries_fixes = [(1, 1), (4, 4), (5, 1), (8, 15), (11, 1), (12, 25)]
    current = date_debut
    jours_ouvres = 0
    while current <= date_fin:
        if current.weekday() not in [5, 6] and (current.month, current.day) not in feries_fixes:
            jours_ouvres += 1
        current += timedelta(days=1)
    return jours_ouvres

df = st.session_state.df_asp
active_sid = st.session_state.session_active_id
session_courante = st.session_state.sessions_db[active_sid]
statut_session = session_courante["statut"]

def modification_autorisee():
    return statut_session in ["OUVERTE", "EN COURS DE CONTRÔLE", "ROUVERTE APRÈS CLÔTURE"]

# Sceau et QR Code
def generer_sceau_electronique(contenu_texte, signataire="Direction des Ressources Humaines (DRH - ASP)"):
    timestamp = datetime.now(DAKAR_TZ).strftime('%Y-%m-%d %H:%M:%S %Z')
    signature_base = f"{contenu_texte}-{signataire}-{timestamp}"
    hash_sceau = hashlib.sha256(signature_base.encode('utf-8')).hexdigest()[:32].upper()
    return f"--- DOCUMENT SIGNE ---\nSignataire: {signataire}\nSHA-256: {hash_sceau}", hash_sceau

def generer_image_qrcode(data_texte):
    qr = qrcode.QRCode(version=1, box_size=5, border=2)
    qr.add_data(data_texte)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    byte_io = io.BytesIO()
    img.save(byte_io, format='PNG')
    byte_io.seek(0)
    return byte_io

class PDFOfficiel(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 10)
        self.cell(0, 5, "REPUBLIQUE DU SENEGAL", 0, 1, 'C')
        self.set_font('Helvetica', '', 9)
        self.cell(0, 4, "Un peuple - Un But - Une Foi", 0, 1, 'C')
        self.cell(0, 4, "MINISTERE DE L'INTERIEUR - DIRECTION DE L'ASP", 0, 1, 'C')
        self.ln(8)
    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f"Page {self.page_no()} - Document officiel sécurisé", 0, 0, 'C')

def generer_pdf_attestation(type_attestation, agent):
    pdf = PDFOfficiel(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 12)
    titres = {"prise": "ATTESTATION DE PRISE EN SERVICE", "service": "ATTESTATION DE SERVICE", "conge": "ATTESTATION DE CONGE", "reprise": "ATTESTATION DE REPRISE"}
    pdf.cell(0, 8, titres.get(type_attestation, "ATTESTATION"), 0, 1, 'C')
    pdf.ln(6)
    pdf.set_font('Helvetica', '', 10)
    corps = f"Agent : {agent.get('Prénom','')} {agent.get('Nom','')}\nCNI / Matricule : {agent.get('Matricule_CNI','')}\nRégion : {agent.get('Région','')}"
    pdf.multi_cell(0, 5, corps)
    pdf.ln(10)
    sceau, hash_val = generer_sceau_electronique(f"ATTESTATON-{agent.get('Matricule_CNI','')}")
    qr_io = generer_image_qrcode(f"HASH: {hash_val}")
    pdf.image(qr_io, x=155, y=pdf.get_y(), w=35)
    return bytes(pdf.output())

# --- 4. BARRE LATÉRALE ---
with st.sidebar:
    st.markdown("### ⚙️ Gestion & Sécurité")
    st.session_state.user_role = st.selectbox("Profil Connecté :", ["Gestionnaire RH", "Directeur des Ressources Humaines (DRH)", "Administrateur technique"])
    st.write("---")
    st.markdown(f"### 📅 Session : {active_sid}")
    st.info(f"Statut : **{statut_session}**")

# --- 5. NAVIGATION PAR ONGLETS ---
onglet1, onglet2, onglet3, onglet4, onglet5, onglet6, onglet7, onglet8, onglet9 = st.tabs([
    "📋 Registre", "📂 Dossier & Signature", "📅 Congés", "⚖️ Discipline", "💶 Paie", "🔒 Cycle", "📊 Rapports", "📧 Alertes", "📜 Audit"
])

# ==============================================================================
# ONGLET 1 : REGISTRE (AVEC PAGINATION DE 200 AGENTS PAR PAGE)
# ==============================================================================
with onglet1:
    st.subheader("👤 Registre des Volontaires ASP (Pagination : 200 agents par page)")
    
    # Filtres de recherche rapide pour alléger
    col_sr1, col_sr2, col_sr3 = st.columns(3)
    with col_sr1:
        f_reg = st.selectbox("Filtrer par Région :", ['Toutes'] + regions_list, key="reg_reg_filtre")
    with col_sr2:
        f_cni = st.text_input("Recherche par CNI / Matricule ou Nom :")
    with col_sr3:
        f_statut = st.selectbox("Filtrer par Statut :", ['Tous', 'Actif', 'Radié', 'Démissionnaire'])

    df_filtered = df.copy()
    if f_reg != 'Toutes':
        df_filtered = df_filtered[df_filtered['Région'] == f_reg]
    if f_cni:
        df_filtered = df_filtered[
            df_filtered['Matricule_CNI'].astype(str).str.contains(f_cni, case=False, na=False) |
            df_filtered['Nom'].astype(str).str.contains(f_cni, case=False, na=False)
        ]
    if f_statut != 'Tous':
        df_filtered = df_filtered[df_filtered['Statut'] == f_statut]

    total_lignes = len(df_filtered)
    agents_par_page = 200
    total_pages = max(1, (total_lignes + agents_par_page - 1) // agents_par_page)

    st.write(f"Résultats trouvés : **{total_lignes:,} agents**")
    
    if total_lignes > 0:
        page_courante = st.number_input("Page de résultats :", min_value=1, max_value=total_pages, step=1, value=1)
        debut_idx = (page_courante - 1) * agents_par_page
        fin_idx = min(debut_idx + agents_par_page, total_lignes)
        
        df_page = df_filtered.iloc[debut_idx:fin_idx]
        st.markdown(f"Affichage des agents **{debut_idx + 1} à {fin_idx}** sur {total_lignes} (Page {page_courante}/{total_pages})")
        
        cols_affichage = [c for c in ['Matricule_CNI', 'Nom', 'Prénom', 'Région', 'Département', 'Lieu_Affectation', 'Statut', 'Net_A_Payer'] if c in df_page.columns]
        st.dataframe(df_page[cols_affichage], use_container_width=True)
    else:
        st.info("Aucun agent ne correspond aux critères de recherche.")

# ==============================================================================
# ONGLET 2 : DOSSIER & SIGNATURE ÉLECTRONIQUE
# ==============================================================================
with onglet2:
    st.subheader("📂 Dossier Personnel & Attestations Sécurisées")
    agent_cni = st.selectbox("Sélectionner un Volontaire (par CNI) :", options=df['Matricule_CNI'].values, key="sel_dossier_cni")
    if agent_cni:
        agent_row = df[df['Matricule_CNI'] == agent_cni].iloc[0]
        st.write(f"**Nom & Prénom :** {agent_row.get('Prénom','')} {agent_row.get('Nom','')}")
        st.write(f"**Région / Département :** {agent_row.get('Région','')} / {agent_row.get('Département','')}")
        
        if st.session_state.user_role == "Directeur des Ressources Humaines (DRH)":
            pdf_b = generer_pdf_attestation("prise", agent_row)
            st.download_button("🔏 Télécharger Attestation Prise en Service (Signée + QR Code)", data=pdf_b, file_name=f"attestation_{agent_cni}.pdf", mime="application/pdf")
        else:
            st.warning("⚠️ Seul le profil DRH peut générer les actes signés électroniquement.")

# ==============================================================================
# ONGLET 3 : CONGÉS
# ==============================================================================
with onglet3:
    st.subheader("📅 Planification des Congés (Jours Ouvrés)")
    actifs = df[df['Statut'] == 'Actif']
    if not actifs.empty:
        cni_conge = st.selectbox("Agent demandeur (CNI) :", options=actifs['Matricule_CNI'].values)
        if cni_conge:
            idx_c = df[df['Matricule_CNI'] == cni_conge].index[0]
            st.info(f"Solde actuel : {df.at[idx_c, 'Conges_Restants']} jours")
            d_deb = st.date_input("Début", value=date.today())
            d_fin = st.date_input("Fin", value=date.today() + timedelta(days=5))
            if st.button("Valider le congé"):
                nb_j = calculer_jours_ouvres(d_deb, d_fin)
                if nb_j <= df.at[idx_c, 'Conges_Restants']:
                    df.at[idx_c, 'Conges_Restants'] -= nb_j
                    st.session_state.df_asp = df
                    st.success(f"Congé accordé de {nb_j} jours.")
                    st.rerun()
                else:
                    st.error("Solde insuffisant.")

# ==============================================================================
# ONGLET 4 : DISCIPLINE
# ==============================================================================
with onglet4:
    st.subheader("⚖️ Conseil de Discipline & Sanctions")
    st.info("Gestion des avertissements, sanctions pécuniaires et radiations.")

# ==============================================================================
# ONGLET 5 : PAIE
# ==============================================================================
with onglet5:
    st.subheader(f"💶 Variables de Pécules - Session : {active_sid}")
    st.dataframe(df[['Matricule_CNI', 'Nom', 'Prénom', 'Pécule_Base', 'Prime', 'Net_A_Payer']].head(200), use_container_width=True)

# ==============================================================================
# ONGLET 6 : CYCLE MENSUEL
# ==============================================================================
with onglet6:
    st.subheader("🔒 Gouvernance des Sessions & Clôture")
    st.write(f"Session active : {active_sid} | Statut : {statut_session}")

# ==============================================================================
# ONGLET 7 : RAPPORTS & EXPORTS
# ==============================================================================
with onglet7:
    st.subheader("📊 Rapports & Exports Masse Salariale")
    if st.button("Télécharger l'état complet en Excel"):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Masse_Salariale')
        st.download_button("Télécharger le fichier .xlsx", data=output.getvalue(), file_name="etat_masse_salariale_asp.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ==============================================================================
# ONGLET 8 : ALERTES E-MAIL
# ==============================================================================
with onglet8:
    st.subheader("📧 Centre de Simulation des Alertes E-mail")
    for em in st.session_state.notifications_emails:
        st.text(em.get('Sujet'))

# ==============================================================================
# ONGLET 9 : AUDIT
# ==============================================================================
with onglet9:
    st.subheader("📜 Journal d'Audit")
    st.dataframe(pd.DataFrame(st.session_state.journal_audit), use_container_width=True)
