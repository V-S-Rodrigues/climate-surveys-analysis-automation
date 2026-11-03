 Atualização: análise de clima segmentada por área

## Arquivos
- `Google_forms_extractor.py`: preserva as respostas por submissão e calcula médias por área.
- `Gerar_relatorio_forms.py`: inclui distribuição de respondentes e tabelas de médias por área no Word.
- `interface.py`: mantido sem alterações; continua chamando `gerar_relatorio`.

## Instalação
```bash
pip install google-auth google-auth-oauthlib google-api-python-client python-docx
```

Mantenha `credentials.json` na pasta dos scripts e autorize o acesso pelo navegador. O `token.json` será criado nessa mesma pasta. Não publique esses arquivos no GitHub.

## Execução
```bash
python interface.py
```

A pergunta de segmentação é identificada pelo título contendo “qual área” e referências a “setor”, “vinculado” ou “pertence”. A forma usada no formulário de teste — “A qual área seu setor está vinculado?” — é reconhecida.

## Saída
O Word apresenta as médias gerais, a distribuição de respondentes por área e, para cada questão quantitativa, a média e o número de respostas válidas (`n`) por área. Respostas em branco não são convertidas em zero.

## Observações
- A segmentação mantém as respostas agrupadas por submissão durante o processamento; o relatório apresenta agregados, não identificadores individuais.
- A classificação de questões quantitativas mantém a regra atual: todas as respostas não vazias da questão precisam ser numéricas. Isso evita calcular médias de respostas categóricas, mas ainda não substitui uma configuração explícita de quais perguntas são indicadores de clima.
- A integração com a API do Google depende de credenciais e permissões válidas. Os testes realizados nesta entrega cobrem o processamento com dados sintéticos e a geração do documento Word, não uma chamada real à API.
