import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
import calendar
from zoneinfo import ZoneInfo
from fpdf import FPDF
import io
import hashlib
import qrcode

# Configuration du fuseau horaire Africa/Dakar (RG-11)
DAKAR_TZ = ZoneInfo("Africa/Dakar")

st.set_page_config(page_title="Système National ASP Sénégal", layout="wide")

st.title("🇸🇳 Système Intégré de Gestion des Volontaires ASP")
st.markdown("### Direction des Ressources Humaines de l'ASP####")

# --- 1. INITIALISATION DE LA BASE DE DONNÉES AGENTS EN SESSION ---
if 'df_asp' not in st.session_state:
    np.random.seed(42)
    regions = ['Dakar', 'Thiès', 'Saint-Louis', 'Ziguinchor', 'Kaolack', 'Diourbel', 'Tambacounda','Louga','Kolda','Sedhiou','Podor','Matam','Fatick']
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
        'Nombre_Avertissements': [0] * 10,
        'Historique_Discipline': ["Aucun antécédent"] * 10,
        'Motif_Action': ["RAS"] * 10,
        'Conges_Restants': [30] * 10,
        'Dernier_Conge_Debut': ["-"] * 10,
        'Dernier_Conge_Fin': ["-"] * 10,
        'Dernier_Conge_Jours': [0] * 10,
        'Statut': ['Actif'] * 10
    })
    
    mask_om = df_init['Canal_Paiement'] == 'Orange Money'
    df_init.loc[mask_om, 'Compte_Numero'] = [f"77 {np.random.randint(100, 999)} {np.random.randint(10, 99)} {np.random.randint(10, 99)}" for _ in range(mask_om.sum())]
    
    st.session_state.df_asp = df_init

# --- 2. INITIALISATION DES ÉTATS DE SESSION & SÉCURITÉ ---
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

if 'notifications_emails' not in st.session_state:
    st.session_state.notifications_emails = [
        {
            "Timestamp": now_dakar.strftime("%Y-%m-%d %H:%M:%S"),
            "Destinataires": "DAF, DG",
            "Sujet": f"Ouverture session {current_session_id}",
            "Contenu": f"La session de pécules {current_session_id} est ouverte et opérationnelle."
        }
    ]

if 'user_role' not in st.session_state:
    st.session_state.user_role = "Gestionnaire RH" 

if 'sanction_soumise_id' not in st.session_state:
    st.session_state.sanction_soumise_id = None

# --- 3. FONCTIONS UTILITAIRES ---
def enregistrer_audit(utilisateur, action, session_id, details):
    st.session_state.journal_audit.insert(0, {
        "Timestamp": datetime.now(DAKAR_TZ).strftime("%Y-%m-%d %H:%M:%S"),
        "Utilisateur": utilisateur,
        "Action": action,
        "Session": session_id,
        "Détails": details
    })

def envoyer_alerte_email_daf_dg(session_id, type_cloture, masse_totale):
    timestamp_str = datetime.now(DAKAR_TZ).strftime("%Y-%m-%d %H:%M:%S")
    sujet = f"[ALERTE OFFICIELLE ASP] Clôture et transmission signée - Session {session_id}"
    contenu = (
        f"À l'attention de la DAF et du Directeur Général,\n\n"
        f"Nous vous informons que la session de pécules '{session_id}' vient d'être clôturée "
        f"({type_cloture}) et signée électroniquement par la DRH.\n"
        f"Masse salariale nette arrêtée : {masse_totale:,.0f} F CFA.\n"
        f"Les états de paie et les rapports avec cachet numérique sont prêts pour mandatement."
    )
    st.session_state.notifications_emails.insert(0, {
        "Timestamp": timestamp_str,
        "Destinataires": "DAF (daf@asp.gouv.sn), Directeur Général (dg@asp.gouv.sn)",
        "Sujet": sujet,
        "Contenu": contenu
    })

def calculer_jours_ouvres(date_debut, date_fin):
    if date_debut > date_fin:
        return 0
    feries_fixes = [(1, 1), (4, 4), (5, 1), (8, 15), (11, 1), (12, 25)]
    current = date_debut
    jours_ouvres = 0
    while current <= date_fin:
        is_weekend = current.weekday() in [5, 6]
        is_ferie = (current.month, current.day) in feries_fixes
        if not is_weekend and not is_ferie:
            jours_ouvres += 1
        current += timedelta(days=1)
    return jours_ouvres

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

