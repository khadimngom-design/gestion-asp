import streamlit as st
import pandas as pd
import numpy as np
import io

st.set_page_config(page_title="Système National ASP Sénégal", layout="wide")

st.title("🇸🇳 Système Intégré de Gestion des Volontaires ASP")
st.markdown("### Direction des Ressources Humaines et de la Solde - Sénégal")

# --- INITIALISATION DE LA BASE DE DONNÉES EN SESSION ---
if 'df_asp' not in st.session_state:
    np.random.seed(42)
    regions = ['Dakar', 'Thiès', 'Saint-Louis', 'Ziguinchor', 'Kaolack', 'Diourbel', 'Tambacounda']
    canaux = ['BOA', 'Orange Money', 'BNDE']
    
    # Simulation de 10 agents de départ avec des numéros de CNI sénégalais réalistes (13 chiffres)
    df_init = pd.DataFrame({
        'Matricule_CNI': [f"1{np.random.randint(100, 999)}199{np.random.randint(10,99)}{np.random.randint(10000, 99999)}" for i in range(10)],
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
        'Beneficie_Prime': [True, False, True, False, False, True, False, False, True, False],
        'Prime':,
        'Cotisation_Mutuelle': [2500] * 10,
        'Retenue_Pret':,
        'Sanction_Discipline': [0] * 10,
        'Motif_Action': ["RAS"] * 10,
        'Conges_Restants': [30] * 10,
        'Statut': ['Actif'] * 10
    })
    
    mask_om = df_init['Canal_Paiement'] == 'Orange Money'
    df_init.loc[mask_om, 'Compte_Numero'] = [f"77 {np.random.randint(100, 999)} {np.random.randint(10, 99)} {np.random.randint(10, 99)}" for _ in range(mask_om.sum())]
    
    st.session_state.df_asp = df_init

if 'suspension_primes_globale' not in st.session_state:
    st.session_state.suspension_primes_globale = False

df = st.session_state.df_asp

# --- REGLE METIER : CALCUL DU NET A PAYER ---
def calculer_net(row):
    if row['Statut'] in ['Radié', 'Démissionnaire']:
        return 0
    prime_effective = 0
    if row['Beneficie_Prime'] and not st.session_state.suspension_primes_globale:
        prime_effective = row['Prime']
        
    net = row['Pécule_Base'] + prime_effective - row['Cotisation_Mutuelle'] - row['Retenue_Pret'] - row['Sanction_Discipline']
    return max(0, net)

df['Net_A_Payer'] = df.apply(calculer_net, axis=1)

# --- NAVIGATION PAR ONGLETS ---
onglet1, onglet2, onglet3 = st.tabs(["📋 Registre & Recrutement", "📅 Gestion des Congés", "💶 Paie & Primes Secteur"])

