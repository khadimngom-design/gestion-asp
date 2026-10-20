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
