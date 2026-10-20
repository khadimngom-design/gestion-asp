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
        'Matricule': [f"ASP-2026-{i:04d}" for i in range(1, 101)], # 100 profils de test fluides sur mobile
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
        'Prime': np.random.choice([0, 15000, 25000], 100, p=[0.6, 0.3, 0.1]),
        'Cotisation_Mutuelle': [2500] * 100,
        'Retenue_Pret': np.random.choice([0, 10000], 100, p=[0.9, 0.1]),
        'Sanction_Discipline': [0] * 100,
        'Motif_Action': ["RAS"] * 100,
        'Conges_Restants': np.random.randint(10, 30, 100),
        'Statut': ['Actif'] * 100
    })
    st.session_state.df_asp = df_init

# Initialisation du commutateur global des primes
if 'suspension_primes_globale' not in st.session_state:
    st.session_state.suspension_primes_globale = False

# Récupération des données synchronisées
df = st.session_state.df_asp

# --- REGLE METIER : SUSPENSION GLOBALE OU CALCUL DES PRIMES ---
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
# ONGLET 1 : RECRUTEMENT ET MODIFICATION DES INFORMATIONS
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
                st.success(f"Félicitations ! L'ASP {n_prenom} {n_nom} a été intégré avec le Matricule : {nouveau_matricule}")
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
                st.success("Les informations de l'ASP ont été corrigées avec succès dans la base nationale.")
                st.rerun()

    st.write("---")
    st.markdown("#### 📋 Liste générale de contrôle")
    st.dataframe(df[['Matricule', 'Nom', 'Prénom', 'Région', 'Lieu_Affectation', 'Date_Engagement', 'Statut']], use_container_width=True)

# ==============================================================================
# ONGLET 2 : GESTION DES CONGÉS
# ==============================================================================
with onglet2:
    st.subheader("📅 Planification des Congés Annuuels")
    asp_conge = st.selectbox("Sélectionnez l'ASP demandeur de congé :", options=df[df['Statut']=='Actif']['Matricule'].values, key="conge_box")
    
    if asp_conge:
        idx_c = df[df['Matricule'] == asp_conge].index[0]
        st.info(f"Le volontaire dispose actuellement de : **{df.at[idx_c, 'Conges_Restants']} jours** de congé annuel disponibles.")
        
        jours_demandes = st.number_input("Nombre de jours à poser :", min_value=1, max_value=int(df.at[idx_c, 'Conges_Restants']), value=1)
        
        if st.button("🌴 Valider et déduire le congé"):
            df.at[idx_c, 'Conges_Restants'] -= jours_demandes
            st.session_state.df_asp = df
            st.success(f"Congé accordé. Nouveau solde de l'ASP : {df.at[idx_c, 'Conges_Restants']} jours.")
            st.rerun()

# ==============================================================================
# ONGLET 3 : PAIE, CRITÈRES ET COMMUTATEUR GLOBAL DE SÉCURITÉ DES PRIMES
# ==============================================================================
with onglet3:
    st.subheader("💶 Gestion Financière Avancée")
    
    # MODULE SECURITE DRH : BLOCAGE DES PRIMES
    st.error("⚠️ ZONE DE CONTROLE DIRECTION GENERALE")
    st.write("Conformément aux critères de performance budgétaire, la Direction peut décider de geler temporairement le versement de l'ensemble des critères de primes sur toute l'étendue du territoire.")
    
    label_bouton = "🔴 SUSPENDRE TOUTES LES PRIMES NATIONALES" if not st.session_state.suspension_primes_globale else "🟢 RÉACTIVER LES PRIMES AUTOMATIQUES"
    if st.button(label_bouton):
        st.session_state.suspension_primes_globale = not st.session_state.suspension_primes_globale
        st.rerun()
        
    if st.session_state.suspension_primes_globale:
        st.warning("🚨 ALERTE : Toutes les primes sont actuellement SUSPENDUES au Sénégal. Seul le pécule de base (moins retenues) est calculé.")
    else:
        st.success("✅ État Normal : Les primes s'appliquent au cas par cas selon les critères de la DRH.")

    st.write("---")
    st.markdown("#### 📑 Aperçu des liquidations de la solde mensuelle")
import streamlit as st
import pandas as pd
import numpy as np
import io

st.set_page_config(page_title="RH, Paie & Discipline ASP", layout="wide")

