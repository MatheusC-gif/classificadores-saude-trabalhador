"""Aplicação Streamlit para classificação de estresse no trabalho e IPAQ."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import streamlit as st


FREQUENCIA = (
    "Nunca ou quase nunca",
    "Raramente",
    "Às vezes",
    "Frequentemente",
)

APOIO = (
    "Discordo totalmente",
    "Discordo mais que concordo",
    "Concordo mais que discordo",
    "Concordo totalmente",
)

QUESTOES_DEMANDA = (
    "Com que frequência você tem que fazer suas tarefas de trabalho com muita rapidez?",
    "Com que frequência você tem que trabalhar intensamente (produzir muito em pouco tempo)?",
    "Seu trabalho exige demais de você?",
    "Você tem tempo suficiente para cumprir todas as tarefas do seu trabalho?",
    "O seu trabalho costuma apresentar exigências contraditórias ou discordantes?",
)

QUESTOES_CONTROLE = (
    "Você tem possibilidade de aprender coisas novas em seu trabalho?",
    "Seu trabalho exige muita habilidade ou conhecimentos especializados?",
    "Seu trabalho exige que você tome iniciativas?",
    "No seu trabalho, você tem que repetir muitas vezes as mesmas tarefas?",
    "Você pode escolher COMO fazer o seu trabalho?",
    "Você pode escolher O QUE fazer no seu trabalho?",
)

QUESTOES_APOIO = (
    "Existe um ambiente calmo e agradável onde trabalho.",
    "No trabalho, nós nos relacionamos bem uns com os outros.",
    "Eu posso contar com o apoio dos meus colegas de trabalho.",
    "Se eu não estiver num bom dia, meus colegas compreendem.",
    "No trabalho, eu me relaciono bem com meus chefes.",
    "Eu gosto de trabalhar com meus colegas.",
)

OPCOES_FREQUENCIA = ("Selecione uma resposta",) + FREQUENCIA
OPCOES_APOIO = ("Selecione uma resposta",) + APOIO


@dataclass(frozen=True)
class ResultadoEstresse:
    media_demanda: float
    media_controle: float
    media_apoio: float
    demanda: str
    controle: str
    apoio: str
    quadrante: str


@dataclass(frozen=True)
class Atividade:
    dias: int
    minutos_sessao: int

    @property
    def minutos_semana(self) -> int:
        return self.dias * self.minutos_sessao


@dataclass(frozen=True)
class ResultadoIPAQ:
    classificacao: str
    reduzida: str
    criterio: str
    frequencia_somada: int
    minutos_semana: int


def _pontuar(respostas: list[int], invertidas: set[int] | None = None) -> list[int]:
    invertidas = invertidas or set()
    return [5 - valor if indice in invertidas else valor for indice, valor in enumerate(respostas)]


def calcular_estresse(
    demanda: list[int],
    controle: list[int],
    apoio: list[int],
) -> ResultadoEstresse:
    if len(demanda) != 5 or len(controle) != 6 or len(apoio) != 6:
        raise ValueError("Responda todas as 17 questões.")

    media_demanda = sum(_pontuar(demanda, {3})) / 5
    media_controle = sum(_pontuar(controle, {3})) / 6
    media_apoio = sum(_pontuar(apoio)) / 6

    demanda_alta = media_demanda >= 2
    controle_alto = media_controle >= 2

    if demanda_alta and not controle_alto:
        quadrante = "Alto desgaste"
    elif demanda_alta and controle_alto:
        quadrante = "Trabalho ativo"
    elif not demanda_alta and not controle_alto:
        quadrante = "Trabalho passivo"
    else:
        quadrante = "Baixo desgaste"

    return ResultadoEstresse(
        media_demanda=media_demanda,
        media_controle=media_controle,
        media_apoio=media_apoio,
        demanda="Alta demanda" if demanda_alta else "Baixa demanda",
        controle="Alto controle" if controle_alto else "Baixo controle",
        apoio="Alto apoio social" if media_apoio >= 2 else "Baixo apoio social",
        quadrante=quadrante,
    )


def calcular_ipaq(caminhada: Atividade, moderada: Atividade, vigorosa: Atividade) -> ResultadoIPAQ:
    atividades = (caminhada, moderada, vigorosa)
    for atividade in atividades:
        if not 0 <= atividade.dias <= 7:
            raise ValueError("A frequência deve estar entre 0 e 7 dias.")
        if not 0 <= atividade.minutos_sessao <= 1440:
            raise ValueError("A duração deve estar entre 0 e 1.440 minutos.")
        if atividade.dias == 0 and atividade.minutos_sessao != 0:
            raise ValueError("Quando a frequência for zero, informe também zero minuto.")
        if atividade.dias > 0 and atividade.minutos_sessao < 10:
            raise ValueError("Considere apenas sessões com pelo menos 10 minutos contínuos.")

    frequencia_somada = sum(a.dias for a in atividades)
    minutos_semana = sum(a.minutos_semana for a in atividades)
    dias_caminhada_moderada_30 = (
        (caminhada.dias if caminhada.minutos_sessao >= 30 else 0)
        + (moderada.dias if moderada.minutos_sessao >= 30 else 0)
    )

    muito_ativo_a = vigorosa.dias >= 5 and vigorosa.minutos_sessao >= 30
    muito_ativo_b = (
        vigorosa.dias >= 3
        and vigorosa.minutos_sessao >= 20
        and dias_caminhada_moderada_30 >= 5
    )
    ativo_a = vigorosa.dias >= 3 and vigorosa.minutos_sessao >= 20
    ativo_b = (
        (moderada.dias >= 5 and moderada.minutos_sessao >= 30)
        or (caminhada.dias >= 5 and caminhada.minutos_sessao >= 30)
    )
    ativo_c = frequencia_somada >= 5 and minutos_semana >= 150

    if muito_ativo_a:
        classificacao = "Muito ativo"
        criterio = "Atividade vigorosa ≥ 5 dias/semana e ≥ 30 minutos por sessão."
    elif muito_ativo_b:
        classificacao = "Muito ativo"
        criterio = (
            "Atividade vigorosa ≥ 3 dias/semana e ≥ 20 minutos, somada a caminhada "
            "e/ou atividade moderada ≥ 5 dias/semana e ≥ 30 minutos."
        )
    elif ativo_a:
        classificacao = "Ativo"
        criterio = "Atividade vigorosa ≥ 3 dias/semana e ≥ 20 minutos por sessão."
    elif ativo_b:
        classificacao = "Ativo"
        criterio = "Caminhada ou atividade moderada ≥ 5 dias/semana e ≥ 30 minutos por sessão."
    elif ativo_c:
        classificacao = "Ativo"
        criterio = "Frequência somada ≥ 5 dias/semana e tempo total ≥ 150 minutos/semana."
    elif any(a.dias > 0 and a.minutos_sessao >= 10 for a in atividades):
        classificacao = "Irregularmente ativo"
        criterio = "Realiza atividade física, mas não alcança os critérios de Ativo ou Muito ativo."
    else:
        classificacao = "Inativo"
        criterio = "Não realizou atividade física por pelo menos 10 minutos contínuos na semana."

    reduzida = (
        "Suficientemente ativo"
        if classificacao in {"Ativo", "Muito ativo"}
        else "Sedentário ou insuficientemente ativo"
    )
    return ResultadoIPAQ(classificacao, reduzida, criterio, frequencia_somada, minutos_semana)


def relatorio_estresse(nome: str, r: ResultadoEstresse) -> str:
    efeito = (
        "O apoio social elevado pode minimizar os efeitos da sobrecarga."
        if r.media_apoio >= 2
        else "O apoio social baixo pode acentuar os efeitos da sobrecarga."
    )
    return (
        "RESULTADO - ESCALA DE ESTRESSE NO TRABALHO\n"
        f"Data: {datetime.now():%d/%m/%Y %H:%M}\n"
        f"Identificação: {nome.strip() or 'Não informada'}\n\n"
        f"Demanda: {r.media_demanda:.2f} - {r.demanda}\n"
        f"Controle: {r.media_controle:.2f} - {r.controle}\n"
        f"Apoio social: {r.media_apoio:.2f} - {r.apoio}\n\n"
        f"CLASSIFICAÇÃO: {r.quadrante.upper()}\n\n"
        f"Observação: {efeito}\n"
        "Esta classificação não constitui diagnóstico clínico.\n"
    )


def relatorio_ipaq(
    nome: str,
    caminhada: Atividade,
    moderada: Atividade,
    vigorosa: Atividade,
    r: ResultadoIPAQ,
) -> str:
    return (
        "RESULTADO - NÍVEL DE ATIVIDADE FÍSICA IPAQ\n"
        f"Data: {datetime.now():%d/%m/%Y %H:%M}\n"
        f"Identificação: {nome.strip() or 'Não informada'}\n\n"
        f"Caminhada: {caminhada.dias} dia(s), {caminhada.minutos_sessao} min/sessão\n"
        f"Moderada: {moderada.dias} dia(s), {moderada.minutos_sessao} min/sessão\n"
        f"Vigorosa: {vigorosa.dias} dia(s), {vigorosa.minutos_sessao} min/sessão\n\n"
        f"Frequência somada: {r.frequencia_somada} dia(s)/semana\n"
        f"Tempo total: {r.minutos_semana} min/semana\n\n"
        f"CLASSIFICAÇÃO IPAQ: {r.classificacao.upper()}\n"
        f"CLASSIFICAÇÃO REDUZIDA: {r.reduzida.upper()}\n"
        f"Critério: {r.criterio}\n\n"
        "Esta classificação não substitui avaliação profissional.\n"
    )


def _respostas_selectbox(
    questoes: tuple[str, ...],
    opcoes: tuple[str, ...],
    prefixo: str,
) -> list[int] | None:
    respostas = [
        st.selectbox(questao, opcoes, key=f"{prefixo}_{indice}")
        for indice, questao in enumerate(questoes)
    ]
    if any(resposta == opcoes[0] for resposta in respostas):
        return None
    return [opcoes.index(resposta) for resposta in respostas]


def _mostrar_estresse() -> None:
    st.subheader("Escala de Estresse no Trabalho")
    st.caption("Responda às 17 questões. As pontuações inversas são aplicadas automaticamente.")
    with st.form("form_estresse"):
        nome = st.text_input("Identificação (opcional)", key="nome_estresse")
        with st.expander("1. Demanda no trabalho", expanded=True):
            demanda = _respostas_selectbox(
                QUESTOES_DEMANDA,
                OPCOES_FREQUENCIA,
                "demanda",
            )
        with st.expander("2. Controle no trabalho", expanded=False):
            controle = _respostas_selectbox(
                QUESTOES_CONTROLE,
                OPCOES_FREQUENCIA,
                "controle",
            )
        with st.expander("3. Apoio social", expanded=False):
            apoio = _respostas_selectbox(
                QUESTOES_APOIO,
                OPCOES_APOIO,
                "apoio",
            )
        enviado = st.form_submit_button("Calcular classificação", use_container_width=True)

    if enviado:
        if demanda is None or controle is None or apoio is None:
            st.error("Responda todas as 17 questões antes de calcular.")
        else:
            resultado = calcular_estresse(demanda, controle, apoio)
            st.session_state["resultado_estresse"] = resultado
            st.session_state["relatorio_estresse"] = relatorio_estresse(nome, resultado)

    resultado = st.session_state.get("resultado_estresse")
    if resultado:
        st.markdown('<div class="resultado-titulo">Resultado</div>', unsafe_allow_html=True)
        st.success(f"Classificação: **{resultado.quadrante}**")
        coluna1, coluna2, coluna3 = st.columns(3)
        coluna1.metric("Demanda", f"{resultado.media_demanda:.2f}", resultado.demanda)
        coluna2.metric("Controle", f"{resultado.media_controle:.2f}", resultado.controle)
        coluna3.metric("Apoio social", f"{resultado.media_apoio:.2f}", resultado.apoio)
        st.download_button(
            "Baixar relatório",
            st.session_state["relatorio_estresse"],
            file_name="resultado_estresse.txt",
            mime="text/plain",
            use_container_width=True,
        )


def _campo_atividade(titulo: str, chave: str) -> Atividade:
    st.markdown(f"**{titulo}**")
    coluna1, coluna2 = st.columns(2)
    dias = coluna1.number_input(
        "Dias por semana",
        min_value=0,
        max_value=7,
        step=1,
        key=f"{chave}_dias",
    )
    minutos = coluna2.number_input(
        "Minutos por sessão",
        min_value=0,
        max_value=1440,
        step=1,
        key=f"{chave}_minutos",
    )
    return Atividade(int(dias), int(minutos))


def _mostrar_ipaq() -> None:
    st.subheader("Nível de Atividade Física - IPAQ")
    st.caption("Considere apenas atividades realizadas por pelo menos 10 minutos contínuos.")
    with st.form("form_ipaq"):
        nome = st.text_input("Identificação (opcional)", key="nome_ipaq")
        caminhada = _campo_atividade("Caminhada", "caminhada")
        st.divider()
        moderada = _campo_atividade("Atividade moderada", "moderada")
        st.divider()
        vigorosa = _campo_atividade("Atividade vigorosa", "vigorosa")
        enviado = st.form_submit_button("Calcular classificação", use_container_width=True)

    if enviado:
        try:
            resultado = calcular_ipaq(caminhada, moderada, vigorosa)
        except ValueError as erro:
            st.error(str(erro))
        else:
            st.session_state["resultado_ipaq"] = resultado
            st.session_state["relatorio_ipaq"] = relatorio_ipaq(
                nome,
                caminhada,
                moderada,
                vigorosa,
                resultado,
            )

    resultado = st.session_state.get("resultado_ipaq")
    if resultado:
        st.markdown('<div class="resultado-titulo">Resultado</div>', unsafe_allow_html=True)
        st.success(f"Classificação IPAQ: **{resultado.classificacao}**")
        coluna1, coluna2, coluna3 = st.columns(3)
        coluna1.metric("Grupo reduzido", resultado.reduzida)
        coluna2.metric("Tempo semanal", f"{resultado.minutos_semana} min")
        coluna3.metric("Frequência somada", f"{resultado.frequencia_somada} dias")
        st.info(resultado.criterio)
        st.download_button(
            "Baixar relatório",
            st.session_state["relatorio_ipaq"],
            file_name="resultado_ipaq.txt",
            mime="text/plain",
            use_container_width=True,
        )


def main() -> None:
    st.set_page_config(
        page_title="Saúde do Trabalhador",
        page_icon="🫀",
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
        .block-container { max-width: 1050px; padding-top: 2rem; padding-bottom: 4rem; }
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
        [data-testid="stForm"] {
            background: white;
            border: 1px solid #dde5ee;
            border-radius: 18px;
            padding: 1.25rem;
            box-shadow: 0 10px 28px rgba(23, 50, 77, 0.06);
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
    st.title("Saúde do Trabalhador")
    st.write("Classificação automatizada da Escala de Estresse no Trabalho e do IPAQ.")
    aba_estresse, aba_ipaq = st.tabs(("Estresse no trabalho", "Atividade física - IPAQ"))
    with aba_estresse:
        _mostrar_estresse()
    with aba_ipaq:
        _mostrar_ipaq()
    st.divider()
    st.caption(
        "Ferramenta de apoio à classificação dos protocolos. "
        "Não armazena respostas e não substitui avaliação profissional."
    )


if __name__ == "__main__":
    main()
