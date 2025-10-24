import boto3
import uuid
import base64
import json
import re

s3 = boto3.client('s3')
textract = boto3.client('textract')
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')  # Ajuste a região conforme necessário

BUCKET_NAME = 'sprint-4-5-6-squad4'

def lambda_handler(event, context):
    try:
        # Obtem tipo de conteúdo e decodifica
        content_type = event['headers'].get('content-type') or event['headers'].get('Content-Type')
        body = base64.b64decode(event['body'])

        # Extrai o arquivo da estrutura multipart/form-data
        boundary = content_type.split("boundary=")[1]
        parts = body.split(("--" + boundary).encode())

        file_bytes = None
        for part in parts:
            if b"filename=" in part:
                start = part.find(b"\r\n\r\n") + 4
                file_bytes = part[start:].strip()
                break

        if not file_bytes:
            return {
                "statusCode": 400,
                "body": json.dumps({"erro": "Arquivo não encontrado no corpo da requisição"})
            }

        # Envia para o S3
        file_name = f"nota-{uuid.uuid4()}.jpg"
        s3.put_object(Bucket=BUCKET_NAME, Key=file_name, Body=file_bytes)

        # Extrai texto do Textract
        response = textract.detect_document_text(
            Document={"S3Object": {"Bucket": BUCKET_NAME, "Name": file_name}}
        )
        linhas = [block["Text"] for block in response["Blocks"] if block["BlockType"] == "LINE"]
        texto_nota = "\n".join(linhas)

        # Extração inicial com regex
        resultado_inicial = extrair_dados_com_regex(texto_nota)
        
        # Refina os dados com o Bedrock
        resultado_refinado = refinar_com_bedrock(texto_nota, resultado_inicial)
        
        # Classifica a forma de pagamento e move para pasta adequada
        forma_pgto = resultado_refinado.get('forma_pgto', '').lower()
        if 'dinheiro' in forma_pgto or 'pix' in forma_pgto:
            new_key = f"dinheiro/{file_name}"
        else:
            new_key = f"outros/{file_name}"
            
        s3.copy_object(Bucket=BUCKET_NAME, CopySource={'Bucket': BUCKET_NAME, 'Key': file_name}, Key=new_key)
        s3.delete_object(Bucket=BUCKET_NAME, Key=file_name)

        return {
            "statusCode": 200,
            "body": json.dumps(resultado_refinado, ensure_ascii=False)
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"erro": str(e)})
        }

def extrair_dados_com_regex(texto):
    """Função para extração inicial com regex (mantendo sua lógica original)"""
    def buscar(regex, flags=re.IGNORECASE):
        match = re.search(regex, texto, flags)
        return match.group(1).strip() if match else None

    # Nome do emissor
    nome_emissor = buscar(r"(?:Emitente|Raz[aã]o Social|Empresa)[:\s]*([^\n]+)")
    if not nome_emissor:
        # Se não achar pelo rótulo, pega a linha anterior ao CNPJ
        cnpj_match = re.search(r"CNPJ[:\s]*([\d./-]+)", texto, re.IGNORECASE)
        if cnpj_match:
            idx = texto.find(cnpj_match.group(0))
            parte_antes = texto[:idx].strip().split("\n")
            if parte_antes:
                nome_emissor = parte_antes[-1].strip()

    resultado = {
        "nome_emissor": nome_emissor,
        "CNPJ_emissor": buscar(r"CNPJ[:\s]*([\d./-]+)"),
        "endereco_emissor": buscar(r"(?:End(?:\.|ereco|ereço)?|Local)[:\s]*([^\n]+)"),
        "CNPJ_CPF_consumidor": buscar(r"(?:Consumidor|CPF|CNPJ\s*do\s*consumidor)[:\s]*([\d./-]+)"),
        "data_emissao": buscar(r"(\d{2}[-/\.]\d{2}[-/\.]\d{4})"),
        "numero_nota_fiscal": buscar(r"(?:N[ºo]|Número|Nota Fiscal|No\.)[:\s]*([\d]+)"),
        "serie_nota_fiscal": buscar(r"S[ée]rie[:\s]*([\w\d]+)"),
        "valor_total": None,
        "forma_pgto": buscar(r"(Dinheiro|Cr[eé]dito|D[eé]bito|PIX|Boleto|Transfer[eê]ncia)")
    }

    # Valor total: pega última ocorrência
    valores_total = re.findall(r"TOTAL\s*R?\$?\s*([\d.,]+)", texto, re.IGNORECASE)
    if valores_total:
        resultado["valor_total"] = valores_total[-1].strip()

    return resultado

def refinar_com_bedrock(texto_nota, dados_iniciais):
    """Função para refinar os dados extraídos usando o AWS Bedrock"""
    prompt = f"""
    Você é um assistente especializado em processar notas fiscais eletrônicas. 
    Abaixo está o texto extraído de uma nota fiscal e alguns dados preliminares:

    TEXTO DA NOTA:
    {texto_nota}

    DADOS EXTRAÍDOS INICIALMENTE:
    {json.dumps(dados_iniciais, indent=2)}

    Sua tarefa é:
    1. Validar e corrigir os dados extraídos inicialmente
    2. Completar qualquer campo que esteja faltando ou marcado como None
    3. Padronizar os formatos (ex: data como DD/MM/AAAA, CNPJ como XX.XXX.XXX/XXXX-XX)
    4. Identificar claramente a forma de pagamento (dinheiro/pix/outros)

    Retorne APENAS um JSON com os seguintes campos:
    {{
        "nome_emissor": "Nome completo do emissor",
        "CNPJ_emissor": "CNPJ formatado",
        "endereco_emissor": "Endereço completo",
        "CNPJ_CPF_consumidor": "CPF ou CNPJ formatado",
        "data_emissao": "Data formatada",
        "numero_nota_fiscal": "Número da nota",
        "serie_nota_fiscal": "Série da nota",
        "valor_total": "Valor total",
        "forma_pgto": "dinheiro/pix/outros"
    }}
    """

    try:
        # Configuração para o modelo DeepSeek
        body = json.dumps({
            "prompt": prompt,
            "max_tokens": 1000,
            "temperature": 0.3  # Menos criatividade, mais precisão
        })

        response = bedrock.invoke_model(
            modelId='us.deepseek.r1-v1:0',
            body=body
        )

        response_body = json.loads(response['body'].read())
        resultado_refinado = json.loads(response_body.get('generated_text', '{}'))
        
        # Garante que todos os campos estejam presentes
        for campo in dados_iniciais.keys():
            if campo not in resultado_refinado:
                resultado_refinado[campo] = dados_iniciais[campo]
                
        return resultado_refinado

    except Exception as e:
        print(f"Erro ao chamar Bedrock: {str(e)}")
        return dados_iniciais  # Retorna os dados originais se houver erro