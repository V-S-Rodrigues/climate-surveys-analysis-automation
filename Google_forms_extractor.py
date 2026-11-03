
"""
Google Forms Extractor
======================

Extrai perguntas e respostas de formulários Google, processa os dados
e separa questões numéricas de respostas textuais.

Dependências:
    pip install google-auth google-auth-oauthlib google-api-python-client

Configuração:
    1. Ative a Google Forms API no Google Cloud.
    2. Crie credenciais OAuth 2.0 para aplicativo desktop.
    3. Salve o arquivo como credentials.json na raiz do projeto.
    4. Execute o programa e autorize o acesso pelo navegador.

Segurança:
    credentials.json e token.json não devem ser publicados no GitHub.
"""

import os
from pathlib import Path
from decimal import Decimal, InvalidOperation

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# ============================================================
# CONFIGURAÇÕES
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

ARQUIVO_CREDENCIAIS = BASE_DIR / "credentials.json"
ARQUIVO_TOKEN = BASE_DIR / "token.json"

SCOPES = [
    "https://www.googleapis.com/auth/forms.responses.readonly",
    "https://www.googleapis.com/auth/forms.body.readonly",
]

QUESTOES_IGNORADAS = {
    "Você é membro ou diretor?",
}

# A pergunta de área é identificada pelo título normalizado. Isso permite
# reconhecer variações de caixa, acentuação e espaços sem depender do texto
# exato usado em cada formulário.

TAMANHO_PAGINA = 5000


# ============================================================
# AUTENTICAÇÃO
# ============================================================

