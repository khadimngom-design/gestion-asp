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

# --- INITIALISATION DE L'ÉTAT DES SESSIONS DE PAIE ---
if 'session_mois' not in st.session_state:
    st.session_state.session_mois = "Avril 2026"
if 'session_statut' not in st.session_state:
    st.session_state.session_statut = "Ouverte"  # Valeurs : "Ouverte", "Clôturée & Transmise"
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
    "📋 Registre & Recrutement", 
    "📅 Gestion des Congés", 
    "💶 Paie & Primes", 
    "🔒 Sessions de Paie & Validation"
])

regions_list = ['Dakar', 'Thiès', 'Saint-Louis', 'Ziguinchor', 'Kaolack', 'Diourbel', 'Tambacounda']

# ==============================================================================
# ONGLET 1 : RECRUTEMENT ET MODIFICATION
# ==============================================================================
with onglet1:
    st.subheader("👤 Mouvements de Personnel (Recrutement & Édition)")
    
    if st.session_state.session_statut == "Clôturée & Transmise":
        st.warning(f"🔒 La session de paie de **{st.session_state.session_mois}** est actuellement **clôturée et transmise à la DAF et au DG**. Les modifications de personnel sont verrouillées pour ce cycle.")
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
                
                st.markdown("**Configuration de la Prime DRH**")
                n_has_prime = st.checkbox("Cet agent est-il bénéficiaire d'une prime ?")
                n_montant_prime = 0
                if n_has_prime:
                    n_montant_prime = st.number_input("Montant de la prime (F CFA) :", min_value=0, step=5000, value=15000)
                
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
                        st.success(f"L'ASP a été enregistré sous le Matricule CNI : {n_cni}")
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
                    edit_reg = st.selectbox("Région", regions_list, index=regions_list.index(df.at[idx, 'Région']))
                    statuts_list = ['Actif', 'Radié', 'Démissionnaire']
                    edit_statut = st.selectbox("Statut RH", statuts_list, index=statuts_list.index(df.at[idx, 'Statut']))
                    
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
    st.dataframe(df[['Matricule_CNI', 'Nom', 'Prénom', 'Région', 'Lieu_Affectation', 'Beneficie_Prime', 'Prime', 'Statut', 'Net_A_Payer']], use_container_width=True)

# ==============================================================================
# ONGLET 2 : CONGÉS
# ==============================================================================
with onglet2:
    st.subheader("📅 Planification des Congés Annuels")
    actifs_df = df[df['Statut'] == 'Actif']
    if not actifs_df.empty:
        asp_conge = st.selectbox("Sélectionnez l'ASP demandeur (Par sa CNI) :", options=actifs_df['Matricule_CNI'].values, key="conge_box")
        if asp_conge:
            idx_c = df[df['Matricule_CNI'] == asp_conge].index[0]
            st.info(f"Solde disponible : **{df.at[idx_c, 'Conges_Restants']} jours**.")
            jours_demandes = st.number_input("Jours à poser :", min_value=1, max_value=max(1, int(df.at[idx_c, 'Conges_Restants'])), value=1)
            if st.button("🌴 Accorder le congé"):
                df.at[idx_c, 'Conges_Restants'] -= jours_demandes
                st.session_state.df_asp = df
                st.success("Compteur mis à jour.")
                st.rerun()
    else:
        st.warning("Aucun agent actif disponible.")

# ==============================================================================
# ONGLET 3 : PAIE, PRIMES, SANCTIONS & RETENUES (MISES À JOUR MENSUELLES)
# ==============================================================================
with onglet3:
    st.subheader(f"💶 Variables de Paie - Session : {st.session_state.session_mois}")
    
    if st.session_state.session_statut == "Clôturée & Transmise":
        st.warning("🔒 Session clôturée : les variables financières (sanctions, prêts, primes) sont verrouillées pour cette période.")
        st.dataframe(df[['Matricule_CNI', 'Nom', 'Prénom', 'Pécule_Base', 'Prime', 'Retenue_Pret', 'Sanction_Discipline', 'Net_A_Payer']], use_container_width=True)
    else:
        st.info("💡 Mettez à jour ici les sanctions disciplinaires, les remboursements de prêts ou les ajustements de primes avant de clôturer la session.")
        
        # Modification groupée ou individuelle rapide des variables de paie du mois
        agent_paie = st.selectbox("Sélectionner un agent pour ajuster ses variables de paie du mois :", options=df[df['Statut']=='Actif']['Matricule_CNI'].values, key="select_paie")
        if agent_paie:
            idx_p = df[df['Matricule_CNI'] == agent_paie].index[0]
            st.markdown(f"**Agent :** {df.at[idx_p, 'Prénom']} {df.at[idx_p, 'Nom']} (Matricule CNI: {agent_paie})")
            
            col_p1, col_p2, col_p3 = st.columns(3)
            with col_p1:
                val_pret = st.number_input("Retenue Prêt (F CFA)", value=int(df.at[idx_p, 'Retenue_Pret']), step=1000, key="v_pret")
            with col_p2:
                val_sanction = st.number_input("Sanction / Retenue Discipline (F CFA)", value=int(df.at[idx_p, 'Sanction_Discipline']), step=1000, key="v_sanc")
            with col_p3:
                val_motif = st.text_input("Motif de l'action / sanction", value=str(df.at[idx_p, 'Motif_Action']), key="v_motif")
                
            if st.button("💾 Enregistrer les variables de paie de l'agent"):
                df.at[idx_p, 'Retenue_Pret'] = val_pret
                df.at[idx_p, 'Sanction_Discipline'] = val_sanction
                df.at[idx_p, 'Motif_Action'] = val_motif
                st.session_state.df_asp = df
                st.success("Variables de paie mises à jour pour cet agent.")
                st.rerun()

        st.write("---")
        st.markdown("#### Tableau récapitulatif des variables du mois en cours")
        st.dataframe(df[['Matricule_CNI', 'Nom', 'Prénom', 'Pécule_Base', 'Prime', 'Retenue_Pret', 'Sanction_Discipline', 'Net_A_Payer', 'Motif_Action']], use_container_width=True)

