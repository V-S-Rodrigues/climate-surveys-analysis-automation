
"""
Interface grafica para a automacao de pesquisas do Google Forms.
"""

import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

import Gerar_relatorio_forms as gerador


class InterfaceAutomacao(tk.Tk):

    def __init__(self):
        super().__init__()

        self.title("Automacao de Pesquisas")
        self.geometry("650x300")
        self.resizable(False, False)

        self.nome_formulario = tk.StringVar()
        self.pasta_destino = tk.StringVar()
        self.nome_arquivo = tk.StringVar()

        self.botao_executar = None
        self.status = tk.StringVar(
            value="Preencha os campos para iniciar."
        )

        self._criar_widgets()

    def _criar_widgets(self):
        tk.Label(
            self,
            text="Nome do formulario:"
        ).pack(pady=(15, 5))

        tk.Entry(
            self,
            textvariable=self.nome_formulario,
            width=65
        ).pack()

        tk.Label(
            self,
            text="Pasta de destino:"
        ).pack(pady=(12, 5))

        frame_pasta = tk.Frame(self)
        frame_pasta.pack()

        tk.Entry(
            frame_pasta,
            textvariable=self.pasta_destino,
            width=48
        ).pack(side="left", padx=5)

        tk.Button(
            frame_pasta,
            text="Selecionar pasta",
            command=self.selecionar_pasta
        ).pack(side="left")

        tk.Label(
            self,
            text="Nome do arquivo:"
        ).pack(pady=(12, 5))

        tk.Entry(
            self,
            textvariable=self.nome_arquivo,
            width=65
        ).pack()

        self.botao_executar = tk.Button(
            self,
            text="Gerar relatorio",
            width=22,
            command=self.executar
        )
        self.botao_executar.pack(pady=15)

        tk.Label(
            self,
            textvariable=self.status,
            wraplength=580
        ).pack(pady=5)

    def selecionar_pasta(self):
        pasta = filedialog.askdirectory()

        if pasta:
            self.pasta_destino.set(pasta)

    def executar(self):
        nome_form = self.nome_formulario.get().strip()
        pasta = self.pasta_destino.get().strip()
        nome_arquivo = self.nome_arquivo.get().strip()

        if not nome_form or not pasta or not nome_arquivo:
            messagebox.showwarning(
                "Campos obrigatorios",
                "Preencha todos os campos antes de continuar."
            )
            return

        if not os.path.isdir(pasta):
            messagebox.showwarning(
                "Pasta invalida",
                "Selecione uma pasta de destino existente."
            )
            return

        if not nome_arquivo.lower().endswith(".docx"):
            nome_arquivo += ".docx"

        # Impede que o nome do arquivo inclua outro caminho.
        if os.path.basename(nome_arquivo) != nome_arquivo:
            messagebox.showwarning(
                "Nome invalido",
                "Informe somente o nome do arquivo, sem caminhos."
            )
            return

        caminho_completo = os.path.join(
            pasta,
            nome_arquivo
        )

        if os.path.exists(caminho_completo):
            confirmar = messagebox.askyesno(
                "Arquivo existente",
                "Ja existe um arquivo com esse nome. "
                "Deseja substitui-lo?"
            )

            if not confirmar:
                return

        self.botao_executar.config(state="disabled")
        self.status.set("Processando formulario. Aguarde...")

        thread = threading.Thread(
            target=self._processar,
            args=(nome_form, caminho_completo),
            daemon=True
        )
        thread.start()

    def _processar(self, nome_form, caminho):
        try:
            resultado = gerador.gerar_relatorio(
                nome_formulario=nome_form,
                caminho_saida=caminho
            )

            if not resultado or not os.path.isfile(resultado):
                raise RuntimeError(
                    "O gerador nao confirmou a criacao do arquivo."
                )

            self.after(
                0,
                self._finalizar_sucesso,
                resultado
            )

        except Exception as erro:
            self.after(
                0,
                self._finalizar_erro,
                str(erro)
            )

    def _finalizar_sucesso(self, caminho):
        self.botao_executar.config(state="normal")
        self.status.set("Relatorio gerado com sucesso.")

        messagebox.showinfo(
            "Concluido",
            f"Relatorio gerado com sucesso!\n\n{caminho}"
        )

    def _finalizar_erro(self, erro):
        self.botao_executar.config(state="normal")
        self.status.set("Nao foi possivel gerar o relatorio.")

        messagebox.showerror(
            "Erro durante a execucao",
            erro
        )


if __name__ == "__main__":
    app = InterfaceAutomacao()
    app.mainloop()
