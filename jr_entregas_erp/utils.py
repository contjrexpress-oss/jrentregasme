import requests
import re
import pdfplumber
from io import BytesIO
from datetime import datetime


# ============ VALIDAÇÕES ============

def validar_data(data_str):
    """Valida formato de data (DD/MM/YYYY). Retorna (bool, mensagem)."""
    if not data_str or not str(data_str).strip():
        return False, "Data não informada"
    data_str = str(data_str).strip()
    # Aceitar separadores / - .
    data_limpa = data_str.replace('-', '/').replace('.', '/')
    try:
        dt = datetime.strptime(data_limpa, "%d/%m/%Y")
        # Verificar se data não é futura
        if dt > datetime.now():
            return False, f"Data '{data_str}' é uma data futura"
        # Verificar se data não é muito antiga (antes de 2020)
        if dt.year < 2020:
            return False, f"Data '{data_str}' é anterior a 2020"
        return True, "OK"
    except ValueError:
        return False, f"Formato de data inválido: '{data_str}' (esperado: DD/MM/AAAA)"


def validar_cep(cep_str):
    """Valida formato de CEP (8 dígitos). Retorna (bool, mensagem)."""
    if not cep_str or not str(cep_str).strip():
        return False, "CEP não informado"
    cep_limpo = re.sub(r'\D', '', str(cep_str))
    if len(cep_limpo) != 8:
        return False, f"CEP inválido: '{cep_str}' (deve ter 8 dígitos, encontrou {len(cep_limpo)})"
    if cep_limpo == '00000000':
        return False, "CEP inválido: '00000000'"
    return True, "OK"


def validar_numero_nota(numero_str):
    """Valida número da nota fiscal. Retorna (bool, mensagem)."""
    if not numero_str or not str(numero_str).strip():
        return False, "Número da nota não informado"
    numero_limpo = str(numero_str).strip()
    # Deve conter apenas dígitos (após limpeza de pontos)
    numero_digitos = numero_limpo.replace('.', '')
    if not numero_digitos.isdigit():
        return False, f"Número da nota inválido: '{numero_str}' (deve conter apenas dígitos)"
    if int(numero_digitos) <= 0:
        return False, f"Número da nota deve ser maior que zero"
    return True, "OK"


def validar_quantidade(qtd):
    """Valida se quantidade é um número positivo. Retorna (bool, mensagem)."""
    try:
        qtd_num = int(float(qtd))
        if qtd_num <= 0:
            return False, f"Quantidade deve ser positiva (encontrou: {qtd})"
        return True, "OK"
    except (ValueError, TypeError):
        return False, f"Quantidade inválida: '{qtd}' (deve ser um número)"


def validar_dados_nota(numero, data, cep, itens):
    """Valida todos os campos de uma nota. Retorna dict com resultados por campo."""
    resultados = {
        'campos_ok': [],
        'campos_aviso': [],
        'campos_erro': [],
        'itens_validos': 0,
        'itens_invalidos': 0,
        'valido': True  # indica se pode importar
    }

    # Número da nota
    ok, msg = validar_numero_nota(numero)
    if ok:
        resultados['campos_ok'].append(f"Nº Nota: {numero}")
    else:
        resultados['campos_erro'].append(f"Nº Nota: {msg}")
        resultados['valido'] = False

    # Data
    ok, msg = validar_data(data)
    if ok:
        resultados['campos_ok'].append(f"Data: {data}")
    elif not data:
        resultados['campos_aviso'].append(f"Data: {msg}")
    else:
        resultados['campos_erro'].append(f"Data: {msg}")

    # CEP
    ok, msg = validar_cep(cep)
    if ok:
        resultados['campos_ok'].append(f"CEP: {cep}")
    elif not cep:
        resultados['campos_aviso'].append(f"CEP: {msg}")
    else:
        resultados['campos_erro'].append(f"CEP: {msg}")

    # Itens
    if itens:
        for codigo, qtd in itens:
            ok_qtd, _ = validar_quantidade(qtd)
            if ok_qtd:
                resultados['itens_validos'] += 1
            else:
                resultados['itens_invalidos'] += 1
        resultados['campos_ok'].append(f"Itens: {resultados['itens_validos']} válido(s)")
        if resultados['itens_invalidos'] > 0:
            resultados['campos_aviso'].append(f"Itens: {resultados['itens_invalidos']} com quantidade inválida")
    else:
        resultados['campos_aviso'].append("Itens: Nenhum item extraído")

    return resultados


