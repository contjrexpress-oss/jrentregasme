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
            # Padrão NFe: "Nº 000.123.456" or "NF-e Nº" or "NOTA FISCAL"
            patterns_numero = [
                r'N[º°]\s*\.?\s*([\d\.]+)',
                r'NF-?e?\s*N[º°]?\s*\.?\s*([\d\.]+)',
                r'NOTA\s+FISCAL[\s\S]*?N[º°]\s*\.?\s*([\d\.]+)',
                r'(?:Número|NUMERO)\s*:?\s*([\d\.]+)',
                r'(?:DANFE|NFe)[\s\S]*?([\d]{3}\.?[\d]{3}\.?[\d]{3})',
                r'NF\s*[:-]?\s*(\d+)',
                r'PEDIDO\s*(?:INTERNO)?\s*N?[º°]?\s*:?\s*(\d+)',
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
            
            # === Extrair CEP ===
            patterns_cep = [
                r'CEP[:\s]*([\d]{5}[\-\.]?[\d]{3})',
                r'CEP[:\s]*(\d{8})',
                r'(\d{5})[\-\.](\d{3})',
            ]
            for pat in patterns_cep:
                m = re.search(pat, full_text, re.IGNORECASE)
                if m:
                    if m.lastindex == 2:
                        resultado['cep'] = m.group(1) + m.group(2)
                    else:
                        resultado['cep'] = re.sub(r'\D', '', m.group(1))
                    break
            
            # === Extrair itens ===
            # Strategy 1: Look for tables with code and quantity columns
            itens_encontrados = []
            
            for table in all_tables:
                if not table or len(table) < 2:
                    continue
                # Try to identify header row
                header = table[0] if table[0] else []
                header_str = ' '.join([str(h).upper() for h in header if h])
                
                cod_idx = None
                qtd_idx = None
                
                for i, h in enumerate(header):
                    if h is None:
                        continue
                    h_up = str(h).upper().strip()
                    if any(k in h_up for k in ['CÓDIGO', 'CODIGO', 'CÓD', 'COD']):
                        cod_idx = i
                    if any(k in h_up for k in ['QTDE', 'QTD', 'QUANT', 'QUANTIDADE']):
                        qtd_idx = i
                
                if cod_idx is not None and qtd_idx is not None:
                    for row in table[1:]:
                        if row and len(row) > max(cod_idx, qtd_idx):
                            codigo = str(row[cod_idx]).strip() if row[cod_idx] else ""
                            qtd_str = str(row[qtd_idx]).strip() if row[qtd_idx] else "0"
                            qtd_str = re.sub(r'[^\d,\.]', '', qtd_str).replace(',', '.')
                            try:
                                qtd = int(float(qtd_str)) if qtd_str else 0
                            except ValueError:
                                qtd = 0
                            if codigo and qtd > 0:
                                itens_encontrados.append((codigo, qtd))
            
            # Strategy 2: If no items from tables, try regex on text
            if not itens_encontrados:
                # Pattern: code (alphanumeric) followed by description and quantity
                lines = full_text.split('\n')
                for line in lines:
                    # Match lines with a product code pattern and a quantity
                    m = re.match(r'^\s*([A-Za-z0-9\-\.]+)\s+.+?\s+(\d+[,\.]?\d*)\s+(?:UN|PC|CX|KG|LT|MT)', line, re.IGNORECASE)
                    if m:
                        codigo = m.group(1).strip()
                        qtd_str = m.group(2).replace(',', '.')
                        try:
                            qtd = int(float(qtd_str))
                        except ValueError:
                            qtd = 0
                        if codigo and qtd > 0:
                            itens_encontrados.append((codigo, qtd))
            
            # Strategy 3: More aggressive pattern matching
            if not itens_encontrados:
                # Try matching any line with code-like pattern followed by numbers
                item_pattern = re.findall(
                    r'([A-Z]{2,}[\d]+[A-Z\d\-]*)\s+.*?(\d+)\s*(?:UN|PC|CX|PÇ|PÇS|PCS|UNID)',
                    full_text, re.IGNORECASE
                )
                for codigo, qtd_str in item_pattern:
                    try:
                        qtd = int(qtd_str)
                    except ValueError:
                        qtd = 0
                    if qtd > 0:
                        itens_encontrados.append((codigo.strip(), qtd))
            
            resultado['itens'] = itens_encontrados
    
    except Exception as e:
        resultado['erro'] = str(e)
    
    return resultado
