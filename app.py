"""Aplicação Streamlit para classificação de estresse no trabalho e IPAQ."""

from __future__ import annotations

from io import BytesIO
from dataclasses import dataclass
from datetime import datetime

import streamlit as st
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.graphics.shapes import Circle, Drawing, Line, Rect, String
from reportlab.platypus import (
    Paragraph,
    PageBreak,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


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


def _grafico_estresse(r: ResultadoEstresse) -> Drawing:
    """Cria o gráfico individual de demanda, controle e apoio social."""
    desenho = Drawing(480, 270)
    x0, y0, largura, altura = 48, 55, 300, 180
    corte_x = x0 + largura / 3
    corte_y = y0 + altura / 3

    # Quadrantes do modelo demanda-controle, com corte em 2,0.
    desenho.add(Rect(x0, y0, corte_x - x0, corte_y - y0, fillColor=colors.HexColor("#F4E8B8"), strokeColor=None))
    desenho.add(Rect(corte_x, y0, x0 + largura - corte_x, corte_y - y0, fillColor=colors.HexColor("#DCEFE4"), strokeColor=None))
    desenho.add(Rect(x0, corte_y, corte_x - x0, y0 + altura - corte_y, fillColor=colors.HexColor("#F3D5D1"), strokeColor=None))
    desenho.add(Rect(corte_x, corte_y, x0 + largura - corte_x, y0 + altura - corte_y, fillColor=colors.HexColor("#D9E7F4"), strokeColor=None))

    desenho.add(String(x0 + 5, y0 + 7, "Trabalho passivo", fontName="Helvetica-Bold", fontSize=7, fillColor=colors.HexColor("#263B50")))
    desenho.add(String(corte_x + 7, y0 + 7, "Baixo desgaste", fontName="Helvetica-Bold", fontSize=7, fillColor=colors.HexColor("#263B50")))
    desenho.add(String(x0 + 5, corte_y + 7, "Alto desgaste", fontName="Helvetica-Bold", fontSize=7, fillColor=colors.HexColor("#263B50")))
    desenho.add(String(corte_x + 7, corte_y + 7, "Trabalho ativo", fontName="Helvetica-Bold", fontSize=7, fillColor=colors.HexColor("#263B50")))

    desenho.add(Line(x0, y0, x0 + largura, y0, strokeColor=colors.HexColor("#526779"), strokeWidth=1))
    desenho.add(Line(x0, y0, x0, y0 + altura, strokeColor=colors.HexColor("#526779"), strokeWidth=1))
    desenho.add(Line(corte_x, y0, corte_x, y0 + altura, strokeColor=colors.HexColor("#8DA0AF"), strokeWidth=0.8))
    desenho.add(Line(x0, corte_y, x0 + largura, corte_y, strokeColor=colors.HexColor("#8DA0AF"), strokeWidth=0.8))

    for valor in range(1, 5):
        px = x0 + ((valor - 1) / 3) * largura
        py = y0 + ((valor - 1) / 3) * altura
        desenho.add(Line(px, y0 - 3, px, y0 + 3, strokeColor=colors.HexColor("#526779")))
        desenho.add(String(px - 2, y0 - 15, str(valor), fontSize=7, fillColor=colors.HexColor("#526779")))
        desenho.add(Line(x0 - 3, py, x0 + 3, py, strokeColor=colors.HexColor("#526779")))
        desenho.add(String(x0 - 17, py - 2, str(valor), fontSize=7, fillColor=colors.HexColor("#526779")))

    ponto_x = x0 + ((r.media_controle - 1) / 3) * largura
    ponto_y = y0 + ((r.media_demanda - 1) / 3) * altura
    desenho.add(Circle(ponto_x, ponto_y, 6, fillColor=colors.HexColor("#17324D"), strokeColor=colors.white, strokeWidth=1.5))
    desenho.add(String(ponto_x + 9, ponto_y + 2, "Participante", fontName="Helvetica-Bold", fontSize=7, fillColor=colors.HexColor("#17324D")))
    desenho.add(String(x0 + 105, y0 - 32, "CONTROLE", fontName="Helvetica-Bold", fontSize=9, fillColor=colors.HexColor("#17324D")))
    desenho.add(String(5, y0 + 80, "DEMANDA", fontName="Helvetica-Bold", fontSize=9, fillColor=colors.HexColor("#17324D"), angle=90))

    # Barra individual de apoio social.
    bx, by, bw, bh = 392, 70, 38, 165
    preenchimento = ((r.media_apoio - 1) / 3) * bh
    desenho.add(String(372, 247, "APOIO SOCIAL", fontName="Helvetica-Bold", fontSize=9, fillColor=colors.HexColor("#17324D")))
    desenho.add(Rect(bx, by, bw, bh, fillColor=colors.HexColor("#EAF1F6"), strokeColor=colors.HexColor("#8DA0AF")))
    desenho.add(Rect(bx, by, bw, preenchimento, fillColor=colors.HexColor("#19705A"), strokeColor=None))
    corte_apoio = by + bh / 3
    desenho.add(Line(bx - 4, corte_apoio, bx + bw + 4, corte_apoio, strokeColor=colors.HexColor("#C54B3C"), strokeWidth=1.2))
    desenho.add(String(bx + 11, by - 14, "1", fontSize=7))
    desenho.add(String(bx + 11, by + bh + 4, "4", fontSize=7))
    desenho.add(String(370, 45, f"Média: {r.media_apoio:.2f}", fontName="Helvetica-Bold", fontSize=9, fillColor=colors.HexColor("#17324D")))
    desenho.add(String(367, 31, r.apoio, fontSize=7.5, fillColor=colors.HexColor("#526779")))
    desenho.add(String(47, 253, "Quadrante demanda-controle (corte = 2,0)", fontName="Helvetica-Bold", fontSize=10, fillColor=colors.HexColor("#17324D")))
    return desenho


def relatorio_estresse_pdf(nome: str, r: ResultadoEstresse) -> bytes:
    """Gera o relatório individual de estresse com gráfico em PDF."""
    buffer = BytesIO()
    documento = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.7 * cm,
        leftMargin=1.7 * cm,
        topMargin=1.7 * cm,
        bottomMargin=1.7 * cm,
        title="Resultado da Escala de Estresse no Trabalho",
        author="Calculadoras de Saúde do Trabalhador",
    )
    estilos = getSampleStyleSheet()
    titulo = ParagraphStyle(
        "TituloEstresse",
        parent=estilos["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#17324D"),
        alignment=TA_CENTER,
        spaceAfter=8,
    )
    corpo = ParagraphStyle(
        "CorpoEstresse",
        parent=estilos["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#263B50"),
    )
    classificacao = ParagraphStyle(
        "ClassificacaoEstresse",
        parent=corpo,
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        alignment=TA_CENTER,
        textColor=colors.white,
    )
    efeito = (
        "O apoio social elevado pode minimizar os efeitos da sobrecarga."
        if r.media_apoio >= 2
        else "O apoio social baixo pode acentuar os efeitos da sobrecarga."
    )
    identificacao = nome.strip() or "Não informada"
    historia = [
        Paragraph("Resultado - Escala de Estresse no Trabalho", titulo),
        Spacer(1, 8),
        Table(
            [
                ["Data", f"{datetime.now():%d/%m/%Y %H:%M}"],
                ["Identificação", identificacao],
            ],
            colWidths=[3.2 * cm, 13.2 * cm],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EAF1F6")),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#263B50")),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD8E3")),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            ),
        ),
        Spacer(1, 13),
        Table(
            [
                ["Domínio", "Média", "Resultado"],
                ["Demanda", f"{r.media_demanda:.2f}", r.demanda],
                ["Controle", f"{r.media_controle:.2f}", r.controle],
                ["Apoio social", f"{r.media_apoio:.2f}", r.apoio],
            ],
            colWidths=[6.2 * cm, 3.2 * cm, 7 * cm],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17324D")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("ALIGN", (1, 1), (1, -1), "CENTER"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD8E3")),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            ),
        ),
        Spacer(1, 14),
        Table(
            [[Paragraph(f"CLASSIFICAÇÃO: {r.quadrante.upper()}", classificacao)]],
            colWidths=[16.4 * cm],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#19705A")),
                    ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#145846")),
                    ("TOPPADDING", (0, 0), (-1, -1), 11),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 11),
                ]
            ),
        ),
        Spacer(1, 12),
        _grafico_estresse(r),
        Spacer(1, 5),
        Paragraph(f"<b>Interpretação do apoio social:</b> {efeito}", corpo),
        Paragraph(
            "Resultado calculado conforme a pontuação fornecida para a Escala de Estresse "
            "no Trabalho. Esta classificação não constitui diagnóstico clínico.",
            corpo,
        ),
    ]
    documento.build(historia)
    return buffer.getvalue()


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


