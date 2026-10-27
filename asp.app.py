import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import pytz

# Configuration du fuseau horaire Africa/Dakar
DAKAR_TZ = pytz.timezone('Africa/Dakar')

st.set_page_config(page_title="Système National ASP Sénégal", layout="wide")

st.title("🇸🇳 Système Intégré de Gestion des Volontaires ASP")
st.markdown("### Direction des Ressources Humaines et de la Solde - Sénégal")

# --- INITIALISATION DE LA BASE DE DONNÉES EN SESSION ---
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

# --- INITIALISATION DU CYCLE DES SESSIONS MENSUELLES & JOURNAL D'AUDIT ---
if 'sessions_historique' not in st.session_state:
    # Session en cours (Avril 2026 par exemple)
    st.session_state.sessions_historique = {
        "Avril 2026": {
            "statut": "OUVERTE", # Statuts autorisés : EN ATTENTE D'OUVERTURE, OUVERTE, EN COURS DE CONTRÔLE, CLÔTURÉE, ROUVERTE APRÈS CLÔTURE, ARCHIVÉE, CLÔTURE EN ÉCHEC
            "date_ouverture": datetime.now(DAKAR_TZ).strftime("%Y-%m-%d %H:%M"),
            "date_cloture": None,
            "motif_reouverture": "",
            "drh_reouverture": "",
            "archives_donnees": None
        }
    }

if 'session_active_mois' not in st.session_state:
    st.session_state.session_active_mois = "Avril 2026"

if 'journal_audit' not in st.session_state:
    st.session_state.journal_audit = [
        {"Timestamp": datetime.now(DAKAR_TZ).strftime("%Y-%m-%d %H:%M:%S"), "Utilisateur": "Système DRH", "Action": "Ouverture automatique de la session Avril 2026", "Données": "Initialisation du cycle mensuel"}
    ]

if 'user_role' not in st.session_state:
    st.session_state.user_role = "Gestionnaire RH" # Options : "Gestionnaire RH", "Directeur des Ressources Humaines (DRH)"

def enregistrer_audit(utilisateur, action, donnees):
    st.session_state.journal_audit.insert(0, {
        "Timestamp": datetime.now(DAKAR_TZ).strftime("%Y-%m-%d %H:%M:%S"),
        "Utilisateur": utilisateur,
        "Action": action,
        "Données": donnees
    })

df = st.session_state.df_asp
curr_session = st.session_state.session_active_mois
session_data = st.session_state.sessions_historique[curr_session]
statut_actuel = session_data["statut"]

# Fonction de vérification d'édition
def modification_autorisee():
    return statut_actuel in ["OUVERTE", "EN COURS DE CONTRÔLE", "ROUVERTE APRÈS CLÔTURE"]

# --- REGLE METIER : CALCUL DU NET A PAYER ---
def calculer_net(row):
    if row['Statut'] in ['Radié', 'Démissionnaire']:
        return 0
    prime_effective = 0
    if row['Beneficie_Prime']:
        prime_effective = row['Prime']
        
    net = row['Pécule_Base'] + prime_effective - row['Cotisation_Mutuelle'] - row['Retenue_Pret'] - row['Sanction_Discipline']
    return max(0, net)

df['Net_A_Payer'] = df.apply(calculer_net, axis=1)

# --- BARRE LATÉRALE DE CONTRÔLE DE SESSION ---
with st.sidebar:
    st.markdown("### ⚙️ Paramètres & Rôle")
    st.session_state.user_role = st.selectbox("Rôle Connecté :", ["Gestionnaire RH", "Directeur des Ressources Humaines (DRH)"])
    
    st.write("---")
    st.markdown("### 📅 Session Active")
    st.info(f"Mois : **{curr_session}**\n\nStatut : **{statut_actuel}**")
    
    # Indicateur de simulation temporelle (pour tester le 29 du mois)
    st.markdown("#### ⏱️ Simulateur de Cycle")
    if statut_actuel in ["OUVERTE", "EN COURS DE CONTRÔLE", "ROUVERTE APRÈS CLÔTURE"]:
        if st.button("⚡ Simuler Clôture automatique (29 du mois)"):
            session_data["statut"] = "CLÔTURÉE"
            session_data["date_cloture"] = datetime.now(DAKAR_TZ).strftime("%Y-%m-%d %H:%M")
            session_data["archives_donnees"] = df.copy()
            
            # Préparation du mois suivant en mode "EN ATTENTE D'OUVERTURE"
            st.session_state.sessions_historique["Mai 2026"] = {
                "statut": "EN ATTENTE D'OUVERTURE",
                "date_ouverture": None,
                "date_cloture": None,
                "motif_reouverture": "",
                "drh_reouverture": "",
                "archives_donnees": None
            }
            enregistrer_audit(st.session_state.user_role, "Clôture automatique du 29", f"Session {curr_session} clôturée et archivée.")
            st.success("Session clôturée avec succès et archivée. Cycle suivant préparé.")
            st.rerun()

