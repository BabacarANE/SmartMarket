"""
Dashboard SmartMarket Intelligence — Streamlit
Design professionnel thème sombre
"""

import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from sqlalchemy import create_engine, text

# ─── Config ──────────────────────────────────────────────────────────

st.set_page_config(
    page_title="SmartMarket Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS Custom ──────────────────────────────────────────────────────

st.markdown("""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    /* Global */
    .stApp {
        background-color: #0F1117;
        font-family: 'Inter', sans-serif;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #161B27;
        border-right: 1px solid #1E2535;
    }

    [data-testid="stSidebar"] .stRadio label {
        color: #8B9CC7 !important;
        font-size: 0.9rem;
        padding: 8px 12px;
        border-radius: 8px;
        transition: all 0.2s;
    }

    /* KPI Cards */
    .kpi-card {
        background: linear-gradient(135deg, #161B27 0%, #1A2035 100%);
        border: 1px solid #1E2A45;
        border-radius: 16px;
        padding: 24px 28px;
        margin: 8px 0;
        position: relative;
        overflow: hidden;
    }

    .kpi-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0;
        width: 4px; height: 100%;
        border-radius: 16px 0 0 16px;
    }

    .kpi-card.blue::before { background: #4F8EF7; }
    .kpi-card.purple::before { background: #8B5CF6; }
    .kpi-card.green::before { background: #10B981; }
    .kpi-card.orange::before { background: #F59E0B; }

    .kpi-label {
        color: #6B7A99;
        font-size: 0.78rem;
        font-weight: 500;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 8px;
    }

    .kpi-value {
        color: #E8EDF8;
        font-size: 2rem;
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
        line-height: 1;
    }

    .kpi-sub {
        color: #4F8EF7;
        font-size: 0.78rem;
        margin-top: 6px;
    }

    /* Section headers */
    .section-header {
        color: #C5CDE8;
        font-size: 1.1rem;
        font-weight: 600;
        letter-spacing: 0.02em;
        margin: 24px 0 16px 0;
        display: flex;
        align-items: center;
        gap: 10px;
    }

    .section-header::after {
        content: '';
        flex: 1;
        height: 1px;
        background: linear-gradient(90deg, #1E2A45 0%, transparent 100%);
    }

    /* Page title */
    .page-title {
        color: #E8EDF8;
        font-size: 1.8rem;
        font-weight: 700;
        margin-bottom: 4px;
    }

    .page-subtitle {
        color: #6B7A99;
        font-size: 0.9rem;
        margin-bottom: 32px;
    }

    /* Brand header */
    .brand-name {
        color: #E8EDF8;
        font-size: 1.15rem;
        font-weight: 700;
        margin-top: 12px;
    }

    .brand-tag {
        color: #4F8EF7;
        font-size: 0.78rem;
        font-weight: 500;
        letter-spacing: 0.06em;
    }

    /* Status badge */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: #0D2137;
        border: 1px solid #10B981;
        color: #10B981;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 500;
        margin-top: 16px;
    }

    .status-badge.error {
        border-color: #EF4444;
        color: #EF4444;
        background: #1F0D0D;
    }

    /* Prediction result */
    .pred-result {
        background: linear-gradient(135deg, #0D2137 0%, #0F2847 100%);
        border: 1px solid #1E4080;
        border-radius: 16px;
        padding: 32px;
        text-align: center;
        margin: 16px 0;
    }

    .pred-amount {
        color: #4F8EF7;
        font-size: 3rem;
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
    }

    .pred-label {
        color: #6B7A99;
        font-size: 0.9rem;
        margin-top: 8px;
    }

    .pred-range {
        color: #8B9CC7;
        font-size: 0.85rem;
        margin-top: 12px;
        font-family: 'JetBrains Mono', monospace;
    }

    /* Metric comparison */
    .metric-row {
        display: flex;
        gap: 16px;
        margin-top: 24px;
    }

    .metric-box {
        flex: 1;
        background: #161B27;
        border: 1px solid #1E2535;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
    }

    .metric-box-label {
        color: #6B7A99;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }

    .metric-box-value {
        color: #E8EDF8;
        font-size: 1.4rem;
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
        margin-top: 4px;
    }

    /* Divider */
    hr {
        border: none;
        border-top: 1px solid #1E2535;
        margin: 28px 0;
    }

    /* Streamlit overrides */
    .stSelectbox label, .stMultiSelect label, .stTextInput label,
    .stTextArea label, .stCheckbox label {
        color: #8B9CC7 !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
    }

    .stButton button {
        background: linear-gradient(135deg, #4F8EF7 0%, #6366F1 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        padding: 12px 32px !important;
        font-size: 0.95rem !important;
        transition: all 0.2s !important;
    }

    .stButton button:hover {
        opacity: 0.9 !important;
        transform: translateY(-1px) !important;
    }

    /* Hide Streamlit branding */
    #MainMenu, footer, header { visibility: hidden; }
    .stDeployButton { display: none; }
</style>
""", unsafe_allow_html=True)

# ─── Palette Plotly ───────────────────────────────────────────────────

PLOTLY_TEMPLATE = "plotly_dark"
COLOR_PRIMARY = "#4F8EF7"
COLOR_SECONDARY = "#8B5CF6"
COLOR_SUCCESS = "#10B981"
COLOR_WARNING = "#F59E0B"
COLOR_SCALE = ["#1E3A6E", "#2E5BA8", "#4F8EF7", "#7BB3FF", "#A8D1FF"]
COLOR_TECH = px.colors.sequential.Blues_r

API_URL = os.environ.get("API_URL", "http://localhost:8000")
DB_CONN = os.environ.get("DB_CONN_STRING", "postgresql+pg8000://smartmarket:x@localhost:5433/smartmarket_db")
MLFLOW_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000")

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

def plotly_layout(fig, height=420):
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=height,
        font=dict(family="Inter", color="#8B9CC7", size=12),
        margin=dict(l=16, r=16, t=40, b=16),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor="#1E2535",
            font=dict(color="#8B9CC7"),
        ),
    )
    fig.update_xaxes(gridcolor="#1E2535", zerolinecolor="#1E2535")
    fig.update_yaxes(gridcolor="#1E2535", zerolinecolor="#1E2535")
    return fig

