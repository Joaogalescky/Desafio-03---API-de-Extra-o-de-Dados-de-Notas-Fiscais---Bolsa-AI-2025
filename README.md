
# **API de Extração de Dados de Notas Fiscais**  

# Projeto 3 (Sprints 4, 5 e 6)

## Processamento de Notas Fiscais com AWS
Este projeto implementa uma solução serverless para processamento de notas fiscais utilizando serviços da AWS como Lambda, Gateway, S3, Textract e Bedrock.

## Visão Geral
O sistema permite o envio de imagens de notas fiscais via API REST, que são então processadas para extração automática dos principais dados como:
- Nome do emissor.
- CNPJ do emissor.
- Endereço do emissor.
- CNPJ ou CPF do consumidor.
- Data de emissão.
- Número da nota fiscal.
- Série da nota fiscal.
- Valor total.
- Forma de pagamento.

## Arquitetura
![Diagrama da Arquitetura](./assets/sprints_4-5-6.jpg)

1. **Frontend/Cliente**: Envia a imagem da nota fiscal via requisição POST;
2. **API Gateway**: Recebe a requisição e encaminha para a Lambda;
3. **Lambda Function**: Processa a imagem e extrai os dados;
4. **Amazon S3**: Armazena as imagens das notas fiscais;
5. **Amazon Textract**: Extrai texto das imagens;
6. **AWS Bedrock**: Refina os dados extraídos usando IA.

## Configuração

### Pré-requisitos
- Conta AWS.
- AWS CLI configurada (opcional).
- Permissões para criar recursos na AWS.

### Passos de Implementação
1. **Criar Bucket S3**
   - Nome: `sprint-4-5-6-squad4`.
   - Região: `sa-east-1` (ou sua região preferencial).
   - Configurações padrão.

2. **Criar Função Lambda**
   - Nome: `extrairDadosNota`.
   - Runtime: Python 3.12.
   - Permissões básicas.

3. **Configurar Permissões**
   - Anexar políticas:
     - `AmazonS3FullAccess`.
     - `AmazonTextractFullAccess`.

4. **Criar API Gateway**
   - Tipo: HTTP API.
   - Rota: POST `/api/v1/invoice`.
   - Integração com a Lambda `extrairDadosNota`.

## Uso

### Enviando uma Nota Fiscal

#### Comando básico:
```bash
curl -X POST \
  -H "Content-Type: multipart/form-data" \
  -F "file=@nota_fiscal.jpg" \
  https://abc123.execute-api.sa-east-1.amazonaws.com/api/v1/invoice
```

#### Comando completo (Windows):
```bash
curl --location --request POST "https://20wakiw9w3.execute-api.us-east-2.amazonaws.com/api/v1/invoice" ^
--form "file=@\"C:/Users/eduar/Documents/Projetos do Estágio - UOL/sprints-4-5-6-pb-aws-maio/dataset/NFs/NFs/18080001-2.jpg\""
```

#### Comando para Linux/Mac:
```bash
curl --location --request POST "https://20wakiw9w3.execute-api.us-east-2.amazonaws.com/api/v1/invoice" \
--form "file=@\"$HOME/Documents/Projetos do Estágio - UOL/sprints-4-5-6-pb-aws-maio/dataset/NFs/NFs/18080001-2.jpg\""
```

### Corpo de resposta:
```json
{
    "nome_emissor": "<nome-fornecedor>"
    "CNPJ_emissor": "00.000.000/0000-00",
    "endereco_emissor": "<endereco-fornecedor>"
    "CNPJ_CPF_consumidor": "000.000.000-00",
    "data_emissao": "00/00/0000",
    "numero_nota_fiscal": "123456",
    "serie_nota_fiscal": "123",
    "valor_total": "0000.00",
    "forma_pgto": "<dinheiro||pix/outros>"
}
```

### Exemplo de resposta:
```json
{
  "nome_emissor": "LOJAS AMERICANAS S.A.",
  "CNPJ_emissor": "33.014.556/0001-96",
  "endereco_emissor": "RUA SACADURA CABRAL, 102 - RIO DE JANEIRO - RJ",
  "CNPJ_CPF_consumidor": "123.456.789-09",
  "data_emissao": "15/03/2024",
  "numero_nota_fiscal": "123456",
  "serie_nota_fiscal": "1",
  "valor_total": "125.90",
  "forma_pgto": "pix"
}
```

## Estrutura do Código
A função Lambda principal (`lambda_handler`) realiza as seguintes operações:
1. Decodifica o arquivo enviado;
2. Armazena no S3;
3. Extrai texto com Textract;
4. Processa dados com regex;
5. Refina dados com Bedrock;
6. Classifica e move o arquivo conforme a forma de pagamento, onde pagamentos do tipo "dinheiro" e "pix" são destinados ao diretório `dinheiro`, e as "demais" formas para o diretório `outros`.

## Funções Auxiliares
- `extrair_dados_com_regex`: Extração inicial de dados usando expressões regulares.
- `refinar_com_bedrock`: Refinamento dos dados usando modelos de IA do AWS Bedrock.

## Variáveis de Ambiente
| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `BUCKET_NAME` | Nome do bucket S3 | `sprint-4-5-6-squad4` |

## Melhorias Futuras
- Adicionar validação mais robusta dos dados.
- Implementar fila SQS para processamento assíncrono.
- Adicionar suporte a PDF além de imagens.
- Criar dashboard de monitoramento.

## Troubleshooting
- **Erro 403**: Verifique as permissões da função Lambda.
- **Erro 400**: Certifique-se que o arquivo está sendo enviado corretamente no formato multipart.
- **Erro 500**: Verifique os logs da Lambda para detalhes do erro.

## Dificuldades Técnicas

### Integração do NFTK (Nota Fiscal Toolkit)
- **Problemas com dependências**:
  - Não foi possível instalar as bibliotecas específicas do NFTK na Lambda.
  - Incompatibilidade com o runtime Python 3.12 da AWS.
  - Dificuldades para empacotar as dependências complexas em layers.

- **Solução implementada**:
  - Substituímos o NFTK por uma combinação de:
    1. Amazon Textract (para OCR básico).
    2. Processamento com regex (para extração de padrões).
    3. AWS Bedrock (para refinamento dos dados).

## Autores

- [Maria Eduarda da Nóbrega](https://github.com/eduardanb)
- [Vinícius França de Oliveira Sousa](https://github.com/marditin)
- [João Vitor Campõe Galescky](https://github.com/Joaogalescky) 
- [Gabriel Medeiros Nóbrega](https://github.com/Prozis-dev)