# --- NAVIGATION PAR ONGLETS ---
onglet1, onglet2, onglet3, onglet4, onglet5 = st.tabs([
    "📋 Registre & Recrutement", 
    "📅 Gestion des Congés", 
    "💶 Paie & Variables", 
    "🔒 Cycle Mensuel & Sessions",
    "📜 Journal d'Audit"
])

regions_list = ['Dakar', 'Thiès', 'Saint-Louis', 'Ziguinchor', 'Kaolack', 'Diourbel', 'Tambacounda']

# ==============================================================================
# ONGLET 1 : RECRUTEMENT ET MODIFICATION
# ==============================================================================
with onglet1:
    st.subheader("👤 Mouvements de Personnel (Recrutement & Édition)")
    
    if not modification_autorisee():
        st.warning(f"🔒 La session de pécules **{curr_session}** est au statut **{statut_actuel}**. Les modifications administratives sont verrouillées.")
    else:
        choix_action = st.radio("Action RH :", ["Consulter & Modifier un Profil", "Créer / Recruter un nouvel ASP"], horizontal=True)
        
        if choix_action == "Créer / Recruter un nouvel ASP":
            st.markdown("#### Formulaire d'engagement (Le numéro de CNI fait office de Matricule)")
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                n_cni = st.text_input("Numéro de Carte d'Identité (CNI) *")
                n_prenom = st.text_input("Prénom *")
                n_nom = st.text_input("Nom de famille *")
                n_dn = st.date_input("Date de naissance", value=pd.to_datetime("2000-01-01"))
                n_ln = st.text_input("Lieu de naissance")
            with col_r2:
                n_de = st.date_input("Date d'engagement officiel", value=pd.to_datetime("2026-01-01"))
                n_reg = st.selectbox("Région d'affectation", regions_list)
                n_aff = st.text_input("Lieu précis d'affectation")
                n_canal = st.selectbox("Mode de paiement initial", ['Orange Money', 'BOA', 'BNDE'])
                
                n_has_prime = st.checkbox("Bénéficiaire d'une prime ?")
                n_montant_prime = st.number_input("Montant de la prime (F CFA) :", min_value=0, step=5000, value=15000) if n_has_prime else 0
                
            if st.button("💾 Enregistrer le Recrutement"):
                if n_cni and n_prenom and n_nom:
                    if n_cni in df['Matricule_CNI'].values:
                        st.error("🛑 Erreur : Un volontaire avec ce numéro de CNI existe déjà.")
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
                        enregistrer_audit(st.session_state.user_role, "Recrutement ASP", f"Ajout de l'agent CNI: {n_cni}")
                        st.success(f"L'ASP a été enregistré sous le Matricule CNI : {n_cni}")
                        st.rerun()

        elif choix_action == "Consulter & Modifier un Profil":
            matricule_modif = st.selectbox("Sélectionnez l'ASP par sa CNI :", options=df['Matricule_CNI'].values)
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
                    edit_has_prime = st.checkbox("Bénéficiaire d'une prime", value=bool(df.at[idx, 'Beneficie_Prime']))
                    edit_montant_prime = st.number_input("Montant de la Prime", value=int(df.at[idx, 'Prime']), step=5000) if edit_has_prime else 0
                
                if st.button("💾 Sauvegarder les modifications"):
                    df.at[idx, 'Prénom'] = edit_prenom
                    df.at[idx, 'Nom'] = edit_nom
                    df.at[idx, 'Lieu_Affectation'] = edit_aff
                    df.at[idx, 'Région'] = edit_reg
                    df.at[idx, 'Statut'] = edit_statut
                    df.at[idx, 'Beneficie_Prime'] = edit_has_prime
                    df.at[idx, 'Prime'] = edit_montant_prime
                    
                    st.session_state.df_asp = df
                    enregistrer_audit(st.session_state.user_role, "Modification Profil", f"Mise à jour agent CNI: {matricule_modif}")
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
        st.warning("🔒 Session verrouillée : gestion des congés suspendue pour cette période.")
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
                    enregistrer_audit(st.session_state.user_role, "Attribution Congé", f"{jours_demandes} jours attribués à CNI: {asp_conge}")
                    st.success("Compteur mis à jour.")
                    st.rerun()

