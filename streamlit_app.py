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
    
    df_init = pd.DataFrame({
        'Matricule': [f"ASP-2026-{i:04d}" for i in range(1, 101)],
        'Nom': np.random.choice(['Diop', 'Ndiaye', 'Sow', 'Fall', 'Gueye', 'Diallo', 'Faye'], 100),
        'Prénom': np.random.choice(['Moussa', 'Fatou', 'Ousmane', 'Awa', 'Amadou', 'Khady', 'Ibrahima'], 100),
        'Date_Naissance': ['1998-05-12'] * 100,
        'Lieu_Naissance': np.random.choice(['Dakar', 'Thiès', 'Saint-Louis', 'Kaolack'], 100),
        'Date_Engagement': ['2024-01-01'] * 100,
        'Région': np.random.choice(regions, 100),
        'Lieu_Affectation': np.random.choice(['Commissariat Central', 'Préfecture', 'Mairie', 'Lycée'], 100),
        'Canal_Paiement': np.random.choice(canaux, 100),
        'Compte_Numero': [f"SN012-{np.random.randint(10000, 99999)}" for _ in range(100)],
        'Pécule_Base': [90000] * 100,
        'Prime': np.random.choice([0, 10000, 20000], 100, p=[0.6, 0.3, 0.1]),
        'Cotisation_Mutuelle': [2500] * 100,
        'Retenue_Pret': np.random.choice([0, 5000], 100, p=[0.9, 0.1]),
        'Sanction_Discipline': [0] * 100,
        'Motif_Action': ["RAS"] * 100,
        'Conges_Restants': np.random.randint(10, 30, 100),
        'Statut': ['Actif'] * 100
    })
    
    # Formatage des numéros Orange Money au format Sénégal
    mask_om = df_init['Canal_Paiement'] == 'Orange Money'
    df_init.loc[mask_om, 'Compte_Numero'] = [f"77 {np.random.randint(100, 999)} {np.random.randint(10, 99)} {np.random.randint(10, 99)}" for _ in range(mask_om.sum())]
    
    st.session_state.df_asp = df_init

# Initialisation du commutateur global des primes
if 'suspension_primes_globale' not in st.session_state:
    st.session_state.suspension_primes_globale = False

# Récupération des données synchronisées
df = st.session_state.df_asp

# --- REGLE METIER : CALCUL DU NET A PAYER ---
def calculer_net(row):
    if row['Statut'] in ['Radié', 'Démissionnaire']:
        return 0
    prime_effective = 0 if st.session_state.suspension_primes_globale else row['Prime']
    net = row['Pécule_Base'] + prime_effective - row['Cotisation_Mutuelle'] - row['Retenue_Pret'] - row['Sanction_Discipline']
    return max(0, net)

df['Net_A_Payer'] = df.apply(calculer_net, axis=1)


# --- INTERFACE TACTILE : NAVIGATION PAR ONGLETS ---
onglet1, onglet2, onglet3 = st.tabs(["📋 Registre & Recrutement", "📅 Gestion des Congés", "💶 Paie & Primes Secteur"])