# --- GÉNÉRATEUR DE SIGNATURE ÉLECTRONIQUE & QR CODE ---
def generer_sceau_electronique(contenu_texte, signataire="Direction des Ressources Humaines (DRH - ASP)"):
    timestamp = datetime.now(DAKAR_TZ).strftime('%Y-%m-%d %H:%M:%S %Z')
    signature_base = f"{contenu_texte}-{signataire}-{timestamp}"
    hash_sceau = hashlib.sha256(signature_base.encode('utf-8')).hexdigest()[:32].upper()
    
    sceau_block = (
        f"--- DOCUMENT SIGNE ELECTRONIQUEMENT ---\n"
        f"Signataire : {signataire}\n"
        f"Horodatage (Dakar) : {timestamp}\n"
        f"Empreinte / Sceau Numérique SHA-256 : {hash_sceau}\n"
        f"Statut : Authentifie et Certifie conforme"
    )
    return sceau_block, hash_sceau

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
        self.cell(0, 4, "MINISTERE DE L'INTERIEUR - DIRECTION DE L'AGENCE D'ASSISTANCE A LA SECURITE DE PROXIMITE (ASP)", 0, 1, 'C')
        self.cell(0, 4, "Direction des Ressources Humaines et de la Solde", 0, 1, 'C')
        self.ln(8)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f"Page {self.page_no()} - Document officiel sécurisé par Sceau Électronique & QR Code DRH", 0, 0, 'C')

def generer_pdf_session(session_id, session_data, df_archivé, filtre_region="Toutes", filtre_canal="Tous"):
    pdf = PDFOfficiel(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 8, f"ETAT DE LA MASSE SALARIALE - {session_id}", 0, 1, 'C')
    pdf.set_font('Helvetica', '', 9)
    pdf.cell(0, 5, f"Filtre Region : {filtre_region} | Filtre Canal : {filtre_canal}", 0, 1, 'C')
    pdf.cell(0, 5, f"Date de generation : {datetime.now(DAKAR_TZ).strftime('%Y-%m-%d %H:%M')}", 0, 1, 'C')
    pdf.ln(4)
    
    actifs_df = df_archivé[df_archivé['Statut'] == 'Actif']
    total_agents = len(actifs_df)
    masse_totale = df_archivé['Net_A_Payer'].sum()
    
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(0, 5, f"Effectif Filtré : {total_agents} agents", 0, 1, 'L')
    pdf.cell(0, 5, f"Masse Nette Filtrée : {masse_totale:,.0f} F CFA".replace(',', ' '), 0, 1, 'L')
    pdf.ln(4)
    
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(30, 6, "CNI", 1, 0, 'C', True)
    pdf.cell(30, 6, "Nom", 1, 0, 'C', True)
    pdf.cell(30, 6, "Prenom", 1, 0, 'C', True)
    pdf.cell(25, 6, "Region", 1, 0, 'C', True)
    pdf.cell(25, 6, "Canal", 1, 0, 'C', True)
    pdf.cell(45, 6, "Net a Payer (F CFA)", 1, 1, 'C', True)
    
    pdf.set_font('Helvetica', '', 8)
    for _, row in df_archivé.iterrows():
        pdf.cell(30, 5, str(row['Matricule_CNI']), 1, 0, 'C')
        pdf.cell(30, 5, str(row['Nom'])[:15], 1, 0, 'L')
        pdf.cell(30, 5, str(row['Prénom'])[:15], 1, 0, 'L')
        pdf.cell(25, 5, str(row['Région']), 1, 0, 'C')
        pdf.cell(25, 5, str(row['Canal_Paiement']), 1, 0, 'C')
        pdf.cell(45, 5, f"{row['Net_A_Payer']:,.0f}".replace(',', ' '), 1, 1, 'R')
        
    pdf.ln(6)
    
    sceau, hash_val = generer_sceau_electronique(f"SESSION-{session_id}-{masse_totale}")
    
    # Insertion du QR Code dans le PDF
    qr_io = generer_image_qrcode(f"ASP-SENEGAL VERIFIED HASH: {hash_val} SESSION: {session_id}")
    pdf.image(qr_io, x=155, y=pdf.get_y(), w=35)
    
    pdf.set_font('Helvetica', 'B', 7)
    pdf.set_text_color(0, 51, 102)
    pdf.multi_cell(130, 4, sceau, border=1, fill=False)
    pdf.set_text_color(0, 0, 0)
    
    return bytes(pdf.output())

def generer_excel_session(session_id, df_archivé):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_archivé.to_excel(writer, sheet_name=f'Masse_{session_id}', index=False)
    return output.getvalue()

