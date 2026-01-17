import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import plotly.express as px
import io

# --- CONFIGURATION DU VIBE (FULL SCREEN) ---
st.set_page_config(page_title="Ficelle Flow V2", page_icon="🧶", layout="wide")

# --- CSS CUSTOM POUR LE STYLE ---
st.markdown("""
<style>
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 10px;
    }
    .hess-alert {
        color: #ff4b4b;
        font-weight: bold;
        border: 1px solid #ff4b4b;
        padding: 5px;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# --- GESTION DE LA BASE DE DONNÉES (SQLite) ---
def init_db():
    conn = sqlite3.connect('inventaire_ficelle.db')
    c = conn.cursor()
    
    # Table Stock (Mise à jour avec PHOTO BLOB)
    c.execute('''CREATE TABLE IF NOT EXISTS stock
                 (id INTEGER PRIMARY KEY, type TEXT, matiere TEXT, couleur_hex TEXT, 
                  longueur_initiale REAL, longueur_restante REAL, 
                  nombre_pelotes INT, prix REAL, provenance TEXT, 
                  photo BLOB, date_ajout TEXT)''')
    
    # Table Historique
    c.execute('''CREATE TABLE IF NOT EXISTS historique
                 (id INTEGER PRIMARY KEY, stock_id INTEGER, quantite_utilisee REAL, 
                  date_usage TEXT, projet TEXT)''')
    
    # Table Wishlist (NOUVEAU !)
    c.execute('''CREATE TABLE IF NOT EXISTS wishlist
                 (id INTEGER PRIMARY KEY, produit TEXT, couleur TEXT, 
                  priorite TEXT, lien TEXT, statut TEXT)''')
                  
    conn.commit()
    conn.close()

def run_query(query, params=(), return_data=False):
    conn = sqlite3.connect('inventaire_ficelle.db')
    c = conn.cursor()
    c.execute(query, params)
    if return_data:
        data = c.fetchall()
        cols = [description[0] for description in c.description]
        conn.close()
        return pd.DataFrame(data, columns=cols)
    conn.commit()
    conn.close()

# Initialisation
init_db()

# --- SIDEBAR & NAV ---
st.sidebar.title("🧶 Ficelle Flow V2")
st.sidebar.markdown("L'assistant officiel des bg de la broderie.")
menu = st.sidebar.radio("Menu", 
    ["Dashboard & Alerte Hess", 
     "Ajouter du Stock (Scan)", 
     "Mon Inventaire (Visuel)", 
     "L'Atelier (Découpe)", 
     "Calculateur de Prix (Moula)", 
     "Ma Wishlist ✨"])

# --- 1. DASHBOARD & ALERTE HESS ---
if menu == "Dashboard & Alerte Hess":
    st.title("📊 Dashboard du Patron")
    
    # KPI Rapides
    df_stock = run_query("SELECT * FROM stock", return_data=True)
    df_hist = run_query("SELECT * FROM historique", return_data=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_metre = df_stock['longueur_restante'].sum() if not df_stock.empty else 0
    valeur_stock = df_stock['prix'].sum() if not df_stock.empty else 0
    total_conso = df_hist['quantite_utilisee'].sum() if not df_hist.empty else 0
    nb_ref = len(df_stock)
    
    col1.metric("Stock Total (m)", f"{total_metre:.1f} m")
    col2.metric("Valeur Inventaire", f"{valeur_stock:.2f} €")
    col3.metric("Fil Consommé", f"{total_conso:.1f} m")
    col4.metric("Références", nb_ref)
    
    st.divider()
    
    # ALERTE LA HESS (Low Stock)
    st.subheader("🚨 Alerte La Hess (Bientôt à sec !)")
    if not df_stock.empty:
        # On considère "Hess" si < 15% du stock initial ou < 5 mètres
        low_stock = df_stock[
            (df_stock['longueur_restante'] < 5) | 
            (df_stock['longueur_restante'] < (df_stock['longueur_initiale'] * 0.15))
        ]
        
        if not low_stock.empty:
            st.error(f"Attention frérot ! Il y a {len(low_stock)} pelotes en danger critique.")
            for index, row in low_stock.iterrows():
                st.markdown(f"🔴 **{row['type']} - {row['matiere']}** : Il reste que **{row['longueur_restante']:.2f}m** !")
        else:
            st.success("Tout est carré, les stocks sont pleins ! 😎")
    
    st.divider()
    # Petits graphs pour le flex
    if not df_hist.empty:
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.caption("Répartition du stock par matière")
            fig_pie = px.pie(df_stock, values='longueur_restante', names='matiere', hole=0.5)
            st.plotly_chart(fig_pie, use_container_width=True)

# --- 2. AJOUTER DU STOCK ---
elif menu == "Ajouter du Stock (Scan)":
    st.header("📥 Nouvel Arrivage")
    st.caption("Remplis ça proprement.")
    
    with st.form("add_stock_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            type_fil = st.text_input("Type de fil (ex: Laine, Soie)")
            matiere = st.text_input("Matière précise (ex: Alpaga)")
            prov = st.text_input("Marque / Provenance")
            couleur = st.color_picker("Nuancier Couleur", "#334455")
        
        with col2:
            longueur = st.number_input("Longueur par pelote (m)", min_value=1.0, value=100.0)
            nb_pelotes = st.number_input("Nombre de pelotes", min_value=1, value=1)
            prix = st.number_input("Prix total (€)", min_value=0.0)
            
        # NOUVEAU : UPLOAD PHOTO
        uploaded_file = st.file_uploader("Photo de la texture (Optionnel)", type=['png', 'jpg', 'jpeg'])
        
        submitted = st.form_submit_button("Enregistrer le matos 💾")
        
        if submitted:
            total_longueur = longueur * nb_pelotes
            
            # Gestion image binaire
            photo_blob = None
            if uploaded_file is not None:
                photo_blob = uploaded_file.getvalue()
            
            run_query('''INSERT INTO stock (type, matiere, couleur_hex, longueur_initiale, longueur_restante, nombre_pelotes, prix, provenance, photo, date_ajout)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                         (type_fil, matiere, couleur, total_longueur, total_longueur, nb_pelotes, prix, prov, photo_blob, datetime.now()))
            st.success("C'est dans la boîte ! Stock mis à jour.")

# --- 3. MON INVENTAIRE (VISUEL) ---
elif menu == "Mon Inventaire (Visuel)":
    st.header("📦 La Caverne d'Ali Baba")
    
    df = run_query("SELECT * FROM stock", return_data=True)
    
    if not df.empty:
        # Recherche
        search = st.text_input("🔍 Chercher un fil...", "")
        if search:
            df = df[df['type'].str.contains(search, case=False) | df['matiere'].str.contains(search, case=False)]

        # Affichage en mode "Carte" (Grid)
        cols = st.columns(3)
        for index, row in df.iterrows():
            with cols[index % 3]:
                with st.container(border=True):
                    # En-tête avec couleur
                    st.markdown(f"### {row['type']} <span style='color:{row['couleur_hex']};'>●</span>", unsafe_allow_html=True)
                    st.caption(f"{row['matiere']} - {row['provenance']}")
                    
                    # Affichage Photo si dispo
                    if row['photo']:
                        st.image(row['photo'], use_container_width=True)
                    else:
                        st.markdown(f"<div style='background-color:{row['couleur_hex']};height:100px;border-radius:5px;'></div>", unsafe_allow_html=True)
                    
                    # Jauge de stock
                    pourcentage = (row['longueur_restante'] / row['longueur_initiale'])
                    st.progress(pourcentage, text=f"Reste : {row['longueur_restante']:.1f} m")
                    
                    if pourcentage < 0.15:
                        st.markdown("<div class='hess-alert'>⚠️ ALERTE HESS</div>", unsafe_allow_html=True)
    else:
        st.info("Rien en stock. Va acheter des trucs !")

# --- 4. L'ATELIER (DÉCOUPE) ---
elif menu == "L'Atelier (Découpe)":
    st.header("✂️ On charbonne")
    df = run_query("SELECT id, type, matiere, couleur_hex, longueur_restante FROM stock WHERE longueur_restante > 0", return_data=True)
    
    if not df.empty:
        options = {row['id']: f"{row['type']} - {row['matiere']} (Reste: {row['longueur_restante']}m)" for index, row in df.iterrows()}
        selected_id = st.selectbox("Tu tapes dans quelle pelote ?", options.keys(), format_func=lambda x: options[x])
        
        col1, col2, col3 = st.columns(3)
        with col1:
            conso_val = st.number_input("J'ai utilisé...", min_value=0.1)
        with col2:
            unit = st.radio("Unité", ["cm", "m"], horizontal=True)
        with col3:
            projet = st.text_input("Pour quel projet ?")
            
        if st.button("Couper ! ✂️"):
            conso_m = conso_val if unit == "m" else conso_val / 100
            current_stock = df[df['id'] == selected_id]['longueur_restante'].values[0]
            
            if conso_m > current_stock:
                st.error("Wesh doucement ! T'as pas assez de fil.")
            else:
                new_stock = current_stock - conso_m
                run_query("UPDATE stock SET longueur_restante = ? WHERE id = ?", (new_stock, selected_id))
                run_query("INSERT INTO historique (stock_id, quantite_utilisee, date_usage, projet) VALUES (?, ?, ?, ?)",
                          (selected_id, conso_m, datetime.now(), projet))
                st.balloons()
                st.success(f"Stock déduit ! Il reste {new_stock:.2f}m.")

# --- 5. CALCULATEUR DE PRIX (MOULA) ---
elif menu == "Calculateur de Prix (Moula)":
    st.header("💰 Ça vaut combien ton art ?")
    st.markdown("Arrête de vendre à perte. Calcule le VRAI prix.")
    
    with st.expander("Calculer un prix de vente", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            temps = st.number_input("Temps passé (heures)", min_value=0.0, step=0.5)
            taux_horaire = st.number_input("Ton taux horaire (€/h)", value=15.0)
        with c2:
            cout_materiel = st.number_input("Coût estimé du matériel (€)", min_value=0.0)
            marge = st.slider("Marge benef (%)", 0, 100, 20)
            
        if st.button("Calculer le Prix Juste"):
            cout_travail = temps * taux_horaire
            total_cout = cout_travail + cout_materiel
            prix_vente = total_cout * (1 + (marge/100))
            
            st.metric("Coût de production", f"{total_cout:.2f} €")
            st.success(f"💵 PRIX DE VENTE CONSEILLÉ : **{prix_vente:.2f} €**")
            if prix_vente > 100:
                st.caption("C'est du luxe ça mon pote !")

# --- 6. MA WISHLIST ---
elif menu == "Ma Wishlist ✨":
    st.header("✨ Wishlist & Idées")
    
    with st.form("wishlist_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            w_prod = st.text_input("Produit / Fil")
        with c2:
            w_prio = st.select_slider("Priorité", ["Tranquille", "Besoin", "URGENT"])
        with c3:
            w_lien = st.text_input("Lien / Magasin")
            
        if st.form_submit_button("Ajouter à la liste"):
            run_query("INSERT INTO wishlist (produit, priorite, lien, statut) VALUES (?, ?, ?, ?)", 
                      (w_prod, w_prio, w_lien, "À acheter"))
            st.rerun()
            
    # Affichage de la liste
    df_wish = run_query("SELECT * FROM wishlist", return_data=True)
    if not df_wish.empty:
        st.dataframe(df_wish[['produit', 'priorite', 'lien', 'statut']], use_container_width=True)
        
        # Suppression
        to_delete = st.selectbox("Supprimer un item (une fois acheté)", df_wish['id'].astype(str) + " - " + df_wish['produit'])
        if st.button("J'ai acheté / Supprimer"):
            id_del = int(to_delete.split(" - ")[0])
            run_query("DELETE FROM wishlist WHERE id = ?", (id_del,))
            st.success("Item retiré de la liste !")
            st.rerun()
    else:
        st.info("Ta liste est vide. T'as besoin de rien ? Mythu.")
