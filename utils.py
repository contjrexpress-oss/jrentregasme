import requests
import re
import pdfplumber
from io import BytesIO


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
            # Estratégia: localizar a seção do destinatário e extrair o CEP de lá
            # Em uma DANFE, o destinatário aparece DEPOIS do emitente
            cep_dest = None
            
            # Tentar encontrar seção do destinatário e pegar CEP dela
            # Padrão 1: Buscar CEP após marcadores de destinatário
            dest_patterns = [
                # CEP que aparece após "DESTINATÁRIO" ou "DEST" no texto
                r'DESTINAT[ÁA]RIO.*?CEP[:\s]*([\d]{5}[\-\.]?[\d]{3})',
                r'DEST(?:INAT[ÁA]RIO)?.*?CEP[:\s]*([\d]{5}[\-\.]?[\d]{3})',
                # CEP que aparece após "DATA ENTRADA" ou "ENTRADA/SAÍDA" (seção do dest)
                r'DATA\s+ENTRADA.*?CEP[:\s]*([\d]{5}[\-\.]?[\d]{3})',
                r'ENTRADA/?SA[ÍI]DA.*?CEP[:\s]*([\d]{5}[\-\.]?[\d]{3})',
            ]
            for pat in dest_patterns:
                m = re.search(pat, full_text, re.IGNORECASE | re.DOTALL)
                if m:
                    cep_dest = re.sub(r'\D', '', m.group(1))
                    break
            
            # Padrão 2: Coletar TODOS os CEPs e pegar o segundo (destinatário)
            # Em DANFEs, o primeiro CEP é do emitente e o segundo do destinatário
            if not cep_dest:
                all_ceps = re.findall(r'CEP[:\s]*([\d]{5}[\-\.]?[\d]{3})', full_text, re.IGNORECASE)
                if not all_ceps:
                    all_ceps = re.findall(r'(\d{5}[\-\.]\d{3})', full_text)
                
                if len(all_ceps) >= 2:
                    # Segundo CEP = destinatário
                    cep_dest = re.sub(r'\D', '', all_ceps[1])
                elif len(all_ceps) == 1:
                    # Se só tem um, usa esse mesmo
                    cep_dest = re.sub(r'\D', '', all_ceps[0])
            
            # Padrão 3: CEP sem label (8 dígitos consecutivos no formato XXXXX-XXX)
            if not cep_dest:
                m = re.search(r'(\d{5})[\-\.](\d{3})', full_text)
                if m:
                    cep_dest = m.group(1) + m.group(2)
            
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