st.title("🇸🇳 Système Intégré de Gestion des Volontaires ASP")
st.markdown("### Module RH : Paie, Canaux de Paiement et Registre Disciplinaire avec Motifs")

# --- INITIALISATION DE LA BASE DE DONNÉES ---
if 'df_asp' not in st.session_state:
    np.random.seed(42)
    regions = ['Dakar', 'Thiès', 'Saint-Louis', 'Ziguinchor', 'Kaolack', 'Diourbel']
    canaux = ['BOA', 'Orange Money', 'BNDE']
    
    df_init = pd.DataFrame({
        'Matricule': [f"ASP-2026-{i:04d}" for i in range(1, 501)],
        'Nom': np.random.choice(['Diop', 'Ndiaye', 'Sow', 'Fall', 'Gueye', 'Diallo', 'Faye'], 500),
        'Prénom': np.random.choice(['Moussa', 'Fatou', 'Ousmane', 'Awa', 'Amadou', 'Khady', 'Ibrahima'], 500),
        'Région': np.random.choice(regions, 500),
        'Canal de Paiement': np.random.choice(canaux, 500, p=[0.4, 0.4, 0.2]),
        'Compte / Numéro': [f"SN012-01001-{np.random.randint(10000000, 99999999)}-22" for _ in range(500)],
        'Pécule de Base (F)': [90000] * 500,
        'Prime Spéciale (F)': np.random.choice([0, 10000, 20000], 500, p=[0.6, 0.3, 0.1]),
        'Cotisation Mutuelle (F)': [2500] * 500,
        'Mensualité Prêt (F)': np.random.choice([0, 5000, 10000], 500, p=[0.85, 0.10, 0.05]),
        'Sanction Discipline (F)': [0] * 500,
        'Motif Action': ["Aucun incident - RAS"] * 500,
        'Congés Restants (Jours)': np.random.randint(0, 30, 500),
        'Statut': ['Actif'] * 500
    })
    
    mask_om = df_init['Canal de Paiement'] == 'Orange Money'
    df_init.loc[mask_om, 'Compte / Numéro'] = [f"77 {np.random.randint(100, 999)} {np.random.randint(10, 99)} {np.random.randint(10, 99)}" for _ in range(mask_om.sum())]
    
    st.session_state.df_asp = df_init

df = st.session_state.df_asp

# RECALCUL DE LA PAIE NETTE
def calculer_net(row):
    if row['Statut'] in ['Radié', 'Démissionnaire']:
        return 0
    net = row['Pécule de Base (F)'] + row['Prime Spéciale (F)'] - row['Cotisation Mutuelle (F)'] - row['Mensualité Prêt (F)'] - row['Sanction Discipline (F)']
    return max(0, net)

df['Net à Payer (F)'] = df.apply(calculer_net, axis=1)


# --- BARRE LATÉRALE : DECISIONS DRH ET MOTIFS ---
st.sidebar.header("⚖️ Module Décisions DRH / Discipline")
v_matricule = st.sidebar.selectbox("Sélectionner l'ASP concerné :", options=df['Matricule'].values)