def generer_pdf_attestation(type_attestation, agent):
    pdf = PDFOfficiel(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    
    pdf.set_font('Helvetica', 'B', 12)
    titres = {
        "prise": "ATTESTATION DE PRISE EN SERVICE",
        "service": "ATTESTATION DE SERVICE (PRESENCE EFFECTIVE)",
        "conge": "ATTESTATION DE JOUISSANCE DE CONGE",
        "reprise": "ATTESTATION DE REPRISE DE SERVICE"
    }
    pdf.cell(0, 8, titres.get(type_attestation, "ATTESTATION ADMINISTRATIVE"), 0, 1, 'C')
    pdf.ln(6)
    
    pdf.set_font('Helvetica', '', 10)
    nom_complet = f"{agent['Prénom']} {agent['Nom']}"
    cni = agent['Matricule_CNI']
    date_naiss = agent['Date_Naissance']
    lieu_naiss = agent['Lieu_Naissance']
    date_eng = agent['Date_Engagement']
    affectation = agent['Lieu_Affectation']
    region = agent['Région']
    
    c_debut = str(agent.get('Dernier_Conge_Debut', 'Non spécifiée'))
    c_fin = str(agent.get('Dernier_Conge_Fin', 'Non spécifiée'))
    c_jours = str(agent.get('Dernier_Conge_Jours', 0))
    
    corps = {
        "prise": (
            f"Le Directeur des Ressources Humaines de l'Agence d'Assistance à la Sécurité de Proximité (ASP) "
            f"atteste par la présente que l'Agent de Sécurité de Proximité (Volontaire) :\n\n"
            f"   - Nom et Prénom : {nom_complet}\n"
            f"   - Numéro CNI (Matricule) : {cni}\n"
            f"   - Né(e) le : {date_naiss} à {lieu_naiss}\n\n"
            f"a bien pris ses fonctions et service en date du {date_eng} à l'affectation suivante : "
            f"{affectation} (Région de {region}).\n\n"
            f"En foi de quoi, la présente attestation lui est délivrée pour servir et valoir ce que de droit."
        ),
        "service": (
            f"Le Directeur des Ressources Humaines de l'Agence d'Assistance à la Sécurité de Proximité (ASP) "
            f"atteste par la présente que l'Agent de Sécurité de Proximité (Volontaire) :\n\n"
            f"   - Nom et Prénom : {nom_complet}\n"
            f"   - Numéro CNI (Matricule) : {cni}\n"
            f"   - Né(e) le : {date_naiss} à {lieu_naiss}\n\n"
            f"Est régulièrement en fonction et en activité au sein de l'affectation : {affectation} "
            f"(Région de {region}) depuis son engagement en date du {date_eng}.\n\n"
            f"La présente attestation est délivrée à l'intéressé(e) sur sa demande pour servir et valoir ce que de droit."
        ),
        "conge": (
            f"Le Directeur des Ressources Humaines de l'Agence d'Assistance à la Sécurité de Proximité (ASP) "
            f"atteste par la présente que l'Agent de Sécurité de Proximité (Volontaire) :\n\n"
            f"   - Nom et Prénom : {nom_complet}\n"
            f"   - Numéro CNI (Matricule) : {cni}\n"
            f"   - Affectation : {affectation} ({region})\n\n"
            f"Bénéficie d'un congé annuel réglementaire accordé selon les modalités suivantes :\n"
            f"   - Date de début : {c_debut}\n"
            f"   - Date de fin : {c_fin}\n"
            f"   - Durée effective : {c_jours} jour(s) ouvré(s) (hors samedis, dimanches et jours fériés légaux).\n\n"
            f"En foi de quoi, la présente attestation de congé est délivrée pour servir et valoir ce que de droit."
        ),
        "reprise": (
            f"Le Directeur des Ressources Humaines de l'Agence d'Assistance à la Sécurité de Proximité (ASP) "
            f"atteste par la présente que l'Agent de Sécurité de Proximité (Volontaire) :\n\n"
            f"   - Nom et Prénom : {nom_complet}\n"
            f"   - Numéro CNI (Matricule) : {cni}\n"
            f"   - Affectation : {affectation} ({region})\n\n"
            f"A effectivement repris son service le {c_fin} à l'issue de son congé réglementaire de {c_jours} jour(s) ouvré(s).\n\n"
            f"En foi de quoi, la présente attestation de reprise de service est délivrée pour servir et valoir ce que de droit."
        )
    }
    
    pdf.multi_cell(0, 5, corps.get(type_attestation, ""))
    pdf.ln(10)
    
    sceau_agent, hash_val = generer_sceau_electronique(f"ATTESTATION-{type_attestation.upper()}-{cni}")
    
    # Insertion du QR Code dans l'attestation
    qr_io = generer_image_qrcode(f"ASP-SENEGAL VERIFIED HASH: {hash_val} CNI: {cni} ACTE: {type_attestation.upper()}")
    pdf.image(qr_io, x=155, y=pdf.get_y(), w=35)
    
    pdf.set_font('Helvetica', 'B', 7)
    pdf.set_text_color(0, 51, 102)
    pdf.multi_cell(130, 4, sceau_agent, border=1, fill=False)
    pdf.set_text_color(0, 0, 0)
    
    return bytes(pdf.output())

# --- 4. BARRE LATÉRALE ---
with st.sidebar:
    st.markdown("### ⚙️ Gestion des Acteurs & Sécurité")
    st.session_state.user_role = st.selectbox(
        "Profil Connecté :", 
        ["Gestionnaire RH", "Directeur des Ressources Humaines (DRH)", "Administrateur technique"]
    )
    
    st.write("---")
    st.markdown(f"### 📅 Session : {active_sid}")
    st.info(f"Statut : **{statut_session}**")
    
    st.markdown("#### 🔔 Dernières Alertes E-mail")
    if st.session_state.notifications_emails:
        derniere_notif = st.session_state.notifications_emails[0]
        st.info(f"**{derniere_notif['Timestamp']}**\n\n{derniere_notif['Sujet']}")

# --- 5. NAVIGATION PAR ONGLETS ---
onglet1, onglet2, onglet3, onglet4, onglet5, onglet6, onglet7, onglet8, onglet9 = st.tabs([
    "📋 Registre", 
    "📂 Dossier & Signature",
    "📅 Congés", 
    "⚖️ Conseil de Discipline",
    "💶 Paie", 
    "🔒 Cycle Mensuel",
    "📊 Rapports & Exports",
    "📧 Alertes",
    "📜 Audit"
])

regions_list = ['Dakar', 'Thiès', 'Saint-Louis', 'Ziguinchor', 'Kaolack', 'Diourbel', 'Tambacounda']

# ==============================================================================
# ONGLET 1 : REGISTRE & RECRUTEMENT
# ==============================================================================
with onglet1:
    st.subheader("👤 Mouvements de Personnel (Recrutement & Édition)")
    
    if not modification_autorisee():
        st.error(f"🔒 VERROUILLAGE SÉCURISÉ : La session **{active_sid}** est au statut **{statut_session}**.")
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
                            'Nombre_Avertissements': 0, 'Historique_Discipline': "Aucun antécédent",
                            'Motif_Action': "Nouveau recrutement", 'Conges_Restants': 30,
                            'Dernier_Conge_Debut': "-", 'Dernier_Conge_Fin': "-", 'Dernier_Conge_Jours': 0,
                            'Statut': 'Actif'
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
    st.dataframe(df[['Matricule_CNI', 'Nom', 'Prénom', 'Région', 'Lieu_Affectation', 'Statut', 'Net_A_Payer']], use_container_width=True)

# ==============================================================================
# ONGLET 2 : DOSSIER PERSONNEL & SIGNATURE ÉLECTRONIQUE DES ACTES
# ==============================================================================
with onglet2:
    st.subheader("📂 Dossier Personnel & Traçabilité Disciplinaire")
    st.markdown("Consultez le dossier d'un volontaire, ses avertissements, sanctions et téléchargez ses attestations officielles signées par le DRH avec QR Code.")
    
    agent_selection_cni = st.selectbox("Rechercher un Volontaire (par CNI) :", options=df['Matricule_CNI'].values, format_func=lambda x: f"{x} - {df[df['Matricule_CNI']==x]['Prénom'].values[0]} {df[df['Matricule_CNI']==x]['Nom'].values[0]} ({df[df['Matricule_CNI']==x]['Statut'].values[0]})")
    
    if agent_selection_cni:
        agent_row = df[df['Matricule_CNI'] == agent_selection_cni].iloc[0]
        
        st.write("---")
        st.markdown(f"### Fiche Signalétique : {agent_row['Prénom']} {agent_row['Nom']}")
        
        col_d1, col_d2, col_d3 = st.columns(3)
        with col_d1:
            st.metric("Matricule CNI", agent_row['Matricule_CNI'])
            st.text(f"Nom : {agent_row['Nom']}")
            st.text(f"Prénom : {agent_row['Prénom']}")
        with col_d2:
            st.text(f"Date de naissance : {agent_row['Date_Naissance']}")
            st.text(f"Lieu de naissance : {agent_row['Lieu_Naissance']}")
            st.text(f"Date d'engagement : {agent_row['Date_Engagement']}")
        with col_d3:
            st.text(f"Région : {agent_row['Région']}")
            st.text(f"Affectation : {agent_row['Lieu_Affectation']}")
            st.metric("Statut RH", agent_row['Statut'])
            
        st.write("---")
        st.markdown("#### ⚖️ Suivi Disciplinaire & Antécédents")
        col_disc1, col_disc2 = st.columns(2)
        with col_disc1:
            st.metric("Nombre total d'Avertissements", agent_row['Nombre_Avertissements'])
        with col_disc2:
            st.text_area("Historique et Motifs Disciplinaires :", value=str(agent_row['Historique_Discipline']), disabled=True)
            
        st.write("---")
        st.markdown("#### 🔏 Génération & Signature Électronique avec QR Code")
        
        if st.session_state.user_role != "Directeur des Ressources Humaines (DRH)":
            st.warning("⚠️ Restriction de sécurité : Seul le profil **Directeur des Ressources Humaines (DRH)** peut apposer la signature électronique officielle et le QR Code sur les actes administratifs.")
        else:
            st.success("✔ Profil DRH authentifié : Vous pouvez générer les actes sécurisés par QR Code.")
            
            col_att1, col_att2 = st.columns(2)
            with col_att1:
                pdf_prise = generer_pdf_attestation("prise", agent_row)
                st.download_button(
                    label="🔏 Télécharger Prise en Service (Signée + QR Code)",
                    data=pdf_prise,
                    file_name=f"prise_en_service_signee_{agent_row['Matricule_CNI']}.pdf",
                    mime='application/pdf'
                )
                
                pdf_service = generer_pdf_attestation("service", agent_row)
                st.download_button(
                    label="🔏 Télécharger Attestation de Service (Signée + QR Code)",
                    data=pdf_service,
                    file_name=f"attestation_service_signee_{agent_row['Matricule_CNI']}.pdf",
                    mime='application/pdf'
                )
                
            with col_att2:
                pdf_conge = generer_pdf_attestation("conge", agent_row)
                st.download_button(
                    label="🔏 Télécharger Attestation de Congé (Signée + QR Code)",
                    data=pdf_conge,
                    file_name=f"attestation_conge_signee_{agent_row['Matricule_CNI']}.pdf",
                    mime='application/pdf'
                )
                
                pdf_reprise = generer_pdf_attestation("reprise", agent_row)
                st.download_button(
                    label="🔏 Télécharger Reprise de Service (Signée + QR Code)",
                    data=pdf_reprise,
                    file_name=f"reprise_service_signee_{agent_row['Matricule_CNI']}.pdf",
                    mime='application/pdf'
                )

# ==============================================================================
# ONGLET 3 : PLANIFICATION DES CONGÉS
# ==============================================================================
with onglet3:
    st.subheader("📅 Planification des Congés Annuels (Calcul en Jours Ouvrés)")
    st.markdown("⚠️ **Règle de décompte :** Les samedis, dimanches et jours fériés légaux au Sénégal ne sont **pas comptés**.")
    
    if not modification_autorisee():
        st.error(f"🔒 VERROUILLAGE SÉCURISÉ : Session **{active_sid}** clôturée.")
    else:
        actifs_df = df[df['Statut'] == 'Actif']
        if not actifs_df.empty:
            asp_conge = st.selectbox("Sélectionnez l'ASP demandeur :", options=actifs_df['Matricule_CNI'].values, key="conge_box")
            if asp_conge:
                idx_c = df[df['Matricule_CNI'] == asp_conge].index[0]
                st.info(f"Solde actuel disponible : **{df.at[idx_c, 'Conges_Restants']} jours ouvrés**.")
                
                col_cg1, col_cg2 = st.columns(2)
                with col_cg1:
                    date_debut_conge = st.date_input("Date de début de congé :", value=date.today())
                with col_cg2:
                    date_fin_conge = st.date_input("Date de fin de congé :", value=date.today() + timedelta(days=7))
                    
                jours_ouvres_calcules = calculer_jours_ouvres(date_debut_conge, date_fin_conge)
                st.markdown(f"📈 **Durée décomptée :** **{jours_ouvres_calcules} jour(s) ouvré(s)** (du {date_debut_conge.strftime('%d/%m/%Y')} au {date_fin_conge.strftime('%d/%m/%Y')})")
                
                if st.button("🌴 Accorder et Valider le Congé"):
                    if jours_ouvres_calcules <= 0:
                        st.error("🛑 Erreur : La date de fin doit être supérieure ou égale à la date de début.")
                    elif jours_ouvres_calcules > df.at[idx_c, 'Conges_Restants']:
                        st.error(f"🛑 Solde insuffisant ! L'agent dispose de {df.at[idx_c, 'Conges_Restants']} jours.")
                    else:
                        df.at[idx_c, 'Conges_Restants'] -= jours_ouvres_calcules
                        df.at[idx_c, 'Dernier_Conge_Debut'] = str(date_debut_conge)
                        df.at[idx_c, 'Dernier_Conge_Fin'] = str(date_fin_conge)
                        df.at[idx_c, 'Dernier_Conge_Jours'] = jours_ouvres_calcules
                        
                        st.session_state.df_asp = df
                        enregistrer_audit(st.session_state.user_role, "Attribution Congé", active_sid, f"Congé accordé du {date_debut_conge} au {date_fin_conge} ({jours_ouvres_calcules}j) à CNI: {asp_conge}")
                        st.success(f"Congé accordé avec succès ! Solde restant : {df.at[idx_c, 'Conges_Restants']} jours.")
                        st.rerun()

# ==============================================================================
# ONGLET 4 : CONSEIL DE DISCIPLINE & SANCTIONS
# ==============================================================================
with onglet4:
    st.subheader("⚖️ Gestion du Conseil de Discipline & Sanctions")
    st.markdown("Enregistrez les décisions du Conseil de Discipline : **Avertissement**, **Sanction Pécuniaire**, ou **Radiation** (nécessitant l'approbation du DRH).")
    
    choix_mode_disc = st.radio("Action Disciplinaire :", ["Prononcer une Sanction", "Gestion des Réintégrations (Réservé DRH)"], horizontal=True)
    
    if choix_mode_disc == "Prononcer une Sanction":
        agent_disc_cni = st.selectbox("Sélectionner l'agent concerné (par CNI) :", options=df[df['Statut']=='Actif']['Matricule_CNI'].values, key="select_disc")
        if agent_disc_cni:
            idx_disc = df[df['Matricule_CNI'] == agent_disc_cni].index[0]
            agent_nom_complet = f"{df.at[idx_disc, 'Prénom']} {df.at[idx_disc, 'Nom']}"
            
            st.info(f"Agent sélectionné : **{agent_nom_complet}** (Affectation : {df.at[idx_disc, 'Lieu_Affectation']} - {df.at[idx_disc, 'Région']})")
            
            type_sanction = st.selectbox("Type de sanction prononcée par le Conseil :", ["Avertissement", "Sanction Pécuniaire", "Radiation"])
            motif_sanction = st.text_area("Motif détaillé de la faute / infraction :", placeholder="Ex: Absence injustifiée, insubordination, manquement au règlement intérieur...")
            
            montant_sanction = 0
            if type_sanction == "Sanction Pécuniaire":
                montant_sanction = st.number_input("Montant de la retenue pécuniaire (F CFA) :", min_value=1000, step=5000, value=10000)
            
            current_action_signature = f"{agent_disc_cni}-{type_sanction}-{motif_sanction}-{montant_sanction}"
            
            if st.button("⚖️ Valider et Appliquer la Décision Disciplinaire", type="primary"):
                if not motif_sanction.strip():
                    st.error("🛑 Erreur : Le motif de la sanction est obligatoire.")
                elif st.session_state.sanction_soumise_id == current_action_signature:
                    st.warning("⚠️ Cette sanction a déjà été validée et enregistrée. Session verrouillée.")
                else:
                    date_jour = datetime.now(DAKAR_TZ).strftime("%Y-%m-%d")
                    
                    if type_sanction == "Avertissement":
                        df.at[idx_disc, 'Nombre_Avertissements'] += 1
                        act_hist = df.at[idx_disc, 'Historique_Discipline']
                        nouveau_motif = f"[{date_jour}] Avertissement : {motif_sanction}"
                        df.at[idx_disc, 'Historique_Discipline'] = nouveau_motif if act_hist == "Aucun antécédent" else f"{act_hist} | {nouveau_motif}"
                        
                        st.session_state.df_asp = df
                        st.session_state.sanction_soumise_id = current_action_signature
                        enregistrer_audit(st.session_state.user_role, "Conseil de Discipline - Avertissement", active_sid, f"Avertissement prononcé pour CNI: {agent_disc_cni}. Motif: {motif_sanction}")
                        st.success(f"✅ SANCTION VALIDÉE : Avertissement enregistré avec succès pour {agent_nom_complet}. Total avertissements : {df.at[idx_disc, 'Nombre_Avertissements']}.")
                        st.rerun()
                        
                    elif type_sanction == "Sanction Pécuniaire":
                        df.at[idx_disc, 'Sanction_Discipline'] += montant_sanction
                        act_hist = df.at[idx_disc, 'Historique_Discipline']
                        nouveau_motif = f"[{date_jour}] Sanction Pécuniaire ({montant_sanction:,.0f} F CFA) : {motif_sanction}"
                        df.at[idx_disc, 'Historique_Discipline'] = nouveau_motif if act_hist == "Aucun antécédent" else f"{act_hist} | {nouveau_motif}"
                        
                        st.session_state.df_asp = df
                        st.session_state.sanction_soumise_id = current_action_signature
                        enregistrer_audit(st.session_state.user_role, "Conseil de Discipline - Sanction Pécuniaire", active_sid, f"Retenue de {montant_sanction} F CFA appliquée à CNI: {agent_disc_cni}. Motif: {motif_sanction}")
                        st.success(f"✅ SANCTION VALIDÉE & ALERTE DRH : Retenue pécuniaire de {montant_sanction:,.0f} F CFA appliquée aux variables de paie.")
                        st.rerun()
                        
                    elif type_sanction == "Radiation":
                        if st.session_state.user_role != "Directeur des Ressources Humaines (DRH)":
                            st.warning("⚠️ Approbation DRH requise : Seul le profil **Directeur des Ressources Humaines (DRH)** peut valider définitivement une radiation.")
                        else:
                            df.at[idx_disc, 'Statut'] = 'Radié'
                            act_hist = df.at[idx_disc, 'Historique_Discipline']
                            nouveau_motif = f"[{date_jour}] RADIATION VALIDÉE PAR LE DRH : {motif_sanction}"
                            df.at[idx_disc, 'Historique_Discipline'] = nouveau_motif if act_hist == "Aucun antécédent" else f"{act_hist} | {nouveau_motif}"
                            
                            st.session_state.df_asp = df
                            st.session_state.sanction_soumise_id = current_action_signature
                            enregistrer_audit("DRH", "Conseil de Discipline - Radiation validée", active_sid, f"Agent CNI: {agent_disc_cni} radié. Motif: {motif_sanction}")
                            st.success(f"✅ SANCTION VALIDÉE : Radiation approuvée par le DRH. L'agent {agent_nom_complet} est désormais inactif.")
                            st.rerun()

    elif choix_mode_disc == "Gestion des Réintégrations (Réservé DRH)":
        st.markdown("#### 🔄 Réintégration d'un Agent Radié")
        agents_radies = df[df['Statut'] == 'Radié']
        
        if agents_radies.empty:
            st.info("ℹ️ Aucun agent radié actuellement dans la base.")
        else:
            cni_radie = st.selectbox("Sélectionner l'agent radié à réintégrer :", options=agents_radies['Matricule_CNI'].values, format_func=lambda x: f"{x} - {df[df['Matricule_CNI']==x]['Prénom'].values[0]} {df[df['Matricule_CNI']==x]['Nom'].values[0]}")
            
            if cni_radie:
                idx_radie = df[df['Matricule_CNI'] == cni_radie].index[0]
                st.text(f"Historique disciplinaire de l'agent : {df.at[idx_radie, 'Historique_Discipline']}")
                
                motif_reintegration = st.text_area("Motif détaillé et obligatoire de la réintégration (Réservé DRH) :", placeholder="Ex: Décision de recours favorable, grâce gracieuse...")
                
                if st.session_state.user_role != "Directeur des Ressources Humaines (DRH)":
                    st.warning("⚠️ Seul le profil **Directeur des Ressources Humaines (DRH)** est habilité à réintégrer un agent radié.")
                else:
                    if st.button("🔓 Approuver la Réintégration de l'Agent", type="primary"):
                        if not motif_reintegration.strip():
                            st.error("🛑 Erreur : Le motif de réintégration est obligatoire.")
                        else:
                            df.at[idx_radie, 'Statut'] = 'Actif'
                            date_jour = datetime.now(DAKAR_TZ).strftime("%Y-%m-%d")
                            act_hist = df.at[idx_radie, 'Historique_Discipline']
                            nouveau_motif = f"[{date_jour}] RÉINTÉGRATION PAR LE DRH : {motif_reintegration}"
                            df.at[idx_radie, 'Historique_Discipline'] = f"{act_hist} | {nouveau_motif}"
                            
                            st.session_state.df_asp = df
                            enregistrer_audit("DRH", "Réintégration Agent Radié", active_sid, f"Agent CNI: {cni_radie} réintégré. Motif: {motif_reintegration}")
                            st.success(f"✅ RÉINTÉGRATION VALIDÉE : Agent CNI {cni_radie} réintégré avec succès et replacé au statut 'Actif'.")
                            st.rerun()

# ==============================================================================
# ONGLET 5 : PAIE & VARIABLES
# ==============================================================================
with onglet5:
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
                val_sanction = st.number_input("Sanction Pécuniaire / Discipline (F CFA)", value=int(df.at[idx_p, 'Sanction_Discipline']), step=1000)
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
# ONGLET 6 : GESTION DU CYCLE MENSUEL & SESSIONS
# ==============================================================================
with onglet6:
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

    st.write("---")
    
    if sess_details["statut"] in ["OUVERTE", "EN COURS DE CONTRÔLE", "ROUVERTE APRÈS CLÔTURE"]:
        st.markdown("#### 🛑 Clôture de Session par le DRH")
        if st.session_state.user_role == "Directeur des Ressources Humaines (DRH)":
            if st.checkbox("Je confirme vouloir clôturer cette session et y apposer la signature électronique officielle."):
                if st.button("🔒 Clôturer et Signer la Session", type="primary"):
                    sess_details["statut"] = "CLÔTURÉE"
                    sess_details["date_cloture"] = datetime.now(DAKAR_TZ).strftime("%Y-%m-%d %H:%M")
                    sess_details["type_cloture"] = "MANUELLE"
                    sess_details["archives_donnees"] = df.copy()
                    
                    masse_tot = df['Net_A_Payer'].sum()
                    envoyer_alerte_email_daf_dg(selected_sid, "MANUELLE", masse_tot)
                    
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
                    enregistrer_audit("DRH", "Clôture & Signature", selected_sid, "Session clôturée et signée électroniquement.")
                    st.success("Session clôturée avec succès, signée électroniquement et transmise à la DAF/DG.")
                    st.rerun()
        else:
            st.info("ℹ️ Seul le Directeur des Ressources Humaines (DRH) peut clôturer et signer la session.")

    if sess_details["archives_donnees"] is not None:
        st.markdown("#### 📦 Données Archivées & Rapports Signés Électroniquement")
        st.dataframe(sess_details["archives_donnees"][['Matricule_CNI', 'Nom', 'Prénom', 'Statut', 'Net_A_Payer']], use_container_width=True)

# ==============================================================================
# ONGLET 7 : RAPPORTS & EXPORTS MULTICRITÈRES
# ==============================================================================
onglet7_1, onglet7_2, onglet7_3 = st.tabs(["📊 Rapports de Suivi", "📥 Exports Masse Salariale (Filtrés)", "🛠️ Supervision Technique"])

with onglet7:
    pass

with onglet7_1:
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

with onglet7_2:
    st.subheader("📥 Téléchargement des États de la Masse Salariale (Filtres Avancés)")
    session_export_choice = st.selectbox("Sélectionner la session / mois :", list(st.session_state.sessions_db.keys()), key="select_export_mois")
    session_export_data = st.session_state.sessions_db[session_export_choice]
    
    df_base_export = session_export_data["archives_donnees"] if session_export_data["archives_donnees"] is not None else df
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        options_regions = ['Toutes'] + list(df_base_export['Région'].unique())
        filtre_region = st.selectbox("Filtrer par Région :", options_regions)
    with col_f2:
        options_canaux = ['Tous'] + list(df_base_export['Canal_Paiement'].unique())
        filtre_canal = st.selectbox("Filtrer par Canal de Paiement :", options_canaux)
        
    df_a_exporter = df_base_export.copy()
    if filtre_region != 'Toutes':
        df_a_exporter = df_a_exporter[df_a_exporter['Région'] == filtre_region]
    if filtre_canal != 'Tous':
        df_a_exporter = df_a_exporter[df_a_exporter['Canal_Paiement'] == filtre_canal]
        
    st.info(f"Filtres actifs -> Session : **{session_export_choice}** | Région : **{filtre_region}** | Canal : **{filtre_canal}**\n\n"
            f"Effectif concerné : **{len(df_a_exporter)} agents** | Masse Nette Filtrée : **{df_a_exporter['Net_A_Payer'].sum():,.0f} F CFA**".replace(',', ' '))
    
    st.dataframe(df_a_exporter[['Matricule_CNI', 'Nom', 'Prénom', 'Région', 'Canal_Paiement', 'Statut', 'Net_A_Payer']], use_container_width=True)
    
    col_exp1, col_exp2 = st.columns(2)
    with col_exp1:
        excel_bytes = generer_excel_session(f"{session_export_choice}_{filtre_region}_{filtre_canal}", df_a_exporter)
        st.download_button(
            label=f"📊 Télécharger en EXCEL (.xlsx) - Filtre Actif",
            data=excel_bytes,
            file_name=f"masse_salariale_{session_export_choice.lower()}_{filtre_region.lower()}_{filtre_canal.lower().replace(' ', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    with col_exp2:
        pdf_export_bytes = generer_pdf_session(session_export_choice, session_export_data, df_a_exporter, filtre_region, filtre_canal)
        st.download_button(
            label=f"🔏 Télécharger en PDF Signé (.pdf) - Filtre Actif",
            data=pdf_export_bytes,
            file_name=f"masse_salariale_{session_export_choice.lower()}_{filtre_region.lower()}_{filtre_canal.lower().replace(' ', '_')}.pdf",
            mime="application/pdf"
        )

with onglet7_3:
    st.subheader("🛠️ Supervision Technique & Tâches (Admin)")
    if st.session_state.user_role == "Administrateur technique":
        st.info("🔧 Panneau d'administration technique : Diagnostic et supervision des services de fond.")
        st.write(f"**Fuseau Horaire Actif :** Dakar / Sénégal (`Africa/Dakar`)")
        st.write(f"**État du Moteur de Tâches :** Actif & Opérationnel")
    else:
        st.warning("⚠️ Accès restreint : Réservé à l'Administrateur technique.")

# ==============================================================================
# ONGLET 8 : ALERTES E-MAIL
# ==============================================================================
with onglet8:
    st.subheader("📧 Centre de Simulation des Alertes E-mail (DAF & DG)")
    st.markdown("Historique des notifications électroniques émises lors des clôtures signées.")
    for email in st.session_state.notifications_emails:
        with st.expander(f"📨 [{email['Timestamp']}] {email['Sujet']} (Destinataires : {email['Destinataires']})"):
            st.text(email['Contenu'])

# ==============================================================================
# ONGLET 9 : JOURNAL D'AUDIT
# ==============================================================================
with onglet9:
    st.subheader("📜 Journal d'Audit & Traçabilité des Opérations")
    st.markdown("Traçabilité réglementaire complète de toutes les opérations.")
    df_audit = pd.DataFrame(st.session_state.journal_audit)
    st.dataframe(df_audit, use_container_width=True)