# ─── Sidebar ─────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style="padding: 8px 0 24px 0;">
        <div style="width:48px;height:48px;background:linear-gradient(135deg,#4F8EF7,#6366F1);
             border-radius:12px;display:flex;align-items:center;justify-content:center;
             font-size:1.4rem;">⚡</div>
        <div class="brand-name">SmartMarket</div>
        <div class="brand-tag">INTELLIGENCE · TECH JOBS</div>
    </div>
    """, unsafe_allow_html=True)

    page = st.radio(
        "Navigation",
        ["Vue Marché", "Carte Salaires", "Prédiction", "Monitoring ML"],
        label_visibility="collapsed",
    )

    st.markdown("<hr>", unsafe_allow_html=True)

    health = get_api("/health")
    model_ok = health.get("model_loaded", False)
    badge_class = "status-badge" if model_ok else "status-badge error"
    badge_icon = "●" if model_ok else "●"
    badge_text = "Modèle actif" if model_ok else "Modèle offline"
    st.markdown(f'<div class="{badge_class}">{badge_icon} {badge_text}</div>', unsafe_allow_html=True)

    st.markdown("""
    <div style="margin-top:auto;padding-top:32px;color:#3A4560;font-size:0.72rem;">
        Données · France Travail & Adzuna<br>
        Modèle · LightGBM · MAE 7 065€
    </div>
    """, unsafe_allow_html=True)

# ─── Page 1 — Vue Marché ─────────────────────────────────────────────

if page == "Vue Marché":
    st.markdown('<div class="page-title">Marché de l\'emploi tech</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">France · données temps réel · collecte quotidienne</div>', unsafe_allow_html=True)

    kpi = get_db_data("""
        SELECT COUNT(*) as nb_offres,
               COUNT(DISTINCT entreprise) as nb_entreprises,
               ROUND(AVG(salaire_median)) as salaire_median,
               COUNT(CASE WHEN is_remote THEN 1 END) as nb_remote
        FROM clean.offres
    """)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class="kpi-card blue">
            <div class="kpi-label">Offres indexées</div>
            <div class="kpi-value">{kpi['nb_offres'][0]:,}</div>
            <div class="kpi-sub">France Travail + Adzuna</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="kpi-card purple">
            <div class="kpi-label">Entreprises</div>
            <div class="kpi-value">{kpi['nb_entreprises'][0]:,}</div>
            <div class="kpi-sub">recruteurs actifs</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="kpi-card green">
            <div class="kpi-label">Salaire médian</div>
            <div class="kpi-value">{int(kpi['salaire_median'][0]):,}€</div>
            <div class="kpi-sub">brut annuel</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="kpi-card orange">
            <div class="kpi-label">Remote</div>
            <div class="kpi-value">{kpi['nb_remote'][0]:,}</div>
            <div class="kpi-sub">offres télétravail</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown('<div class="section-header">Top technologies demandées</div>', unsafe_allow_html=True)
        tech = get_db_data("""
            SELECT technologie, SUM(nb_offres) as total, ROUND(AVG(salaire_moyen)) as sal
            FROM analytics.agg_tech_tendances
            GROUP BY technologie ORDER BY total DESC LIMIT 15
        """)
        fig = px.bar(tech, x="total", y="technologie", orientation="h",
                     color="sal", color_continuous_scale="Blues",
                     labels={"total": "Offres", "technologie": "", "sal": "Salaire moyen €"})
        fig.update_traces(marker_line_width=0)
        fig.update_coloraxes(showscale=False)
        st.plotly_chart(plotly_layout(fig), use_container_width=True)

    with col2:
        st.markdown('<div class="section-header">Distribution salariale</div>', unsafe_allow_html=True)
        sal = get_db_data("""
            SELECT salaire_median, niveau_experience FROM clean.offres
            WHERE salaire_median BETWEEN 15000 AND 150000
        """)
        color_map = {"junior": "#4F8EF7", "mid": "#8B5CF6", "senior": "#10B981", "non_specifie": "#374151"}
        fig = px.histogram(sal, x="salaire_median", color="niveau_experience",
                           nbins=40, color_discrete_map=color_map,
                           labels={"salaire_median": "Salaire (€)", "count": "Offres"})
        fig.update_traces(marker_line_width=0)
        st.plotly_chart(plotly_layout(fig), use_container_width=True)

    st.markdown('<div class="section-header">Répartition des contrats</div>', unsafe_allow_html=True)
    contrat = get_db_data("""
        SELECT type_contrat, COUNT(*) as nb FROM clean.offres
        GROUP BY type_contrat ORDER BY nb DESC
    """)
    fig = px.pie(contrat, values="nb", names="type_contrat",
                 color_discrete_sequence=["#4F8EF7","#8B5CF6","#10B981","#F59E0B","#EF4444"])
    fig.update_traces(textfont_color="white", hole=0.45)
    st.plotly_chart(plotly_layout(fig, height=340), use_container_width=True)

# ─── Page 2 — Carte Salaires ─────────────────────────────────────────

elif page == "Carte Salaires":
    st.markdown('<div class="page-title">Salaires par localisation</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Classement des villes par rémunération moyenne</div>', unsafe_allow_html=True)

    sal = get_db_data("""
        SELECT ville, nb_offres, salaire_moyen, salaire_median
        FROM analytics.agg_salaires_par_ville
        WHERE nb_offres >= 3 ORDER BY salaire_moyen DESC
    """)

    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown('<div class="section-header">Top 20 villes · salaire moyen</div>', unsafe_allow_html=True)
        fig = px.bar(sal.head(20), x="ville", y="salaire_moyen",
                     color="nb_offres", color_continuous_scale="Blues",
                     labels={"salaire_moyen": "Salaire moyen (€)", "ville": "", "nb_offres": "Nb offres"})
        fig.update_traces(marker_line_width=0)
        fig.update_layout(xaxis_tickangle=-35)
        st.plotly_chart(plotly_layout(fig, height=460), use_container_width=True)

    with col2:
        st.markdown('<div class="section-header">Classement</div>', unsafe_allow_html=True)
        for i, (_, row) in enumerate(sal.head(8).iterrows()):
            rank_color = ["#F59E0B","#8B9CC7","#CD7C3F"] if i < 3 else ["#374151"]
            color = rank_color[min(i, len(rank_color)-1)]
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;align-items:center;
                 padding:10px 14px;background:#161B27;border:1px solid #1E2535;
                 border-radius:10px;margin-bottom:8px;">
                <div>
                    <span style="color:{color};font-weight:700;font-size:0.8rem;">#{i+1}</span>
                    <span style="color:#C5CDE8;font-size:0.85rem;margin-left:8px;">{row['ville'][:18]}</span>
                </div>
                <span style="color:#4F8EF7;font-family:'JetBrains Mono',monospace;font-size:0.85rem;font-weight:600;">
                    {int(row['salaire_moyen']):,}€
                </span>
            </div>""", unsafe_allow_html=True)

    st.markdown('<div class="section-header">Salaires par région</div>', unsafe_allow_html=True)
    reg = get_db_data("""
        SELECT region, COUNT(*) as nb, ROUND(AVG(salaire_median)) as sal
        FROM clean.offres
        WHERE region NOT IN ('Inconnue','Autre') AND salaire_median IS NOT NULL
        GROUP BY region ORDER BY sal DESC
    """)
    fig = px.bar(reg, x="region", y="sal", color="nb",
                 color_continuous_scale="Purples",
                 labels={"sal": "Salaire moyen (€)", "region": "", "nb": "Offres"})
    fig.update_traces(marker_line_width=0)
    fig.update_layout(xaxis_tickangle=-25)
    st.plotly_chart(plotly_layout(fig, height=360), use_container_width=True)