def relatorio_ipaq_pdf(
    nome: str,
    caminhada: Atividade,
    moderada: Atividade,
    vigorosa: Atividade,
    r: ResultadoIPAQ,
) -> bytes:
    """Gera um relatório IPAQ em PDF pronto para download."""
    buffer = BytesIO()
    documento = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.7 * cm,
        leftMargin=1.7 * cm,
        topMargin=1.7 * cm,
        bottomMargin=1.7 * cm,
        title="Resultado IPAQ",
        author="Calculadoras de Saúde do Trabalhador",
    )

    estilos = getSampleStyleSheet()
    titulo = ParagraphStyle(
        "TituloIPAQ",
        parent=estilos["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#17324D"),
        alignment=TA_CENTER,
        spaceAfter=8,
    )
    subtitulo = ParagraphStyle(
        "SubtituloIPAQ",
        parent=estilos["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#17324D"),
        spaceBefore=12,
        spaceAfter=7,
    )
    corpo = ParagraphStyle(
        "CorpoIPAQ",
        parent=estilos["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#263B50"),
    )
    classificacao = ParagraphStyle(
        "ClassificacaoIPAQ",
        parent=corpo,
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        alignment=TA_CENTER,
        textColor=colors.white,
    )

    identificacao = nome.strip() or "Não informada"
    historia = [
        Paragraph("Resultado - Nível de Atividade Física", titulo),
        Paragraph("Questionário Internacional de Atividade Física - IPAQ", corpo),
        Spacer(1, 10),
        Table(
            [
                ["Data", f"{datetime.now():%d/%m/%Y %H:%M}"],
                ["Identificação", identificacao],
            ],
            colWidths=[3.2 * cm, 13.2 * cm],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EAF1F6")),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#263B50")),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD8E3")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            ),
        ),
        Paragraph("Atividades informadas", subtitulo),
        Table(
            [
                ["Atividade", "Dias/semana", "Min/sessão", "Min/semana"],
                ["Caminhada", caminhada.dias, caminhada.minutos_sessao, caminhada.minutos_semana],
                ["Moderada", moderada.dias, moderada.minutos_sessao, moderada.minutos_semana],
                ["Vigorosa", vigorosa.dias, vigorosa.minutos_sessao, vigorosa.minutos_semana],
                ["Total", r.frequencia_somada, "-", r.minutos_semana],
            ],
            colWidths=[6.1 * cm, 3.4 * cm, 3.4 * cm, 3.5 * cm],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17324D")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#EAF1F6")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("ALIGN", (1, 1), (-1, -1), "CENTER"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD8E3")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            ),
        ),
        Spacer(1, 12),
        _grafico_ipaq(caminhada, moderada, vigorosa),
        Spacer(1, 16),
        Table(
            [[Paragraph(f"CLASSIFICAÇÃO IPAQ: {r.classificacao.upper()}", classificacao)]],
            colWidths=[16.4 * cm],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#19705A")),
                    ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#145846")),
                    ("TOPPADDING", (0, 0), (-1, -1), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ]
            ),
        ),
        Spacer(1, 10),
        Paragraph(f"<b>Classificação reduzida:</b> {r.reduzida}", corpo),
        Paragraph(f"<b>Critério alcançado:</b> {r.criterio}", corpo),
        Spacer(1, 14),
        Paragraph(
            "Resultado calculado conforme a Classificação do Nível de Atividade Física "
            "IPAQ (CELAFISCS, 2012). Esta ferramenta não substitui avaliação profissional.",
            corpo,
        ),
    ]

    documento.build(historia)
    return buffer.getvalue()


