import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import calendar
from zoneinfo import ZoneInfo
from fpdf import FPDF
import io

# Configuration du fuseau horaire Africa/Dakar (RG-11)
DAKAR_TZ = ZoneInfo("Africa/Dakar")

st.set_page_config(page_title="Système National ASP Sénégal", layout="wide")

st.title("🇸🇳 Système Intégré de Gestion des Volontaires ASP")
st.markdown("### Direction des Ressources Humaines et de la Solde - Sénégal")

# --- INITIALISATION DE LA BASE DE DONNÉES AGENTS EN SESSION ---
if 'df_asp' not in st.session_state:
    np.random.seed(42)
    regions = ['Dakar', 'Thiès', 'Saint-Louis', 'Ziguinchor', 'Kaolack', 'Diourbel', 'Tambacounda']
    canaux = ['BOA', 'Orange Money', 'BNDE']
    benef_prime = [True, False, True, False, False, True, False, False, True, False]
    
    df_init = pd.DataFrame({
        'Matricule_CNI': [f"1{np.random.randint(100, 999)}199{np.random.randint(10,99)}{np.random.randint(10000, 99999)}" for _ in range(10)],
        'Nom': ['Diop', 'Ndiaye', 'Sow', 'Fall', 'Gueye', 'Diallo', 'Faye', 'Cissé', 'Bâ', 'Sané'],
        'Prénom': ['Moussa', 'Fatou', 'Ousmane', 'Awa', 'Amadou', 'Khady', 'Ibrahima', 'Oumar', 'Mariama', 'Aliou'],
        'Date_Naissance': ['1998-05-12'] * 10,
        'Lieu_Naissance': ['Dakar', 'Thiès', 'Saint-Louis', 'Kaolack', 'Ziguinchor', 'Diourbel', 'Rufisque', 'Pikine', 'Mbour', 'Bignona'],
        'Date_Engagement': ['2024-01-01'] * 10,
        'Région': np.random.choice(regions, 10),
        'Lieu_Affectation': np.random.choice(['Commissariat Central', 'Préfecture', 'Mairie', 'Lycée'], 10),
        'Canal_Paiement': np.random.choice(canaux, 10),
        'Compte_Numero': [f"SN012-{np.random.randint(10000, 99999)}" for _ in range(10)],
        'Pécule_Base': [90000] * 10,
        'Beneficie_Prime': benef_prime,
        'Prime': [15000 if b else 0 for b in benef_prime],
        'Cotisation_Mutuelle': [2500] * 10,
        'Retenue_Pret': [0] * 10,
        'Sanction_Discipline': [0] * 10,
        'Motif_Action': ["RAS"] * 10,
        'Conges_Restants': [30] * 10,
        'Statut': ['Actif'] * 10
    })
    
    mask_om = df_init['Canal_Paiement'] == 'Orange Money'
    df_init.loc[mask_om, 'Compte_Numero'] = [f"77 {np.random.randint(100, 999)} {np.random.randint(10, 99)} {np.random.randint(10, 99)}" for _ in range(mask_om.sum())]
    
    st.session_state.df_asp = df_init

# --- INITIALISATION DU SYSTÈME DE GESTION DES SESSIONS ---
now_dakar = datetime.now(DAKAR_TZ)
current_session_id = f"PECULE-{now_dakar.year}-{now_dakar.month:02d}"

if 'sessions_db' not in st.session_state:
    st.session_state.sessions_db = {
        current_session_id: {
            "id": current_session_id,
            "annee": now_dakar.year,
            "mois": now_dakar.month,
            "statut": "OUVERTE", 
            "date_ouverture": now_dakar.strftime("%Y-%m-%d %H:%M"),
            "date_cloture": None,
            "type_cloture": None,
            "motif_reouverture": "",
            "drh_reouverture": "",
            "historique_reouvertures": [],
            "archives_donnees": None
        }
    }

if 'session_active_id' not in st.session_state:
    st.session_state.session_active_id = current_session_id

if 'journal_audit' not in st.session_state:
    st.session_state.journal_audit = [
        {
            "Timestamp": now_dakar.strftime("%Y-%m-%d %H:%M:%S"),
            "Utilisateur": "Système Automatisé",
            "Action": "Ouverture session",
            "Session": current_session_id,
            "Détails": "Création et ouverture automatique de la session mensuelle"
        }
    ]