# ==============================================================================
# ONGLET 1 : RECRUTEMENT ET MODIFICATION
# ==============================================================================
with onglet1:
    st.subheader("👤 Mouvements de Personnel (Recrutement & Édition)")
    
    choix_action = st.radio("Action RH :", ["Consulter & Modifier un Profil", "Créer / Recruter un nouvel ASP"], horizontal=True)
    
    if choix_action == "Créer / Recruter un nouvel ASP":
        st.markdown("#### Formulaire d'engagement d'un nouveau volontaire")
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            n_prenom = st.text_input("Prénom")
            n_nom = st.text_input("Nom de famille")
            n_dn = st.date_input("Date de naissance", value=pd.to_datetime("2000-01-01"))
            n_ln = st.text_input("Lieu de naissance (Ex: Rufisque, Thiès...)")
        with col_r2:
            n_de = st.date_input("Date d'engagement officiel", value=pd.to_datetime("2026-01-01"))
            n_reg = st.selectbox("Région d'affectation", ['Dakar', 'Thiès', 'Saint-Louis', 'Ziguinchor', 'Kaolack', 'Diourbel', 'Tambacounda'])
            n_aff = st.text_input("Lieu précis d'affectation (Ex: Commissariat de Medina)")
            n_canal = st.selectbox("Mode de paiement initial", ['Orange Money', 'BOA', 'BNDE'])
            
        if st.button("💾 Enregistrer le Recrutement"):
            if n_prenom and n_nom:
                nouveau_matricule = f"ASP-2026-{len(df)+1:04d}"
                nouvel_asp = {
                    'Matricule': nouveau_matricule, 'Nom': n_nom, 'Prénom': n_prenom,
                    'Date_Naissance': str(n_dn), 'Lieu_Naissance': n_ln, 'Date_Engagement': str(n_de),
                    'Région': n_reg, 'Lieu_Affectation': n_aff, 'Canal_Paiement': n_canal,
                    'Compte_Numero': "A renseigner", 'Pécule_Base': 90000, 'Prime': 0,
                    'Cotisation_Mutuelle': 2500, 'Retenue_Pret': 0, 'Sanction_Discipline': 0,
                    'Motif_Action': "Nouveau recrutement", 'Conges_Restants': 30, 'Statut': 'Actif'
                }
                df = pd.concat([df, pd.DataFrame([nouvel_asp])], ignore_index=True)
                st.session_state.df_asp = df
                st.success(f"L'ASP {n_prenom} {n_nom} a été intégré avec le Matricule : {nouveau_matricule}")
                st.rerun()
            else:
                st.error("Veuillez renseigner au moins le prénom et le nom.")

    elif choix_action == "Consulter & Modifier un Profil":
        matricule_modif = st.selectbox("Sélectionnez le matricule à modifier :", options=df['Matricule'].values)
        if matricule_modif:
            idx = df[df['Matricule'] == matricule_modif].index[0]
            
            st.markdown(f"#### ✏️ Modification des informations de : {df.at[idx, 'Prénom']} {df.at[idx, 'Nom']}")
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                edit_prenom = st.text_input("Prénom", value=df.at[idx, 'Prénom'])
                edit_nom = st.text_input("Nom", value=df.at[idx, 'Nom'])
                edit_ln = st.text_input("Lieu de Naissance", value=df.at[idx, 'Lieu_Naissance'])
                edit_aff = st.text_input("Lieu précis d'affectation", value=df.at[idx, 'Lieu_Affectation'])
            with col_m2:
                edit_reg = st.selectbox("Région", ['Dakar', 'Thiès', 'Saint-Louis', 'Ziguinchor', 'Kaolack', 'Diourbel', 'Tambacounda'], index=['Dakar', 'Thiès', 'Saint-Louis', 'Ziguinchor', 'Kaolack', 'Diourbel', 'Tambacounda'].index(df.at[idx, 'Région']))
                edit_statut = st.selectbox("Statut Disciplinaire/RH", ['Actif', 'Radié', 'Démissionnaire'], index=['Actif', 'Radié', 'Démissionnaire'].index(df.at[idx, 'Statut']))
                edit_prime = st.number_input("Montant de sa Prime Spécifique (F CFA)", value=int(df.at[idx, 'Prime']), step=5000)
            
            if st.button("💾 Sauvegarder les corrections d'erreurs"):
                df.at[idx, 'Prénom'] = edit_prenom
                df.at[idx, 'Nom'] = edit_nom
                df.at[idx, 'Lieu_Naissance'] = edit_ln
                df.at[idx, 'Lieu_Affectation'] = edit_aff
                df.at[idx, 'Région'] = edit_reg
                df.at[idx, 'Statut'] = edit_statut
                df.at[idx, 'Prime'] = edit_prime
                
                st.session_state.df_asp = df
                st.success("Les informations ont été corrigées avec succès dans la base nationale.")
                st.rerun()

    st.write("---")
    st.dataframe(df[['Matricule', 'Nom', 'Prénom', 'Région', 'Lieu_Affectation', 'Date_Engagement', 'Statut']], use_container_width=True)

# ==============================================================================
# ONGLET 2 : GESTION DES CONGÉS
# ==============================================================================
with onglet2:
    st.subheader("📅 Planification des Congés Annuels")
    asp_conge = st.selectbox("Sélectionnez l'ASP demandeur de congé :", options=df[df['Statut']=='Actif']['Matricule'].values, key="conge_box")
    
    if asp_conge:
        idx_c = df[df['Matricule'] == asp_conge].index[0]
        st.info(f"Le volontaire dispose de : **{df.at[idx_c, 'Conges_Restants']} jours** de congé restants.")
        
        jours_demandes = st.number_input("Nombre de jours à poser :", min_value=1, max_value=max(1, int(df.at[idx_c, 'Conges_Restants'])), value=1)
        
        if st.button("🌴 Valider et déduire le congé"):
            df.at[idx_c, 'Conges_Restants'] -= jours_demandes
            st.session_state.df_asp = df
            st.success(f"Congé accordé. Nouveau solde : {df.at[idx_c, 'Conges_Restants']} jours.")
            st.rerun()

# ==============================================================================
# ONGLET 3 : PAIE, CRITÈRES ET BLOCAGE GLOBAL
# ==============================================================================
with onglet3:
    st.subheader("💶 Gestion Financière Avancée")
    
    st.error("⚠️ ZONE DE CONTROLE DIRECTION GENERALE")
    st.write("Gel temporaire du versement de l'ensemble des critères de primes sur toute l'étendue du territoire.")
    
    label_bouton = "🔴 SUSPENDRE TOUTES LES PRIMES NATIONALES" if not st.session_state.suspension_primes_globale else "🟢 RÉACTIVER LES PRIMES AUTOMATIQUES"
    if st.button(label_bouton):
        st.session_state.suspension_primes_globale = not st.session_state.suspension_primes_globale
        st.rerun()
        
    if st.session_state.suspension_primes_globale:
        st.warning("🚨 ALERTE : Toutes les primes sont actuellement SUSPENDUES au Sénégal. Seul le pécule de base (moins retenues) est calculé.")
    else:
        st.success("✅ État Normal : Les primes s'appliquent au cas par cas selon les critères de la DRH.")

    st.write("---")
    st.dataframe(df[['Matricule', 'Nom', 'Prénom', 'Canal_Paiement', 'Pécule_Base', 'Prime', 'Cotisation_Mutuelle', 'Retenue_Pret', 'Net_A_Payer']], use_container_width=True)