# ==============================================================================
# ONGLET 4 : GESTION DES SESSIONS DE PAIE (OUVERTURE / CLÔTURE & TRANSMISSION DAF/DG)
# ==============================================================================
with onglet4:
    st.subheader("🔒 Gestion du Cycle Mensuel de Paie (DRH ➔ DAF ➔ DG)")
    
    st.markdown("""
    * **Règle du processus :** Vers le 15 de chaque mois précédant l'échéance (ex: 15 mars pour la paie d'avril), le DRH ouvre la session, met à jour les données (prêts, sanctions, primes), puis clôture et transmet l'état à la **DAF** et au **Directeur Général (DG)** pour validation finale et décaissement.
    """)
    
    st.write("---")
    
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        nouveau_mois = st.selectbox("Sélectionner le mois de paie concerné :", ["Mars 2026", "Avril 2026", "Mai 2026", "Juin 2026", "Juillet 2026", "Août 2026", "Septembre 2026", "Octobre 2026", "Novembre 2026", "Décembre 2026"], index=1)
        st.session_state.session_mois = nouveau_mois
        
    with col_s2:
        st.metric("État actuel de la session", st.session_state.session_statut)
        
    st.write("---")
    
    # Boutons d'action DRH
    col_b1, col_b2 = st.columns(2)
    
    with col_b1:
        if st.session_state.session_statut == "Clôturée & Transmise":
            if st.button("🔓 Rouvrir la session (Action DRH - Cas exceptionnel)"):
                st.session_state.session_statut = "Ouverte"
                st.success(f"La session de paie de {st.session_state.session_mois} a été rouverte pour modifications.")
                st.rerun()
        else:
            st.info("La session est ouverte. Vous pouvez modifier les primes, prêts et sanctions dans l'onglet 'Paie & Primes'.")
            
    with col_b2:
        if st.session_state.session_statut == "Ouverte":
            if st.button("📤 Clôturer la session et Transmettre à la DAF & au DG", type="primary"):
                st.session_state.session_statut = "Clôturée & Transmise"
                st.success(f"✅ Session de {st.session_state.session_mois} clôturée avec succès et transmise électroniquement à la DAF et à la Direction Générale !")
                st.rerun()
        else:
            st.success("✔ État validé : Transmis à la hiérarchie (DAF & DG). En attente de mandatement / virement bancaire.")

    st.write("---")
    st.markdown("#### 📥 Téléchargement des États Validés pour la DAF et la Banque")
    
    # Option d'export global si la session est transmise
    canal_export = st.selectbox("Canal de décaissement :", ['Tous', 'Orange Money', 'BOA', 'BNDE'], key="export_session")
    df_export = df.copy()
    if canal_export != 'Tous':
        df_export = df_export[df_export['Canal_Paiement'] == canal_export]
        
    st.dataframe(df_export[['Matricule_CNI', 'Nom', 'Prénom', 'Canal_Paiement', 'Compte_Numero', 'Net_A_Payer']], use_container_width=True)
    
    csv_data = df_export.to_csv(index=False, sep=';').encode('utf-8')
    st.download_button(
        label=f"📥 Télécharger l'état de paie officiel - {st.session_state.session_mois} ({canal_export})",
        data=csv_data,
        file_name=f"etat_paie_officiel_{st.session_state.session_mois.lower().replace(' ', '_')}_{canal_export.lower()}.csv",
        mime='text/csv'
    )