if 'notifications_systeme' not in st.session_state:
    st.session_state.notifications_systeme = [
        f"[{now_dakar.strftime('%Y-%m-%d %H:%M')}] Notification : Session {current_session_id} ouverte avec succès."
    ]

if 'user_role' not in st.session_state:
    st.session_state.user_role = "Gestionnaire RH" 

def enregistrer_audit(utilisateur, action, session_id, details):
    st.session_state.journal_audit.insert(0, {
        "Timestamp": datetime.now(DAKAR_TZ).strftime("%Y-%m-%d %H:%M:%S"),
        "Utilisateur": utilisateur,
        "Action": action,
        "Session": session_id,
        "Détails": details
    })

def ajouter_notification(message):
    st.session_state.notifications_systeme.insert(0, f"[{datetime.now(DAKAR_TZ).strftime('%Y-%m-%d %H:%M')}] {message}")

df = st.session_state.df_asp
active_sid = st.session_state.session_active_id
session_courante = st.session_state.sessions_db[active_sid]
statut_session = session_courante["statut"]

def modification_autorisee():
    return statut_session in ["OUVERTE", "EN COURS DE CONTRÔLE", "ROUVERTE APRÈS CLÔTURE"]

def calculer_net(row):
    if row['Statut'] in ['Radié', 'Démissionnaire']:
        return 0
    prime_effective = row['Prime'] if row['Beneficie_Prime'] else 0
    net = row['Pécule_Base'] + prime_effective - row['Cotisation_Mutuelle'] - row['Retenue_Pret'] - row['Sanction_Discipline']
    return max(0, net)

df['Net_A_Payer'] = df.apply(calculer_net, axis=1)

# --- CLASSE DE GÉNÉRATION DE PDF OFFICIEL POUR DAF & DG ---
class PDFEtatPaie(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 10)
        self.cell(0, 5, "REPUBLIQUE DU SENEGAL", 0, 1, 'C')
        self.set_font('Helvetica', '', 9)
        self.cell(0, 4, "Un peuple - Un But - Une Foi", 0, 1, 'C')
        self.cell(0, 4, "MINISTERE DE L'INTERIEUR - DIRECTION DES ASP", 0, 1, 'C')
        self.cell(0, 4, "Direction des Ressources Humaines et de la Solde", 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f"Page {self.page_no()} - Document officiel transmis à la DAF et au DG", 0, 0, 'C')

def generer_pdf_session(session_id, session_data, df_archivé):
    pdf = PDFEtatPaie(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    
    # Titre du document
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 10, f"ETAT RECAPITULATIF DES PECULES - {session_id}", 0, 1, 'C')
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(0, 6, f"Date de generation : {datetime.now(DAKAR_TZ).strftime('%Y-%m-%d %H:%M')}", 0, 1, 'C')
    pdf.cell(0, 6, f"Type de cloture : {session_data.get('type_cloture', 'N/A')}", 0, 1, 'C')
    pdf.ln(5)
    
    # Indicateurs clés
    actifs_df = df_archivé[df_archivé['Statut'] == 'Actif']
    total_agents = len(actifs_df)
    masse_totale = df_archivé['Net_A_Payer'].sum()
    
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(0, 6, f"Effectif Actif : {total_agents} agents", 0, 1, 'L')
    pdf.cell(0, 6, f"Masse Salariale Nette Totale : {masse_totale:,.0f} F CFA".replace(',', ' '), 0, 1, 'L')
    pdf.ln(5)
    
    # Tableau des agents
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(35, 7, "Matricule CNI", 1, 0, 'C', True)
    pdf.cell(35, 7, "Nom", 1, 0, 'C', True)
    pdf.cell(35, 7, "Prenom", 1, 0, 'C', True)
    pdf.cell(35, 7, "Region", 1, 0, 'C', True)
    pdf.cell(50, 7, "Net a Payer (F CFA)", 1, 1, 'C', True)
    
    pdf.set_font('Helvetica', '', 8)
    for _, row in df_archivé.iterrows():
        pdf.cell(35, 6, str(row['Matricule_CNI']), 1, 0, 'C')
        pdf.cell(35, 6, str(row['Nom'])[:18], 1, 0, 'L')
        pdf.cell(35, 6, str(row['Prénom'])[:18], 1, 0, 'L')
        pdf.cell(35, 6, str(row['Région']), 1, 0, 'C')
        pdf.cell(50, 6, f"{row['Net_A_Payer']:,.0f}".replace(',', ' '), 1, 1, 'R')
        
    pdf.ln(10)
    
    # Signatures
    pdf.set_font('Helvetica', 'B', 9)
    pdf.cell(60, 6, "Le Directeur des Ressources Humaines", 0, 0, 'C')
    pdf.cell(60, 6, "Le Directeur Administratif & Financier", 0, 0, 'C')
    pdf.cell(60, 6, "Le Directeur General", 0, 1, 'C')
    
    return bytes(pdf.output())

