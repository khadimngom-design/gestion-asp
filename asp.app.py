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
                            "id": next_id, 
                            "annee": next_y, 
                            "mois": next_m,
                            "statut": "EN ATTENTE D'OUVERTURE", 
                            "date_ouverture": None,
                            "date_cloture": None, 
                            "type_cloture": None,
                            "motif_reouverture": "", 
                            "drh_reouverture": "",
                            "historique_reouvertures": [], 
                            "archives_donnees": None
                        }
                        
                    enregistrer_audit("DRH", "Clôture & Signature", selected_sid, "Session clôturée et signée électroniquement.")
                    st.success("Session clôturée avec succès, signée électroniquement et transmise à la DAF/DG.")
                    st.rerun()
        else:
            st.info("ℹ️ Seul le Directeur des Ressources Humaines (DRH) peut clôturer et signer la session.")
