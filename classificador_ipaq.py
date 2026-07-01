"""Classificador do nível de atividade física - IPAQ.

Baseado no documento do Centro Coordenador do IPAQ no Brasil - CELAFISCS
"Classificação do Nível de Atividade Física IPAQ" (2012).
"""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


@dataclass(frozen=True)
class Atividade:
    dias: int
    minutos_sessao: int

    @property
    def minutos_semana(self) -> int:
        return self.dias * self.minutos_sessao

    @property
    def possui_sessao_valida(self) -> bool:
        return self.dias > 0 and self.minutos_sessao >= 10


@dataclass(frozen=True)
class ResultadoIPAQ:
    classificacao: str
    classificacao_reduzida: str
    criterio: str
    frequencia_somada: int
    minutos_semana: int


def calcular_ipaq(
    caminhada: Atividade,
    moderada: Atividade,
    vigorosa: Atividade,
) -> ResultadoIPAQ:
    atividades = (caminhada, moderada, vigorosa)
    for atividade in atividades:
        if not 0 <= atividade.dias <= 7:
            raise ValueError("A frequência deve estar entre 0 e 7 dias por semana.")
        if not 0 <= atividade.minutos_sessao <= 1440:
            raise ValueError("A duração deve estar entre 0 e 1.440 minutos por sessão.")
        if atividade.dias == 0 and atividade.minutos_sessao != 0:
            raise ValueError("Quando a frequência for zero, informe também zero minuto.")
        if atividade.dias > 0 and atividade.minutos_sessao < 10:
            raise ValueError("Considere apenas atividades realizadas por pelo menos 10 minutos contínuos.")

    frequencia_somada = sum(a.dias for a in atividades)
    minutos_semana = sum(a.minutos_semana for a in atividades)

    # Os exemplos do documento combinam caminhada e atividade moderada.
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
        classificacao = "MUITO ATIVO"
        criterio = "Atividade vigorosa em 5 ou mais dias/semana, por 30 minutos ou mais por sessão."
    elif muito_ativo_b:
        classificacao = "MUITO ATIVO"
        criterio = (
            "Atividade vigorosa em 3 ou mais dias/semana, por 20 minutos ou mais, "
            "com caminhada e/ou atividade moderada em frequência somada de 5 ou mais "
            "dias/semana, por 30 minutos ou mais."
        )
    elif ativo_a:
        classificacao = "ATIVO"
        criterio = "Atividade vigorosa em 3 ou mais dias/semana, por 20 minutos ou mais por sessão."
    elif ativo_b:
        classificacao = "ATIVO"
        criterio = (
            "Caminhada ou atividade moderada em 5 ou mais dias/semana, "
            "por 30 minutos ou mais por sessão."
        )
    elif ativo_c:
        classificacao = "ATIVO"
        criterio = "Frequência somada de 5 ou mais dias/semana e 150 minutos ou mais por semana."
    elif any(a.possui_sessao_valida for a in atividades):
        classificacao = "IRREGULARMENTE ATIVO"
        criterio = "Realiza atividade física, mas não alcança os critérios de Ativo ou Muito ativo."
    else:
        classificacao = "INATIVO"
        criterio = "Não realizou atividade física por pelo menos 10 minutos contínuos na semana."

    classificacao_reduzida = (
        "SUFICIENTEMENTE ATIVO"
        if classificacao in {"ATIVO", "MUITO ATIVO"}
        else "SEDENTÁRIO OU INSUFICIENTEMENTE ATIVO"
    )

    return ResultadoIPAQ(
        classificacao=classificacao,
        classificacao_reduzida=classificacao_reduzida,
        criterio=criterio,
        frequencia_somada=frequencia_somada,
        minutos_semana=minutos_semana,
    )


def montar_relatorio(
    nome: str,
    caminhada: Atividade,
    moderada: Atividade,
    vigorosa: Atividade,
    resultado: ResultadoIPAQ,
) -> str:
    identificacao = nome.strip() or "Não informada"
    return (
        "RESULTADO - NÍVEL DE ATIVIDADE FÍSICA IPAQ\n"
        f"Data: {datetime.now():%d/%m/%Y %H:%M}\n"
        f"Identificação: {identificacao}\n\n"
        "DADOS INFORMADOS\n"
        f"Caminhada: {caminhada.dias} dia(s)/semana, "
        f"{caminhada.minutos_sessao} min/sessão, {caminhada.minutos_semana} min/semana\n"
        f"Moderada: {moderada.dias} dia(s)/semana, "
        f"{moderada.minutos_sessao} min/sessão, {moderada.minutos_semana} min/semana\n"
        f"Vigorosa: {vigorosa.dias} dia(s)/semana, "
        f"{vigorosa.minutos_sessao} min/sessão, {vigorosa.minutos_semana} min/semana\n\n"
        f"Frequência somada: {resultado.frequencia_somada} dia(s)/semana\n"
        f"Tempo total: {resultado.minutos_semana} min/semana\n\n"
        f"CLASSIFICAÇÃO IPAQ: {resultado.classificacao}\n"
        f"CLASSIFICAÇÃO REDUZIDA: {resultado.classificacao_reduzida}\n"
        f"Critério alcançado: {resultado.criterio}\n\n"
        "Esta ferramenta automatiza a classificação informada no protocolo "
        "e não substitui avaliação profissional.\n"
    )


