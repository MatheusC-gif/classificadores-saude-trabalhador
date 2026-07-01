"""Calculadora isolada da Escala de Estresse no Trabalho."""

import streamlit as st

from app import _mostrar_estresse


st.set_page_config(
    page_title="Calculadora de Estresse no Trabalho",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    .stApp {
        background: #f6f8fb;
        color: #263b50;
    }
    .block-container {
        max-width: 900px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }
    h1, h2, h3,
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stWidgetLabel"] p,
    [data-testid="stCaptionContainer"] {
        color: #17324d !important;
    }
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div,
    div[data-baseweb="base-input"] {
        background: #ffffff !important;
        color: #17324d !important;
    }
    div[data-baseweb="select"] span,
    input {
        color: #17324d !important;
    }
    [data-testid="stExpander"] details,
    [data-testid="stExpander"] summary {
        background: #eef4f8 !important;
        color: #17324d !important;
    }
    [data-testid="stExpander"] summary p,
    [data-testid="stExpander"] summary span {
        color: #17324d !important;
    }
    [data-testid="stExpander"] summary svg {
        fill: #17324d !important;
    }
    [data-testid="stForm"] {
        background: white;
        border: 1px solid #dde5ee;
        border-radius: 18px;
        padding: 1.25rem;
        box-shadow: 0 10px 28px rgba(23, 50, 77, 0.06);
    }
    [data-testid="stFormSubmitButton"] button,
    [data-testid="stDownloadButton"] button {
        background: #17324d;
        color: #ffffff;
        border: 0;
    }
    [data-testid="stFormSubmitButton"] button p,
    [data-testid="stDownloadButton"] button p {
        color: #ffffff !important;
    }
    .resultado-titulo {
        color: #17324d;
        font-size: 1.3rem;
        font-weight: 700;
        margin: 1.4rem 0 0.5rem;
    }
    div[data-testid="stMetric"] {
        background: white;
        border: 1px solid #dde5ee;
        border-radius: 14px;
        padding: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Calculadora de Estresse no Trabalho")
st.write("Informe as respostas do questionário para receber as classificações automaticamente.")
_mostrar_estresse()
st.divider()
st.caption(
    "A ferramenta não armazena as respostas e não substitui avaliação profissional."
)
