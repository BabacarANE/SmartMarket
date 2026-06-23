"""
Dashboard SmartMarket Intelligence — Streamlit
Pages : Vue Marché | Carte Salaires | Prédiction | Monitoring ML
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from sqlalchemy import create_engine, text

# ─── Config ──────────────────────────────────────────────────────────

st.set_page_config(
    page_title="SmartMarket Intelligence",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_URL = "http://localhost:8000"
DB_CONN = "postgresql+pg8000://smartmarket:x@localhost:5433/smartmarket_db"

# ─── Helpers ─────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def get_db_data(query: str) -> pd.DataFrame:
    engine = create_engine(DB_CONN)
    with engine.connect() as conn:
        return pd.read_sql(query, conn)

@st.cache_data(ttl=60)
def get_api(endpoint: str) -> dict:
    try:
        resp = requests.get(f"{API_URL}{endpoint}", timeout=5)
        return resp.json()
    except:
        return {}

# ─── Sidebar ─────────────────────────────────────────────────────────

st.sidebar.image("https://img.icons8.com/color/96/artificial-intelligence.png", width=80)
st.sidebar.title("SmartMarket Intelligence")
st.sidebar.markdown("*Analyse du marché tech français*")

page = st.sidebar.radio(
    "Navigation",
    ["🏠 Vue Marché", "🗺️ Carte Salaires", "🤖 Prédiction", "📊 Monitoring ML"]
)

st.sidebar.markdown("---")
health = get_api("/health")
if health.get("model_loaded"):
    st.sidebar.success("✅ Modèle ML actif")
else:
    st.sidebar.error("❌ Modèle non disponible")

# ─── Page 1 — Vue Marché ─────────────────────────────────────────────

if page == "🏠 Vue Marché":
    st.title("🏠 Vue Marché Tech France")

    # KPIs
    kpi_data = get_db_data("""
        SELECT
            COUNT(*) as nb_offres,
            COUNT(DISTINCT entreprise) as nb_entreprises,
            ROUND(AVG(salaire_median)) as salaire_median,
            COUNT(CASE WHEN is_remote THEN 1 END) as nb_remote
        FROM clean.offres
    """)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📋 Offres actives", f"{kpi_data['nb_offres'][0]:,}")
    col2.metric("🏢 Entreprises", f"{kpi_data['nb_entreprises'][0]:,}")
    col3.metric("💰 Salaire médian", f"{kpi_data['salaire_median'][0]:,}€")
    col4.metric("🏡 Remote", f"{kpi_data['nb_remote'][0]:,}")

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🔧 Top 15 Technologies")
        tech_data = get_db_data("""
            SELECT technologie, SUM(nb_offres) as total,
                   ROUND(AVG(salaire_moyen)) as sal_moyen
            FROM analytics.agg_tech_tendances
            GROUP BY technologie
            ORDER BY total DESC
            LIMIT 15
        """)
        fig = px.bar(
            tech_data,
            x="total", y="technologie",
            orientation="h",
            color="sal_moyen",
            color_continuous_scale="Viridis",
            labels={"total": "Nb offres", "technologie": "", "sal_moyen": "Salaire moyen"},
            title="Technologies les plus demandées"
        )
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("📊 Distribution des salaires")
        sal_data = get_db_data("""
            SELECT salaire_median, niveau_experience, type_contrat
            FROM clean.offres
            WHERE salaire_median BETWEEN 15000 AND 150000
        """)
        fig = px.histogram(
            sal_data,
            x="salaire_median",
            color="niveau_experience",
            nbins=40,
            labels={"salaire_median": "Salaire médian (€)", "count": "Nb offres"},
            title="Distribution des salaires par expérience"
        )
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)

    # Répartition par type de contrat
    st.subheader("📋 Répartition par type de contrat")
    contrat_data = get_db_data("""
        SELECT type_contrat, COUNT(*) as nb
        FROM clean.offres
        GROUP BY type_contrat
        ORDER BY nb DESC
    """)
    fig = px.pie(contrat_data, values="nb", names="type_contrat",
                 title="Types de contrats")
    st.plotly_chart(fig, use_container_width=True)

# ─── Page 2 — Carte Salaires ─────────────────────────────────────────

elif page == "🗺️ Carte Salaires":
    st.title("🗺️ Carte des Salaires par Ville")

    sal_data = get_db_data("""
        SELECT ville, nb_offres, salaire_moyen, salaire_median
        FROM analytics.agg_salaires_par_ville
        WHERE nb_offres >= 3
        ORDER BY salaire_moyen DESC
    """)

    col1, col2 = st.columns([2, 1])

    with col1:
        fig = px.bar(
            sal_data.head(20),
            x="ville", y="salaire_moyen",
            color="nb_offres",
            color_continuous_scale="Blues",
            labels={"salaire_moyen": "Salaire moyen (€)", "ville": "Ville", "nb_offres": "Nb offres"},
            title="Top 20 villes par salaire moyen"
        )
        fig.update_layout(xaxis_tickangle=-45, height=500)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("📍 Top 10 villes")
        for _, row in sal_data.head(10).iterrows():
            st.markdown(f"**{row['ville']}**")
            st.markdown(f"💰 {row['salaire_moyen']:,.0f}€ | 📋 {row['nb_offres']} offres")
            st.markdown("---")

    # Salaires par région
    st.subheader("🗾 Salaires par région")
    region_data = get_db_data("""
        SELECT region, COUNT(*) as nb_offres,
               ROUND(AVG(salaire_median)) as salaire_moyen
        FROM clean.offres
        WHERE region NOT IN ('Inconnue', 'Autre')
          AND salaire_median IS NOT NULL
        GROUP BY region
        ORDER BY salaire_moyen DESC
    """)
    fig = px.bar(
        region_data,
        x="region", y="salaire_moyen",
        color="nb_offres",
        color_continuous_scale="Greens",
        title="Salaire moyen par région"
    )
    fig.update_layout(xaxis_tickangle=-30)
    st.plotly_chart(fig, use_container_width=True)

# ─── Page 3 — Prédiction ─────────────────────────────────────────────

elif page == "🤖 Prédiction":
    st.title("🤖 Prédiction de Salaire")
    st.markdown("Renseigne les caractéristiques du poste pour obtenir une estimation salariale.")

    col1, col2 = st.columns(2)

    with col1:
        titre = st.text_input("Titre du poste", "Data Engineer Senior")
        ville = st.selectbox("Ville", ["Paris", "Lyon", "Marseille", "Toulouse", "Bordeaux", "Nantes", "Strasbourg", "Lille"])
        type_contrat = st.selectbox("Type de contrat", ["CDI", "CDD", "Freelance", "Alternance"])
        niveau_exp = st.selectbox("Niveau d'expérience", ["junior", "mid", "senior"])
        is_remote = st.checkbox("Télétravail possible")

    with col2:
        description = st.text_area("Description du poste", "Nous recherchons un profil tech expérimenté...")
        technologies = st.multiselect(
            "Technologies",
            ["python", "sql", "java", "javascript", "react", "angular", "vue",
             "docker", "kubernetes", "aws", "gcp", "azure", "spark", "kafka",
             "airflow", "dbt", "postgresql", "mongodb", "redis", "git",
             "scala", "typescript", "machine learning", "mlops"],
            default=["python", "sql", "docker"]
        )

    if st.button("🎯 Prédire le salaire", type="primary"):
        with st.spinner("Calcul en cours..."):
            payload = {
                "titre": titre,
                "description": description,
                "type_contrat": type_contrat,
                "ville": ville,
                "niveau_experience": niveau_exp,
                "technologies": technologies,
                "is_remote": is_remote,
            }
            try:
                resp = requests.post(f"{API_URL}/predict", json=payload, timeout=10)
                result = resp.json()

                if "salaire_predit" in result:
                    sal = result["salaire_predit"]
                    ic_low = result["intervalle_confiance"][0]
                    ic_high = result["intervalle_confiance"][1]

                    st.success(f"### 💰 Salaire prédit : {sal:,}€ / an")
                    st.info(f"📊 Intervalle de confiance : {ic_low:,}€ — {ic_high:,}€")

                    # Comparaison avec le marché
                    market = get_db_data(f"""
                        SELECT ROUND(AVG(salaire_median)) as avg_sal
                        FROM clean.offres
                        WHERE niveau_experience = '{niveau_exp}'
                          AND salaire_median IS NOT NULL
                    """)
                    market_avg = int(market["avg_sal"][0])
                    diff = sal - market_avg
                    diff_pct = (diff / market_avg) * 100

                    col1, col2, col3 = st.columns(3)
                    col1.metric("Salaire prédit", f"{sal:,}€")
                    col2.metric("Médiane marché", f"{market_avg:,}€")
                    col3.metric("Écart", f"{diff:+,}€", f"{diff_pct:+.1f}%")

                else:
                    st.error(f"Erreur: {result.get('detail', 'Inconnu')}")
            except Exception as e:
                st.error(f"Erreur API: {e}")

# ─── Page 4 — Monitoring ML ──────────────────────────────────────────

elif page == "📊 Monitoring ML":
    st.title("📊 Monitoring ML")

    # Info modèle en production
    model_info = get_api("/model/info")
    if model_info:
        col1, col2, col3 = st.columns(3)
        col1.metric("Version", model_info.get("version", "—"))
        col2.metric("MAE", f"{model_info.get('mae', 0):,.0f}€")
        col3.metric("R²", f"{model_info.get('r2', 0):.3f}")

    st.markdown("---")

    # Historique des runs MLflow
    st.subheader("📈 Historique des expériences")
    try:
        import mlflow
        mlflow.set_tracking_uri("http://localhost:5000")
        client = mlflow.MlflowClient()
        exp = client.get_experiment_by_name("smartmarket-salary-prediction")
        if exp:
            runs = client.search_runs(
                experiment_ids=[exp.experiment_id],
                order_by=["start_time DESC"],
            )
            runs_data = []
            for r in runs:
                runs_data.append({
                    "Run": r.data.tags.get("mlflow.runName", r.info.run_id[:8]),
                    "MAE": r.data.metrics.get("test_mae", None),
                    "R²": r.data.metrics.get("test_r2", None),
                    "MAPE": r.data.metrics.get("test_mape", None),
                })
            df_runs = pd.DataFrame(runs_data).dropna()
            st.dataframe(df_runs, use_container_width=True)

            if len(df_runs) > 0:
                fig = px.bar(
                    df_runs,
                    x="Run", y="MAE",
                    title="MAE par run (€ — plus bas = meilleur)",
                    color="MAE",
                    color_continuous_scale="RdYlGn_r",
                )
                st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"MLflow non disponible: {e}")

    # Stats données
    st.subheader("📊 Qualité des données")
    stats = get_db_data("""
        SELECT
            COUNT(*) as total,
            COUNT(salaire_median) as avec_salaire,
            ROUND(COUNT(salaire_median)::numeric/COUNT(*)*100,1) as pct_salaire,
            COUNT(CASE WHEN is_remote THEN 1 END) as remote
        FROM clean.offres
    """)
    col1, col2, col3 = st.columns(3)
    col1.metric("Total offres", f"{stats['total'][0]:,}")
    col2.metric("Avec salaire", f"{stats['avec_salaire'][0]:,} ({stats['pct_salaire'][0]}%)")
    col3.metric("Remote", f"{stats['remote'][0]:,}")