def _grafico_ipaq(
    caminhada: Atividade,
    moderada: Atividade,
    vigorosa: Atividade,
) -> Drawing:
    """Cria gráficos individuais de frequência e duração semanal do IPAQ."""
    desenho = Drawing(480, 245)
    atividades = (caminhada, moderada, vigorosa)
    rotulos = ("Caminhada", "Moderada", "Vigorosa")
    cores = (
        colors.HexColor("#4C90C0"),
        colors.HexColor("#44A177"),
        colors.HexColor("#D97A45"),
    )

    def painel_barras(
        x0: float,
        titulo: str,
        valores: tuple[int, int, int],
        maximo: float,
        unidade: str,
        referencia: float | None = None,
    ) -> None:
        y0, largura, altura = 47, 190, 150
        desenho.add(String(x0, 222, titulo, fontName="Helvetica-Bold", fontSize=10, fillColor=colors.HexColor("#17324D")))
        desenho.add(Line(x0, y0, x0 + largura, y0, strokeColor=colors.HexColor("#526779")))
        desenho.add(Line(x0, y0, x0, y0 + altura, strokeColor=colors.HexColor("#526779")))
        if referencia is not None and referencia <= maximo:
            ry = y0 + (referencia / maximo) * altura
            desenho.add(Line(x0, ry, x0 + largura, ry, strokeColor=colors.HexColor("#C54B3C"), strokeWidth=1, strokeDashArray=[3, 2]))
            desenho.add(String(x0 + 92, ry + 4, f"Referência: {int(referencia)} {unidade}", fontSize=6.5, fillColor=colors.HexColor("#C54B3C")))
        barra_largura = 38
        espaco = 20
        for indice, (rotulo, valor, cor) in enumerate(zip(rotulos, valores, cores)):
            bx = x0 + 15 + indice * (barra_largura + espaco)
            bh = 0 if maximo == 0 else (valor / maximo) * altura
            desenho.add(Rect(bx, y0, barra_largura, bh, fillColor=cor, strokeColor=None))
            desenho.add(String(bx + 8, y0 + bh + 5, str(valor), fontName="Helvetica-Bold", fontSize=7, fillColor=colors.HexColor("#263B50")))
            desenho.add(String(bx - 2, y0 - 14, rotulo, fontSize=6.5, fillColor=colors.HexColor("#526779")))
        desenho.add(String(x0, 23, unidade, fontSize=7, fillColor=colors.HexColor("#526779")))

    frequencias = tuple(a.dias for a in atividades)
    minutos = tuple(a.minutos_semana for a in atividades)
    max_minutos = max(150, max(minutos, default=0)) * 1.12
    painel_barras(30, "Frequência semanal", frequencias, 7, "dias/semana")
    painel_barras(
        270,
        f"Duração semanal - total: {sum(minutos)} min",
        minutos,
        max_minutos,
        "minutos/semana",
    )
    return desenho