# ==============================================================================
# ONGLET 1 : RECRUTEMENT ET MODIFICATION
# ==============================================================================
with onglet1:
    st.subheader("👤 Mouvements de Personnel (Recrutement & Édition)")
    choix_action = st.radio("Action RH :", ["Consulter & Modifier un Profil", "Créer / Recruter un nouvel ASP"], horizontal=True)
    
    if choix_action == "Créer / Recruter un nouvel ASP":
        st.markdown("#### Formulaire d'engagement (Le numéro de CNI fera office de Matricule)")
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            n_cni = st.text_input("Numéro de Carte d'Identité (CNI) *")
            n_prenom = st.text_input("Prénom *")
            n_nom = st.text_input("Nom de famille *")
            n_dn = st.date_input("Date de naissance", value=pd.to_datetime("2000-01-01"))
            n_ln = st.text_input("Lieu de naissance")
        with col_r2:
            n_de = st.date_input("Date d'engagement officiel", value=pd.to_datetime("2026-01-01"))
            n_reg = st.selectbox("Région d'affectation", ['Dakar', 'Thiès', 'Saint-Louis', 'Ziguinchor', 'Kaolack', 'Diourbel', 'Tambacounda'])
            n_aff = st.text_input("Lieu précis d'affectation")
            n_canal = st.selectbox("Mode de paiement initial", ['Orange Money', 'BOA', 'BNDE'])
            
            st.markdown("**Configuration de la Prime DRH**")
            n_has_prime = st.checkbox("Cet agent est-il bénéficiaire d'une prime ?")
            n_montant_prime = 0
            if n_has_prime:
                n_montant_prime = st.number_input("Montant de la prime déterminé par la DRH (F CFA) :", min_value=0, step=5000, value=0)
            
        if st.button("💾 Enregistrer le Recrutement"):
            if n_cni and n_prenom and n_nom:
                if n_cni in df['Matricule_CNI'].values:
                    st.error("🛑 Erreur : Un volontaire avec ce numéro de CNI existe déjà dans la base.")
                else:
                    nouvel_asp = {
                        'Matricule_CNI': n_cni, 'Nom': n_nom, 'Prénom': n_prenom,
                        'Date_Naissance': str(n_dn), 'Lieu_Naissance': n_ln, 'Date_Engagement': str(n_de),
                        'Région': n_reg, 'Lieu_Affectation': n_aff, 'Canal_Paiement': n_canal,
                        'Compte_Numero': "A renseigner", 'Pécule_Base': 90000, 
                        'Beneficie_Prime': n_has_prime, 'Prime': n_montant_prime if n_has_prime else 0,
                        'Cotisation_Mutuelle': 2500, 'Retenue_Pret': 0, 'Sanction_Discipline': 0,
                        'Motif_Action': "Nouveau recrutement", 'Conges_Restants': 30, 'Statut': 'Actif'
                    }
                    df = pd.concat([df, pd.DataFrame([nouvel_asp])], ignore_index=True)
                    st.session_state.df_asp = df
                    st.success(f"L'ASP a été enregistré avec succès sous le Matricule CNI : {n_cni}")
                    st.rerun()
            else:
                st.error("Veuillez remplir les champs obligatoires (*)")

    elif choix_action == "Consulter & Modifier un Profil":
        matricule_modif = st.selectbox("Sélectionnez l'ASP par sa CNI :", options=df['Matricule_CNI'].values)
        if matricule_modif:
            idx = df[df['Matricule_CNI'] == matricule_modif].index[0]
            
            st.markdown(f"#### ✏️ Modification des informations de : {df.at[idx, 'Prénom']} {df.at[idx, 'Nom']}")
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                edit_prenom = st.text_input("Prénom", value=df.at[idx, 'Prénom'])
                edit_nom = st.text_input("Nom", value=df.at[idx, 'Nom'])
                edit_ln = st.text_input("Lieu de Naissance", value=df.at[idx, 'Lieu_Naissance'])
                edit_aff = st.text_input("Lieu d'affectation", value=df.at[idx, 'Lieu_Affectation'])
            with col_m2:
                edit_reg = st.selectbox("Région", ['Dakar', 'Thiès', 'Saint-Louis', 'Ziguinchor', 'Kaolack', 'Diourbel', 'Tambacounda'], index=['Dakar', 'Thiès', 'Saint-Louis', 'Ziguinchor', 'Kaolack', 'Diourbel', 'Tambacounda'].index(df.at[idx, 'Région']))
                edit_statut = st.selectbox("Statut RH", ['Actif', 'Radié', 'Démissionnaire'], index=['Actif', 'Radié', 'Démissionnaire'].index(df.at[idx, 'Statut']))
                
                st.markdown("**Ajustement de la Prime**")
                edit_has_prime = st.checkbox("Bénéficiaire d'une prime", value=bool(df.at[idx, 'Beneficie_Prime']))
                edit_montant_prime = 0
                if edit_has_prime:
                    edit_montant_prime = st.number_input("Montant de la Prime (F CFA)", value=int(df.at[idx, 'Prime']), step=5000)
            
            if st.button("💾 Sauvegarder les modifications"):
                df.at[idx, 'Prénom'] = edit_prenom
                df.at[idx, 'Nom'] = edit_nom
                df.at[idx, 'Lieu_Naissance'] = edit_ln
                df.at[idx, 'Lieu_Affectation'] = edit_aff
                df.at[idx, 'Région'] = edit_reg
                df.at[idx, 'Statut'] = edit_statut
                df.at[idx, 'Beneficie_Prime'] = edit_has_prime
                df.at[idx, 'Prime'] = edit_montant_prime if edit_has_prime else 0
                
                st.session_state.df_asp = df
                st.success("Dossier mis à jour.")
                st.rerun()

    st.write("---")
    st.dataframe(df[['Matricule_CNI', 'Nom', 'Prénom', 'Région', 'Lieu_Affectation', 'Beneficie_Prime', 'Prime', 'Statut']], use_container_width=True)

# ==============================================================================
# ONGLET 2 : CONGÉS
# ==============================================================================
with onglet2:
    st.subheader("📅 Planification des Congés Annuuels")
    asp_conge = st.selectbox("Sélectionnez l'ASP demandeur (Par sa CNI) :", options=df[df['Statut']=='Actif']['Matricule_CNI'].values, key="conge_box")
    if asp_conge:
        idx_c = df[df['Matricule_CNI'] == asp_conge].index[0]
        st.info(f"Solde disponible : **{df.at[idx_c, 'Conges_Restants']} jours**.")
        jours_demandes = st.number_input("Jours à poser :", min_value=1, max_value=max(1, int(df.at[idx_c, 'Conges_Restants'])), value=1)
        if st.button("🌴 Accorder le congé"):
            df.at[idx_c, 'Conges_Restants'] -= jours_demandes
            st.session_state.df_asp = df
            st.success("Compteur mis à jour.")
            st.rerun()

# ==============================================================================
# ONGLET 3 : FINANCES & FICHIERS BANQUES
# ==============================================================================
with onglet3:
