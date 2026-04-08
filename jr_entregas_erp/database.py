import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = "jr_entregas.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    # Tabela de produtos
    c.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            codigo TEXT PRIMARY KEY,
            descricao TEXT NOT NULL,
            estoque_inicial INTEGER DEFAULT 0,
            estoque_minimo INTEGER DEFAULT 0,
            estoque_maximo INTEGER DEFAULT NULL
        )
    """)
    
    # Tabela de notas fiscais
    c.execute("""
        CREATE TABLE IF NOT EXISTS notas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT NOT NULL,
            data_nota TEXT,
            cep TEXT,
            bairro TEXT,
            municipio TEXT,
            tipo TEXT NOT NULL CHECK(tipo IN ('entrada', 'saida')),
            total_unidades INTEGER DEFAULT 0,
            data_importacao TEXT NOT NULL,
            arquivo_nome TEXT
        )
    """)
    
    # Tabela de itens da nota
    c.execute("""
        CREATE TABLE IF NOT EXISTS itens_nota (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nota_id INTEGER NOT NULL,
            codigo_produto TEXT NOT NULL,
            quantidade INTEGER NOT NULL,
            FOREIGN KEY (nota_id) REFERENCES notas(id) ON DELETE CASCADE,
            FOREIGN KEY (codigo_produto) REFERENCES produtos(codigo)
        )
    """)
    
    # Tabela de faturamento
    c.execute("""
        CREATE TABLE IF NOT EXISTS faturamento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nota_id INTEGER,
            data TEXT NOT NULL,
            descricao TEXT,
            regiao TEXT,
            veiculo TEXT,
            valor REAL NOT NULL,
            cep TEXT,
            bairro TEXT,
            municipio TEXT,
            cliente TEXT DEFAULT '',
            FOREIGN KEY (nota_id) REFERENCES notas(id) ON DELETE CASCADE
        )
    """)
    
    # Migração: adicionar coluna cliente se não existir
    try:
        c.execute("SELECT cliente FROM faturamento LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE faturamento ADD COLUMN cliente TEXT DEFAULT ''")
    
    # Migração: adicionar colunas estoque_minimo e estoque_maximo na tabela produtos
    try:
        c.execute("SELECT estoque_minimo FROM produtos LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE produtos ADD COLUMN estoque_minimo INTEGER DEFAULT 0")
    try:
        c.execute("SELECT estoque_maximo FROM produtos LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE produtos ADD COLUMN estoque_maximo INTEGER DEFAULT NULL")
    
    # Tabela de custos
    c.execute("""
        CREATE TABLE IF NOT EXISTS custos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            descricao TEXT NOT NULL,
            categoria TEXT,
            valor REAL NOT NULL
        )
    """)
    
    # Tabela de histórico de notas excluídas
    c.execute("""
        CREATE TABLE IF NOT EXISTS notas_excluidas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_nota TEXT NOT NULL,
            data_nota TEXT,
            tipo TEXT,
            total_unidades INTEGER,
            arquivo_nome TEXT,
            motivo TEXT,
            data_exclusao TEXT NOT NULL,
            usuario TEXT
        )
    """)
    
    # ============ FASE 5: NOVAS TABELAS ============
    
    # Tabela de categorias de custos
    c.execute("""
        CREATE TABLE IF NOT EXISTS categorias_custos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            cor TEXT DEFAULT '#718096',
            ativo INTEGER DEFAULT 1
        )
    """)
    
    # Tabela de subcategorias de custos
    c.execute("""
        CREATE TABLE IF NOT EXISTS subcategorias_custos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            categoria_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            ativo INTEGER DEFAULT 1,
            FOREIGN KEY (categoria_id) REFERENCES categorias_custos(id) ON DELETE CASCADE
        )
    """)
    
    # Tabela de contas a pagar/receber
    c.execute("""
        CREATE TABLE IF NOT EXISTS contas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL CHECK(tipo IN ('pagar', 'receber')),
            descricao TEXT NOT NULL,
            valor REAL NOT NULL,
            data_vencimento TEXT NOT NULL,
            data_pagamento TEXT,
            status TEXT NOT NULL DEFAULT 'pendente' CHECK(status IN ('pendente', 'pago', 'atrasado', 'cancelado')),
            categoria_id INTEGER,
            observacoes TEXT DEFAULT '',
            data_criacao TEXT NOT NULL,
            FOREIGN KEY (categoria_id) REFERENCES categorias_custos(id)
        )
    """)
    
    # Migração: adicionar colunas categoria_id e subcategoria_id na tabela custos
    try:
        c.execute("SELECT categoria_id FROM custos LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE custos ADD COLUMN categoria_id INTEGER DEFAULT NULL")
    try:
        c.execute("SELECT subcategoria_id FROM custos LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE custos ADD COLUMN subcategoria_id INTEGER DEFAULT NULL")
    
    # Inserir categorias padrão se não existirem
    categorias_padrao = [
        ("Veículo", "#3182CE"),
        ("Operacional", "#38A169"),
        ("Administrativo", "#805AD5"),
        ("Outros", "#718096"),
    ]
    for nome, cor in categorias_padrao:
        existing = c.execute("SELECT id FROM categorias_custos WHERE nome = ?", (nome,)).fetchone()
        if not existing:
            c.execute("INSERT INTO categorias_custos (nome, cor) VALUES (?, ?)", (nome, cor))
    
    # Inserir subcategorias padrão se não existirem
    subcategorias_padrao = {
        "Veículo": ["Combustível", "Manutenção", "Seguro", "IPVA/Licenciamento", "Multas"],
        "Operacional": ["Embalagens", "Pedágio", "Estacionamento", "Alimentação"],
        "Administrativo": ["Aluguel", "Internet/Telefone", "Contador", "Software"],
        "Outros": ["Diversos"],
    }
    for cat_nome, subcats in subcategorias_padrao.items():
        cat_row = c.execute("SELECT id FROM categorias_custos WHERE nome = ?", (cat_nome,)).fetchone()
        if cat_row:
            cat_id = cat_row[0]
            for sub_nome in subcats:
                existing = c.execute(
                    "SELECT id FROM subcategorias_custos WHERE categoria_id = ? AND nome = ?",
                    (cat_id, sub_nome)
                ).fetchone()
                if not existing:
                    c.execute("INSERT INTO subcategorias_custos (categoria_id, nome) VALUES (?, ?)",
                              (cat_id, sub_nome))
    
    conn.commit()
    conn.close()

# ============ PRODUTOS ============
def inserir_produtos(lista_produtos):
    """lista_produtos: list of (codigo, descricao)"""
    conn = get_connection()
    c = conn.cursor()
    inseridos = 0
    atualizados = 0
    for codigo, descricao in lista_produtos:
        codigo = str(codigo).strip()
        descricao = str(descricao).strip()
        existing = c.execute("SELECT codigo FROM produtos WHERE codigo = ?", (codigo,)).fetchone()
        if existing:
            c.execute("UPDATE produtos SET descricao = ? WHERE codigo = ?", (descricao, codigo))
            atualizados += 1
        else:
            c.execute("INSERT INTO produtos (codigo, descricao, estoque_inicial) VALUES (?, ?, 0)", (codigo, descricao))
            inseridos += 1
    conn.commit()
    conn.close()
    return inseridos, atualizados

def get_produtos():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM produtos ORDER BY codigo").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def produto_existe(codigo):
    conn = get_connection()
    r = conn.execute("SELECT codigo FROM produtos WHERE codigo = ?", (str(codigo).strip(),)).fetchone()
    conn.close()
    return r is not None

def atualizar_estoque_inicial(codigo, valor):
    conn = get_connection()
    conn.execute("UPDATE produtos SET estoque_inicial = ? WHERE codigo = ?", (valor, codigo))
    conn.commit()
    conn.close()

def atualizar_limites_estoque(codigo, estoque_minimo, estoque_maximo=None):
    """Atualiza os limites de estoque mínimo e máximo de um produto."""
    conn = get_connection()
    conn.execute("UPDATE produtos SET estoque_minimo = ?, estoque_maximo = ? WHERE codigo = ?",
                 (estoque_minimo, estoque_maximo, codigo))
    conn.commit()
    conn.close()

def atualizar_limites_estoque_lote(lista_limites):
    """Atualiza limites de estoque em lote.
    lista_limites: list of (codigo, estoque_minimo, estoque_maximo)
    """
    conn = get_connection()
    c = conn.cursor()
    atualizados = 0
    erros = []
    for codigo, est_min, est_max in lista_limites:
        codigo = str(codigo).strip()
        existing = c.execute("SELECT codigo FROM produtos WHERE codigo = ?", (codigo,)).fetchone()
        if existing:
            c.execute("UPDATE produtos SET estoque_minimo = ?, estoque_maximo = ? WHERE codigo = ?",
                       (est_min, est_max, codigo))
            atualizados += 1
        else:
            erros.append(codigo)
    conn.commit()
    conn.close()
    return atualizados, erros

def obter_produtos_estoque_baixo():
    """Retorna lista de produtos com estoque atual abaixo do estoque mínimo."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT 
            p.codigo,
            p.descricao,
            p.estoque_inicial,
            p.estoque_minimo,
            p.estoque_maximo,
            COALESCE(SUM(CASE WHEN n.tipo = 'entrada' THEN in2.quantidade ELSE 0 END), 0) as entradas,
            COALESCE(SUM(CASE WHEN n.tipo = 'saida' THEN in2.quantidade ELSE 0 END), 0) as saidas
        FROM produtos p
        LEFT JOIN itens_nota in2 ON p.codigo = in2.codigo_produto
        LEFT JOIN notas n ON in2.nota_id = n.id
        GROUP BY p.codigo, p.descricao, p.estoque_inicial, p.estoque_minimo, p.estoque_maximo
        HAVING (p.estoque_inicial + entradas - saidas) < p.estoque_minimo AND p.estoque_minimo > 0
        ORDER BY (p.estoque_inicial + entradas - saidas) - p.estoque_minimo ASC
    """).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d['estoque_atual'] = d['estoque_inicial'] + d['entradas'] - d['saidas']
        d['repor'] = d['estoque_minimo'] - d['estoque_atual']
        result.append(d)
    return result

# ============ NOTAS ============
def inserir_nota(numero, data_nota, cep, bairro, municipio, tipo, total_unidades, arquivo_nome, itens):
    """itens: list of (codigo_produto, quantidade)"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO notas (numero, data_nota, cep, bairro, municipio, tipo, total_unidades, data_importacao, arquivo_nome)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (numero, data_nota, cep, bairro, municipio, tipo, total_unidades, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), arquivo_nome))
    nota_id = c.lastrowid
    for codigo_produto, quantidade in itens:
        c.execute("INSERT INTO itens_nota (nota_id, codigo_produto, quantidade) VALUES (?, ?, ?)",
                  (nota_id, str(codigo_produto).strip(), quantidade))
    conn.commit()
    conn.close()
    return nota_id