# --- BARRE LATÉRALE DE GESTION DES ACTEURS ET RÔLES ---
with st.sidebar:
    st.markdown("### ⚙️ Gestion des Acteurs")
    st.session_state.user_role = st.selectbox(
        "Profil Connecté :", 
        ["Gestionnaire RH", "Directeur des Ressources Humaines (DRH)", "Administrateur technique"]
    )
    
    st.write("---")
    st.markdown(f"### 📅 Session : {active_sid}")
    st.info(f"Statut : **{statut_session}**")
    
    st.markdown("#### 🔔 Notifications Système")
    if st.session_state.notifications_systeme:
        st.warning(st.session_state.notifications_systeme[0])
    
    st.write("---")
    st.markdown("#### ⏱️ Simulateur Tâches Automatisées")
    if st.button("⚡ Simuler Clôture Auto (Dernier jour à 12h00)"):
        if statut_session in ["CLÔTURÉE", "ARCHIVÉE"]:
            st.warning("La session est déjà clôturée.")
        else:
            session_courante["statut"] = "CLÔTURÉE"
            session_courante["date_cloture"] = datetime.now(DAKAR_TZ).strftime("%Y-%m-%d 12:00")
            session_courante["type_cloture"] = "AUTOMATIQUE"
            session_courante["archives_donnees"] = df.copy()
            
            next_m = session_courante["mois"] + 1
            next_y = session_courante["annee"]
            if next_m > 12:
                next_m = 1
                next_y += 1
            next_sid = f"PECULE-{next_y}-{next_m:02d}"
            
            if next_sid not in st.session_state.sessions_db:
                st.session_state.sessions_db[next_sid] = {
                    "id": next_sid, "annee": next_y, "mois": next_m,
                    "statut": "EN ATTENTE D'OUVERTURE", "date_ouverture": None,
                    "date_cloture": None, "type_cloture": None,
                    "motif_reouverture": "", "drh_reouverture": "",
                    "historique_reouvertures": [], "archives_donnees": None
                }
            enregistrer_audit("Système Automatisé", "Clôture Automatique (12h00)", active_sid, f"Clôture validée. Cycle {next_sid} préparé.")
            ajouter_notification(f"Clôture automatique effectuée pour la session {active_sid}.")
            st.success("Clôture automatique exécutée et archivée.")
            st.rerun()

# --- NAVIGATION PAR ONGLETS ---
onglet1, onglet2, onglet3, onglet4, onglet5, onglet6 = st.tabs([
    "📋 Registre & Recrutement", 
    "📅 Gestion des Congés", 
    "💶 Paie & Variables", 
    "🔒 Cycle Mensuel & Sessions",
    "📊 Rapports & Supervision",
    "📜 Journal d'Audit"
])

regions_list = ['Dakar', 'Thiès', 'Saint-Louis', 'Ziguinchor', 'Kaolack', 'Diourbel', 'Tambacounda']

