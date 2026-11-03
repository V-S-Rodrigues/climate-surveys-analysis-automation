
"""
Geracao de relatorios de pesquisas do Google Forms.

Fluxo:
1. Autentica nas APIs do Google.
2. Busca um formulario pelo nome no Drive.
3. Exige um unico resultado para evitar relatorios ambiguos.
4. Extrai e processa as respostas.
5. Gera um arquivo Word (.docx) localmente.
"""

from pathlib import Path

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import Google_forms_extractor as extrator


# O token compartilhado precisa contemplar os escopos dos dois modulos.
SCOPES = [
    "https://www.googleapis.com/auth/drive.metadata.readonly",
    "https://www.googleapis.com/auth/forms.responses.readonly",
    "https://www.googleapis.com/auth/forms.body.readonly",
]

BASE_DIR = Path(__file__).resolve().parent
ARQUIVO_TOKEN = BASE_DIR / "token.json"
ARQUIVO_CREDENCIAIS = BASE_DIR / "credentials.json"
TAMANHO_PAGINA = 1000


def autenticar():
    """
    Autentica o usuario e salva as credenciais em token.json.

    Se o token existente nao tiver todos os escopos necessarios,
    solicita uma nova autorizacao.
    """
    credenciais = None

    if ARQUIVO_TOKEN.exists():
        credenciais = Credentials.from_authorized_user_file(
            str(ARQUIVO_TOKEN),
            SCOPES
        )

    if credenciais and credenciais.expired and credenciais.refresh_token:
        try:
            credenciais.refresh(Request())
        except Exception:
            credenciais = None

    if (
        not credenciais
        or not credenciais.valid
        or not credenciais.has_scopes(SCOPES)
    ):
        if not ARQUIVO_CREDENCIAIS.exists():
            raise FileNotFoundError(
                "Arquivo credentials.json nao encontrado."
            )

        fluxo = InstalledAppFlow.from_client_secrets_file(
            str(ARQUIVO_CREDENCIAIS),
            SCOPES
        )
        credenciais = fluxo.run_local_server(port=0)

    ARQUIVO_TOKEN.write_text(
        credenciais.to_json(),
        encoding="utf-8"
    )

    return credenciais


def criar_servico_drive(credenciais):
    """Cria o cliente da API do Google Drive."""
    return build(
        "drive",
        "v3",
        credentials=credenciais
    )


def escapar_termo_drive(termo):
    """Escapa caracteres especiais usados na consulta do Drive."""
    return termo.replace("\\", "\\\\").replace("'", "\\'")


def buscar_formularios_no_drive(drive_service, nome_formulario):
    """
    Busca formularios cujo nome contenha o termo informado.

    Percorre todas as paginas retornadas pela API.
    """
    termo = escapar_termo_drive(nome_formulario)

    consulta = (
        f"name contains '{termo}' "
        "and mimeType = 'application/vnd.google-apps.form' "
        "and trashed = false"
    )

    formularios = []
    pagina_token = None

    while True:
        parametros = {
            "q": consulta,
            "pageSize": TAMANHO_PAGINA,
            "fields": "nextPageToken, files(id, name)",
            "orderBy": "name"
        }

        if pagina_token:
            parametros["pageToken"] = pagina_token

        resultado = drive_service.files().list(
            **parametros
        ).execute()

        formularios.extend(resultado.get("files", []))
        pagina_token = resultado.get("nextPageToken")

        if not pagina_token:
            break

    return formularios


def selecionar_formulario(formularios, nome_formulario):
    """
    Garante que a busca retornou exatamente um formulario.
    """
    if not formularios:
        raise ValueError(
            f"Nenhum formulario encontrado com o termo: "
            f"'{nome_formulario}'."
        )

    if len(formularios) > 1:
        encontrados = "\n".join(
            f"- {formulario['name']} (ID: {formulario['id']})"
            for formulario in formularios
        )

        raise ValueError(
            "A busca encontrou mais de um formulario. "
            "Informe um nome mais especifico.\n\n"
            f"Resultados encontrados:\n{encontrados}"
        )

    return formularios[0]


def adicionar_respostas_abertas(documento, respostas_abertas):
    """Adiciona as respostas textuais ao documento."""
    documento.add_heading(
        "Questoes abertas",
        level=1
    )

    for pergunta, resposta in respostas_abertas:
        paragrafo = documento.add_paragraph()

        trecho = paragrafo.add_run(f"{pergunta}\n")
        trecho.bold = True

        paragrafo.add_run(str(resposta))


