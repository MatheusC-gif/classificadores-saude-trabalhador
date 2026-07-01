"""Classificador da Escala de Estresse no Trabalho.

Aplicativo local baseado nas regras do documento
"Pontuação Escala de Estresse". Não realiza diagnóstico clínico.
"""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


RESPOSTAS_FREQUENCIA = (
    "Nunca ou quase nunca",
    "Raramente",
    "Às vezes",
    "Frequentemente",
)

RESPOSTAS_APOIO = (
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


@dataclass(frozen=True)
class Resultado:
    media_demanda: float
    media_controle: float
    media_apoio: float
    demanda: str
    controle: str
    apoio: str
    quadrante: str


def pontuar(respostas: list[int], invertidas: set[int] | None = None) -> list[int]:
    """Converte respostas de 1 a 4 e inverte os índices indicados."""
    invertidas = invertidas or set()
    if not respostas or any(valor not in (1, 2, 3, 4) for valor in respostas):
        raise ValueError("Todas as respostas devem possuir valores entre 1 e 4.")
    return [5 - valor if indice in invertidas else valor for indice, valor in enumerate(respostas)]


def calcular_resultado(
    demanda: list[int],
    controle: list[int],
    apoio: list[int],
) -> Resultado:
    if len(demanda) != 5 or len(controle) != 6 or len(apoio) != 6:
        raise ValueError("São necessárias 5 respostas de demanda, 6 de controle e 6 de apoio.")

    # Índice 3 = quarta questão. Nessas duas dimensões, ela tem pontuação inversa.
    pontos_demanda = pontuar(demanda, {3})
    pontos_controle = pontuar(controle, {3})
    pontos_apoio = pontuar(apoio)

    media_demanda = sum(pontos_demanda) / 5
    media_controle = sum(pontos_controle) / 6
    media_apoio = sum(pontos_apoio) / 6

    demanda_alta = media_demanda >= 2
    controle_alto = media_controle >= 2

    if demanda_alta and not controle_alto:
        quadrante = "ALTO DESGASTE"
    elif demanda_alta and controle_alto:
        quadrante = "TRABALHO ATIVO"
    elif not demanda_alta and not controle_alto:
        quadrante = "TRABALHO PASSIVO"
    else:
        quadrante = "BAIXO DESGASTE"

    return Resultado(
        media_demanda=media_demanda,
        media_controle=media_controle,
        media_apoio=media_apoio,
        demanda="Alta demanda" if demanda_alta else "Baixa demanda",
        controle="Alto controle" if controle_alto else "Baixo controle",
        apoio="Alto apoio social" if media_apoio >= 2 else "Baixo apoio social",
        quadrante=quadrante,
    )


def montar_relatorio(nome: str, resultado: Resultado) -> str:
    identificacao = nome.strip() or "Não informada"
    efeito_apoio = (
        "O apoio social elevado pode minimizar os efeitos da sobrecarga de trabalho."
        if resultado.media_apoio >= 2
        else "O apoio social baixo pode acentuar os efeitos da sobrecarga de trabalho."
    )
    return (
        "RESULTADO - ESCALA DE ESTRESSE NO TRABALHO\n"
        f"Data: {datetime.now():%d/%m/%Y %H:%M}\n"
        f"Identificação: {identificacao}\n\n"
        f"Demanda: {resultado.media_demanda:.2f} - {resultado.demanda}\n"
        f"Controle: {resultado.media_controle:.2f} - {resultado.controle}\n"
        f"Apoio social: {resultado.media_apoio:.2f} - {resultado.apoio}\n\n"
        f"CLASSIFICAÇÃO: {resultado.quadrante}\n\n"
        f"Observação: {efeito_apoio}\n\n"
        "Critério: média menor que 2 = baixa; média maior ou igual a 2 = alta.\n"
        "Este resultado é uma classificação da escala e não constitui diagnóstico clínico.\n"
    )


class Aplicativo(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Escala de Estresse no Trabalho")
        self.geometry("920x720")
        self.minsize(760, 580)
        self.resultado_atual: Resultado | None = None
        self.variaveis: dict[str, list[tk.StringVar]] = {
            "demanda": [],
            "controle": [],
            "apoio": [],
        }
        self._configurar_estilo()
        self._montar_interface()

    def _configurar_estilo(self) -> None:
        estilo = ttk.Style(self)
        estilo.configure("Titulo.TLabel", font=("Segoe UI", 18, "bold"))
        estilo.configure("Secao.TLabel", font=("Segoe UI", 12, "bold"))
        estilo.configure("Resultado.TLabel", font=("Segoe UI", 15, "bold"))
        estilo.configure("TButton", padding=(12, 7))

    def _montar_interface(self) -> None:
        topo = ttk.Frame(self, padding=(18, 14))
        topo.pack(fill="x")
        ttk.Label(topo, text="Escala de Estresse no Trabalho", style="Titulo.TLabel").pack(anchor="w")
        ttk.Label(
            topo,
            text="Preencha as 17 respostas. A pontuação e as inversões são calculadas automaticamente.",
        ).pack(anchor="w", pady=(4, 0))

        identificacao = ttk.Frame(topo)
        identificacao.pack(fill="x", pady=(12, 0))
        ttk.Label(identificacao, text="Identificação (opcional):").pack(side="left")
        self.nome = ttk.Entry(identificacao)
        self.nome.pack(side="left", fill="x", expand=True, padx=(8, 0))

        corpo = ttk.Frame(self)
        corpo.pack(fill="both", expand=True, padx=18)

        canvas = tk.Canvas(corpo, highlightthickness=0)
        barra = ttk.Scrollbar(corpo, orient="vertical", command=canvas.yview)
        self.formulario = ttk.Frame(canvas, padding=(0, 4, 12, 12))
        janela = canvas.create_window((0, 0), window=self.formulario, anchor="nw")
        canvas.configure(yscrollcommand=barra.set)
        canvas.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")

        self.formulario.bind(
            "<Configure>",
            lambda _evento: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.bind(
            "<Configure>",
            lambda evento: canvas.itemconfigure(janela, width=evento.width),
        )
        canvas.bind_all(
            "<MouseWheel>",
            lambda evento: canvas.yview_scroll(int(-evento.delta / 120), "units"),
        )

        self._adicionar_secao("Demanda no trabalho", "demanda", QUESTOES_DEMANDA, RESPOSTAS_FREQUENCIA)
        self._adicionar_secao("Controle no trabalho", "controle", QUESTOES_CONTROLE, RESPOSTAS_FREQUENCIA)
        self._adicionar_secao("Apoio social", "apoio", QUESTOES_APOIO, RESPOSTAS_APOIO)

        rodape = ttk.Frame(self, padding=18)
        rodape.pack(fill="x")
        ttk.Button(rodape, text="Calcular classificação", command=self._calcular).pack(side="left")
        ttk.Button(rodape, text="Limpar", command=self._limpar).pack(side="left", padx=8)
        self.botao_salvar = ttk.Button(
            rodape,
            text="Salvar resultado",
            command=self._salvar,
            state="disabled",
        )
        self.botao_salvar.pack(side="left")
        self.resumo = ttk.Label(rodape, text="Aguardando preenchimento.", style="Resultado.TLabel")
        self.resumo.pack(side="right")

    def _adicionar_secao(
        self,
        titulo: str,
        chave: str,
        questoes: tuple[str, ...],
        respostas: tuple[str, ...],
    ) -> None:
        quadro = ttk.LabelFrame(self.formulario, text=titulo, padding=12)
        quadro.pack(fill="x", pady=(0, 14))
        quadro.columnconfigure(0, weight=1)

        for indice, questao in enumerate(questoes):
            ttk.Label(
                quadro,
                text=f"{indice + 1}. {questao}",
                wraplength=550,
                justify="left",
            ).grid(row=indice, column=0, sticky="w", padx=(0, 12), pady=6)
            variavel = tk.StringVar()
            seletor = ttk.Combobox(
                quadro,
                textvariable=variavel,
                values=respostas,
                state="readonly",
                width=31,
            )
            seletor.grid(row=indice, column=1, sticky="e", pady=6)
            self.variaveis[chave].append(variavel)

    def _valores(self, chave: str, opcoes: tuple[str, ...]) -> list[int]:
        valores: list[int] = []
        for variavel in self.variaveis[chave]:
            resposta = variavel.get()
            if resposta not in opcoes:
                raise ValueError("Responda todas as questões antes de calcular.")
            valores.append(opcoes.index(resposta) + 1)
        return valores

    def _calcular(self) -> None:
        try:
            resultado = calcular_resultado(
                self._valores("demanda", RESPOSTAS_FREQUENCIA),
                self._valores("controle", RESPOSTAS_FREQUENCIA),
                self._valores("apoio", RESPOSTAS_APOIO),
            )
        except ValueError as erro:
            messagebox.showwarning("Preenchimento incompleto", str(erro), parent=self)
            return

        self.resultado_atual = resultado
        self.botao_salvar.configure(state="normal")
        self.resumo.configure(text=resultado.quadrante)
        messagebox.showinfo(
            "Classificação calculada",
            montar_relatorio(self.nome.get(), resultado),
            parent=self,
        )

    def _limpar(self) -> None:
        for grupo in self.variaveis.values():
            for variavel in grupo:
                variavel.set("")
        self.nome.delete(0, "end")
        self.resultado_atual = None
        self.botao_salvar.configure(state="disabled")
        self.resumo.configure(text="Aguardando preenchimento.")

    def _salvar(self) -> None:
        if self.resultado_atual is None:
            return
        destino = filedialog.asksaveasfilename(
            parent=self,
            title="Salvar resultado",
            defaultextension=".txt",
            filetypes=(("Arquivo de texto", "*.txt"),),
            initialfile=f"resultado_estresse_{datetime.now():%Y%m%d_%H%M}.txt",
        )
        if not destino:
            return
        Path(destino).write_text(
            montar_relatorio(self.nome.get(), self.resultado_atual),
            encoding="utf-8",
        )
        messagebox.showinfo("Resultado salvo", "O arquivo foi salvo com sucesso.", parent=self)


if __name__ == "__main__":
    Aplicativo().mainloop()