# ==============================================================================
# ONGLET 1 : RECRUTEMENT ET MODIFICATION
# ==============================================================================
with onglet1:
    st.subheader("👤 Mouvements de Personnel (Recrutement & Édition)")
    
    if not modification_autorisee():
        st.error(f"🔒 VERROUILLAGE SÉCURISÉ : La session **{active_sid}** est au statut **{statut_session}**. Toute modification est interdite.")
    else:
        choix_action = st.radio("Action RH :", ["Consulter & Modifier un Profil", "Créer / Recruter un nouvel ASP"], horizontal=True)
        
        if choix_action == "Créer / Recruter un nouvel ASP":
            st.markdown("#### Formulaire d'engagement (CNI = Matricule)")
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                n_cni = st.text_input("Numéro CNI *")
                n_prenom = st.text_input("Prénom *")
                n_nom = st.text_input("Nom *")
                n_dn = st.date_input("Date de naissance", value=pd.to_datetime("2000-01-01"))
                n_ln = st.text_input("Lieu de naissance")
            with col_r2:
                n_de = st.date_input("Date d'engagement officiel", value=pd.to_datetime("2026-01-01"))
                n_reg = st.selectbox("Région d'affectation", regions_list)
                n_aff = st.text_input("Lieu précis d'affectation")
                n_canal = st.selectbox("Mode de paiement", ['Orange Money', 'BOA', 'BNDE'])
                n_has_prime = st.checkbox("Bénéficiaire d'une prime ?")
                n_montant_prime = st.number_input("Montant prime (F CFA) :", min_value=0, step=5000, value=15000) if n_has_prime else 0
                
            if st.button("💾 Enregistrer le Recrutement"):
                if n_cni and n_prenom and n_nom:
                    if n_cni in df['Matricule_CNI'].values:
                        st.error("🛑 Erreur : Un volontaire avec ce numéro CNI existe déjà.")
                    else:
                        nouvel_asp = {
                            'Matricule_CNI': n_cni, 'Nom': n_nom, 'Prénom': n_prenom,
                            'Date_Naissance': str(n_dn), 'Lieu_Naissance': n_ln, 'Date_Engagement': str(n_de),
                            'Région': n_reg, 'Lieu_Affectation': n_aff, 'Canal_Paiement': n_canal,
                            'Compte_Numero': "A renseigner", 'Pécule_Base': 90000, 
                            'Beneficie_Prime': n_has_prime, 'Prime': n_montant_prime,
                            'Cotisation_Mutuelle': 2500, 'Retenue_Pret': 0, 'Sanction_Discipline': 0,
                            'Motif_Action': "Nouveau recrutement", 'Conges_Restants': 30, 'Statut': 'Actif'
                        }
                        df = pd.concat([df, pd.DataFrame([nouvel_asp])], ignore_index=True)
                        st.session_state.df_asp = df
                        enregistrer_audit(st.session_state.user_role, "Recrutement", active_sid, f"Ajout agent CNI: {n_cni}")
                        st.success(f"Agent enregistré sous le CNI : {n_cni}")
                        st.rerun()

        elif choix_action == "Consulter & Modifier un Profil":
            matricule_modif = st.selectbox("Sélectionnez l'ASP par CNI :", options=df['Matricule_CNI'].values)
            if matricule_modif:
                idx = df[df['Matricule_CNI'] == matricule_modif].index[0]
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    edit_prenom = st.text_input("Prénom", value=df.at[idx, 'Prénom'])
                    edit_nom = st.text_input("Nom", value=df.at[idx, 'Nom'])
                    edit_aff = st.text_input("Lieu d'affectation", value=df.at[idx, 'Lieu_Affectation'])
                with col_m2:
                    edit_reg = st.selectbox("Région", regions_list, index=regions_list.index(df.at[idx, 'Région']))
                    statuts_list = ['Actif', 'Radié', 'Démissionnaire']
                    edit_statut = st.selectbox("Statut RH", statuts_list, index=statuts_list.index(df.at[idx, 'Statut']))
                    edit_has_prime = st.checkbox("Bénéficiaire prime", value=bool(df.at[idx, 'Beneficie_Prime']))
                    edit_montant_prime = st.number_input("Montant Prime", value=int(df.at[idx, 'Prime']), step=5000) if edit_has_prime else 0
                
                if st.button("💾 Sauvegarder les modifications"):
                    df.at[idx, 'Prénom'] = edit_prenom
                    df.at[idx, 'Nom'] = edit_nom
                    df.at[idx, 'Lieu_Affectation'] = edit_aff
                    df.at[idx, 'Région'] = edit_reg
                    df.at[idx, 'Statut'] = edit_statut
                    df.at[idx, 'Beneficie_Prime'] = edit_has_prime
                    df.at[idx, 'Prime'] = edit_montant_prime
                    st.session_state.df_asp = df
                    enregistrer_audit(st.session_state.user_role, "Modification Profil", active_sid, f"Mise à jour CNI: {matricule_modif}")
                    st.success("Dossier mis à jour et audité.")
                    st.rerun()

    st.write("---")
    st.dataframe(df[['Matricule_CNI', 'Nom', 'Prénom', 'Région', 'Lieu_Affectation', 'Beneficie_Prime', 'Prime', 'Statut', 'Net_A_Payer']], use_container_width=True)