# ─── Page 3 — Prédiction ─────────────────────────────────────────────

elif page == "Prédiction":
    st.markdown('<div class="page-title">Estimation salariale</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Renseigne les caractéristiques du poste · LightGBM · MAE ±7 065€</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        titre = st.text_input("Intitulé du poste", "Data Engineer Senior",
                              placeholder="ex: Data Engineer Senior")
        ville = st.selectbox("Localisation", ["Paris","Lyon","Marseille","Toulouse","Bordeaux","Nantes","Strasbourg","Lille"])
        type_contrat = st.selectbox("Type de contrat", ["CDI","CDD","Freelance","Alternance"])
        niveau_exp = st.selectbox("Expérience", ["junior","mid","senior"])
        is_remote = st.checkbox("Télétravail possible")

    with col2:
        description = st.text_area("Description (optionnel)", height=120,
                                   placeholder="Décris le poste pour affiner la prédiction...")
        technologies = st.multiselect(
            "Stack technique",
            ["python","sql","java","javascript","typescript","react","angular","vue",
             "docker","kubernetes","aws","gcp","azure","spark","kafka","airflow","dbt",
             "postgresql","mongodb","redis","git","scala","machine learning","mlops"],
            default=["python","sql","docker"],
        )

    st.markdown("<br>", unsafe_allow_html=True)
    predict_btn = st.button("Estimer le salaire", type="primary", use_container_width=False)

    if predict_btn:
        with st.spinner("Calcul en cours..."):
            payload = {
                "titre": titre, "description": description or "",
                "type_contrat": type_contrat, "ville": ville,
                "niveau_experience": niveau_exp, "technologies": technologies,
                "is_remote": is_remote,
            }
            try:
                resp = requests.post(f"{API_URL}/predict", json=payload, timeout=10)
                result = resp.json()

                if "salaire_predit" in result:
                    sal = result["salaire_predit"]
                    ic_low, ic_high = result["intervalle_confiance"]

                    st.markdown(f"""
                    <div class="pred-result">
                        <div class="pred-label">Salaire annuel estimé</div>
                        <div class="pred-amount">{sal:,} €</div>
                        <div class="pred-range">Fourchette · {ic_low:,}€ — {ic_high:,}€</div>
                    </div>""", unsafe_allow_html=True)

                    market = get_db_data(f"""
                        SELECT ROUND(AVG(salaire_median)) as avg_sal
                        FROM clean.offres
                        WHERE niveau_experience = '{niveau_exp}' AND salaire_median IS NOT NULL
                    """)
                    market_avg = int(market["avg_sal"][0])
                    diff = sal - market_avg
                    diff_pct = (diff / market_avg) * 100
                    diff_color = "#10B981" if diff >= 0 else "#EF4444"
                    diff_sign = "+" if diff >= 0 else ""

                    st.markdown(f"""
                    <div class="metric-row">
                        <div class="metric-box">
                            <div class="metric-box-label">Prédit</div>
                            <div class="metric-box-value" style="color:#4F8EF7">{sal:,}€</div>
                        </div>
                        <div class="metric-box">
                            <div class="metric-box-label">Médiane marché · {niveau_exp}</div>
                            <div class="metric-box-value">{market_avg:,}€</div>
                        </div>
                        <div class="metric-box">
                            <div class="metric-box-label">Écart</div>
                            <div class="metric-box-value" style="color:{diff_color}">
                                {diff_sign}{diff:,}€ ({diff_sign}{diff_pct:.1f}%)
                            </div>
                        </div>
                    </div>""", unsafe_allow_html=True)
                else:
                    st.error(f"Erreur : {result.get('detail','Inconnu')}")
            except Exception as e:
                st.error(f"API non disponible : {e}")