if v_matricule:
    idx = df[df['Matricule'] == v_matricule].index[0]
    asp_actuel = df.loc[idx]
    
    st.sidebar.info(f"**Volontaire :** {asp_actuel['Prénom']} {asp_actuel['Nom']}\n**Statut Actuel :** {asp_actuel['Statut']}")
    
    # 1. Situation Administrative
    nouveau_statut = st.sidebar.selectbox("Modifier la situation administrative :", options=['Actif', 'En Congé', 'Démissionnaire', 'Radié'], index=['Actif', 'En Congé', 'Démissionnaire', 'Radié'].index(asp_actuel['Statut']))
    
    # Choix dynamique des motifs selon l'action
    motifs_possibles = ["Aucun - Changement classique"]
    if nouveau_statut == 'Radié':
        motifs_possibles = ["Abandon de poste", "Faute lourde professionnelle", "Manquement au devoir de réserve", "Condamnation judiciaire", "Atteinte à l'image de l'ASP"]
    elif nouveau_statut == 'Démissionnaire':
        motifs_possibles = ["Insertion dans l'emploi permanent (Police, Gendarmerie, etc.)", "Convenance personnelle", "Problèmes de santé", "Reprise des études"]
    
    # 2. Sanction pécuniaire
    st.sidebar.markdown("**Sanction du Conseil de Discipline**")
    appliquer_sanction = st.sidebar.checkbox("Appliquer une retenue financière", value=bool(asp_actuel['Sanction Discipline (F)'] > 0))
    montant_sanction = 0
    if appliquer_sanction:
        montant_sanction = st.sidebar.number_input("Montant de la retenue (F CFA) :", min_value=0, max_value=90000, step=5000, value=int(asp_actuel['Sanction Discipline (F)']))
        motifs_possibles = ["Retard répété", "Non-respect des consignes", "Absence injustifiée temporaire", "Comportement inapproprié"] + motifs_possibles

    # Saisie du motif final
    motif_selectionne = st.sidebar.selectbox("Sélectionner le motif officiel :", options=motifs_possibles)
    autre_motif = st.sidebar.text_input("Ou tapez un motif personnalisé :")
    
    motif_final = autre_motif if autre_motif else motif_selectionne

    # Bouton de validation DRH
    if st.sidebar.button("Valider la décision DRH"):
        df.at[idx, 'Statut'] = nouveau_statut
        df.at[idx, 'Sanction Discipline (F)'] = montant_sanction if appliquer_sanction else 0
        df.at[idx, 'Motif Action'] = motif_final if (nouveau_statut in ['Radié', 'Démissionnaire'] or appliquer_sanction) else "Aucun incident - RAS"
        
        st.session_state.df_asp = df
        st.sidebar.success("Registre mis à jour avec succès !")
        st.rerun()


# --- INTERFACE PRINCIPALE ---
st.subheader("📊 Rapports d'effectifs & Discipline")
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("ASP Actifs & Déployés", len(df[df['Statut'].isin(['Actif', 'En Congé'])]))
with c2:
    st.metric("Total Radiés / Démissionnaires", len(df[df['Statut'].isin(['Radié', 'Démissionnaire'])]))
with c3:
    st.metric("Masse Budgétaire Net (Mois)", f"{df['Net à Payer (F)'].sum():,} F".replace(",", " "))
with c4:
    st.metric("Sanctions Financières Appliquées", len(df[df['Sanction Discipline (F)'] > 0]))

st.write("---")

# --- FICHE INDIVIDUELLE AVEC MOTIF ---
st.subheader("🔍 Fiche administrative et financière")
if v_matricule:
    asp_data = df.loc[idx]
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        st.markdown(f"### Dossier de l'Agent")
        st.write(f"**Identité :** {asp_data['Prénom']} {asp_data['Nom']}")
        st.write(f"**Région d'affectation :** {asp_data['Région']}")
        st.markdown(f"**Statut RH :** `{asp_data['Statut']}`")
        st.markdown(f"**Historique / Motif Discipline :** *{asp_data['Motif Action']}*")
        if asp_data['Statut'] in ['Radié', 'Démissionnaire']:
            st.error(f"🛑 Dossier clos. Motif de sortie : {asp_data['Motif Action']}")
    
    with col_f2:
        st.markdown(f"### Reçu de Situation Financière")
        bulletin = pd.DataFrame({
            "Rubrique": ["Pécule de Base", "Primes (+)", "Cotisation Mutuelle (-)", "Retenue Prêt (-)", "Sanction Discipline (-)", "NET À PERCEVOIR"],
            "Montant (F CFA)": [
                f"{asp_data['Pécule de Base (F)']} F", f"{asp_data['Prime Spéciale (F)']} F",
                f"-{asp_data['Cotisation Mutuelle (F)']} F", f"-{asp_data['Mensualité Prêt (F)']} F",
                f"-{asp_data['Sanction Discipline (F)']} F", f"**{asp_data['Net à Payer (F)']} F**"
            ]
        })
        st.table(bulletin)

st.write("---")

# --- REGISTRE GENERAL ---
st.subheader("📋 Registre National Matrice RH")
statut_filtre = st.multiselect("Filtrer l'affichage :", options=df['Statut'].unique(), default=df['Statut'].unique())
df_filtré = df[df['Statut'].isin(statut_filtre)]

st.dataframe(df_filtré[['Matricule', 'Nom', 'Prénom', 'Région', 'Statut', 'Motif Action', 'Net à Payer (F)']], use_container_width=True)