def autenticar():
    """
    Realiza autenticação OAuth 2.0 com a API do Google Forms.

    Utiliza token.json para reutilizar a autenticação entre execuções.

    Returns:
        Credentials: credenciais autenticadas.
    """

    credenciais = None

    if ARQUIVO_TOKEN.exists():
        credenciais = Credentials.from_authorized_user_file(
            str(ARQUIVO_TOKEN),
            SCOPES
        )

    if credenciais and credenciais.expired and credenciais.refresh_token:
        credenciais.refresh(Request())

    elif not credenciais or not credenciais.valid:

        if not ARQUIVO_CREDENCIAIS.exists():
            raise FileNotFoundError(
                "Arquivo credentials.json não encontrado. "
                "Configure suas credenciais OAuth do Google."
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


# ============================================================
# CONEXÃO COM A API
# ============================================================

def criar_servico_forms():
    """
    Cria o serviço autenticado da Google Forms API.

    Returns:
        Resource: serviço da API Forms v1.
    """

    credenciais = autenticar()

    return build(
        "forms",
        "v1",
        credentials=credenciais,
        cache_discovery=False
    )


# ============================================================
# EXTRAÇÃO DOS DADOS
# ============================================================

def buscar_todas_as_respostas(servico_forms, form_id):
    """
    Busca todas as respostas de um formulário, percorrendo as páginas
    disponibilizadas pela API.

    Args:
        servico_forms: serviço autenticado da Google Forms API.
        form_id (str): identificador do formulário.

    Returns:
        list: todas as submissões encontradas.
    """

    respostas = []
    page_token = None

    while True:

        parametros = {
            "formId": form_id,
            "pageSize": TAMANHO_PAGINA,
        }

        if page_token:
            parametros["pageToken"] = page_token

        resultado = (
            servico_forms.forms()
            .responses()
            .list(**parametros)
            .execute()
        )

        respostas.extend(resultado.get("responses", []))

        page_token = resultado.get("nextPageToken")

        if not page_token:
            break

    return respostas


def buscar_dados_do_formulario(form_id):
    """
    Busca a estrutura do formulário e todas as suas respostas.

    Args:
        form_id (str): identificador do Google Forms.

    Returns:
        tuple:
            - lista_de_respostas
            - lista_de_questoes
    """

    if not isinstance(form_id, str) or not form_id.strip():
        raise ValueError("O ID do formulário não pode estar vazio.")

    servico_forms = criar_servico_forms()

    try:

        dados_formulario = (
            servico_forms.forms()
            .get(formId=form_id)
            .execute()
        )

        respostas = buscar_todas_as_respostas(
            servico_forms,
            form_id
        )

        questoes = dados_formulario.get("items", [])

        return respostas, questoes

    except HttpError as erro:
        raise RuntimeError(
            f"Erro ao consultar o Google Forms: {erro}"
        ) from erro


# ============================================================
# EXTRAÇÃO DAS PERGUNTAS
# ============================================================

def extrair_perguntas(questoes_brutas):
    """
    Extrai o título e o ID das perguntas do formulário.

    Ignora elementos que não representam perguntas individuais.

    Args:
        questoes_brutas (list): itens retornados pela API.

    Returns:
        list: pares [texto_pergunta, id_questao].
    """

    perguntas = []

    for item in questoes_brutas:

        dados_pergunta = item.get("questionItem", {})
        dados_questao = dados_pergunta.get("question", {})

        if not dados_questao:
            continue

        texto = item.get("title", "").strip()
        question_id = dados_questao.get("questionId")

        if texto and question_id:
            perguntas.append([texto, question_id])

    return perguntas


# ============================================================
# EXTRAÇÃO DAS RESPOSTAS
# ============================================================

def extrair_valores_da_resposta(resposta_bruta):
    """
    Extrai os valores textuais de uma resposta da API.

    A estrutura FormResponse.answers é um dicionário indexado pelo
    questionId. Cada Answer pode conter textAnswers.answers.

    Returns:
        list[str]: valores encontrados.
    """

    text_answers = resposta_bruta.get("textAnswers", {})
    respostas = text_answers.get("answers", [])

    return [
        resposta["value"]
        for resposta in respostas
        if resposta.get("value") is not None
    ]


def limpar_resposta(resposta_bruta):
    """
    Converte uma resposta da API em um valor textual simplificado.

    Quando uma pergunta possui múltiplas alternativas selecionadas,
    os valores são reunidos em uma única string.

    Args:
        resposta_bruta (dict): objeto Answer da API.

    Returns:
        str: resposta normalizada.
    """

    valores = extrair_valores_da_resposta(resposta_bruta)

    if not valores:
        return None

    return "; ".join(valores)


def processar_todas_as_respostas(respostas_brutas):
    """
    Agrupa as respostas por identificador de pergunta.

    Cada resposta é associada ao seu questionId, sem depender
    da ordem dos campos retornados pela API.

    Args:
        respostas_brutas (list): submissões do formulário.

    Returns:
        dict: {
            question_id: [resposta1, resposta2, ...]
        }
    """

    respostas_por_questao = {}

    for submissao in respostas_brutas:

        respostas = submissao.get("answers", {})

        for question_id, resposta_bruta in respostas.items():

            valor = limpar_resposta(resposta_bruta)

            if valor is None:
                continue

            respostas_por_questao.setdefault(
                question_id,
                []
            ).append(valor)

    return respostas_por_questao


# ============================================================
# TRATAMENTO NUMÉRICO
# ============================================================

def converter_para_decimal(valor):
    """
    Tenta converter uma resposta textual para Decimal.

    Aceita números inteiros, decimais com ponto e decimais com vírgula.

    Exemplos:
        "5"    -> Decimal("5")
        "4.5"  -> Decimal("4.5")
        "4,5"  -> Decimal("4.5")

    Returns:
        Decimal | None
    """

    if valor is None:
        return None

    texto = str(valor).strip()

    if not texto:
        return None

    # Não interpreta respostas com múltiplas alternativas como números.
    if ";" in texto:
        return None

    # Trata a vírgula como separador decimal.
    if "," in texto and "." not in texto:
        texto = texto.replace(",", ".")

    try:
        numero = Decimal(texto)

        if not numero.is_finite():
            return None

        return numero

    except InvalidOperation:
        return None


# ============================================================
# CLASSIFICAÇÃO DAS QUESTÕES
# ============================================================

def classificar_questoes(perguntas, respostas_por_questao):
    """
    Separa perguntas em dois grupos:

        - Numéricas: calcula a média das respostas válidas.
        - Textuais: preserva as respostas individuais.

    Uma pergunta só é considerada numérica quando todas as respostas
    não vazias podem ser convertidas para números.

    Args:
        perguntas (list): pares [texto_pergunta, question_id].
        respostas_por_questao (dict): respostas agrupadas por ID.

    Returns:
        tuple:
            medias (dict): médias das perguntas numéricas.
            respostas_abertas (list): respostas textuais.
    """

    medias = {}
    respostas_abertas = []

    for texto_pergunta, question_id in perguntas:

        if texto_pergunta in QUESTOES_IGNORADAS:
            continue

        respostas = respostas_por_questao.get(
            question_id,
            []
        )

        if not respostas:
            continue

        valores_numericos = [
            converter_para_decimal(resposta)
            for resposta in respostas
        ]

        # Só calcula média quando todas as respostas são numéricas.
        if all(valor is not None for valor in valores_numericos):

            media = sum(
                valores_numericos,
                Decimal("0")
            ) / Decimal(len(valores_numericos))

            medias[texto_pergunta] = str(
                media.quantize(Decimal("0.01"))
            )

        else:

            for resposta in respostas:
                respostas_abertas.append([
                    texto_pergunta,
                    resposta
                ])

    return medias, respostas_abertas


# ============================================================
# FLUXO PRINCIPAL
# ============================================================

def extrair_e_processar_formulario(form_id):
    """
    Executa o fluxo completo de extração e processamento.

    Args:
        form_id (str): ID do Google Forms.

    Returns:
        tuple:
            - medias
            - respostas_abertas
    """

    print("Conectando ao Google Forms...")

    respostas_brutas, questoes_brutas = (
        buscar_dados_do_formulario(form_id)
    )

    print(
        f"Total de submissões encontradas: "
        f"{len(respostas_brutas)}"
    )

    perguntas = extrair_perguntas(questoes_brutas)

    respostas_por_questao = processar_todas_as_respostas(
        respostas_brutas
    )

    medias, respostas_abertas = classificar_questoes(
        perguntas,
        respostas_por_questao
    )

    return medias, respostas_abertas


# ============================================================
# ANÁLISE POR RESPONDENTE E SEGMENTAÇÃO POR ÁREA
# ============================================================

import unicodedata


def normalizar_texto(texto):
    """Normaliza texto para comparação, sem alterar o valor original."""
    texto = str(texto or "").strip().casefold()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(
        caractere for caractere in texto
        if not unicodedata.combining(caractere)
    )
    return " ".join(texto.split())


def identificar_pergunta_area(perguntas):
    """Retorna (título, questionId) da pergunta padronizada de área."""
    for titulo, question_id in perguntas:
        titulo_normalizado = normalizar_texto(titulo)
        pergunta_sobre_area = (
            "qual area" in titulo_normalizado
            and (
                "setor" in titulo_normalizado
                or "pertence" in titulo_normalizado
                or "vinculado" in titulo_normalizado
            )
        )
        if pergunta_sobre_area:
            return titulo, question_id

    raise ValueError(
        "Não foi possível identificar a pergunta de área. "
        "Verifique se o formulário contém a pergunta padronizada "
        "'A qual área seu setor está vinculado?' ."
    )


def padronizar_area(valor):
    """Padroniza variações conhecidas de escrita e preserva nomes legíveis."""
    if valor is None or not str(valor).strip():
        return "Não informado"

    chave = normalizar_texto(valor)
    categorias = {
        "rh": "RH",
        "recursos humanos": "RH",
        "operacao": "Operações",
        "operacoes": "Operações",
        "financeiro": "Financeiro",
        "logistica": "Logística",
    }
    return categorias.get(chave, " ".join(str(valor).strip().split()).title())


def extrair_respostas_por_respondente(respostas_brutas, question_id_area):
    """Mantém juntas as respostas de cada submissão, inclusive sua área."""
    respondentes = []

    for indice, submissao in enumerate(respostas_brutas, start=1):
        respostas_brutas_pessoa = submissao.get("answers", {})
        respostas_pessoa = {}

        for question_id, resposta_bruta in respostas_brutas_pessoa.items():
            valor = limpar_resposta(resposta_bruta)
            if valor is not None:
                respostas_pessoa[question_id] = valor

        area = padronizar_area(respostas_pessoa.get(question_id_area))
        respondentes.append({
            "respondente": indice,
            "area": area,
            "respostas": respostas_pessoa,
        })

    return respondentes


def calcular_medias_por_area(perguntas, respondentes, question_id_area):
    """Calcula médias por pergunta e área, informando n de respostas válidas."""
    resultados = {}

    for titulo, question_id in perguntas:
        if question_id == question_id_area or titulo in QUESTOES_IGNORADAS:
            continue

        valores_por_area = {}
        encontrou_resposta = False
        todas_as_respostas_sao_numericas = True

        for pessoa in respondentes:
            valor = pessoa["respostas"].get(question_id)
            if valor is None:
                continue
            encontrou_resposta = True
            numero = converter_para_decimal(valor)
            if numero is None:
                todas_as_respostas_sao_numericas = False
                break
            valores_por_area.setdefault(pessoa["area"], []).append(numero)

        # Mantém a mesma regra da análise geral: só calcula média quando
        # todas as respostas não vazias daquela pergunta são numéricas.
        if not encontrou_resposta or not todas_as_respostas_sao_numericas:
            continue

        resultados[titulo] = {}
        for area, valores in sorted(valores_por_area.items()):
            media = sum(valores, Decimal("0")) / Decimal(len(valores))
            resultados[titulo][area] = {
                "media": str(media.quantize(Decimal("0.01"))),
                "n": len(valores),
            }

    return resultados


def extrair_dados_com_segmentacao(form_id):
    """Extrai análise geral e dados agregados por área sem expor respostas individuais."""
    print("Conectando ao Google Forms...")
    respostas_brutas, questoes_brutas = buscar_dados_do_formulario(form_id)
    perguntas = extrair_perguntas(questoes_brutas)
    titulo_area, question_id_area = identificar_pergunta_area(perguntas)

    respondentes = extrair_respostas_por_respondente(
        respostas_brutas,
        question_id_area
    )
    respostas_por_questao = processar_todas_as_respostas(respostas_brutas)
    medias, respostas_abertas = classificar_questoes(
        perguntas,
        respostas_por_questao
    )

    # A pergunta de área é metadado de segmentação, não uma resposta aberta.
    respostas_abertas = [
        (pergunta, resposta)
        for pergunta, resposta in respostas_abertas
        if pergunta != titulo_area
    ]

    medias_por_area = calcular_medias_por_area(
        perguntas,
        respondentes,
        question_id_area
    )

    distribuicao_areas = {}
    for pessoa in respondentes:
        area = pessoa["area"]
        distribuicao_areas[area] = distribuicao_areas.get(area, 0) + 1

    return {
        "medias": medias,
        "respostas_abertas": respostas_abertas,
        "medias_por_area": medias_por_area,
        "distribuicao_areas": dict(sorted(distribuicao_areas.items())),
        "total_respondentes": len(respondentes),
        "pergunta_area": titulo_area,
    }


# ============================================================
# EXECUÇÃO DIRETA
# ============================================================

if __name__ == "__main__":

    form_id = input(
        "Informe o ID do formulário Google: "
    ).strip()

    try:

        medias, respostas_abertas = (
            extrair_e_processar_formulario(form_id)
        )

        print("\n=== MÉDIAS DAS QUESTÕES NUMÉRICAS ===")

        for pergunta, media in medias.items():
            print(f"{pergunta}: {media}")

        print("\n=== RESPOSTAS TEXTUAIS ===")

        for pergunta, resposta in respostas_abertas:
            print(f"[{pergunta}] -> {resposta}")

    except Exception as erro:

        print(f"\nNão foi possível processar o formulário: {erro}")