# ─── Page 4 — Monitoring ML ──────────────────────────────────────────

elif page == "Monitoring ML":
    st.markdown('<div class="page-title">Monitoring ML</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Performance du modèle en production · MLflow tracking</div>', unsafe_allow_html=True)

    info = get_api("/model/info")
    if info:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f"""
            <div class="kpi-card blue">
                <div class="kpi-label">Version</div>
                <div class="kpi-value">v{info.get('version','—')}</div>
                <div class="kpi-sub">Production</div>
            </div>""", unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class="kpi-card green">
                <div class="kpi-label">MAE</div>
                <div class="kpi-value">{info.get('mae',0):,.0f}€</div>
                <div class="kpi-sub">erreur absolue moyenne</div>
            </div>""", unsafe_allow_html=True)
        with c3:
            st.markdown(f"""
            <div class="kpi-card purple">
                <div class="kpi-label">R²</div>
                <div class="kpi-value">{info.get('r2',0):.3f}</div>
                <div class="kpi-sub">variance expliquée</div>
            </div>""", unsafe_allow_html=True)
        with c4:
            stats = get_db_data("SELECT COUNT(*) as n FROM clean.offres WHERE salaire_median IS NOT NULL")
            st.markdown(f"""
            <div class="kpi-card orange">
                <div class="kpi-label">Données entraînement</div>
                <div class="kpi-value">{stats['n'][0]:,}</div>
                <div class="kpi-sub">offres avec salaire</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    try:
        import mlflow
        mlflow.set_tracking_uri(MLFLOW_URI)
        client = mlflow.MlflowClient()
        exp = client.get_experiment_by_name("smartmarket-salary-prediction")
        if exp:
            runs = client.search_runs(experiment_ids=[exp.experiment_id], order_by=["start_time DESC"])
            rows = []
            for r in runs:
                mae = r.data.metrics.get("test_mae")
                r2 = r.data.metrics.get("test_r2")
                if mae and r2:
                    rows.append({
                        "Run": r.data.tags.get("mlflow.runName", r.info.run_id[:8]),
                        "MAE (€)": int(mae),
                        "R²": round(r2, 3),
                        "MAPE (%)": round(r.data.metrics.get("test_mape", 0), 1),
                    })

            if rows:
                df_runs = pd.DataFrame(rows)

                col1, col2 = st.columns(2)
                with col1:
                    st.markdown('<div class="section-header">MAE par run</div>', unsafe_allow_html=True)
                    fig = px.bar(df_runs, x="Run", y="MAE (€)",
                                 color="MAE (€)", color_continuous_scale="RdYlGn_r",
                                 labels={"MAE (€)": "MAE (€)"})
                    fig.update_traces(marker_line_width=0)
                    st.plotly_chart(plotly_layout(fig, height=320), use_container_width=True)

                with col2:
                    st.markdown('<div class="section-header">R² par run</div>', unsafe_allow_html=True)
                    fig = px.bar(df_runs, x="Run", y="R²",
                                 color="R²", color_continuous_scale="Blues",
                                 labels={"R²": "R²"})
                    fig.update_traces(marker_line_width=0)
                    st.plotly_chart(plotly_layout(fig, height=320), use_container_width=True)

                st.markdown('<div class="section-header">Détail des runs</div>', unsafe_allow_html=True)
                st.dataframe(
                    df_runs.style.background_gradient(subset=["MAE (€)"], cmap="RdYlGn_r"),
                    use_container_width=True, hide_index=True,
                )
    except Exception as e:
        st.warning(f"MLflow non disponible : {e}")

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">Qualité des données</div>', unsafe_allow_html=True)

    stats = get_db_data("""
        SELECT COUNT(*) as total,
               COUNT(salaire_median) as avec_salaire,
               ROUND(COUNT(salaire_median)::numeric/COUNT(*)*100,1) as pct,
               COUNT(CASE WHEN is_remote THEN 1 END) as remote,
               COUNT(DISTINCT source) as sources
        FROM clean.offres
    """)

    col1, col2, col3 = st.columns(3)
    with col1:
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=float(stats['pct'][0]),
            title={"text": "Taux salaires renseignés", "font": {"color": "#8B9CC7", "size": 13}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "#374151"},
                "bar": {"color": "#4F8EF7"},
                "bgcolor": "#161B27",
                "bordercolor": "#1E2535",
                "steps": [
                    {"range": [0, 20], "color": "#1F0D0D"},
                    {"range": [20, 50], "color": "#1A1A0D"},
                    {"range": [50, 100], "color": "#0D1F0D"},
                ],
            },
            number={"suffix": "%", "font": {"color": "#E8EDF8", "size": 28}},
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            font={"color": "#8B9CC7"},
            height=220, margin=dict(l=16, r=16, t=40, b=16),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown(f"""
        <div class="kpi-card blue" style="margin-top:16px">
            <div class="kpi-label">Total offres</div>
            <div class="kpi-value">{stats['total'][0]:,}</div>
        </div>
        <div class="kpi-card green" style="margin-top:12px">
            <div class="kpi-label">Avec salaire</div>
            <div class="kpi-value">{stats['avec_salaire'][0]:,}</div>
        </div>""", unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="kpi-card purple" style="margin-top:16px">
            <div class="kpi-label">Offres remote</div>
            <div class="kpi-value">{stats['remote'][0]:,}</div>
        </div>
        <div class="kpi-card orange" style="margin-top:12px">
            <div class="kpi-label">Sources actives</div>
            <div class="kpi-value">{stats['sources'][0]}</div>
        </div>""", unsafe_allow_html=True)