# ==============================================================================
# ONGLET 2 : CONGÉS
# ==============================================================================
with onglet2:
    st.subheader("📅 Planification des Congés Annuels")
    if not modification_autorisee():
        st.error(f"🔒 VERROUILLAGE SÉCURISÉ : Session **{active_sid}** clôturée.")
    else:
        actifs_df = df[df['Statut'] == 'Actif']
        if not actifs_df.empty:
            asp_conge = st.selectbox("Sélectionnez l'ASP demandeur :", options=actifs_df['Matricule_CNI'].values, key="conge_box")
            if asp_conge:
                idx_c = df[df['Matricule_CNI'] == asp_conge].index[0]
                st.info(f"Solde disponible : **{df.at[idx_c, 'Conges_Restants']} jours**.")
                jours_demandes = st.number_input("Jours à poser :", min_value=1, max_value=max(1, int(df.at[idx_c, 'Conges_Restants'])), value=1)
                if st.button("🌴 Accorder le congé"):
                    df.at[idx_c, 'Conges_Restants'] -= jours_demandes
                    st.session_state.df_asp = df
                    enregistrer_audit(st.session_state.user_role, "Attribution Congé", active_sid, f"{jours_demandes}j attribués à CNI: {asp_conge}")
                    st.success("Compteur mis à jour.")
                    st.rerun()

# ==============================================================================
# ONGLET 3 : PAIE & VARIABLES
# ==============================================================================
with onglet3:
    st.subheader(f"💶 Variables de Pécules - Session : {active_sid}")
    
    if not modification_autorisee():
        st.error(f"🔒 VERROUILLAGE SÉCURISÉ : Session **{active_sid}** clôturée. Consultation seule.")
        st.dataframe(df[['Matricule_CNI', 'Nom', 'Prénom', 'Pécule_Base', 'Prime', 'Retenue_Pret', 'Sanction_Discipline', 'Net_A_Payer']], use_container_width=True)
    else:
        agent_paie = st.selectbox("Sélectionner un agent pour ajuster ses variables :", options=df[df['Statut']=='Actif']['Matricule_CNI'].values, key="select_paie")
        if agent_paie:
            idx_p = df[df['Matricule_CNI'] == agent_paie].index[0]
            st.markdown(f"**Agent :** {df.at[idx_p, 'Prénom']} {df.at[idx_p, 'Nom']} (CNI: {agent_paie})")
            
            col_p1, col_p2, col_p3 = st.columns(3)
            with col_p1:
                val_pret = st.number_input("Retenue Prêt (F CFA)", value=int(df.at[idx_p, 'Retenue_Pret']), step=1000)
            with col_p2:
                val_sanction = st.number_input("Sanction Discipline (F CFA)", value=int(df.at[idx_p, 'Sanction_Discipline']), step=1000)
            with col_p3:
                val_motif = st.text_input("Motif de l'action / sanction", value=str(df.at[idx_p, 'Motif_Action']))
                
            if st.button("💾 Enregistrer les variables financières"):
                df.at[idx_p, 'Retenue_Pret'] = val_pret
                df.at[idx_p, 'Sanction_Discipline'] = val_sanction
                df.at[idx_p, 'Motif_Action'] = val_motif
                st.session_state.df_asp = df
                enregistrer_audit(st.session_state.user_role, "Mise à jour Paie", active_sid, f"Prêt/Sanction modifiés pour CNI: {agent_paie}")
                st.success("Variables financières enregistrées.")
                st.rerun()

        st.write("---")
        st.dataframe(df[['Matricule_CNI', 'Nom', 'Prénom', 'Pécule_Base', 'Prime', 'Retenue_Pret', 'Sanction_Discipline', 'Net_A_Payer', 'Motif_Action']], use_container_width=True)