def _grafico_ipaq_coletivo(participantes: list[dict[str, object]]) -> Drawing:
    """Compara frequência e duração dos participantes em um único gráfico."""
    desenho = Drawing(740, 430)
    cores = (
        colors.HexColor("#4C90C0"),
        colors.HexColor("#44A177"),
        colors.HexColor("#D97A45"),
    )
    atividades = ("Caminhada", "Moderada", "Vigorosa")
    n = max(1, len(participantes))
    x0, largura = 58, 650
    largura_grupo = largura / n

    desenho.add(
        String(
            58,
            408,
            "Frequência semanal por atividade",
            fontName="Helvetica-Bold",
            fontSize=12,
            fillColor=colors.HexColor("#17324D"),
        )
    )
    base_frequencia, altura_frequencia = 248, 125
    desenho.add(Line(x0, base_frequencia, x0 + largura, base_frequencia, strokeColor=colors.HexColor("#526779")))
    desenho.add(Line(x0, base_frequencia, x0, base_frequencia + altura_frequencia, strokeColor=colors.HexColor("#526779")))
    for valor in (0, 2, 4, 6, 7):
        y = base_frequencia + (valor / 7) * altura_frequencia
        desenho.add(Line(x0 - 3, y, x0 + largura, y, strokeColor=colors.HexColor("#DDE5EE"), strokeWidth=0.4))
        desenho.add(String(x0 - 18, y - 2, str(valor), fontSize=7, fillColor=colors.HexColor("#526779")))

    barra = min(20, max(8, (largura_grupo - 18) / 3))
    for indice, participante in enumerate(participantes):
        centro = x0 + indice * largura_grupo + largura_grupo / 2
        frequencias = (
            int(participante["caminhada_dias"]),
            int(participante["moderada_dias"]),
            int(participante["vigorosa_dias"]),
        )
        inicio = centro - (3 * barra + 4) / 2
        for atividade_indice, (valor, cor) in enumerate(zip(frequencias, cores)):
            bx = inicio + atividade_indice * (barra + 2)
            bh = (valor / 7) * altura_frequencia
            desenho.add(Rect(bx, base_frequencia, barra, bh, fillColor=cor, strokeColor=None))
            desenho.add(String(bx + barra / 2 - 2, base_frequencia + bh + 4, str(valor), fontSize=6.5))
        identificacao = str(participante["identificacao"])[:14]
        desenho.add(String(centro - min(30, len(identificacao) * 2.7), base_frequencia - 14, identificacao, fontSize=6.5))

    totais = [int(p["minutos_semana"]) for p in participantes]
    maximo_minutos = max(150, max(totais, default=0)) * 1.12
    base_duracao, altura_duracao = 45, 135
    desenho.add(
        String(
            58,
            215,
            "Duração semanal por participante",
            fontName="Helvetica-Bold",
            fontSize=12,
            fillColor=colors.HexColor("#17324D"),
        )
    )
    desenho.add(Line(x0, base_duracao, x0 + largura, base_duracao, strokeColor=colors.HexColor("#526779")))
    desenho.add(Line(x0, base_duracao, x0, base_duracao + altura_duracao, strokeColor=colors.HexColor("#526779")))
    referencia_y = base_duracao + (150 / maximo_minutos) * altura_duracao
    desenho.add(
        Line(
            x0,
            referencia_y,
            x0 + largura,
            referencia_y,
            strokeColor=colors.HexColor("#C54B3C"),
            strokeWidth=1,
            strokeDashArray=[4, 3],
        )
    )

    largura_empilhada = min(42, max(18, largura_grupo * 0.5))
    for indice, participante in enumerate(participantes):
        centro = x0 + indice * largura_grupo + largura_grupo / 2
        bx = centro - largura_empilhada / 2
        minutos = (
            int(participante["caminhada_dias"]) * int(participante["caminhada_minutos"]),
            int(participante["moderada_dias"]) * int(participante["moderada_minutos"]),
            int(participante["vigorosa_dias"]) * int(participante["vigorosa_minutos"]),
        )
        acumulado = base_duracao
        for valor, cor in zip(minutos, cores):
            bh = (valor / maximo_minutos) * altura_duracao
            desenho.add(Rect(bx, acumulado, largura_empilhada, bh, fillColor=cor, strokeColor=colors.white, strokeWidth=0.4))
            acumulado += bh
        total = sum(minutos)
        desenho.add(String(centro - 8, acumulado + 5, str(total), fontName="Helvetica-Bold", fontSize=7))
        identificacao = str(participante["identificacao"])[:14]
        desenho.add(String(centro - min(30, len(identificacao) * 2.7), base_duracao - 14, identificacao, fontSize=6.5))

    legenda_x = 470
    for indice, (atividade, cor) in enumerate(zip(atividades, cores)):
        lx = legenda_x + indice * 82
        desenho.add(Rect(lx, 404, 9, 9, fillColor=cor, strokeColor=None))
        desenho.add(String(lx + 13, 405, atividade, fontSize=7, fillColor=colors.HexColor("#526779")))
    desenho.add(String(12, 300, "Dias/semana", fontSize=7, fillColor=colors.HexColor("#526779"), angle=90))
    desenho.add(String(12, 92, "Minutos/semana", fontSize=7, fillColor=colors.HexColor("#526779"), angle=90))
    return desenho


