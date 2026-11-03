# Climate Surveys Analysis Automation

Automação para extração, tratamento e análise de respostas de pesquisas de clima organizacional realizadas no Google Forms. O projeto organiza as respostas por submissão, calcula indicadores quantitativos e permite visualizar resultados segmentados por área, gerando um relatório em Word.

> **Projeto demonstrativo:** desenvolvido em Python com integração às APIs do Google Forms e Google Drive.

## Demonstração

- **[Acessar o formulário de teste](https://docs.google.com/forms/d/e/1FAIpQLSeJq8QiiPLqBd60Ol_4ELbnXWYmc4K0GjHru9GtKvWVepFFfQ/viewform?usp=dialog)**
- **[Visualizar exemplo de relatório gerado](https://github.com/V-S-Rodrigues/climate-surveys-analysis-automation/blob/9f5e0ccd295c5014a698751ad6645b1cb836c936/exemplodeanalise.docx)**

O documento de exemplo foi produzido com dados sintéticos para demonstrar a estrutura e a apresentação dos resultados. Ele não contém respostas reais de colaboradores.

## Funcionalidades

- Autenticação OAuth 2.0 para acesso às APIs do Google.
- Busca de formulários no Google Drive pelo nome informado.
- Extração paginada das respostas do Google Forms.
- Associação das respostas às respectivas submissões, preservando o contexto de cada respondente durante o processamento.
- Classificação de questões quantitativas e textuais.
- Cálculo de médias gerais para questões quantitativas elegíveis.
- Identificação e padronização da área dos respondentes.
- Cálculo de médias por questão e por área, acompanhado do número de respostas válidas (`n`).
- Geração de relatório em formato `.docx`.
- Interface gráfica para informar o formulário, selecionar a pasta de destino e definir o nome do arquivo.

## Como funciona

O processamento está organizado em três módulos principais:

| Arquivo | Responsabilidade |
|---|---|
| `interface.py` | Interface gráfica e coleta dos parâmetros de execução. |
| `Gerar_relatorio_forms.py` | Coordenação do fluxo, busca do formulário no Drive e geração do documento Word. |
| `Google_forms_extractor.py` | Extração, tratamento, classificação e segmentação das respostas. |

O fluxo parte da interface, passa pelo módulo gerador, consulta o extrator e termina com a criação do relatório no local escolhido pelo usuário.

## Tecnologias e dependências

- Python 3
- Google Forms API
- Google Drive API
- Tkinter
- `google-api-python-client`
- `google-auth`
- `google-auth-oauthlib`
- `google-auth-httplib2`
- `python-docx`

## Instalação

1. Clone este repositório:

   ```bash
   git clone https://github.com/V-S-Rodrigues/climate-surveys-analysis-automation.git
   cd climate-surveys-analysis-automation
   ```

   Se preferir, baixe o repositório como arquivo ZIP diretamente pelo GitHub.

2. (Recomendado) Crie e ative um ambiente virtual:

   ```bash
   python -m venv .venv
   ```

   Windows:

   ```bash
   .venv\Scripts\activate
   ```

   macOS/Linux:

   ```bash
   source .venv/bin/activate
   ```

3. Instale as dependências:

   ```bash
   python -m pip install -r requirements.txt
   ```

## Configuração das APIs do Google

Para executar a extração, é necessário configurar o acesso às APIs do Google:

1. Acesse o [Google Cloud Console](https://console.cloud.google.com/).
2. Crie ou selecione um projeto no Google Cloud.
3. Habilite a **Google Forms API** e a **Google Drive API**.
4. Configure a tela de consentimento OAuth conforme o tipo de conta e o ambiente de teste.
5. Crie uma credencial OAuth do tipo **Aplicativo para computador**.
6. Baixe o arquivo de credenciais e salve-o na pasta raiz do projeto com o nome `credentials.json`.
7. Na primeira execução, o navegador será aberto para autorização. Após a autorização, o programa armazenará o token localmente em `token.json`.

**Segurança:** não compartilhe nem publique `credentials.json` ou `token.json`. Esses arquivos contêm informações de autenticação e estão incluídos nas regras do `.gitignore`. Não utilize dados pessoais ou respostas reais em ambientes públicos de teste.

## Execução

Com o ambiente virtual ativado, as dependências instaladas e as credenciais configuradas, execute:

```bash
python interface.py
```

Na interface:

1. Informe o nome do formulário exatamente ou um termo suficientemente específico para localizá-lo no Drive.
2. Selecione a pasta em que o relatório será salvo.
3. Informe o nome desejado para o arquivo Word.
4. Clique em **Gerar relatório**.

Se a busca retornar mais de um formulário, o programa solicita um termo mais específico para evitar a seleção ambígua.

## Estrutura do relatório

O documento gerado pode apresentar:

- total de respondentes;
- médias das questões quantitativas na visão geral;
- quantidade de respondentes por área;
- médias por questão e por área;
- número de respostas numéricas válidas (`n`) utilizado em cada média;
- respostas textuais abertas.

Respostas em branco não são convertidas em zero. O número `n` pode variar entre questões e áreas, conforme a quantidade de respostas válidas disponível para cada cálculo.

## Regras e limitações atuais

- A identificação da pergunta de segmentação depende de um título que contenha a expressão “qual área” e referências a “setor”, “vinculado” ou “pertence”.
- As categorias de área conhecidas são padronizadas no código. Respostas não reconhecidas são preservadas como categorias próprias.
- Uma questão só é classificada como quantitativa quando todas as respostas não vazias encontradas para ela podem ser convertidas em números. Se houver uma resposta textual, a questão é tratada como textual na versão atual.
- A classificação automática não substitui uma definição explícita das perguntas que devem compor os indicadores de clima.
- A busca pelo nome do formulário exige um único resultado para prosseguir.
- A integração depende de credenciais OAuth válidas, permissões adequadas e APIs habilitadas no Google Cloud.

## Privacidade e uso responsável

Pesquisas de clima podem conter informações sensíveis sobre relações de trabalho e percepções individuais. Antes de compartilhar relatórios, verifique se respostas abertas, grupos pequenos ou combinações de atributos podem permitir a identificação indireta de participantes. Utilize dados sintéticos nas demonstrações públicas e restrinja o acesso aos relatórios com dados reais.

## Testes

O exemplo de relatório incluído neste repositório demonstra a geração do documento com dados sintéticos. Ele não representa uma validação de integração com uma conta Google real. A execução ponta a ponta deve ser testada em um ambiente autorizado, com um formulário de teste e credenciais próprias.

## Licença

Nenhuma licença de uso foi especificada neste repositório até o momento. Entre em contato com a autora antes de reutilizar ou distribuir o projeto.