def buscar_cep(cep):
    """Busca bairro e município via API ViaCEP."""
    cep_limpo = re.sub(r'\D', '', str(cep))
    if len(cep_limpo) != 8:
        return None, None
    try:
        resp = requests.get(f"https://viacep.com.br/ws/{cep_limpo}/json/", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if 'erro' not in data:
                return data.get('bairro', ''), data.get('localidade', '')
    except Exception:
        pass
    return None, None


def calcular_faturamento(cep, total_unidades):
    """Calcula faturamento com base no CEP e quantidade total de unidades."""
    cep_num = int(re.sub(r'\D', '', str(cep))[:5])
    
    # Região 1: Centro/Santa Teresa/Estácio
    regiao1_ranges = [
        (20000, 20231),
    ]
    regiao1_exact = [20240, 20250, 20210]
    
    # Região 2: Zona Sul
    regiao2_ranges = [
        (22210, 22290),
        (22010, 22081),
        (22410, 22471),
    ]
    
    # Região 3: Tijuca/Vila Isabel
    regiao3_ranges = [
        (20510, 20561),
    ]
    
    # Região 4: Barra da Tijuca
    regiao4_ranges = [
        (22600, 22699),
    ]
    
    # Região 5: Recreio/Jacarepaguá
    regiao5_ranges = [
        (22790, 22795),
        (22710, 22775),
    ]
    
    def in_ranges(cep_val, ranges):
        for start, end in ranges:
            if start <= cep_val <= end:
                return True
        return False
    
    regiao = None
    nome_regiao = ""
    
    if in_ranges(cep_num, regiao1_ranges) or cep_num in regiao1_exact:
        regiao = 1
        nome_regiao = "Centro/Santa Teresa/Estácio"
    elif in_ranges(cep_num, regiao2_ranges):
        regiao = 2
        nome_regiao = "Zona Sul"
    elif in_ranges(cep_num, regiao3_ranges):
        regiao = 3
        nome_regiao = "Tijuca/Vila Isabel"
    elif in_ranges(cep_num, regiao4_ranges):
        regiao = 4
        nome_regiao = "Barra da Tijuca"
    elif in_ranges(cep_num, regiao5_ranges):
        regiao = 5
        nome_regiao = "Recreio/Jacarepaguá"
    
    if regiao is None:
        return None, None, None, None
    
    if regiao in [1, 2, 3]:
        if total_unidades <= 24:
            return 45.00, "Motoboy", nome_regiao, regiao
        else:
            return 120.00, "Carro", nome_regiao, regiao
    elif regiao == 4:
        if total_unidades <= 24:
            return 70.00, "Motoboy", nome_regiao, regiao
        else:
            return 170.00, "Carro", nome_regiao, regiao
    elif regiao == 5:
        if total_unidades <= 24:
            return 120.00, "Motoboy", nome_regiao, regiao
        else:
            return 240.00, "Carro", nome_regiao, regiao
    
    return None, None, None, None



def extrair_dados_danfe(pdf_file):
    """Extrai dados de uma DANFE (PDF) usando pdfplumber."""
    resultado = {
        'numero': None,
        'data': None,
        'cep': None,
        'itens': []  # list of (codigo, quantidade)
    }
    
    try:
        pdf_bytes = pdf_file.read()
        pdf_file.seek(0)
        
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            full_text = ""
            all_tables = []
            
            for page in pdf.pages:
                text = page.extract_text() or ""
                full_text += text + "\n"
                tables = page.extract_tables()
                if tables:
                    all_tables.extend(tables)
            
            # === Extrair número da nota ===
            # Prioridade 1: Pedido Interno (ex: "PED. INTERNO  32606")
            # Prioridade 2: NF-e com No. (ex: "NF-e\nNo. 001183")
            # Prioridade 3: Outros padrões genéricos
            patterns_numero = [
                # Pedido interno: "PED. INTERNO 32606" ou "PEDIDO INTERNO 32606"
                r'PED(?:IDO)?\.?\s*INTERNO\s*[:\s]*(\d+)',
                # NF-e No. 001183
                r'NF-?e\s*\n?\s*No\.?\s*(\d+)',
                # No. seguido de número (dentro de contexto NF-e)
                r'No\.?\s+(\d{3,})',
                # NÚMERO: 001183 ou Número: 001183
                r'(?:N[Úú]MERO|NUMERO)\s*:?\s*([\d\.]+)',
                # Nº seguido de número (formato com pontos: 000.123.456)
                r'N[º°]\s*\.?\s*([\d\.]{5,})',
                # NF-e Nº
                r'NF-?e?\s*N[º°]?\s*\.?\s*([\d\.]+)',
                # NOTA FISCAL ... Nº
                r'NOTA\s+FISCAL[\s\S]*?N[º°]\s*\.?\s*([\d\.]+)',
                # NF simples
                r'NF\s*[:-]?\s*(\d+)',
            ]
            for pat in patterns_numero:
                m = re.search(pat, full_text, re.IGNORECASE)
                if m:
                    resultado['numero'] = m.group(1).replace('.', '').strip()
                    break
            
            # === Extrair data ===
            patterns_data = [
                r'(?:EMISS[ÃA]O|DATA)[\s:]*?(\d{2}[/\-]\d{2}[/\-]\d{4})',
                r'(\d{2}/\d{2}/\d{4})',
                r'(\d{2}\.\d{2}\.\d{4})',
            ]
            for pat in patterns_data:
                m = re.search(pat, full_text, re.IGNORECASE)
                if m:
                    data_str = m.group(1).replace('-', '/').replace('.', '/')
                    resultado['data'] = data_str
                    break
            
            # === Extrair CEP do DESTINATÁRIO ===
            # Em uma DANFE, o CEP do destinatário fica na seção "DESTINATÁRIO / REMETENTE"
            # que aparece DEPOIS da seção do emitente. Precisamos extrair ESSE CEP.
            cep_dest = None
            
            # --- Estratégia 1: Localizar a seção DESTINATÁRIO e extrair CEP dela ---
            # Procurar o início da seção do destinatário
            dest_section_start = None
            dest_markers = [
                r'DESTINAT[ÁA]RIO\s*/?\s*REMETENTE',
                r'DESTINAT[ÁA]RIO',
            ]
            for marker in dest_markers:
                m = re.search(marker, full_text, re.IGNORECASE)
                if m:
                    dest_section_start = m.start()
                    break
            
            if dest_section_start is not None:
                # Extrair texto a partir do destinatário até a próxima seção grande
                # (FATURA, DADOS DO PRODUTO, CÁLCULO DO IMPOSTO, TRANSPORTADOR, etc.)
                dest_text = full_text[dest_section_start:]
                end_markers = [
                    r'\bFATURA\b',
                    r'\bDADOS\s+DO\s+PRODUTO\b',
                    r'\bDADOS\s+DOS\s+PRODUTOS\b',
                    r'\bC[ÁA]LCULO\s+DO\s+IMPOSTO\b',
                    r'\bTRANSPORTADOR\b',
                    r'\bINFORMA[ÇC][ÕO]ES\s+COMPLEMENT',
                    r'\bIMPOSTO\b',
                ]
                for end_marker in end_markers:
                    end_m = re.search(end_marker, dest_text[50:], re.IGNORECASE)
                    if end_m:
                        dest_text = dest_text[:50 + end_m.start()]
                        break
                
                # Buscar CEP dentro da seção do destinatário
                # Padrão com label "CEP"
                cep_match = re.search(r'CEP[:\s]*([\d]{5}[\-\.]?[\d]{3})', dest_text, re.IGNORECASE)
                if cep_match:
                    cep_dest = re.sub(r'\D', '', cep_match.group(1))
                else:
                    # Padrão sem label - formato XXXXX-XXX na seção
                    cep_match = re.search(r'(\d{5})[\-\.](\d{3})', dest_text)
                    if cep_match:
                        cep_dest = cep_match.group(1) + cep_match.group(2)
            
            # --- Estratégia 2: Buscar CEP em tabelas na seção do destinatário ---
            if not cep_dest:
                for table in all_tables:
                    if not table:
                        continue
                    for row in table:
                        if not row:
                            continue
                        row_str = ' '.join([str(c) for c in row if c])
                        row_upper = row_str.upper()
                        # Se a linha contém marcadores do destinatário E um CEP
                        if any(k in row_upper for k in ['DESTINAT', 'BAIRRO/DISTRITO', 'BAIRRO / DISTRITO']):
                            cep_m = re.search(r'(\d{5})[\-\.](\d{3})', row_str)
                            if cep_m:
                                cep_dest = cep_m.group(1) + cep_m.group(2)
                                break
                        # Se a célula individual tem label CEP seguido do valor
                        for cell in row:
                            if cell is None:
                                continue
                            cell_str = str(cell).strip()
                            cell_upper = cell_str.upper()
                            if 'CEP' in cell_upper:
                                cep_m = re.search(r'(\d{5})[\-\.]?(\d{3})', cell_str)
                                if cep_m:
                                    # Guarda como candidato, mas continua procurando
                                    # na seção do destinatário
                                    cep_dest = cep_m.group(1) + cep_m.group(2)
                    if cep_dest:
                        break
            
            # --- Estratégia 3: Coletar TODOS os CEPs e pegar o segundo (destinatário) ---
            # Em DANFEs, o primeiro CEP é do emitente e o segundo do destinatário
            if not cep_dest:
                all_ceps = re.findall(r'(\d{5})[\-\.](\d{3})', full_text)
                if len(all_ceps) >= 2:
                    # Segundo CEP = destinatário
                    cep_dest = all_ceps[1][0] + all_ceps[1][1]
                elif len(all_ceps) == 1:
                    cep_dest = all_ceps[0][0] + all_ceps[0][1]
            
            resultado['cep'] = cep_dest
            
            # === Extrair itens ===
            # Os códigos de produto seguem o formato "P" + 6 dígitos (ex: P000058, P000225)
            itens_encontrados = []
            
            # Strategy 1: Extrair de tabelas do PDF
            for table in all_tables:
                if not table or len(table) < 2:
                    continue
                
                # Tentar identificar a linha de cabeçalho
                # Verificar cada linha como possível cabeçalho
                header_row_idx = None
                cod_idx = None
                qtd_idx = None
                
                for row_idx, row in enumerate(table):
                    if not row:
                        continue
                    row_str = ' '.join([str(c).upper() for c in row if c])
                    
                    # Verificar se esta linha contém cabeçalhos de código de produto
                    temp_cod_idx = None
                    temp_qtd_idx = None
                    
                    for i, cell in enumerate(row):
                        if cell is None:
                            continue
                        cell_up = str(cell).upper().strip()
                        if any(k in cell_up for k in ['CÓDIGO PRODUTO', 'CODIGO PRODUTO',
                                'COD. PRODUTO', 'COD PRODUTO', 'CÓDIGO', 'CODIGO',
                                'CÓD. PROD', 'COD. PROD', 'CÓD', 'COD']):
                            temp_cod_idx = i
                        if any(k in cell_up for k in ['QTDE', 'QTD', 'QUANT', 'QUANTIDADE',
                                'QTD.', 'QTDE.']):
                            temp_qtd_idx = i
                    
                    if temp_cod_idx is not None:
                        header_row_idx = row_idx
                        cod_idx = temp_cod_idx
                        qtd_idx = temp_qtd_idx
                        break
                
                if cod_idx is not None:
                    for row in table[header_row_idx + 1:]:
                        if not row or len(row) <= cod_idx:
                            continue
                        codigo = str(row[cod_idx]).strip() if row[cod_idx] else ""
                        
                        # Extrair código no formato P + 6 dígitos da célula
                        cod_match = re.search(r'(P\d{6})', codigo, re.IGNORECASE)
                        if cod_match:
                            codigo = cod_match.group(1).upper()
                        elif not re.match(r'^P\d{6}$', codigo, re.IGNORECASE):
                            # Se não parece um código válido, pular
                            continue
                        
                        # Extrair quantidade
                        qtd = 1  # Default: 1 unidade se não encontrar qtd
                        if qtd_idx is not None and len(row) > qtd_idx and row[qtd_idx]:
                            qtd_str = str(row[qtd_idx]).strip()
                            qtd_str = re.sub(r'[^\d,\.]', '', qtd_str).replace(',', '.')
                            try:
                                qtd = int(float(qtd_str)) if qtd_str else 1
                            except ValueError:
                                qtd = 1
                        
                        if codigo and qtd > 0:
                            itens_encontrados.append((codigo, qtd))
            
            # Strategy 2: Buscar códigos P+6dígitos diretamente no texto
            if not itens_encontrados:
                # Localizar seção de produtos no texto
                # Procurar após "DADOS DO PRODUTO", "CÓDIGO PRODUTO", etc.
                produto_section = full_text
                section_markers = [
                    r'DADOS\s+DO\s+PRODUTO',
                    r'DADOS\s+DOS\s+PRODUTOS',
                    r'C[ÓO]DIGO\s+PRODUTO',
                    r'COD\.?\s+PRODUTO',
                ]
                for marker in section_markers:
                    m = re.search(marker, full_text, re.IGNORECASE)
                    if m:
                        produto_section = full_text[m.start():]
                        break
                
                # Buscar todos os códigos P + 6 dígitos na seção de produtos
                codigos_found = re.findall(r'(P\d{6})', produto_section, re.IGNORECASE)
                
                if codigos_found:
                    # Para cada código, tentar encontrar a quantidade associada
                    lines = produto_section.split('\n')
                    for line in lines:
                        cod_in_line = re.findall(r'(P\d{6})', line, re.IGNORECASE)
                        for cod in cod_in_line:
                            cod = cod.upper()
                            # Tentar extrair quantidade da mesma linha
                            # Padrão: código ... quantidade ... UN/PC/CX etc.
                            qtd = 1
                            qtd_match = re.search(
                                r'(?:' + re.escape(cod) + r')\s+.*?(\d+[,\.]?\d*)\s*(?:UN|PC|CX|KG|LT|MT|PÇ|PCS|UNID)',
                                line, re.IGNORECASE
                            )
                            if qtd_match:
                                qtd_str = qtd_match.group(1).replace(',', '.')
                                try:
                                    qtd = int(float(qtd_str))
                                except ValueError:
                                    qtd = 1
                            if qtd > 0:
                                itens_encontrados.append((cod, qtd))
                    
                    # Se encontrou códigos mas não conseguiu parear com linhas,
                    # adicionar cada código com quantidade 1
                    if not itens_encontrados and codigos_found:
                        for cod in codigos_found:
                            itens_encontrados.append((cod.upper(), 1))
            
            # Strategy 3: Regex genérico para códigos alfanuméricos + quantidade
            if not itens_encontrados:
                # Tentar padrão genérico: código alfanumérico + descrição + qtd + unidade
                lines = full_text.split('\n')
                for line in lines:
                    m = re.match(
                        r'^\s*\d*\s*([A-Za-z]\d{4,}[A-Za-z\d\-]*)\s+.+?\s+(\d+[,\.]?\d*)\s+(?:UN|PC|CX|KG|LT|MT|PÇ|PCS|UNID)',
                        line, re.IGNORECASE
                    )
                    if m:
                        codigo = m.group(1).strip().upper()
                        qtd_str = m.group(2).replace(',', '.')
                        try:
                            qtd = int(float(qtd_str))
                        except ValueError:
                            qtd = 0
                        if codigo and qtd > 0:
                            itens_encontrados.append((codigo, qtd))
            
            # Strategy 4: Mais agressivo - qualquer código seguido de números
            if not itens_encontrados:
                item_pattern = re.findall(
                    r'([A-Z]\d{4,}[A-Z\d\-]*)\s+.*?(\d+)\s*(?:UN|PC|CX|PÇ|PÇS|PCS|UNID)',
                    full_text, re.IGNORECASE
                )
                for codigo, qtd_str in item_pattern:
                    try:
                        qtd = int(qtd_str)
                    except ValueError:
                        qtd = 0
                    if qtd > 0:
                        itens_encontrados.append((codigo.strip().upper(), qtd))
            
            # Deduplicar: agrupar por código, somando quantidades
            if itens_encontrados:
                itens_dict = {}
                for codigo, qtd in itens_encontrados:
                    if codigo in itens_dict:
                        itens_dict[codigo] += qtd
                    else:
                        itens_dict[codigo] = qtd
                resultado['itens'] = [(cod, qtd) for cod, qtd in itens_dict.items()]
            else:
                resultado['itens'] = []
    
    except Exception as e:
        resultado['erro'] = str(e)
    
    return resultado
