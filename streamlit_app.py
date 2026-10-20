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
    
    # Simulation de 10 agents de départ avec CNI
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
        'Retenue_Pret': [0] * 10,
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
onglet1, onglet2, onglet3, onglet4 = st.tabs([
    "👤 Registre & Recrutement", 
    "🏅 Attribution des Primes", 
    "📅 Gestion des Congés", 
    "💶 Paie & Sécurité Globale"
])

# ==============================================================================
# ONGLET 1 : RECRUTEMENT ET MODIFICATION (SANS LES PRIMES)
# ==============================================================================
with onglet1:
    st.subheader("👤 Mouvements de Personnel (Recrutement & Édition)")
    choix_action = st.radio("Action RH :", ["Consulter & Modifier un Profil", "Créer / Recruter un nouvel ASP"], horizontal=True)
    
    if choix_action == "Créer / Recruter un nouvel ASP":
        st.markdown("#### Formulaire d'engagement (Matricule = CNI)")
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            n_cni = st.text_input("Numéro de CNI *")
            n_prenom = st.text_input("Prénom *")
            n_nom = st.text_input("Nom de famille *")
            n_dn = st.date_input("Date de naissance", value=pd.to_datetime("2000-01-01"))
        with col_r2:
            n_ln = st.text_input("Lieu de naissance")
            n_de = st.date_input("Date d'engagement officiel", value=pd.to_datetime("2026-01-01"))
            n_reg = st.selectbox("Région d'affectation", ['Dakar', 'Thiès', 'Saint-Louis', 'Ziguinchor', 'Kaolack', 'Diourbel', 'Tambacounda'])
            n_aff = st.text_input("Lieu précis d'affectation")
            n_canal = st.selectbox("Mode de paiement initial", ['Orange Money', 'BOA', 'BNDE'])
            
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
                        'Beneficie_Prime': False, 'Prime': 0, # Pas de prime au recrutement par défaut
                        'Cotisation_Mutuelle': 2500, 'Retenue_Pret': 0, 'Sanction_Discipline': 0,
                        'Motif_Action': "Nouveau recrutement", 'Conges_Restants': 30, 'Statut': 'Actif'
                    }
                    df = pd.concat([df, pd.DataFrame([nouvel_asp])], ignore_index=True)
                    st.session_state.df_asp = df
                    st.success(f"L'ASP a été enregistré sous le Matricule CNI : {n_cni}")
                    st.rerun()
            else:
                st.error("Veuillez remplir les champs obligatoires (*)")

    elif choix_action == "Consulter & Modifier un Profil":
        matricule_modif = st.selectbox("Sélectionnez l'ASP par sa CNI :", options=df['Matricule_CNI'].values, key="select_rh")
        if matricule_modif:
            idx = df[df['Matricule_CNI'] == matricule_modif].index
            
            st.markdown(f"#### ✏️ Modification des informations de : {df.at[idx, 'Prénom']} {df.at[idx, 'Nom']}")
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                edit_prenom = st.text_input("Prénom", value=df.at[idx, 'Prénom'])
                edit_nom = st.text_input("Nom", value=df.at[idx, 'Nom'])
                edit_ln = st.text_input("Lieu de Naissance", value=df.at[idx, 'Lieu_Naissance'])
            with col_m2:
                edit_aff = st.text_input("Lieu d'affectation", value=df.at[idx, 'Lieu_Affectation'])
                edit_reg = st.selectbox("Région", ['Dakar', 'Thiès', 'Saint-Louis', 'Ziguinchor', 'Kaolack', 'Diourbel', 'Tambacounda'], index=['Dakar', 'Thiès', 'Saint-Louis', 'Ziguinchor', 'Kaolack', 'Diourbel', 'Tambacounda'].index(df.at[idx, 'Région']))
                edit_statut = st.selectbox("Statut RH", ['Actif', 'Radié', 'Démissionnaire'], index=['Actif', 'Radié', 'Démissionnaire'].index(df.at[idx, 'Statut']))
            
            if st.button("💾 Sauvegarder les modifications"):
                df.at[idx, 'Prénom'] = edit_prenom
                df.at[idx, 'Nom'] = edit_nom
                df.at[idx, 'Lieu_Naissance'] = edit_ln
                df.at[idx, 'Lieu_Affectation'] = edit_aff
                df.at[idx, 'Région'] = edit_reg
                df.at[idx, 'Statut'] = edit_statut
                
                st.session_state.df_asp = df
                st.success("Dossier administratif mis à jour.")
                st.rerun()

    st.write("---")
    st.dataframe(df[['Matricule_CNI', 'Nom', 'Prénom', 'Région', 'Lieu_Affectation', 'Statut']], use_container_width=True)

# ==============================================================================
# ONGLET 2 : NOUVEAU MODULE - GESTION DES PRIMES PAR MATRICULE / CNI
# ==============================================================================
with onglet2:
    st.subheader("🏅 Bureau d'Attribution et de Gestion des Primes (DRH)")
    st.write("Sélectionnez un volontaire par sa CNI pour lui affecter une prime spécifique ou modifier ses avantages existants.")
    
    prime_cni = st.selectbox("Rechercher l'ASP concerné (Par sa CNI) :", options=df['Matricule_CNI'].values, key="select_prime_tab")
    
    if prime_cni:
        idx_p = df[df['Matricule_CNI'] == prime_cni].index
        st.info(f"**Agent :** {df.at[idx_p, 'Prénom']} {df.at[idx_p, 'Nom']} | **Affectation :** {df.at[idx_p, 'Lieu_Affectation']} ({df.at[idx_p, 'Région']})")
        
        # Statut actuel affiché pour la DRH
        if df.at[idx_p, 'Beneficie_Prime']:
            st.success(f"Cet agent bénéficie actuellement d'une prime de : **{df.at[idx_p, 'Prime']:,} F CFA**".replace(",", " "))
        else:
            st.warning("Cet agent ne perçoit actuellement aucune prime (Pécule de base strict).")
            
        st.write("---")
        st.markdown("#### ⚙️ Mettre à jour les conditions financières de l'agent")
        
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            attribuer_prime = st.checkbox("Accorder / Maintenir une prime pour cet agent", value=bool(df.at[idx_p, 'Beneficie_Prime']))
        with col_p2:
            montant_alloue = 0
            if attribuer_prime:
                montant_alloue = st.number_input("Montant de la prime validé par la DRH (F CFA) :", min_value=0, step=5000, value=int(df.at[idx_p, 'Prime']))
                
        if st.button("⚖️ Valider la décision financière"):
            df.at[idx_p, 'Beneficie_Prime'] = attribuer_prime
            df.at[idx_p, 'Prime'] = montant_alloue if attribuer_prime else 0
            
            st.session_state.df_asp = df
            st.success(f"La fiche financière de l'ASP {df.at[idx_p, 'Prénom']} {df.at[idx_p, 'Nom']} a été ajustée.")
            st.rerun()