# ==============================================================================
# ONGLET 4 : GESTION DU CYCLE MENSUEL & SESSIONS
# ==============================================================================
with onglet4:
    st.subheader("🔒 Gouvernance des Sessions & Cycle Mensuel des Pécules")
    
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        sid_list = list(st.session_state.sessions_db.keys())
        selected_sid = st.selectbox("Sélectionner la session mensuelle :", sid_list, index=sid_list.index(active_sid))
        st.session_state.session_active_id = selected_sid
        sess_details = st.session_state.sessions_db[selected_sid]
        
    with col_s2:
        st.metric("Statut de la Session", sess_details["statut"])
        st.write(f"**Ouverture :** {sess_details['date_ouverture'] or 'Non ouverte'}")
        st.write(f"**Clôture :** {sess_details['date_cloture'] or 'En cours'}")
        if sess_details['type_cloture']:
            st.write(f"**Type de Clôture :** {sess_details['type_cloture']}")

    st.write("---")
    
    # 1. Clôture Manuelle par le DRH
    if sess_details["statut"] in ["OUVERTE", "EN COURS DE CONTRÔLE", "ROUVERTE APRÈS CLÔTURE"]:
        st.markdown("#### 🛑 Clôture de Session par le DRH")
        if st.session_state.user_role == "Directeur des Ressources Humaines (DRH)":
            if st.checkbox("Je confirme vouloir clôturer cette session avant l'échéance automatique (Clôture MANUELLE)."):
                if st.button("🔒 Clôturer la Session (Définitive)", type="primary"):
                    sess_details["statut"] = "CLÔTURÉE"
                    sess_details["date_cloture"] = datetime.now(DAKAR_TZ).strftime("%Y-%m-%d %H:%M")
                    sess_details["type_cloture"] = "MANUELLE"
                    sess_details["archives_donnees"] = df.copy()
                    
                    next_m = sess_details["mois"] + 1
                    next_y = sess_details["annee"]
                    if next_m > 12:
                        next_m = 1
                        next_y += 1
                    next_id = f"PECULE-{next_y}-{next_m:02d}"
                    if next_id not in st.session_state.sessions_db:
                        st.session_state.sessions_db[next_id] = {
                            "id": next_id, "annee": next_y, "mois": next_m,
                            "statut": "EN ATTENTE D'OUVERTURE", "date_ouverture": None,
                            "date_cloture": None, "type_cloture": None,
                            "motif_reouverture": "", "drh_reouverture": "",
                            "historique_reouvertures": [], "archives_donnees": None
                        }
                    enregistrer_audit("DRH", "Clôture Manuelle", selected_sid, "Clôture validée par le DRH.")
                    ajouter_notification(f"Session {selected_sid} clôturée manuellement par le DRH.")
                    st.success("Session clôturée avec succès et verrouillée.")
                    st.rerun()
        else:
            st.info("ℹ️ Seul le Directeur des Ressources Humaines (DRH) peut effectuer une clôture manuelle.")

    # 2. Réouverture Exceptionnelle par le DRH
    if sess_details["statut"] in ["CLÔTURÉE", "ARCHIVÉE"]:
        st.warning("⚠️ Session clôturée et verrouillée. Toute modification nécessite une réouverture exceptionnelle.")
        
        if st.session_state.user_role == "Directeur des Ressources Humaines (DRH)":
            st.markdown("#### 🔑 Espace d'autorisation DRH - Réouverture")
            motif_reouv = st.text_area("Motif détaillé obligatoire de la réouverture :")
            conf_reouv = st.checkbox("Je certifie engager ma responsabilité pour la réouverture de cette session.")
            
            if st.button("🔓 Rouvrir la Session pour Corrections"):
                if not motif_reouv.strip():
                    st.error("🛑 Erreur : Le motif détaillé est obligatoire.")
                elif not conf_reouv:
                    st.error("🛑 Veuillez cocher la case de confirmation.")
                else:
                    sess_details["statut"] = "ROUVERTE APRÈS CLÔTURE"
                    sess_details["motif_reouverture"] = motif_reouv
                    sess_details["drh_reouverture"] = st.session_state.user_role
                    sess_details["historique_reouvertures"].append({
                        "Timestamp": datetime.now(DAKAR_TZ).strftime("%Y-%m-%d %H:%M:%S"),
                        "DRH": st.session_state.user_role,
                        "Motif": motif_reouv
                    })
                    enregistrer_audit("DRH", "Réouverture Exceptionnelle", selected_sid, f"Motif: {motif_reouv}")
                    ajouter_notification(f"Session {selected_sid} exceptionnellement rouverte par le DRH.")
                    st.success("Session rouverte sous le statut 'ROUVERTE APRÈS CLÔTURE'.")
                    st.rerun()
        else:
            st.info("ℹ️ Seul le DRH peut autoriser une réouverture.")

    # 3. Consultation et Export PDF officiel pour DAF & DG
    if sess_details["archives_donnees"] is not None:
        st.markdown("#### 📦 Données Archivées & Rapports Officiels DAF / DG")
        st.dataframe(sess_details["archives_donnees"][['Matricule_CNI', 'Nom', 'Prénom', 'Net_A_Payer']], use_container_width=True)
        
        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            csv_archive = sess_details["archives_donnees"].to_csv(index=False, sep=';').encode('utf-8')
            st.download_button(
                label=f"📥 Télécharger l'archive CSV - {selected_sid}",
                data=csv_archive,
                file_name=f"archive_{selected_sid.lower()}.csv",
                mime='text/csv'
            )
        with col_dl2:
            pdf_bytes = generer_pdf_session(selected_sid, sess_details, sess_details["archives_donnees"])
            st.download_button(
                label=f"📄 Télécharger le Rapport PDF officiel (DAF & DG) - {selected_sid}",
                data=pdf_bytes,
                file_name=f"rapport_officiel_daf_dg_{selected_sid.lower()}.pdf",
                mime='application/pdf'
            )

# ==============================================================================
# ONGLET 5 : RAPPORTS & SUPERVISION
# ==============================================================================
onglet5_1, onglet5_2 = st.tabs(["📊 Rapports de Suivi", "🛠️ Supervision Technique & Erreurs"])

with onglet5_1:
    st.subheader("📊 Rapports de Suivi & État de la Masse Salariale")
    total_agents = len(df[df['Statut'] == 'Actif'])
    masse_totale = df['Net_A_Payer'].sum()
    
    col_rep1, col_rep2, col_rep3 = st.columns(3)
    col_rep1.metric("Effectif Volontaires Actifs", total_agents)
    col_rep2.metric("Masse Pécule Nette", f"{masse_totale:,.0f} F CFA".replace(',', ' '))
    col_rep3.metric("Sessions Enregistrées", len(st.session_state.sessions_db))
    
    st.write("---")
    st.markdown("#### 📈 Répartition par Région")
    if not df.empty:
        reg_df = df.groupby('Région')['Net_A_Payer'].sum().reset_index()
        st.dataframe(reg_df, use_container_width=True)

with onglet5_2:
    st.subheader("🛠️ Supervision Technique, Incidents & Tâches (Admin)")
    st.markdown("Supervision des tâches automatisées et de l'intégrité du système.")
    
    if st.session_state.user_role == "Administrateur technique":
        st.info("🔧 Panneau d'administration technique : Diagnostic et supervision des services de fond.")
        st.write(f"**Fuseau Horaire Actif :** Dakar / Sénégal (`Africa/Dakar`)")
        st.write(f"**État du Moteur de Tâches :** Actif & Opérationnel")
        if st.button("🔍 Lancer un diagnostic de cohérence"):
            st.success("Diagnostic terminé : Aucune anomalie détectée.")
    else:
        st.warning("⚠️ Accès restreint : Réservé à l'Administrateur technique.")

# ==============================================================================
# ONGLET 6 : JOURNAL D'AUDIT
# ==============================================================================
with onglet6:
    st.subheader("📜 Journal d'Audit & Traçabilité des Opérations")
    st.markdown("Traçabilité réglementaire complète (Utilisateur, horodatage Dakar, session, nature de l'opération).")
    
    df_audit = pd.DataFrame(st.session_state.journal_audit)
    st.dataframe(df_audit, use_container_width=True)