def get_notas():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM notas ORDER BY data_importacao DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_nota_by_id(nota_id):
    conn = get_connection()
    r = conn.execute("SELECT * FROM notas WHERE id = ?", (nota_id,)).fetchone()
    conn.close()
    return dict(r) if r else None

def get_itens_nota(nota_id):
    conn = get_connection()
    rows = conn.execute("""
        SELECT in2.*, p.descricao 
        FROM itens_nota in2 
        LEFT JOIN produtos p ON in2.codigo_produto = p.codigo 
        WHERE in2.nota_id = ?
    """, (nota_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def excluir_nota(nota_id, motivo="", usuario=""):
    conn = get_connection()
    c = conn.cursor()
    nota = c.execute("SELECT * FROM notas WHERE id = ?", (nota_id,)).fetchone()
    if nota:
        nota = dict(nota)
        c.execute("""
            INSERT INTO notas_excluidas (numero_nota, data_nota, tipo, total_unidades, arquivo_nome, motivo, data_exclusao, usuario)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (nota['numero'], nota['data_nota'], nota['tipo'], nota['total_unidades'], 
              nota['arquivo_nome'], motivo, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), usuario))
        # CASCADE will delete itens_nota and faturamento
        c.execute("DELETE FROM notas WHERE id = ?", (nota_id,))
    conn.commit()
    conn.close()

def get_notas_excluidas():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM notas_excluidas ORDER BY data_exclusao DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def nota_existe(numero, data_nota=None, tipo=None):
    """Verifica se uma nota com mesmo número (e opcionalmente mesma data/tipo) já existe.
    Retorna dict da nota se existir, None caso contrário."""
    conn = get_connection()
    query = "SELECT * FROM notas WHERE numero = ?"
    params = [str(numero).strip()]
    if data_nota:
        query += " AND data_nota = ?"
        params.append(str(data_nota).strip())
    if tipo:
        query += " AND tipo = ?"
        params.append(str(tipo).strip())
    row = conn.execute(query, params).fetchone()
    conn.close()
    return dict(row) if row else None

# ============ ESTOQUE ============
def get_estoque():
    conn = get_connection()
    rows = conn.execute("""
        SELECT 
            p.codigo,
            p.descricao,
            p.estoque_inicial,
            COALESCE(p.estoque_minimo, 0) as estoque_minimo,
            p.estoque_maximo,
            COALESCE(SUM(CASE WHEN n.tipo = 'entrada' THEN in2.quantidade ELSE 0 END), 0) as entradas,
            COALESCE(SUM(CASE WHEN n.tipo = 'saida' THEN in2.quantidade ELSE 0 END), 0) as saidas
        FROM produtos p
        LEFT JOIN itens_nota in2 ON p.codigo = in2.codigo_produto
        LEFT JOIN notas n ON in2.nota_id = n.id
        GROUP BY p.codigo, p.descricao, p.estoque_inicial, p.estoque_minimo, p.estoque_maximo
        ORDER BY p.codigo
    """).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d['estoque_atual'] = d['estoque_inicial'] + d['entradas'] - d['saidas']
        # Calcular status do estoque
        est_min = d['estoque_minimo'] or 0
        if est_min > 0:
            if d['estoque_atual'] < est_min:
                d['status'] = 'critico'
            elif d['estoque_atual'] <= est_min * 1.2:
                d['status'] = 'atencao'
            else:
                d['status'] = 'ok'
        else:
            d['status'] = 'sem_limite'
        result.append(d)
    return result

# ============ FATURAMENTO ============
def inserir_faturamento(nota_id, data, descricao, regiao, veiculo, valor, cep, bairro, municipio, cliente=""):
    conn = get_connection()
    conn.execute("""
        INSERT INTO faturamento (nota_id, data, descricao, regiao, veiculo, valor, cep, bairro, municipio, cliente)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (nota_id, data, descricao, regiao, veiculo, valor, cep, bairro, municipio, cliente or ""))
    conn.commit()
    conn.close()

def get_faturamento():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM faturamento ORDER BY data DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def atualizar_faturamento(faturamento_id, descricao=None, valor=None, cliente=None, data=None, regiao=None, veiculo=None, cep=None, bairro=None, municipio=None):
    conn = get_connection()
    updates = []
    params = []
    if descricao is not None:
        updates.append("descricao = ?")
        params.append(descricao)
    if valor is not None:
        updates.append("valor = ?")
        params.append(valor)
    if cliente is not None:
        updates.append("cliente = ?")
        params.append(cliente)
    if data is not None:
        updates.append("data = ?")
        params.append(data)
    if regiao is not None:
        updates.append("regiao = ?")
        params.append(regiao)
    if veiculo is not None:
        updates.append("veiculo = ?")
        params.append(veiculo)
    if cep is not None:
        updates.append("cep = ?")
        params.append(cep)
    if bairro is not None:
        updates.append("bairro = ?")
        params.append(bairro)
    if municipio is not None:
        updates.append("municipio = ?")
        params.append(municipio)
    if updates:
        params.append(faturamento_id)
        conn.execute(f"UPDATE faturamento SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
    conn.close()

def deletar_faturamento(faturamento_id):
    conn = get_connection()
    conn.execute("DELETE FROM faturamento WHERE id = ?", (faturamento_id,))
    conn.commit()
    conn.close()

# ============ CUSTOS ============
def inserir_custo(data, descricao, categoria, valor):
    conn = get_connection()
    conn.execute("INSERT INTO custos (data, descricao, categoria, valor) VALUES (?, ?, ?, ?)",
                 (data, descricao, categoria, valor))
    conn.commit()
    conn.close()

def get_custos():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM custos ORDER BY data DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def atualizar_custo(custo_id, data, descricao, categoria, valor):
    conn = get_connection()
    conn.execute("UPDATE custos SET data = ?, descricao = ?, categoria = ?, valor = ? WHERE id = ?",
                 (data, descricao, categoria, valor, custo_id))
    conn.commit()
    conn.close()

def deletar_custo(custo_id):
    conn = get_connection()
    conn.execute("DELETE FROM custos WHERE id = ?", (custo_id,))
    conn.commit()
    conn.close()

# ============ CATEGORIAS DE CUSTOS ============
def get_categorias_custos(apenas_ativas=True):
    conn = get_connection()
    query = "SELECT * FROM categorias_custos"
    if apenas_ativas:
        query += " WHERE ativo = 1"
    query += " ORDER BY nome"
    rows = conn.execute(query).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_subcategorias_custos(categoria_id=None, apenas_ativas=True):
    conn = get_connection()
    query = "SELECT s.*, c.nome as categoria_nome FROM subcategorias_custos s LEFT JOIN categorias_custos c ON s.categoria_id = c.id"
    conditions = []
    params = []
    if categoria_id:
        conditions.append("s.categoria_id = ?")
        params.append(categoria_id)
    if apenas_ativas:
        conditions.append("s.ativo = 1")
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY c.nome, s.nome"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def inserir_categoria_custo(nome, cor="#718096"):
    conn = get_connection()
    try:
        conn.execute("INSERT INTO categorias_custos (nome, cor) VALUES (?, ?)", (nome.strip(), cor))
        conn.commit()
        conn.close()
        return True, "Categoria criada com sucesso."
    except sqlite3.IntegrityError:
        conn.close()
        return False, "Já existe uma categoria com esse nome."

def atualizar_categoria_custo(cat_id, nome=None, cor=None, ativo=None):
    conn = get_connection()
    updates = []
    params = []
    if nome is not None:
        updates.append("nome = ?")
        params.append(nome.strip())
    if cor is not None:
        updates.append("cor = ?")
        params.append(cor)
    if ativo is not None:
        updates.append("ativo = ?")
        params.append(1 if ativo else 0)
    if updates:
        params.append(cat_id)
        conn.execute(f"UPDATE categorias_custos SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
    conn.close()

def inserir_subcategoria_custo(categoria_id, nome):
    conn = get_connection()
    existing = conn.execute(
        "SELECT id FROM subcategorias_custos WHERE categoria_id = ? AND nome = ?",
        (categoria_id, nome.strip())
    ).fetchone()
    if existing:
        conn.close()
        return False, "Já existe uma subcategoria com esse nome nesta categoria."
    conn.execute("INSERT INTO subcategorias_custos (categoria_id, nome) VALUES (?, ?)",
                 (categoria_id, nome.strip()))
    conn.commit()
    conn.close()
    return True, "Subcategoria criada com sucesso."

def atualizar_subcategoria_custo(sub_id, nome=None, ativo=None):
    conn = get_connection()
    updates = []
    params = []
    if nome is not None:
        updates.append("nome = ?")
        params.append(nome.strip())
    if ativo is not None:
        updates.append("ativo = ?")
        params.append(1 if ativo else 0)
    if updates:
        params.append(sub_id)
        conn.execute(f"UPDATE subcategorias_custos SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
    conn.close()

# ============ CONTAS A PAGAR/RECEBER ============
def inserir_conta(tipo, descricao, valor, data_vencimento, categoria_id=None, observacoes=""):
    conn = get_connection()
    conn.execute("""
        INSERT INTO contas (tipo, descricao, valor, data_vencimento, status, categoria_id, observacoes, data_criacao)
        VALUES (?, ?, ?, ?, 'pendente', ?, ?, ?)
    """, (tipo, descricao, valor, data_vencimento, categoria_id, observacoes or "",
          datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def get_contas(tipo=None, status=None, data_inicio=None, data_fim=None):
    conn = get_connection()
    query = """SELECT co.*, cc.nome as categoria_nome 
               FROM contas co 
               LEFT JOIN categorias_custos cc ON co.categoria_id = cc.id"""
    conditions = []
    params = []
    if tipo:
        conditions.append("co.tipo = ?")
        params.append(tipo)
    if status:
        conditions.append("co.status = ?")
        params.append(status)
    if data_inicio:
        conditions.append("co.data_vencimento >= ?")
        params.append(data_inicio)
    if data_fim:
        conditions.append("co.data_vencimento <= ?")
        params.append(data_fim)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY co.data_vencimento ASC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def atualizar_conta(conta_id, **kwargs):
    conn = get_connection()
    updates = []
    params = []
    campos_permitidos = ['tipo', 'descricao', 'valor', 'data_vencimento', 'data_pagamento',
                         'status', 'categoria_id', 'observacoes']
    for campo in campos_permitidos:
        if campo in kwargs:
            updates.append(f"{campo} = ?")
            params.append(kwargs[campo])
    if updates:
        params.append(conta_id)
        conn.execute(f"UPDATE contas SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
    conn.close()

def marcar_conta_paga(conta_id, data_pagamento=None):
    if not data_pagamento:
        data_pagamento = datetime.now().strftime("%Y-%m-%d")
    atualizar_conta(conta_id, status='pago', data_pagamento=data_pagamento)

def cancelar_conta(conta_id):
    atualizar_conta(conta_id, status='cancelado')

def deletar_conta(conta_id):
    conn = get_connection()
    conn.execute("DELETE FROM contas WHERE id = ?", (conta_id,))
    conn.commit()
    conn.close()

def atualizar_status_contas_atrasadas():
    """Atualiza contas pendentes que já passaram da data de vencimento para 'atrasado'."""
    conn = get_connection()
    hoje = datetime.now().strftime("%Y-%m-%d")
    conn.execute("""
        UPDATE contas SET status = 'atrasado' 
        WHERE status = 'pendente' AND data_vencimento < ?
    """, (hoje,))
    conn.commit()
    conn.close()

def obter_contas_proximas_vencimento(dias=7):
    """Retorna contas pendentes ou atrasadas que vencem nos próximos N dias (ou já venceram)."""
    conn = get_connection()
    hoje = datetime.now()
    data_limite = (hoje + timedelta(days=dias)).strftime("%Y-%m-%d")
    hoje_str = hoje.strftime("%Y-%m-%d")
    
    rows = conn.execute("""
        SELECT co.*, cc.nome as categoria_nome
        FROM contas co
        LEFT JOIN categorias_custos cc ON co.categoria_id = cc.id
        WHERE co.status IN ('pendente', 'atrasado')
        AND co.data_vencimento <= ?
        ORDER BY co.data_vencimento ASC
    """, (data_limite,)).fetchall()
    conn.close()
    
    result = []
    for r in rows:
        d = dict(r)
        try:
            venc = datetime.strptime(d['data_vencimento'], "%Y-%m-%d")
            dias_restantes = (venc - hoje).days
            d['dias_restantes'] = dias_restantes
            if dias_restantes < 0:
                d['urgencia'] = 'atrasado'
            elif dias_restantes <= 3:
                d['urgencia'] = 'urgente'
            else:
                d['urgencia'] = 'proximo'
        except:
            d['dias_restantes'] = 0
            d['urgencia'] = 'proximo'
        result.append(d)
    return result