class AplicativoIPAQ(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Classificador IPAQ")
        self.geometry("760x600")
        self.minsize(680, 520)
        self.resultado_atual: ResultadoIPAQ | None = None
        self.atividades_atuais: tuple[Atividade, Atividade, Atividade] | None = None
        self.campos: dict[str, tuple[tk.StringVar, tk.StringVar]] = {}
        self._configurar_estilo()
        self._montar_interface()

    def _configurar_estilo(self) -> None:
        estilo = ttk.Style(self)
        estilo.configure("Titulo.TLabel", font=("Segoe UI", 18, "bold"))
        estilo.configure("Resultado.TLabel", font=("Segoe UI", 15, "bold"))
        estilo.configure("TButton", padding=(12, 7))

    def _montar_interface(self) -> None:
        principal = ttk.Frame(self, padding=22)
        principal.pack(fill="both", expand=True)
        ttk.Label(principal, text="Classificação do Nível de Atividade Física", style="Titulo.TLabel").pack(
            anchor="w"
        )
        ttk.Label(
            principal,
            text="IPAQ - informe somente atividades realizadas por pelo menos 10 minutos contínuos.",
        ).pack(anchor="w", pady=(4, 16))

        identificacao = ttk.Frame(principal)
        identificacao.pack(fill="x", pady=(0, 16))
        ttk.Label(identificacao, text="Identificação (opcional):").pack(side="left")
        self.nome = ttk.Entry(identificacao)
        self.nome.pack(side="left", fill="x", expand=True, padx=(8, 0))

        quadro = ttk.LabelFrame(principal, text="Atividades na última semana", padding=14)
        quadro.pack(fill="x")
        ttk.Label(quadro, text="Tipo de atividade").grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Label(quadro, text="Dias/semana").grid(row=0, column=1, padx=12, pady=(0, 8))
        ttk.Label(quadro, text="Minutos/sessão").grid(row=0, column=2, pady=(0, 8))
        quadro.columnconfigure(0, weight=1)

        for linha, (chave, titulo) in enumerate(
            (
                ("caminhada", "Caminhada"),
                ("moderada", "Atividade moderada"),
                ("vigorosa", "Atividade vigorosa"),
            ),
            start=1,
        ):
            dias = tk.StringVar(value="0")
            minutos = tk.StringVar(value="0")
            self.campos[chave] = (dias, minutos)
            ttk.Label(quadro, text=titulo).grid(row=linha, column=0, sticky="w", pady=9)
            ttk.Spinbox(quadro, from_=0, to=7, textvariable=dias, width=10).grid(
                row=linha, column=1, padx=12, pady=9
            )
            ttk.Spinbox(quadro, from_=0, to=1440, textvariable=minutos, width=14).grid(
                row=linha, column=2, pady=9
            )

        botoes = ttk.Frame(principal)
        botoes.pack(fill="x", pady=18)
        ttk.Button(botoes, text="Calcular classificação", command=self._calcular).pack(side="left")
        ttk.Button(botoes, text="Limpar", command=self._limpar).pack(side="left", padx=8)
        self.botao_salvar = ttk.Button(
            botoes,
            text="Salvar resultado",
            command=self._salvar,
            state="disabled",
        )
        self.botao_salvar.pack(side="left")

        resultado = ttk.LabelFrame(principal, text="Resultado", padding=14)
        resultado.pack(fill="both", expand=True)
        self.classificacao = ttk.Label(resultado, text="Aguardando preenchimento.", style="Resultado.TLabel")
        self.classificacao.pack(anchor="w")
        self.detalhes = ttk.Label(resultado, text="", wraplength=670, justify="left")
        self.detalhes.pack(anchor="w", pady=(10, 0))

    def _ler_atividade(self, chave: str) -> Atividade:
        dias_texto, minutos_texto = (variavel.get().strip() for variavel in self.campos[chave])
        try:
            return Atividade(dias=int(dias_texto), minutos_sessao=int(minutos_texto))
        except ValueError as erro:
            raise ValueError("Dias e minutos devem ser números inteiros.") from erro

    def _calcular(self) -> None:
        try:
            caminhada = self._ler_atividade("caminhada")
            moderada = self._ler_atividade("moderada")
            vigorosa = self._ler_atividade("vigorosa")
            resultado = calcular_ipaq(caminhada, moderada, vigorosa)
        except ValueError as erro:
            messagebox.showwarning("Verifique os dados", str(erro), parent=self)
            return

        self.atividades_atuais = (caminhada, moderada, vigorosa)
        self.resultado_atual = resultado
        self.botao_salvar.configure(state="normal")
        self.classificacao.configure(text=resultado.classificacao)
        self.detalhes.configure(
            text=(
                f"{resultado.classificacao_reduzida}\n\n"
                f"{resultado.criterio}\n\n"
                f"Total calculado: {resultado.minutos_semana} minutos/semana."
            )
        )

    def _limpar(self) -> None:
        for dias, minutos in self.campos.values():
            dias.set("0")
            minutos.set("0")
        self.nome.delete(0, "end")
        self.resultado_atual = None
        self.atividades_atuais = None
        self.botao_salvar.configure(state="disabled")
        self.classificacao.configure(text="Aguardando preenchimento.")
        self.detalhes.configure(text="")

    def _salvar(self) -> None:
        if self.resultado_atual is None or self.atividades_atuais is None:
            return
        destino = filedialog.asksaveasfilename(
            parent=self,
            title="Salvar resultado",
            defaultextension=".txt",
            filetypes=(("Arquivo de texto", "*.txt"),),
            initialfile=f"resultado_ipaq_{datetime.now():%Y%m%d_%H%M}.txt",
        )
        if not destino:
            return
        Path(destino).write_text(
            montar_relatorio(
                self.nome.get(),
                *self.atividades_atuais,
                self.resultado_atual,
            ),
            encoding="utf-8",
        )
        messagebox.showinfo("Resultado salvo", "O arquivo foi salvo com sucesso.", parent=self)


if __name__ == "__main__":
    AplicativoIPAQ().mainloop()