def adicionar_analise_por_area(documento, medias_por_area, distribuicao_areas):
    """Inclui a distribuição de respondentes e as médias segmentadas."""
    documento.add_heading("Análise por área", level=1)

    documento.add_paragraph("Quantidade de respondentes por área:")
    tabela_areas = documento.add_table(rows=1, cols=2)
    tabela_areas.style = "Table Grid"
    tabela_areas.rows[0].cells[0].text = "Área"
    tabela_areas.rows[0].cells[1].text = "Respondentes"

    for area, quantidade in distribuicao_areas.items():
        celulas = tabela_areas.add_row().cells
        celulas[0].text = str(area)
        celulas[1].text = str(quantidade)

    if not medias_por_area:
        documento.add_paragraph(
            "Não foram identificadas questões quantitativas elegíveis "
            "para cálculo de médias por área."
        )
        return

    documento.add_paragraph(
        "Médias por questão e área. O n representa a quantidade de "
        "respostas numéricas válidas utilizadas em cada média."
    )

    for pergunta, resultados_area in medias_por_area.items():
        documento.add_heading(pergunta, level=2)
        tabela = documento.add_table(rows=1, cols=3)
        tabela.style = "Table Grid"
        cabecalho = tabela.rows[0].cells
        cabecalho[0].text = "Área"
        cabecalho[1].text = "Média"
        cabecalho[2].text = "n"

        for area, dados in resultados_area.items():
            celulas = tabela.add_row().cells
            celulas[0].text = str(area)
            celulas[1].text = str(dados["media"])
            celulas[2].text = str(dados["n"])


def gerar_documento_word(
    medias,
    respostas_abertas,
    caminho_saida,
    medias_por_area=None,
    distribuicao_areas=None,
    total_respondentes=None,
):
    """Gera relatório Word com análise geral e, quando disponível, por área."""
    caminho_saida = Path(caminho_saida)

    if caminho_saida.suffix.lower() != ".docx":
        raise ValueError("O arquivo de saída precisa ter a extensão .docx.")

    caminho_saida.parent.mkdir(parents=True, exist_ok=True)
    documento = docx.Document()
    documento.add_heading("Relatório de análise de pesquisa", level=0)

    if total_respondentes is not None:
        documento.add_paragraph(f"Total de respondentes: {total_respondentes}")

    if medias:
        documento.add_heading("Questões quantitativas — visão geral", level=1)
        for pergunta, media in medias.items():
            paragrafo = documento.add_paragraph()
            paragrafo.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            trecho = paragrafo.add_run(f"{pergunta}: ")
            trecho.bold = True
            paragrafo.add_run(str(media))

    if medias_por_area is not None and distribuicao_areas is not None:
        adicionar_analise_por_area(
            documento,
            medias_por_area,
            distribuicao_areas
        )

    if respostas_abertas:
        adicionar_respostas_abertas(documento, respostas_abertas)

    if not medias and not respostas_abertas:
        documento.add_paragraph(
            "O formulário não possui respostas válidas para apresentar."
        )

    documento.save(str(caminho_saida))
    if not caminho_saida.exists() or caminho_saida.stat().st_size == 0:
        raise RuntimeError("O documento não foi criado corretamente.")

    return str(caminho_saida.resolve())


def gerar_relatorio(nome_formulario, caminho_saida):
    """
    Coordena a busca, extracao, processamento e geracao do relatorio.

    Retorna:
        Caminho absoluto do arquivo .docx gerado.

    Levanta excecoes quando nao encontra um formulario,
    encontra resultados ambiguos ou ocorre uma falha na API.
    """
    nome_formulario = nome_formulario.strip()

    if not nome_formulario:
        raise ValueError(
            "Informe o nome do formulario."
        )

    credenciais = autenticar()
    drive_service = criar_servico_drive(credenciais)

    try:
        formularios = buscar_formularios_no_drive(
            drive_service,
            nome_formulario
        )

        formulario = selecionar_formulario(
            formularios,
            nome_formulario
        )

        print(
            f"Processando: {formulario['name']} "
            f"(ID: {formulario['id']})"
        )

        dados = extrator.extrair_dados_com_segmentacao(formulario["id"])

        return gerar_documento_word(
            dados["medias"],
            dados["respostas_abertas"],
            caminho_saida,
            medias_por_area=dados["medias_por_area"],
            distribuicao_areas=dados["distribuicao_areas"],
            total_respondentes=dados["total_respondentes"],
        )

    except HttpError as erro:
        raise RuntimeError(
            f"Erro ao consultar as APIs do Google: {erro}"
        ) from erro


if __name__ == "__main__":
    nome = input("Digite o nome do formulario: ").strip()

    caminho = Path(f"{nome}_analisado.docx")

    try:
        arquivo = gerar_relatorio(nome, caminho)
        print(f"Relatorio gerado: {arquivo}")
    except Exception as erro:
        print(f"Falha ao gerar relatorio: {erro}")
