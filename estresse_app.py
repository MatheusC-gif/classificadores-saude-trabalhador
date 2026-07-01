"""Calculadora isolada da Escala de Estresse no Trabalho."""

import streamlit as st

from app import (
    _mostrar_estresse,
    _mostrar_ipaq,
    calcular_estresse,
    relatorio_estresse,
    relatorio_estresse_pdf,
)


DEMANDA_TESTE = [
    "Frequentemente",
    "Frequentemente",
    "Às vezes",
    "Raramente",
    "Às vezes",
]

CONTROLE_TESTE = [
    "Às vezes",
    "Frequentemente",
    "Frequentemente",
    "Raramente",
    "Às vezes",
    "Raramente",
]

APOIO_TESTE = [
    "Concordo mais que discordo",
    "Concordo totalmente",
    "Concordo mais que discordo",
    "Concordo mais que discordo",
    "Concordo totalmente",
    "Concordo totalmente",
]


def carregar_cenario_teste() -> None:
    """Preenche um cenário fictício e calcula o resultado automaticamente."""
    st.session_state["nome_estresse"] = "Participante fictício"

    for indice, resposta in enumerate(DEMANDA_TESTE):
        st.session_state[f"demanda_{indice}"] = resposta
    for indice, resposta in enumerate(CONTROLE_TESTE):
        st.session_state[f"controle_{indice}"] = resposta
    for indice, resposta in enumerate(APOIO_TESTE):
        st.session_state[f"apoio_{indice}"] = resposta

    demanda = [4, 4, 3, 2, 3]
    controle = [3, 4, 4, 2, 3, 2]
    apoio = [3, 4, 3, 3, 4, 4]
    resultado = calcular_estresse(demanda, controle, apoio)

    st.session_state["resultado_estresse"] = resultado
    st.session_state["relatorio_estresse"] = relatorio_estresse(
        "Participante fictício",
        resultado,
    )
    st.session_state["relatorio_estresse_pdf"] = relatorio_estresse_pdf(
        "Participante fictício",
        resultado,
    )
    st.session_state["cenario_teste_carregado"] = True


st.set_page_config(
    page_title="Calculadoras de Saúde do Trabalhador",
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

st.title("Calculadoras de Saúde do Trabalhador")
st.write("Informe as respostas dos questionários para receber as classificações automaticamente.")

aba_estresse, aba_ipaq = st.tabs(("Estresse no trabalho", "Atividade física - IPAQ"))

with aba_estresse:
    st.warning(
        "AMBIENTE DE TESTE — utilize somente dados fictícios. "
        "Os resultados servem para validar o funcionamento da calculadora."
    )
    st.button(
        "Iniciar ambiente de teste",
        on_click=carregar_cenario_teste,
        type="primary",
        use_container_width=True,
    )
    if st.session_state.get("cenario_teste_carregado"):
        st.success(
            "Cenário fictício carregado. As 17 respostas e a classificação "
            "foram preenchidas automaticamente."
        )
    _mostrar_estresse()

with aba_ipaq:
    st.info(
        "Preencha os dias por semana e os minutos por sessão. "
        "O resultado poderá ser baixado em PDF."
    )
    _mostrar_ipaq()

st.divider()
st.caption(
    "As ferramentas não armazenam as respostas e não substituem avaliação profissional."
)