# ==============================================================================
# ONGLET 3 : PAIE, SANCTIONS & PRÊTS
# ==============================================================================
with onglet3:
    st.subheader(f"💶 Gestion des Variables de Pécules - {curr_session}")
    
    if not modification_autorisee():
        st.warning("🔒 Session clôturée : les sanctions, prêts et primes sont verrouillés.")
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
                val_sanction = st.number_input("Sanction / Retenue Discipline (F CFA)", value=int(df.at[idx_p, 'Sanction_Discipline']), step=1000)
            with col_p3:
                val_motif = st.text_input("Motif de l'action / sanction", value=str(df.at[idx_p, 'Motif_Action']))
                
            if st.button("💾 Enregistrer les variables financières"):
                df.at[idx_p, 'Retenue_Pret'] = val_pret
                df.at[idx_p, 'Sanction_Discipline'] = val_sanction
                df.at[idx_p, 'Motif_Action'] = val_motif
                st.session_state.df_asp = df
                enregistrer_audit(st.session_state.user_role, "Mise à jour Paie", f"Prêt/Sanction modifiés pour CNI: {agent_paie}")
                st.success("Variables financières enregistrées.")
                st.rerun()

        st.write("---")
        st.dataframe(df[['Matricule_CNI', 'Nom', 'Prénom', 'Pécule_Base', 'Prime', 'Retenue_Pret', 'Sanction_Discipline', 'Net_A_Payer', 'Motif_Action']], use_container_width=True)

# ==============================================================================
# ONGLET 4 : GESTION DU CYCLE MENSUEL ET STATUTS DE SESSION
# ==============================================================================
with onglet4:
    st.subheader("🔒 Machine à États & Gouvernance des Sessions de Pécules")
    
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        selected_session = st.selectbox("Sélectionner la période mensuelle :", list(st.session_state.sessions_historique.keys()))
        st.session_state.session_active_mois = selected_session
        sess_info = st.session_state.sessions_historique[selected_session]
        
    with col_s2:
        st.metric("Statut Actuel de la Session", sess_info["statut"])
        st.write(f"**Ouverture :** {sess_info['date_ouverture'] or 'Non ouverte'}")
        st.write(f"**Clôture :** {sess_info['date_cloture'] or 'En cours'}")

    st.write("---")
    
    # Workflow DRH de Réouverture Exceptionnelle
    if sess_info["statut"] in ["CLÔTURÉE", "ARCHIVÉE"]:
        st.warning("⚠️ Cette session est clôturée et archivée. Toute modification nécessite une réouverture exceptionnelle par le DRH.")
        
        if st.session_state.user_role == "Directeur des Ressources Humaines (DRH)":
            st.markdown("#### 🔑 Espace d'autorisation DRH - Réouverture Exceptionnelle")
            motif_input = st.text_area("Indiquez obligatoirement le motif détaillé de la réouverture :")
            confirmation = st.checkbox("Je confirme autoriser la réouverture de cette session sous ma responsabilité.")
            
            if st.button("🔓 Autoriser et Rouvrir la Session", type="primary"):
                if not motif_input.strip():
                    st.error("🛑 Erreur : Le motif détaillé est obligatoire pour toute réouverture.")
                elif not confirmation:
                    st.error("🛑 Veuillez cocher la case de confirmation.")
                else:
                    sess_info["statut"] = "ROUVERTE APRÈS CLÔTURE"
                    sess_info["motif_reouverture"] = motif_input
                    sess_info["drh_reouverture"] = st.session_state.user_role
                    enregistrer_audit("DRH", "Réouverture Exceptionnelle", f"Session {selected_session} rouverte. Motif: {motif_input}")
                    st.success(f"Session {selected_session} rouverte avec succès sous le statut 'ROUVERTE APRÈS CLÔTURE'.")
                    st.rerun()
        else:
            st.info("ℹ️ Vous êtes connecté en tant que Gestionnaire RH. Seul le Directeur des Ressources Humaines (DRH) peut autoriser la réouverture d'une session clôturée.")
            if sess_info["motif_reouverture"]:
                st.write(f"**Motif de réouverture enregistré par le DRH :** {sess_info['motif_reouverture']}")

    # Consultation des archives si clôturée
    if sess_info["archives_donnees"] is not None:
        st.markdown("#### 📦 Données Archivées de la Session")
        st.dataframe(sess_info["archives_donnees"][['Matricule_CNI', 'Nom', 'Prénom', 'Net_A_Payer']], use_container_width=True)
        
        csv_archive = sess_info["archives_donnees"].to_csv(index=False, sep=';').encode('utf-8')
        st.download_button(
            label=f"📥 Télécharger l'archive officielle - {selected_session}",
            data=csv_archive,
            file_name=f"archive_pecules_{selected_session.lower().replace(' ', '_')}.csv",
            mime='text/csv'
        )

# ==============================================================================
# ONGLET 5 : JOURNAL D'AUDIT
# ==============================================================================
with onglet5:
    st.subheader("📜 Journal d'Audit & Traçabilité des Opérations")
    st.markdown("Traçabilité réglementaire de toutes les opérations sensibles (utilisateurs, horodatage Dakar, natures d'opérations).")
    
    df_audit = pd.DataFrame(st.session_state.journal_audit)
    st.dataframe(df_audit, use_container_width=True)