def relatorio_ipaq_coletivo_pdf(participantes: list[dict[str, object]]) -> bytes:
    """Gera tabela e gráficos consolidados para até seis participantes."""
    buffer = BytesIO()
    documento = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=1.2 * cm,
        leftMargin=1.2 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
        title="Tabela coletiva de resultados IPAQ",
        author="Calculadoras de Saúde do Trabalhador",
    )
    estilos = getSampleStyleSheet()
    titulo = ParagraphStyle(
        "TituloIPAQColetivo",
        parent=estilos["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#17324D"),
        alignment=TA_CENTER,
        spaceAfter=8,
    )
    corpo = ParagraphStyle(
        "CorpoIPAQColetivo",
        parent=estilos["BodyText"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#263B50"),
    )
    celula = ParagraphStyle(
        "CelulaIPAQColetivo",
        parent=corpo,
        fontSize=7,
        leading=8.5,
    )

    dados = [
        ["Indivíduo", "Caminhada", "", "Moderada", "", "Vigorosa", "", "Totais", "", "Classificação", "Grupo reduzido"],
        ["", "F", "D", "F", "D", "F", "D", "F", "Min", "", ""],
    ]
    for participante in participantes:
        dados.append(
            [
                Paragraph(str(participante["identificacao"]), celula),
                participante["caminhada_dias"],
                participante["caminhada_minutos"],
                participante["moderada_dias"],
                participante["moderada_minutos"],
                participante["vigorosa_dias"],
                participante["vigorosa_minutos"],
                participante["frequencia_somada"],
                participante["minutos_semana"],
                Paragraph(str(participante["classificacao"]), celula),
                Paragraph(str(participante["reduzida"]), celula),
            ]
        )

    tabela = Table(
        dados,
        colWidths=[
            3.2 * cm,
            1.2 * cm,
            1.4 * cm,
            1.2 * cm,
            1.4 * cm,
            1.2 * cm,
            1.4 * cm,
            1.2 * cm,
            1.5 * cm,
            3.0 * cm,
            4.3 * cm,
        ],
        repeatRows=2,
        style=TableStyle(
            [
                ("SPAN", (0, 0), (0, 1)),
                ("SPAN", (1, 0), (2, 0)),
                ("SPAN", (3, 0), (4, 0)),
                ("SPAN", (5, 0), (6, 0)),
                ("SPAN", (7, 0), (8, 0)),
                ("SPAN", (9, 0), (9, 1)),
                ("SPAN", (10, 0), (10, 1)),
                ("BACKGROUND", (0, 0), (-1, 1), colors.HexColor("#17324D")),
                ("TEXTCOLOR", (0, 0), (-1, 1), colors.white),
                ("FONTNAME", (0, 0), (-1, 1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 1), 7.5),
                ("ALIGN", (1, 0), (8, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD8E3")),
                ("ROWBACKGROUNDS", (0, 2), (-1, -1), [colors.white, colors.HexColor("#F4F7F9")]),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        ),
    )

    historia = [
        Paragraph("Resultados coletivos - IPAQ", titulo),
        Paragraph(
            f"Data: {datetime.now():%d/%m/%Y %H:%M} | Participantes cadastrados: {len(participantes)}",
            corpo,
        ),
        Spacer(1, 12),
        tabela,
        Spacer(1, 10),
        Paragraph(
            "<b>Legenda:</b> F = frequência em dias/semana; D = duração em minutos/sessão. "
            "As classificações são calculadas individualmente conforme o manual IPAQ.",
            corpo,
        ),
        PageBreak(),
        Paragraph("Gráficos comparativos", titulo),
        _grafico_ipaq_coletivo(participantes),
        Paragraph(
            "A linha de 150 minutos representa apenas o critério baseado na soma das atividades; "
            "os demais critérios de Ativo e Muito ativo também consideram frequência, intensidade e duração por sessão.",
            corpo,
        ),
        Paragraph(
            "Relatório coletivo de apoio à análise. Não substitui avaliação profissional.",
            corpo,
        ),
    ]
    documento.build(historia)
    return buffer.getvalue()


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
            st.session_state["relatorio_estresse_pdf"] = relatorio_estresse_pdf(nome, resultado)

    resultado = st.session_state.get("resultado_estresse")
    if resultado:
        st.markdown('<div class="resultado-titulo">Resultado</div>', unsafe_allow_html=True)
        st.success(f"Classificação: **{resultado.quadrante}**")
        coluna1, coluna2, coluna3 = st.columns(3)
        coluna1.metric("Demanda", f"{resultado.media_demanda:.2f}", resultado.demanda)
        coluna2.metric("Controle", f"{resultado.media_controle:.2f}", resultado.controle)
        coluna3.metric("Apoio social", f"{resultado.media_apoio:.2f}", resultado.apoio)
        st.download_button(
            "Baixar resultado em PDF",
            st.session_state["relatorio_estresse_pdf"],
            file_name=f"resultado_estresse_{datetime.now():%Y%m%d}.pdf",
            mime="application/pdf",
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
    st.caption(
        "Cadastre até seis indivíduos. Considere apenas atividades realizadas "
        "por pelo menos 10 minutos contínuos."
    )
    participantes = st.session_state.setdefault("participantes_ipaq", [])
    st.progress(len(participantes) / 6, text=f"Participantes cadastrados: {len(participantes)}/6")

    with st.form("form_ipaq"):
        nome = st.text_input(
            "Identificação",
            key="nome_ipaq",
            placeholder=f"Indivíduo {len(participantes) + 1}",
        )
        caminhada = _campo_atividade("Caminhada", "caminhada")
        st.divider()
        moderada = _campo_atividade("Atividade moderada", "moderada")
        st.divider()
        vigorosa = _campo_atividade("Atividade vigorosa", "vigorosa")
        enviado = st.form_submit_button(
            "Adicionar indivíduo à tabela",
            use_container_width=True,
            disabled=len(participantes) >= 6,
        )

    if enviado:
        if len(participantes) >= 6:
            st.warning("A tabela já contém os seis indivíduos previstos.")
        else:
            try:
                resultado = calcular_ipaq(caminhada, moderada, vigorosa)
            except ValueError as erro:
                st.error(str(erro))
            else:
                identificacao = nome.strip() or f"Indivíduo {len(participantes) + 1}"
                participantes.append(
                    {
                        "identificacao": identificacao,
                        "caminhada_dias": caminhada.dias,
                        "caminhada_minutos": caminhada.minutos_sessao,
                        "moderada_dias": moderada.dias,
                        "moderada_minutos": moderada.minutos_sessao,
                        "vigorosa_dias": vigorosa.dias,
                        "vigorosa_minutos": vigorosa.minutos_sessao,
                        "frequencia_somada": resultado.frequencia_somada,
                        "minutos_semana": resultado.minutos_semana,
                        "classificacao": resultado.classificacao,
                        "reduzida": resultado.reduzida,
                        "criterio": resultado.criterio,
                    }
                )
                st.success(
                    f"{identificacao} adicionado: {resultado.classificacao}. "
                    "Altere os campos para cadastrar o próximo indivíduo."
                )

    if participantes:
        st.markdown('<div class="resultado-titulo">Tabela coletiva</div>', unsafe_allow_html=True)
        linhas_tabela = [
            {
                "Indivíduo": p["identificacao"],
                "Caminhada F": p["caminhada_dias"],
                "Caminhada D": p["caminhada_minutos"],
                "Moderada F": p["moderada_dias"],
                "Moderada D": p["moderada_minutos"],
                "Vigorosa F": p["vigorosa_dias"],
                "Vigorosa D": p["vigorosa_minutos"],
                "Total (min/sem)": p["minutos_semana"],
                "Classificação": p["classificacao"],
            }
            for p in participantes
        ]
        st.dataframe(linhas_tabela, use_container_width=True, hide_index=True)

        frequencia_grafico = []
        duracao_grafico = []
        for participante in participantes:
            for atividade, prefixo in (
                ("Caminhada", "caminhada"),
                ("Moderada", "moderada"),
                ("Vigorosa", "vigorosa"),
            ):
                frequencia_grafico.append(
                    {
                        "Indivíduo": participante["identificacao"],
                        "Atividade": atividade,
                        "Dias": participante[f"{prefixo}_dias"],
                    }
                )
                duracao_grafico.append(
                    {
                        "Indivíduo": participante["identificacao"],
                        "Atividade": atividade,
                        "Minutos": (
                            int(participante[f"{prefixo}_dias"])
                            * int(participante[f"{prefixo}_minutos"])
                        ),
                    }
                )

        coluna_grafico1, coluna_grafico2 = st.columns(2)
        with coluna_grafico1:
            st.markdown("**Frequência semanal**")
            st.vega_lite_chart(
                frequencia_grafico,
                {
                    "mark": "bar",
                    "encoding": {
                        "x": {"field": "Indivíduo", "type": "nominal", "title": None},
                        "xOffset": {"field": "Atividade"},
                        "y": {
                            "field": "Dias",
                            "type": "quantitative",
                            "title": "Dias/semana",
                            "scale": {"domain": [0, 7]},
                        },
                        "color": {"field": "Atividade", "type": "nominal"},
                        "tooltip": [
                            {"field": "Indivíduo"},
                            {"field": "Atividade"},
                            {"field": "Dias"},
                        ],
                    },
                },
                use_container_width=True,
            )
        with coluna_grafico2:
            st.markdown("**Duração semanal**")
            st.vega_lite_chart(
                duracao_grafico,
                {
                    "mark": "bar",
                    "encoding": {
                        "x": {"field": "Indivíduo", "type": "nominal", "title": None},
                        "xOffset": {"field": "Atividade"},
                        "y": {
                            "field": "Minutos",
                            "type": "quantitative",
                            "title": "Minutos/semana",
                        },
                        "color": {"field": "Atividade", "type": "nominal"},
                        "tooltip": [
                            {"field": "Indivíduo"},
                            {"field": "Atividade"},
                            {"field": "Minutos"},
                        ],
                    },
                },
                use_container_width=True,
            )

        coluna_acao1, coluna_acao2 = st.columns(2)
        if coluna_acao1.button(
            "Remover último indivíduo",
            use_container_width=True,
        ):
            removido = participantes.pop()
            st.toast(f"{removido['identificacao']} removido.")
        if coluna_acao2.button(
            "Limpar tabela",
            use_container_width=True,
        ):
            participantes.clear()
            st.toast("Tabela IPAQ limpa.")

        st.download_button(
            "Baixar tabela e gráficos em PDF",
            relatorio_ipaq_coletivo_pdf(participantes),
            file_name=f"resultados_coletivos_ipaq_{datetime.now():%Y%m%d}.pdf",
            mime="application/pdf",
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
