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
    # Support pour .xlsx et .xlsb
    if nom_fichier.endswith('.xlsb'):
        df_init = pd.read_excel(nom_fichier, engine='pyxlsb')
    else:
        df_init = pd.read_excel(nom_fichier)
    df_init.columns = df_init.columns.str.strip()
    return df_init

if 'df_asp' not in st.session_state:
    nom_fichier_excel = "base_asp.xlsx"  # Nom de votre fichier en local
    
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
        
        # --- DÉTECTION AUTOMATIQUE DE LA COLONNE CNI / MATRICULE ---
        possibilites_cni = ['CNI', 'Matricule_CNI', 'Matricule', 'Numéro CNI', 'Numero CNI', 'N_CNI', 'Numero_CNI', 'ID']
        colonne_trouvee = None
        for col in df_init.columns:
            if any(p.lower() in col.lower() for p in ['cni', 'matricule', 'identite']):
                colonne_trouvee = col
                break
                
        if colonne_trouvee:
            df_init['Matricule_CNI'] = df_init[colonne_trouvee].astype(str)
        else:
            df_init['Matricule_CNI'] = df_init.iloc[:, 0].astype(str)
            
        # Sécurité pour les autres colonnes obligatoires
        if 'Nom' not in df_init.columns:
            df_init['Nom'] = "Non renseigné"
        if 'Prénom' not in df_init.columns and 'Prenom' in df_init.columns:
            df_init['Prénom'] = df_init['Prenom']
        elif 'Prénom' not in df_init.columns:
            df_init['Prénom'] = "Non renseigné"
            
        if 'Région' not in df_init.columns:
            df_init['Région'] = 'Dakar'
        else:
            df_init['Région'] = df_init['Région'].astype(str).str.strip().str.title()
            
        if 'Département' not in df_init.columns:
            df_init['Département'] = 'Dakar'
        else:
            df_init['Département'] = df_init['Département'].astype(str).str.strip().str.title()
            
        if 'Statut' not in df_init.columns:
            df_init['Statut'] = 'Actif'

        # --- AJOUT DES COLONNES TECHNIQUES & FINANCIÈRES ---
        colonnes_techniques = {
            'Pécule_Base': 90000,
            'Beneficie_Prime': False,  # Par défaut, les primes ne sont pas obligatoires
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
            # Prime optionnelle selon le paramètre de l'agent
            prime_effective = float(row['Prime']) if row.get('Beneficie_Prime', False) else 0.0
            net = float(row['Pécule_Base']) + prime_effective - float(row['Cotisation_Mutuelle']) - float(row['Retenue_Pret']) - float(row['Sanction_Discipline'])
            return max(0.0, net)
            
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

# --- 3. FONCTIONS UTILITAIRES & SCELLAGE PDF ---
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
        self.cell(0, 10, f"Page {self.page_no()} - Document officiel sécurisé ASP", 0, 0, 'C')

def generer_pdf_attestation(type_attestation, agent):
    pdf = PDFOfficiel(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 12)
    
    titres = {
        "prise": "ATTESTATION DE PRISE EN SERVICE",
        "service": "ATTESTATION DE SERVICE",
        "travail": "ATTESTATION DE TRAVAIL",
        "conge": "ATTESTATION DE CONGE"
    }
    
    pdf.cell(0, 8, titres.get(type_attestation, "ATTESTATION ADMINISTRATIVE"), 0, 1, 'C')
    pdf.ln(6)
    
    pdf.set_font('Helvetica', '', 10)
    nom_complet = f"{agent.get('Prénom','')} {agent.get('Nom','')}"
    cni = agent.get('Matricule_CNI','')
    region = agent.get('Région','')
    dept = agent.get('Département','')
    site = agent.get('Lieu_Affectation','')
    
    corps_texte = (
        f"Le Directeur des Ressources Humaines de l'Agence d'Assistance à la Sécurité de Proximité (ASP) "
        f"certifie par la présente que :\n\n"
        f"M./Mme : {nom_complet}\n"
        f"Titulaire de la CNI / Matricule : {cni}\n"
        f"Affecté(e) à la Région de : {region} (Département de {dept}), Site : {site}\n\n"
        f"Remplit pleinement ses fonctions de volontaire de la sécurité de proximité et est enregistré(e) "
        f"régulièrement dans nos fichiers.\n\n"
        f"En foi de quoi, la présente attestation lui est délivrée pour servir et valoir ce que de droit."
    )
    
    pdf.multi_cell(0, 6, corps_texte)
    pdf.ln(15)
    
    sceau, hash_val = generer_sceau_electronique(f"ATTESTATION-{type_attestation.upper()}-{cni}")
    qr_io = generer_image_qrcode(f"ASP-SENEGAL HASH: {hash_val}")
    
    pdf.image(qr_io, x=150, y=pdf.get_y(), w=35)
    pdf.set_font('Helvetica', 'I', 8)
    pdf.multi_cell(90, 4, f"Cachet électronique vérifiable:\n{sceau}")
    
    return bytes(pdf.output())

# --- 4. BARRE LATÉRALE DE NAVIGATION ---
with st.sidebar:
    st.markdown("### ⚙️ Profil & Sécurité")
    st.session_state.user_role = st.selectbox(
        "Profil Connecté :", 
        ["Gestionnaire RH", "Directeur des Ressources Humaines (DRH)", "Administrateur technique"]
    )
    st.write("---")
    st.markdown(f"### 📅 Session : {active_sid}")
    st.info(f"Statut : **{statut_session}**")

# --- 5. NAVIGATION PAR ONGLETS ---
onglet1, onglet2, onglet3, onglet4, onglet5, onglet6, onglet7, onglet8, onglet9 = st.tabs([
    "📋 Registre", "📂 Dossier & Attestations", "📅 Congés", "⚖️ Discipline", "💶 Paie", "🔒 Cycle", "📊 Rapports & Masse", "📧 Alertes", "📜 Audit"
])

# ==============================================================================
# ONGLET 1 : REGISTRE (AVEC FILTRES ET PAGINATION DE 200 AGENTS)
# ==============================================================================
with onglet1:
    st.subheader("👤 Registre National des Volontaires ASP (200 agents / page)")
    
    col_sr1, col_sr2, col_sr3 = st.columns(3)
    with col_sr1:
        f_reg = st.selectbox("Filtrer par Région :", ['Toutes'] + regions_list, key="reg_reg_filtre")
    with col_sr2:
        f_cni = st.text_input("Recherche par CNI / Matricule ou Nom :", key="search_cni_reg")
    with col_sr3:
        f_statut = st.selectbox("Filtrer par Statut :", ['Tous', 'Actif', 'Radié', 'Démissionnaire'], key="statut_reg_filtre")

    df_filtered = df.copy()
    if f_reg != 'Toutes':
        df_filtered = df_filtered[df_filtered['Région'].str.strip().str.title() == f_reg]
    if f_cni:
        df_filtered = df_filtered[
            df_filtered['Matricule_CNI'].astype(str).str.contains(f_cni, case=False, na=False) |
            df_filtered['Nom'].astype(str).str.contains(f_cni, case=False, na=False) |
            df_filtered['Prénom'].astype(str).str.contains(f_cni, case=False, na=False)
        ]
    if f_statut != 'Tous':
        df_filtered = df_filtered[df_filtered['Statut'] == f_statut]

    total_lignes = len(df_filtered)
    agents_par_page = 200
    total_pages = max(1, (total_lignes + agents_par_page - 1) // agents_par_page)

    st.write(f"Résultats trouvés : **{total_lignes:,} agents**")
    
    if total_lignes > 0:
        page_courante = st.number_input("Page de résultats :", min_value=1, max_value=total_pages, step=1, value=1, key="pagination_reg")
        debut_idx = (page_courante - 1) * agents_par_page
        fin_idx = min(debut_idx + agents_par_page, total_lignes)
        
        df_page = df_filtered.iloc[debut_idx:fin_idx]
        st.markdown(f"Affichage des agents **{debut_idx + 1} à {fin_idx}** sur {total_lignes} (Page {page_courante}/{total_pages})")
        
        cols_affichage = [c for c in ['Matricule_CNI', 'Nom', 'Prénom', 'Région', 'Département', 'Lieu_Affectation', 'Statut', 'Net_A_Payer'] if c in df_page.columns]
        st.dataframe(df_page[cols_affichage], use_container_width=True)
    else:
        st.info("Aucun agent ne correspond aux critères de recherche.")

# ==============================================================================
# ONGLET 2 : DOSSIER & SIGNATURE ÉLECTRONIQUE (ATTESTATIONS)
# ==============================================================================
with onglet2:
    st.subheader("📂 Dossier Personnel & Attestations Administratives Sécurisées")
    agent_cni = st.selectbox("Sélectionner un Volontaire (par CNI / Matricule) :", options=df['Matricule_CNI'].values, key="sel_dossier_cni")
    
    if agent_cni:
        agent_row = df[df['Matricule_CNI'] == agent_cni].iloc[0]
        
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.markdown("#### Informations Signalétiques")
            st.write(f"**Nom & Prénom :** {agent_row.get('Prénom','')} {agent_row.get('Nom','')}")
            st.write(f"**CNI / Matricule :** {agent_row.get('Matricule_CNI','')}")
            st.write(f"**Région / Département :** {agent_row.get('Région','')} / {agent_row.get('Département','')}")
            st.write(f"**Site d'Affectation :** {agent_row.get('Lieu_Affectation','')}")
            st.write(f"**Téléphone :** {agent_row.get('Telephone','-')}")
            st.write(f"**Statut Actuel :** {agent_row.get('Statut','Actif')}")
        with col_d2:
            st.markdown("#### Situation Administrative & Congés")
            st.write(f"**Congés Restants :** {agent_row.get('Conges_Restants', 30)} jours")
            st.write(f"**Pécule de Base :** {agent_row.get('Pécule_Base', 0):,} FCFA")
            st.write(f"**Bénéficie d'une Prime :** {'Oui' if agent_row.get('Beneficie_Prime', False) else 'Non'}")
            if agent_row.get('Beneficie_Prime', False):
                st.write(f"**Montant Prime :** {agent_row.get('Prime', 0):,} FCFA")

        st.markdown("---")
        st.markdown("### 🔏 Génération des Actes et Attestations Officiels")
        
        if st.session_state.user_role == "Directeur des Ressources Humaines (DRH)":
            type_acte = st.selectbox("Choisir le type d'attestation à générer :", [
                "Attestation de Prise en Service",
                "Attestation de Service",
                "Attestation de Travail",
                "Attestation de Congé"
            ])
            
            mapping_type = {
                "Attestation de Prise en Service": "prise",
                "Attestation de Service": "service",
                "Attestation de Travail": "travail",
                "Attestation de Congé": "conge"
            }
            
            if st.button("Générer et Sceller l'Attestation (PDF)", key="btn_generer_attestation"):
                code_type = mapping_type[type_acte]
                pdf_b = generer_pdf_attestation(code_type, agent_row)
                st.success("✅ Attestation générée avec succès et scellée électroniquement par le DRH.")
                st.download_button(
                    label=f"📥 Télécharger {type_acte} (PDF Sécurisé + QR Code)",
                    data=pdf_b,
                    file_name=f"attestation_{code_type}_{agent_cni}.pdf",
                    mime="application/pdf"
                )
        else:
            st.warning("⚠️ Seul le profil **Directeur des Ressources Humaines (DRH)** est habilité à signer et télécharger les attestations officielles.")

# ==============================================================================
# ONGLET 3 : CONGÉS
# ==============================================================================
with onglet3:
    st.subheader("📅 Planification et Gestion des Congés (Jours Ouvrés)")
    actifs = df[df['Statut'] == 'Actif']
    
    if not actifs.empty:
        cni_conge = st.selectbox("Sélectionner l'agent (par CNI) :", options=actifs['Matricule_CNI'].values, key="sel_conge_agent")
        if cni_conge:
            idx_c = df[df['Matricule_CNI'] == cni_conge].index[0]
            agent_c = df.loc[idx_c]
            
            st.info(f"Agent : **{agent_c['Prénom']} {agent_c['Nom']}** | Solde de congés actuel : **{agent_c['Conges_Restants']} jours**")
            
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                d_deb = st.date_input("Date de début du congé", value=date.today(), key="date_deb_conge")
            with col_c2:
                d_fin = st.date_input("Date de fin du congé", value=date.today() + timedelta(days=5), key="date_fin_conge")
                
            if st.button("Valider et Enregistrer le Congé", key="btn_valider_conge"):
                nb_j = calculer_jours_ouvres(d_deb, d_fin)
                if nb_j <= 0:
                    st.error("La période sélectionnée ne contient aucun jour ouvré valide.")
                elif nb_j <= df.at[idx_c, 'Conges_Restants']:
                    df.at[idx_c, 'Conges_Restants'] -= nb_j
                    df.at[idx_c, 'Dernier_Conge_Debut'] = str(d_deb)
                    df.at[idx_c, 'Dernier_Conge_Fin'] = str(d_fin)
                    df.at[idx_c, 'Dernier_Conge_Jours'] = nb_j
                    st.session_state.df_asp = df
                    enregistrer_audit(st.session_state.user_role, "Demande congé", active_sid, f"Congé de {nb_j} jours accordé à {cni_conge}")
                    st.success(f"✅ Congé validé avec succès. {nb_j} jours déduits du solde. Nouveau solde : {df.at[idx_c, 'Conges_Restants']} jours.")
                    st.rerun()
                else:
                    st.error(f"Solde insuffisant ! L'agent demande {nb_j} jours mais ne dispose que de {df.at[idx_c, 'Conges_Restants']} jours.")
    else:
        st.warning("Aucun agent actif disponible pour la gestion des congés.")

# ==============================================================================
# ONGLET 4 : DISCIPLINE
# ==============================================================================
with onglet4:
    st.subheader("⚖️ Conseil de Discipline & Sanctions")
    st.info("Gestion des avertissements, sanctions pécuniaires et procédures de radiation validées par la DRH.")
    
    agent_disc_cni = st.selectbox("Sélectionner l'agent concerné :", options=df['Matricule_CNI'].values, key="sel_disc_agent")
    if agent_disc_cni:
        idx_d = df[df['Matricule_CNI'] == agent_disc_cni].index[0]
        ag_d = df.loc[idx_d]
        st.write(f"**Agent :** {ag_d['Prénom']} {ag_d['Nom']} | **Sanction actuelle en cours :** {ag_d['Sanction_Discipline']} FCFA")
        
        nouveau_retrait = st.number_input("Montant de la retenue disciplinaire (FCFA) :", min_value=0, step=500, value=int(ag_d['Sanction_Discipline']))
        motif_sanction = st.text_input("Motif de la sanction :", value=ag_d['Motif_Action'])
        
        if st.button("Mettre à jour la sanction disciplinaire", key="btn_update_sanction"):
            df.at[idx_d, 'Sanction_Discipline'] = nouveau_retrait
            df.at[idx_d, 'Motif_Action'] = motif_sanction
            # Recalcul du net
            prime_eff = float(df.at[idx_d, 'Prime']) if df.at[idx_d, 'Beneficie_Prime'] else 0.0
            net = float(df.at[idx_d, 'Pécule_Base']) + prime_eff - float(df.at[idx_d, 'Cotisation_Mutuelle']) - float(df.at[idx_d, 'Retenue_Pret']) - float(nouveau_retrait)
            df.at[idx_d, 'Net_A_Payer'] = max(0.0, net)
            st.session_state.df_asp = df
            st.success("✅ Sanction enregistrée et impact sur la paie mis à jour.")
            st.rerun()

# ==============================================================================
# ONGLET 5 : PAIE
# ==============================================================================
with onglet5:
    st.subheader(f"💶 Variables de Pécules & Traitement - Session : {active_sid}")
    
    agent_paie_cni = st.selectbox("Ajuster les options de prime pour l'agent (par CNI) :", options=df['Matricule_CNI'].values, key="sel_paie_agent")
    if agent_paie_cni:
        idx_p = df[df['Matricule_CNI'] == agent_paie_cni].index[0]
        ag_p = df.loc[idx_p]
        
        # Sécurisation des conversions en float pour éviter le StreamlitMixedNumericTypesError
        val_prime_initiale = float(pd.to_numeric(ag_p.get('Prime', 15000), errors='coerce') or 15000.0)
        bool_prime_initiale = bool(ag_p.get('Beneficie_Prime', False))
        
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            benef_prime_actuel = st.checkbox("Bénéficie de la prime mensuelle ?", value=bool_prime_initiale, key=f"chk_prime_{agent_paie_cni}")
        with col_p2:
            montant_prime_saisi = st.number_input("Montant de la prime (FCFA) :", value=val_prime_initiale, step=1000.0, format="%.2f", key=f"val_prime_{agent_paie_cni}")
            
        if st.button("Enregistrer les paramètres de paie de l'agent", key="btn_save_paie_agent"):
            df.at[idx_p, 'Beneficie_Prime'] = benef_prime_actuel
            df.at[idx_p, 'Prime'] = float(montant_prime_saisi)
            
            # Recalcul sécurisé du Net
            pecule_b = float(pd.to_numeric(df.at[idx_p, 'Pécule_Base'], errors='coerce') or 90000.0)
            p_eff = float(montant_prime_saisi) if benef_prime_actuel else 0.0
            mutuelle = float(pd.to_numeric(df.at[idx_p, 'Cotisation_Mutuelle'], errors='coerce') or 2500.0)
            pret = float(pd.to_numeric(df.at[idx_p, 'Retenue_Pret'], errors='coerce') or 0.0)
            sanction = float(pd.to_numeric(df.at[idx_p, 'Sanction_Discipline'], errors='coerce') or 0.0)
            
            net = pecule_b + p_eff - mutuelle - pret - sanction
            df.at[idx_p, 'Net_A_Payer'] = max(0.0, net)
            
            st.session_state.df_asp = df
            st.success("✅ Paramètres de paie mis à jour avec succès.")
            st.rerun()

    st.markdown("---")
    st.markdown("### 📋 Aperçu du Tableau de Paie (200 premiers affichés)")
    cols_paie = [c for c in ['Matricule_CNI', 'Nom', 'Prénom', 'Pécule_Base', 'Beneficie_Prime', 'Prime', 'Cotisation_Mutuelle', 'Net_A_Payer'] if c in df.columns]
    st.dataframe(df[cols_paie].head(200), use_container_width=True)

# ==============================================================================
# ONGLET 6 : CYCLE MENSUEL
# ==============================================================================
with onglet6:
    st.subheader("🔒 Gouvernance des Sessions & Clôture de Paie")
    st.write(f"Session active : **{active_sid}** | Statut : **{statut_session}**")
    st.info("La clôture de session verrouille les données de paie pour les 9 000 agents et génère les archives officielles.")

# ==============================================================================
# ONGLET 7 : RAPPORTS & MASSE SALARIALE (POUR LE DRH)
# ==============================================================================
with onglet7:
    st.subheader("📊 Rapports Financiers & Masse Salariale Globale")
    
    if st.session_state.user_role == "Directeur des Ressources Humaines (DRH)":
        st.markdown("### 🏢 Tableau de Bord Financier DRH")
        total_agents_effectif = len(df)
        total_actifs = len(df[df['Statut'] == 'Actif'])
        masse_salariale_totale = df['Net_A_Payer'].sum()
        
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            st.metric("Effectif Total Enregistré", f"{total_agents_effectif:,}")
        with col_m2:
            st.metric("Volontaires Actifs", f"{total_actifs:,}")
        with col_m3:
            st.metric("Masse Salariale Mensuelle (Net)", f"{masse_salariale_totale:,.0f} FCFA")
            
        st.markdown("---")
        st.markdown("### 📥 Export Officiel de la Masse Salariale pour le DRH")
        
        if st.button("📥 Télécharger l'état complet de la masse salariale (Excel)", key="btn_export_excel_drh"):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Masse_Salariale_ASP')
            st.download_button(
                label="📁 Cliquer ici pour télécharger le fichier Excel consolidé",
                data=output.getvalue(),
                file_name=f"masse_salariale_asp_{active_sid}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.warning("⚠️ L'accès détaillé à la masse salariale globale et aux exports financiers est réservé au profil **Directeur des Ressources Humaines (DRH)**.")

# ==============================================================================
# ONGLET 8 : ALERTES E-MAIL
# ==============================================================================
with onglet8:
    st.subheader("📧 Centre de Simulation des Alertes E-mail & Notifications")
    st.info("Journal des notifications transmises aux antennes régionales et aux services financiers.")

# ==============================================================================
# ONGLET 9 : AUDIT
# ==============================================================================
with onglet9:
    st.subheader("📜 Journal d'Audit & Traçabilité des Actions")
    st.dataframe(pd.DataFrame(st.session_state.journal_audit), use_container_width=True)
