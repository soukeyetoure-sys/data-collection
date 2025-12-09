import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup as bs
from requests import get
import matplotlib.pyplot as plt
import seaborn as sns
import sqlite3
import time

# ========== CONFIGURATION DE LA PAGE ==========
st.set_page_config(
    page_title="ImmoDakar Analytics", 
    page_icon="🇸🇳", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========== STYLES CSS PERSONNALISÉS (DESIGN) ==========
st.markdown("""
<style>
    /* Import de police Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap');

    html, body, [class*="css"]  {
        font-family: 'Poppins', sans-serif;
    }

    /* Couleur de fond principale */
    .stApp {
        background-color: #f8f9fa;
    }

    /* Style des titres */
    h1 {
        color: #1e3d59;
        font-weight: 700;
        text-align: center;
        padding-bottom: 20px;
    }
    h2, h3 {
        color: #2E86AB;
        font-weight: 600;
    }

    /* Style des boutons */
    div.stButton > button {
        background-color: #2E86AB;
        color: white;
        border-radius: 12px;
        border: none;
        padding: 10px 24px;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        width: 100%;
    }
    div.stButton > button:hover {
        background-color: #1e3d59;
        color: #ffffff;
        transform: translateY(-2px);
        box-shadow: 0 6px 8px rgba(0,0,0,0.15);
    }

    /* Style des dataframes */
    div[data-testid="stDataFrame"] {
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        background-color: white;
        padding: 10px;
    }

    /* Cards pour les métriques */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        border-left: 5px solid #2E86AB;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e0e0e0;
    }
</style>
""", unsafe_allow_html=True)

# ========== EN-TÊTE ==========
col_logo, col_title = st.columns([1, 4])
with col_title:
    st.markdown("<h1>🇸🇳 IMMO DAKAR ANALYTICS</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #555;'>La solution intelligente pour analyser le marché immobilier au Sénégal</p>", unsafe_allow_html=True)
st.markdown("---")

# ========== FONCTIONS UTILITAIRES ==========
@st.cache_data
def convert_df(df):
    return df.to_csv(index=False).encode('utf-8')

def download_button_custom(dataframe, title, key):
    csv = convert_df(dataframe)
    st.download_button(
        label=f"⬇️ Télécharger {title} (CSV)",
        data=csv,
        file_name=f'{title.replace(" ", "_")}.csv',
        mime='text/csv',
        key=key
    )

# ========== FONCTIONS DE SCRAPING (Logique conservée) ==========
def scrape_data(category, num_pages):
    """Fonction générique pour scraper Villas ou Appartements"""
    df = pd.DataFrame()
    
    # Barre de progression stylisée
    progress_text = "Initialisation du robot..."
    my_bar = st.progress(0, text=progress_text)
    placeholder_log = st.empty()
    
    base_url = f'https://sn.coinafrique.com/categorie/{category}'
    
    for page in range(1, int(num_pages) + 1):
        placeholder_log.info(f"🔄 Scraping de la page {page} sur {num_pages} en cours...")
        url = f'{base_url}?page={page}'
        
        try:
            res = get(url, timeout=10)
            soup = bs(res.content, 'html.parser')
            containers = soup.find_all('div', class_="col s6 m4 l3")
            
            data = []
            for container in containers:
                try:
                    container_url = "https://sn.coinafrique.com" + container.find('a')["href"]
                    # Petite optimisation : on récupère l'info de la carte si possible pour éviter trop de requêtes
                    # Mais je garde votre logique profonde pour entrer dans chaque annonce
                    res_container = get(container_url, timeout=10)
                    soup_container = bs(res_container.content, "html.parser")
                    
                    details = soup_container.find('h1', "title title-ad hide-on-large-and-down").text
                    price = "".join(soup_container.find('p', "price").text.strip().split()).replace('CFA', '')
                    address = soup_container.find_all('span', 'valign-wrapper')[1].text
                    
                    try:
                        div_details = soup_container.find_all('div', class_="details-characteristics")[0]
                        j = div_details.find_all('span', 'qt')
                        number_of_rooms = j[0].text.strip() if len(j) > 0 else None
                    except:
                        number_of_rooms = None

                    try:
                        img = soup_container.find('div', class_="swiper-slide slide-clickable")
                        style = img.get('style')
                        image_link = style.split('url(')[1].split(')')[0].strip('"')
                    except:
                        image_link = None
                    
                    data.append({
                        "details": details,
                        "price": price,
                        "address": address,
                        "number_of_rooms": number_of_rooms,
                        "image_link": image_link
                    })
                    # Pause légère
                    # time.sleep(0.1) 
                except:
                    continue
            
            DF = pd.DataFrame(data)
            df = pd.concat([df, DF], axis=0).reset_index(drop=True)
            my_bar.progress(page / int(num_pages), text=f"Page {page}/{num_pages} terminée")
            
        except Exception as e:
            st.error(f"Erreur page {page}: {str(e)}")
            continue
    
    my_bar.empty()
    placeholder_log.success("✅ Collecte des données terminée avec succès !")
    return df

# ========== FONCTIONS SQL & CLEANING ==========
def save_to_sql(df, table_name, db_name="immobilier.db"):
    try:
        conn = sqlite3.connect(db_name)
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        conn.close()
        st.toast(f"Sauvegarde réussie dans la table '{table_name}'", icon="💾")
    except Exception as e:
        st.error(f"Erreur SQL: {str(e)}")

def load_from_sql(table_name, db_name="immobilier.db"):
    try:
        conn = sqlite3.connect(db_name)
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        conn.close()
        return df
    except:
        return None

def clean_data(df):
    df['price'] = pd.to_numeric(df['price'], errors='coerce').astype('Int64')
    df['number_of_rooms'] = pd.to_numeric(df['number_of_rooms'], errors='coerce').astype('Int64')
    
    if df['price'].notna().sum() > 0:
        median_price = df['price'].median()
        df['price'] = df['price'].fillna(int(median_price)).astype('Int64')
    
    if df['number_of_rooms'].notna().sum() > 0:
        median_rooms = df['number_of_rooms'].median()
        df['number_of_rooms'] = df['number_of_rooms'].fillna(int(median_rooms)).astype('Int64')
    
    return df

# ========== SIDEBAR ==========
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1018/1018529.png", width=80)
    st.markdown("### ⚙️ Panneau de Contrôle")
    
    choice = st.radio(
        "Navigation", 
        ['🔍 Scraper les données', '📥 Base de données', '📊 Dashboard', '📝 Feedback'],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.markdown("##### Paramètres de Scraping")
    pages = st.slider('Nombre de pages à analyser', 1, 200, 2)
    
    st.markdown("---")
    st.info("Développé avec ❤️ pour Dakar")

# ========== PAGE: SCRAPER ==========
if choice == '🔍 Scraper les données':
    st.subheader("📡 Centre de Collecte de Données")
    st.markdown("Activez les robots pour récupérer les dernières annonces en temps réel.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🏡 Villas")
        st.image("https://images.unsplash.com/photo-1580587771525-78b9dba3b91d?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60", use_container_width=True)
        if st.button("Lancer le Scraping Villas"):
            villas_df = scrape_data("villas", pages)
            if not villas_df.empty:
                villas_df = clean_data(villas_df)
                save_to_sql(villas_df, "villas")
                st.dataframe(villas_df.head(), use_container_width=True)
                download_button_custom(villas_df, "Villas", "dl_villas")
    
    with col2:
        st.markdown("### 🏢 Appartements")
        st.image("https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60", use_container_width=True)
        if st.button("Lancer le Scraping Apparts"):
            appart_df = scrape_data("appartements", pages)
            if not appart_df.empty:
                appart_df = clean_data(appart_df)
                save_to_sql(appart_df, "appartements")
                st.dataframe(appart_df.head(), use_container_width=True)
                download_button_custom(appart_df, "Appartements", "dl_apparts")

# ========== PAGE: DATA ==========
elif choice == '📥 Base de données':
    st.subheader("📂 Explorateur de Données")
    
    tab1, tab2 = st.tabs(["🏡 Villas", "🏢 Appartements"])
    
    with tab1:
        df_villas = load_from_sql("villas")
        if df_villas is not None:
            col_kpi1, col_kpi2 = st.columns(2)
            col_kpi1.metric("Total Villas", len(df_villas))
            col_kpi2.metric("Prix Moyen", f"{int(df_villas['price'].mean()):,} FCFA")
            st.dataframe(df_villas, use_container_width=True, height=400)
            download_button_custom(df_villas, "Donnees Complètes Villas", "dl_sql_villas")
        else:
            st.warning("Aucune donnée de villas trouvée. Lancez un scraping.")

    with tab2:
        df_apparts = load_from_sql("appartements")
        if df_apparts is not None:
            col_kpi1, col_kpi2 = st.columns(2)
            col_kpi1.metric("Total Apparts", len(df_apparts))
            col_kpi2.metric("Prix Moyen", f"{int(df_apparts['price'].mean()):,} FCFA")
            st.dataframe(df_apparts, use_container_width=True, height=400)
            download_button_custom(df_apparts, "Donnees Complètes Apparts", "dl_sql_apparts")
        else:
            st.warning("Aucune donnée d'appartements trouvée. Lancez un scraping.")

# ========== PAGE: DASHBOARD ==========
elif choice == '📊 Dashboard':
    st.subheader("📈 Analyse du Marché")
    
    villas_df = load_from_sql("villas")
    appart_df = load_from_sql("appartements")
    
    if villas_df is not None and appart_df is not None:
        # Configuration globale des graphiques
        sns.set_theme(style="whitegrid", palette="mako")
        plt.rcParams['figure.facecolor'] = 'white'
        plt.rcParams['axes.facecolor'] = 'white'
        
        # --- SECTION PRIX ---
        st.markdown("### 💰 Distribution des Prix")
        col1, col2 = st.columns(2)
        
        with col1:
            fig, ax = plt.subplots(figsize=(8, 5))
            # Filtrer les outliers extrêmes pour la beauté du graphe (95e percentile)
            villas_clean = villas_df[villas_df['price'] < villas_df['price'].quantile(0.95)]
            sns.histplot(villas_clean['price'], kde=True, color="#2E86AB", ax=ax, edgecolor=None)
            ax.set_title("Villas", fontsize=14, fontweight='bold', color='#1e3d59')
            ax.set_xlabel("Prix (FCFA)")
            ax.set_ylabel("Nombre")
            sns.despine()
            st.pyplot(fig)
            
        with col2:
            fig, ax = plt.subplots(figsize=(8, 5))
            appart_clean = appart_df[appart_df['price'] < appart_df['price'].quantile(0.95)]
            sns.histplot(appart_clean['price'], kde=True, color="#A23B72", ax=ax, edgecolor=None)
            ax.set_title("Appartements", fontsize=14, fontweight='bold', color='#1e3d59')
            ax.set_xlabel("Prix (FCFA)")
            ax.set_ylabel("Nombre")
            sns.despine()
            st.pyplot(fig)

        st.markdown("---")
        
        # --- SECTION QUARTIERS ---
        st.markdown("### 📍 Top Quartiers les plus populaires")
        col3, col4 = st.columns(2)
        
        with col3:
            fig, ax = plt.subplots(figsize=(8, 6))
            top_villas = villas_df['address'].value_counts().head(10).sort_values()
            ax.barh(top_villas.index, top_villas.values, color='#2E86AB', alpha=0.8)
            ax.set_title("Villas par Quartier", fontsize=12, fontweight='bold')
            ax.grid(axis='x', linestyle='--', alpha=0.7)
            sns.despine(left=True, bottom=True)
            st.pyplot(fig)
            
        with col4:
            fig, ax = plt.subplots(figsize=(8, 6))
            top_apparts = appart_df['address'].value_counts().head(10).sort_values()
            ax.barh(top_apparts.index, top_apparts.values, color='#A23B72', alpha=0.8)
            ax.set_title("Appartements par Quartier", fontsize=12, fontweight='bold')
            ax.grid(axis='x', linestyle='--', alpha=0.7)
            sns.despine(left=True, bottom=True)
            st.pyplot(fig)

    else:
        st.info("👋 Veuillez d'abord scraper les données dans l'onglet 'Scraper les données' pour voir le tableau de bord.")

# ========== PAGE: FEEDBACK ==========
else:
    st.subheader("📝 Votre avis compte")
    st.markdown("Aidez-nous à améliorer cet outil.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.info("Option 1")
        st.link_button("✍️ Remplir sur KoboToolbox", "https://ee-eu.kobotoolbox.org/x/tHEQZ6mL", use_container_width=True)
    
    with col2:
        st.info("Option 2")
        st.link_button("✍️ Remplir sur Google Forms", "https://docs.google.com/forms/d/e/1FAIpQLScD5NzTNFpIH3PL3r5brVssS5JUIv_X3S9VnwGo5Z8QdBoihA/viewform?usp=publish-editorhttps://docs.google.com/forms/", use_container_width=True)
