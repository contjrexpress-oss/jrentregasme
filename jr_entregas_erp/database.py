import sqlite3
import os
import re
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
    
    # ============ FASE 7A: TABELA DE CLIENTES ============
    c.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cpf_cnpj TEXT UNIQUE,
            telefone TEXT DEFAULT '',
            email TEXT DEFAULT '',
            endereco TEXT DEFAULT '',
            bairro TEXT DEFAULT '',
            cidade TEXT DEFAULT '',
            cep TEXT DEFAULT '',
            observacoes TEXT DEFAULT '',
            data_cadastro TEXT NOT NULL,
            ativo INTEGER DEFAULT 1
        )
    """)
    
    # Migração: adicionar coluna cliente_id na tabela faturamento
    try:
        c.execute("SELECT cliente_id FROM faturamento LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE faturamento ADD COLUMN cliente_id INTEGER DEFAULT NULL")
    
    # ============ FASE 7B: MIGRAÇÕES CUSTOS ============
    # Migração: adicionar coluna cliente_id na tabela custos
    try:
        c.execute("SELECT cliente_id FROM custos LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE custos ADD COLUMN cliente_id INTEGER DEFAULT NULL")
    
    # Migração: adicionar coluna faturamento_id na tabela custos (vínculo com faturamento)
    try:
        c.execute("SELECT faturamento_id FROM custos LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE custos ADD COLUMN faturamento_id INTEGER DEFAULT NULL")
    
    # Tabela de custos associados a faturamento
    c.execute("""
        CREATE TABLE IF NOT EXISTS custos_faturamento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faturamento_id INTEGER NOT NULL,
            descricao TEXT NOT NULL,
            valor REAL NOT NULL,
            categoria TEXT DEFAULT '',
            FOREIGN KEY (faturamento_id) REFERENCES faturamento(id) ON DELETE CASCADE
        )
    """)

    
    # ============ FASE 8: TABELA DE USUÁRIOS ============
    c.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            nome TEXT NOT NULL,
            email TEXT DEFAULT '',
            perfil TEXT NOT NULL DEFAULT 'CONVIDADOS' CHECK(perfil IN ('ADM', 'FUNCIONARIOS', 'CONVIDADOS')),
            data_criacao TEXT NOT NULL,
            ativo INTEGER DEFAULT 1
        )
    """)
    
    # Tabela de log de ações de usuários
    c.execute("""
        CREATE TABLE IF NOT EXISTS log_acoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL,
            acao TEXT NOT NULL,
            detalhes TEXT DEFAULT '',
            data TEXT NOT NULL
        )
    """)
    
    # Criar usuário admin padrão se não existir
    import hashlib
    admin_exists = c.execute("SELECT id FROM usuarios WHERE username = 'admin'").fetchone()
    if not admin_exists:
        senha_hash = hashlib.sha256("jr2026".encode()).hexdigest()
        c.execute("""
            INSERT INTO usuarios (username, password_hash, nome, email, perfil, data_criacao, ativo)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        """, ("admin", senha_hash, "Administrador", "", "ADM", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    
    # Criar usuário equipe padrão se não existir
    equipe_exists = c.execute("SELECT id FROM usuarios WHERE username = 'equipe'").fetchone()
    if not equipe_exists:
        senha_hash = hashlib.sha256("jr2026".encode()).hexdigest()
        c.execute("""
            INSERT INTO usuarios (username, password_hash, nome, email, perfil, data_criacao, ativo)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        """, ("equipe", senha_hash, "Equipe", "", "FUNCIONARIOS", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    
    # ============ FASE 7C: TABELA LOG DE BACKUPS ============
    c.execute("""
        CREATE TABLE IF NOT EXISTS log_backups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            tipo TEXT NOT NULL,
            usuario TEXT DEFAULT '',
            tamanho INTEGER DEFAULT 0,
            observacao TEXT DEFAULT ''
        )
    """)
    
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

def atualizar_quantidade_estoque(codigo, nova_quantidade):
    """Atualiza a quantidade real do estoque ajustando o estoque_inicial.
    estoque_atual = estoque_inicial + entradas - saidas
    Portanto: estoque_inicial = nova_quantidade - entradas + saidas
    """
    conn = get_connection()
    row = conn.execute("""
        SELECT 
            COALESCE(SUM(CASE WHEN n.tipo = 'entrada' THEN in2.quantidade ELSE 0 END), 0) as entradas,
            COALESCE(SUM(CASE WHEN n.tipo = 'saida' THEN in2.quantidade ELSE 0 END), 0) as saidas
        FROM produtos p
        LEFT JOIN itens_nota in2 ON p.codigo = in2.codigo_produto
        LEFT JOIN notas n ON in2.nota_id = n.id
        WHERE p.codigo = ?
        GROUP BY p.codigo
    """, (str(codigo).strip(),)).fetchone()
    
    if row:
        entradas = row['entradas']
        saidas = row['saidas']
    else:
        entradas = 0
        saidas = 0
    
    novo_estoque_inicial = int(nova_quantidade) - entradas + saidas
    conn.execute("UPDATE produtos SET estoque_inicial = ? WHERE codigo = ?", (novo_estoque_inicial, str(codigo).strip()))
    conn.commit()
    conn.close()
    return True


def atualizar_quantidade_estoque_lote(lista_atualizacoes, modo='substituir', descricoes=None, cadastrar_novos=False):
    """Atualiza quantidades de estoque em lote, com opção de cadastrar produtos novos.
    lista_atualizacoes: lista de tuplas (codigo, quantidade)
    modo: 'substituir' - nova quantidade é o valor final
          'somar' - adiciona à quantidade atual
    descricoes: dict {codigo: descricao} para cadastro de novos produtos
    cadastrar_novos: se True, cadastra automaticamente produtos não encontrados
    Retorna: (atualizados, novos_cadastrados, erros_list)
      - atualizados: int - quantidade de produtos existentes atualizados
      - novos_cadastrados: list de codigos cadastrados como novos
      - erros_list: list de codigos com erro (código vazio, etc.)
    """
    conn = get_connection()
    atualizados = 0
    novos_cadastrados = []
    erros = []
    if descricoes is None:
        descricoes = {}
    
    for codigo, quantidade in lista_atualizacoes:
        codigo = str(codigo).strip()
        if not codigo:
            erros.append(codigo)
            continue
        
        prod = conn.execute("SELECT codigo FROM produtos WHERE codigo = ?", (codigo,)).fetchone()
        
        if not prod:
            if cadastrar_novos:
                # Cadastrar produto novo automaticamente
                descricao = descricoes.get(codigo, '').strip()
                if not descricao:
                    descricao = f'Produto {codigo}'
                qtd = int(quantidade)
                conn.execute(
                    "INSERT INTO produtos (codigo, descricao, estoque_inicial, estoque_minimo, estoque_maximo) VALUES (?, ?, ?, 0, NULL)",
                    (codigo, descricao, qtd)
                )
                novos_cadastrados.append(codigo)
                continue
            else:
                erros.append(codigo)
                continue
        
        row = conn.execute("""
            SELECT 
                p.estoque_inicial,
                COALESCE(SUM(CASE WHEN n.tipo = 'entrada' THEN in2.quantidade ELSE 0 END), 0) as entradas,
                COALESCE(SUM(CASE WHEN n.tipo = 'saida' THEN in2.quantidade ELSE 0 END), 0) as saidas
            FROM produtos p
            LEFT JOIN itens_nota in2 ON p.codigo = in2.codigo_produto
            LEFT JOIN notas n ON in2.nota_id = n.id
            WHERE p.codigo = ?
            GROUP BY p.codigo
        """, (codigo,)).fetchone()
        
        if row:
            entradas = row['entradas']
            saidas = row['saidas']
            estoque_atual = row['estoque_inicial'] + entradas - saidas
        else:
            entradas = 0
            saidas = 0
            estoque_atual = 0
        
        if modo == 'somar':
            nova_quantidade = estoque_atual + int(quantidade)
        else:
            nova_quantidade = int(quantidade)
        
        novo_estoque_inicial = nova_quantidade - entradas + saidas
        conn.execute("UPDATE produtos SET estoque_inicial = ? WHERE codigo = ?", (novo_estoque_inicial, codigo))
        atualizados += 1
    
    conn.commit()
    conn.close()
    return atualizados, novos_cadastrados, erros


# ============ FATURAMENTO ============
def inserir_faturamento(nota_id, data, descricao, regiao, veiculo, valor, cep, bairro, municipio, cliente="", cliente_id=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO faturamento (nota_id, data, descricao, regiao, veiculo, valor, cep, bairro, municipio, cliente, cliente_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (nota_id, data, descricao, regiao, veiculo, valor, cep, bairro, municipio, cliente or "", cliente_id))
    fat_id = c.lastrowid
    conn.commit()
    conn.close()
    return fat_id

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
def inserir_custo(data, descricao, categoria, valor, categoria_id=None, subcategoria_id=None, cliente_id=None, faturamento_id=None):
    conn = get_connection()
    conn.execute("""INSERT INTO custos (data, descricao, categoria, valor, categoria_id, subcategoria_id, cliente_id, faturamento_id) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                 (data, descricao, categoria, valor, categoria_id, subcategoria_id, cliente_id, faturamento_id))
    conn.commit()
    conn.close()

def get_custos(cliente_id=None, faturamento_id=None):
    conn = get_connection()
    query = """SELECT c.*, cl.nome as cliente_nome 
               FROM custos c 
               LEFT JOIN clientes cl ON c.cliente_id = cl.id"""
    conditions = []
    params = []
    if cliente_id:
        conditions.append("c.cliente_id = ?")
        params.append(cliente_id)
    if faturamento_id:
        conditions.append("c.faturamento_id = ?")
        params.append(faturamento_id)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY c.data DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def atualizar_custo(custo_id, data=None, descricao=None, categoria=None, valor=None, cliente_id=None, faturamento_id=None):
    conn = get_connection()
    updates = []
    params = []
    campo_valores = {
        'data': data, 'descricao': descricao, 'categoria': categoria,
        'valor': valor, 'cliente_id': cliente_id, 'faturamento_id': faturamento_id
    }
    for campo, val in campo_valores.items():
        if val is not None:
            updates.append(f"{campo} = ?")
            params.append(val)
    if updates:
        params.append(custo_id)
        conn.execute(f"UPDATE custos SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
    conn.close()

def deletar_custo(custo_id):
    conn = get_connection()
    conn.execute("DELETE FROM custos WHERE id = ?", (custo_id,))
    conn.commit()
    conn.close()

# ============ CUSTOS ASSOCIADOS A FATURAMENTO ============
def inserir_custos_faturamento(faturamento_id, custos_lista):
    """custos_lista: list of dict(descricao, valor, categoria)"""
    conn = get_connection()
    for c in custos_lista:
        conn.execute("""INSERT INTO custos_faturamento (faturamento_id, descricao, valor, categoria) 
                        VALUES (?, ?, ?, ?)""",
                     (faturamento_id, c['descricao'], c['valor'], c.get('categoria', '')))
    conn.commit()
    conn.close()

def get_custos_faturamento(faturamento_id):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM custos_faturamento WHERE faturamento_id = ? ORDER BY id", 
                        (faturamento_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_lucro_por_faturamento():
    """Retorna faturamento com custos associados e lucro calculado."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT f.*, 
               COALESCE((SELECT SUM(cf.valor) FROM custos_faturamento cf WHERE cf.faturamento_id = f.id), 0) as custos_associados,
               cl.nome as cliente_nome
        FROM faturamento f
        LEFT JOIN clientes cl ON f.cliente_id = cl.id
        ORDER BY f.data DESC
    """).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d['lucro_liquido'] = d['valor'] - d['custos_associados']
        result.append(d)
    return result

def buscar_descricoes_servicos(termo=""):
    """Retorna descrições de serviços já usadas no faturamento (autocomplete)."""
    conn = get_connection()
    if termo:
        rows = conn.execute(
            "SELECT DISTINCT descricao FROM faturamento WHERE descricao LIKE ? ORDER BY descricao LIMIT 20",
            (f"%{termo}%",)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT DISTINCT descricao FROM faturamento ORDER BY descricao LIMIT 50"
        ).fetchall()
    conn.close()
    return [r['descricao'] for r in rows if r['descricao']]

def buscar_categorias_custos_texto():
    """Retorna categorias de custos já usadas (texto livre)."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT categoria FROM custos WHERE categoria IS NOT NULL AND categoria != '' ORDER BY categoria"
    ).fetchall()
    conn.close()
    return [r['categoria'] for r in rows]

def get_faturamento_por_cliente(cliente_id):
    """Retorna faturamento de um cliente específico."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM faturamento WHERE cliente_id = ? ORDER BY data DESC",
        (cliente_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_custos_por_cliente(cliente_id):
    """Retorna custos de um cliente específico."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM custos WHERE cliente_id = ? ORDER BY data DESC",
        (cliente_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

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


# ============ CLIENTES ============

def inserir_cliente(nome, cpf_cnpj="", telefone="", email="", endereco="", bairro="", cidade="", cep="", observacoes=""):
    """Insere um novo cliente. Retorna (sucesso, mensagem, id)."""
    conn = get_connection()
    cpf_cnpj_limpo = re.sub(r'\D', '', str(cpf_cnpj)) if cpf_cnpj else ""
    
    # Verificar duplicidade de CPF/CNPJ
    if cpf_cnpj_limpo:
        existing = conn.execute("SELECT id, nome FROM clientes WHERE cpf_cnpj = ?", (cpf_cnpj_limpo,)).fetchone()
        if existing:
            conn.close()
            return False, f"CPF/CNPJ já cadastrado para o cliente: {existing['nome']}", None
    
    try:
        c = conn.cursor()
        c.execute("""
            INSERT INTO clientes (nome, cpf_cnpj, telefone, email, endereco, bairro, cidade, cep, observacoes, data_cadastro, ativo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (nome.strip(), cpf_cnpj_limpo, telefone.strip(), email.strip(), 
              endereco.strip(), bairro.strip(), cidade.strip(), 
              re.sub(r'\D', '', str(cep)) if cep else "", 
              observacoes.strip(),
              datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        cliente_id = c.lastrowid
        conn.commit()
        conn.close()
        return True, "Cliente cadastrado com sucesso!", cliente_id
    except sqlite3.IntegrityError as e:
        conn.close()
        return False, f"Erro ao cadastrar cliente: {str(e)}", None


def atualizar_cliente(cliente_id, **kwargs):
    """Atualiza dados de um cliente."""
    conn = get_connection()
    updates = []
    params = []
    campos_permitidos = ['nome', 'cpf_cnpj', 'telefone', 'email', 'endereco', 
                         'bairro', 'cidade', 'cep', 'observacoes', 'ativo']
    for campo in campos_permitidos:
        if campo in kwargs:
            valor = kwargs[campo]
            if campo == 'cpf_cnpj':
                valor = re.sub(r'\D', '', str(valor)) if valor else ""
            elif campo == 'cep':
                valor = re.sub(r'\D', '', str(valor)) if valor else ""
            elif campo == 'ativo':
                valor = 1 if valor else 0
            else:
                valor = str(valor).strip() if valor else ""
            updates.append(f"{campo} = ?")
            params.append(valor)
    
    if updates:
        # Verificar duplicidade de CPF/CNPJ se estiver sendo alterado
        if 'cpf_cnpj' in kwargs and kwargs['cpf_cnpj']:
            cpf_limpo = re.sub(r'\D', '', str(kwargs['cpf_cnpj']))
            if cpf_limpo:
                existing = conn.execute(
                    "SELECT id, nome FROM clientes WHERE cpf_cnpj = ? AND id != ?",
                    (cpf_limpo, cliente_id)
                ).fetchone()
                if existing:
                    conn.close()
                    return False, f"CPF/CNPJ já cadastrado para: {existing['nome']}"
        
        params.append(cliente_id)
        conn.execute(f"UPDATE clientes SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
    conn.close()
    return True, "Cliente atualizado com sucesso!"


def obter_clientes(apenas_ativos=True, busca=""):
    """Retorna lista de clientes com filtros opcionais."""
    conn = get_connection()
    query = "SELECT * FROM clientes"
    conditions = []
    params = []
    
    if apenas_ativos:
        conditions.append("ativo = 1")
    if busca:
        conditions.append("(nome LIKE ? OR cpf_cnpj LIKE ? OR email LIKE ? OR telefone LIKE ?)")
        termo = f"%{busca}%"
        params.extend([termo, termo, termo, termo])
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY nome ASC"
    
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def buscar_cliente_por_id(cliente_id):
    """Retorna um cliente por ID."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM clientes WHERE id = ?", (cliente_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def buscar_cliente_por_nome(nome):
    """Busca clientes pelo nome (parcial)."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM clientes WHERE ativo = 1 AND nome LIKE ? ORDER BY nome LIMIT 20",
        (f"%{nome}%",)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def buscar_clientes_autocomplete(termo):
    """Retorna clientes que começam com o termo para autocomplete.
    Busca em nome e CPF/CNPJ. Retorna lista formatada."""
    if not termo or len(termo) < 2:
        return []
    conn = get_connection()
    rows = conn.execute("""
        SELECT id, nome, cpf_cnpj, telefone, cidade, bairro 
        FROM clientes 
        WHERE ativo = 1 AND (nome LIKE ? OR cpf_cnpj LIKE ?)
        ORDER BY nome ASC
        LIMIT 15
    """, (f"%{termo}%", f"%{termo}%")).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def deletar_cliente(cliente_id):
    """Desativa um cliente (soft delete)."""
    return atualizar_cliente(cliente_id, ativo=0)


def reativar_cliente(cliente_id):
    """Reativa um cliente desativado."""
    return atualizar_cliente(cliente_id, ativo=1)


def contar_clientes():
    """Retorna contagem de clientes ativos e inativos."""
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) FROM clientes").fetchone()[0]
    ativos = conn.execute("SELECT COUNT(*) FROM clientes WHERE ativo = 1").fetchone()[0]
    inativos = total - ativos
    conn.close()
    return {'total': total, 'ativos': ativos, 'inativos': inativos}


# ============ FASE 7C: SISTEMA DE BACKUP ============

def _criar_tabela_log_backups():
    """Cria tabela de log de backups se não existir."""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS log_backups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            tipo TEXT NOT NULL,
            usuario TEXT DEFAULT '',
            tamanho INTEGER DEFAULT 0,
            observacao TEXT DEFAULT ''
        )
    """)
    conn.commit()
    conn.close()


def registrar_log_backup(tipo, tamanho, usuario="", observacao=""):
    """Registra um backup no histórico."""
    _criar_tabela_log_backups()
    conn = get_connection()
    conn.execute(
        "INSERT INTO log_backups (data, tipo, usuario, tamanho, observacao) VALUES (?, ?, ?, ?, ?)",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), tipo, usuario, tamanho, observacao)
    )
    conn.commit()
    conn.close()


def obter_log_backups():
    """Retorna histórico de backups."""
    _criar_tabela_log_backups()
    conn = get_connection()
    rows = conn.execute("SELECT * FROM log_backups ORDER BY data DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def criar_backup():
    """Cria cópia do banco de dados para exportação. Retorna bytes do arquivo."""
    import shutil
    import tempfile
    
    db_abs = os.path.abspath(DB_PATH)
    if not os.path.exists(db_abs):
        return None
    
    # Garantir WAL checkpoint antes de copiar
    conn = get_connection()
    conn.execute("PRAGMA wal_checkpoint(FULL)")
    conn.close()
    
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tmp_path = tmp.name
    tmp.close()
    
    shutil.copy2(db_abs, tmp_path)
    
    with open(tmp_path, "rb") as f:
        data = f.read()
    
    os.unlink(tmp_path)
    return data


def validar_backup(arquivo_bytes):
    """Verifica se o arquivo é um banco SQLite válido e contém as tabelas necessárias.
    Retorna (valido: bool, mensagem: str, info: dict)."""
    import tempfile
    
    # Verificar header SQLite
    if not arquivo_bytes or len(arquivo_bytes) < 100:
        return False, "Arquivo muito pequeno ou vazio.", {}
    
    if arquivo_bytes[:16] != b"SQLite format 3\x00":
        return False, "Arquivo não é um banco de dados SQLite válido.", {}
    
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tmp_path = tmp.name
    tmp.close()
    
    try:
        with open(tmp_path, "wb") as f:
            f.write(arquivo_bytes)
        
        conn = sqlite3.connect(tmp_path)
        conn.row_factory = sqlite3.Row
        
        # Verificar integridade
        result = conn.execute("PRAGMA integrity_check").fetchone()
        if result[0] != "ok":
            conn.close()
            return False, f"Banco corrompido: {result[0]}", {}
        
        # Obter tabelas
        tabelas = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()]
        
        tabelas_necessarias = ['produtos', 'notas', 'itens_nota', 'faturamento', 'custos']
        faltando = [t for t in tabelas_necessarias if t not in tabelas]
        
        if faltando:
            conn.close()
            return False, f"Tabelas obrigatórias ausentes: {', '.join(faltando)}", {'tabelas': tabelas}
        
        # Obter estatísticas
        info = {'tabelas': tabelas, 'registros': {}}
        for tabela in tabelas:
            try:
                count = conn.execute(f"SELECT COUNT(*) FROM [{tabela}]").fetchone()[0]
                info['registros'][tabela] = count
            except Exception:
                info['registros'][tabela] = 0
        
        info['tamanho'] = len(arquivo_bytes)
        conn.close()
        return True, "Backup válido.", info
        
    except Exception as e:
        return False, f"Erro ao validar: {str(e)}", {}
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def obter_info_banco():
    """Retorna estatísticas do banco de dados atual."""
    db_abs = os.path.abspath(DB_PATH)
    if not os.path.exists(db_abs):
        return None
    
    info = {
        'tamanho': os.path.getsize(db_abs),
        'ultima_modificacao': datetime.fromtimestamp(os.path.getmtime(db_abs)).strftime("%Y-%m-%d %H:%M:%S"),
        'tabelas': [],
        'registros': {}
    }
    
    conn = get_connection()
    tabelas = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()]
    info['tabelas'] = tabelas
    
    for tabela in tabelas:
        try:
            count = conn.execute(f"SELECT COUNT(*) FROM [{tabela}]").fetchone()[0]
            info['registros'][tabela] = count
        except Exception:
            info['registros'][tabela] = 0
    
    conn.close()
    return info


def restaurar_backup(arquivo_bytes):
    """Restaura banco de dados a partir de backup. 
    Cria backup automático do banco atual antes de restaurar.
    Retorna (sucesso: bool, mensagem: str)."""
    import shutil
    
    db_abs = os.path.abspath(DB_PATH)
    
    # 1. Validar arquivo
    valido, msg, _ = validar_backup(arquivo_bytes)
    if not valido:
        return False, f"Backup inválido: {msg}"
    
    # 2. Backup automático do banco atual antes de substituir
    if os.path.exists(db_abs):
        backup_auto = db_abs + f".auto_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        try:
            # Checkpoint WAL
            conn = get_connection()
            conn.execute("PRAGMA wal_checkpoint(FULL)")
            conn.close()
            shutil.copy2(db_abs, backup_auto)
        except Exception as e:
            return False, f"Erro ao criar backup de segurança: {str(e)}"
    
    # 3. Substituir banco
    try:
        with open(db_abs, "wb") as f:
            f.write(arquivo_bytes)
        return True, "Backup restaurado com sucesso!"
    except Exception as e:
        # Tentar restaurar backup automático
        if os.path.exists(backup_auto):
            shutil.copy2(backup_auto, db_abs)
        return False, f"Erro ao restaurar: {str(e)}"


# ============ FASE 8: USUÁRIOS E PERMISSÕES ============

def _hash_senha(senha):
    """Gera hash SHA-256 da senha."""
    import hashlib
    return hashlib.sha256(senha.encode()).hexdigest()


def inserir_usuario(username, senha, nome, email="", perfil="CONVIDADOS"):
    """Insere um novo usuário. Retorna (sucesso, mensagem)."""
    conn = get_connection()
    # Verificar username único
    existing = conn.execute("SELECT id FROM usuarios WHERE username = ?", (username.strip().lower(),)).fetchone()
    if existing:
        conn.close()
        return False, "Já existe um usuário com esse username."
    
    if len(senha) < 6:
        conn.close()
        return False, "A senha deve ter no mínimo 6 caracteres."
    
    if perfil not in ('ADM', 'FUNCIONARIOS', 'CONVIDADOS'):
        conn.close()
        return False, "Perfil inválido."
    
    try:
        conn.execute("""
            INSERT INTO usuarios (username, password_hash, nome, email, perfil, data_criacao, ativo)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        """, (username.strip().lower(), _hash_senha(senha), nome.strip(), email.strip(), 
              perfil, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        return True, "Usuário criado com sucesso!"
    except sqlite3.IntegrityError as e:
        conn.close()
        return False, f"Erro ao criar usuário: {str(e)}"


def atualizar_usuario(usuario_id, **kwargs):
    """Atualiza dados de um usuário."""
    conn = get_connection()
    updates = []
    params = []
    campos_permitidos = ['nome', 'email', 'perfil', 'ativo']
    
    for campo in campos_permitidos:
        if campo in kwargs:
            valor = kwargs[campo]
            if campo == 'ativo':
                valor = 1 if valor else 0
            elif campo == 'perfil' and valor not in ('ADM', 'FUNCIONARIOS', 'CONVIDADOS'):
                conn.close()
                return False, "Perfil inválido."
            else:
                valor = str(valor).strip() if valor else ""
            updates.append(f"{campo} = ?")
            params.append(valor)
    
    if updates:
        params.append(usuario_id)
        conn.execute(f"UPDATE usuarios SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
    conn.close()
    return True, "Usuário atualizado com sucesso!"


def resetar_senha_usuario(usuario_id, nova_senha):
    """Reseta a senha de um usuário."""
    if len(nova_senha) < 6:
        return False, "A senha deve ter no mínimo 6 caracteres."
    conn = get_connection()
    conn.execute("UPDATE usuarios SET password_hash = ? WHERE id = ?", 
                 (_hash_senha(nova_senha), usuario_id))
    conn.commit()
    conn.close()
    return True, "Senha resetada com sucesso!"


def obter_usuarios(apenas_ativos=False, perfil=None):
    """Retorna lista de usuários."""
    conn = get_connection()
    query = "SELECT id, username, nome, email, perfil, data_criacao, ativo FROM usuarios"
    conditions = []
    params = []
    
    if apenas_ativos:
        conditions.append("ativo = 1")
    if perfil:
        conditions.append("perfil = ?")
        params.append(perfil)
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY nome ASC"
    
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def buscar_usuario_por_username(username):
    """Busca usuário pelo username. Retorna dict com todos os campos."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM usuarios WHERE username = ?", (username.strip().lower(),)).fetchone()
    conn.close()
    return dict(row) if row else None


def buscar_usuario_por_id(usuario_id):
    """Busca usuário pelo ID."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def verificar_senha(username, password):
    """Verifica credenciais do usuário. Retorna dict do usuário se válido, None se inválido."""
    user = buscar_usuario_por_username(username)
    if not user:
        return None
    if not user['ativo']:
        return None
    if user['password_hash'] == _hash_senha(password):
        return user
    return None


def registrar_log_acao(usuario, acao, detalhes=""):
    """Registra uma ação no log."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO log_acoes (usuario, acao, detalhes, data) VALUES (?, ?, ?, ?)",
        (usuario, acao, detalhes, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()


def obter_log_acoes(limite=100, usuario=None):
    """Retorna log de ações."""
    conn = get_connection()
    query = "SELECT * FROM log_acoes"
    params = []
    if usuario:
        query += " WHERE usuario = ?"
        params.append(usuario)
    query += " ORDER BY data DESC LIMIT ?"
    params.append(limite)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]
