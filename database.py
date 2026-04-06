import sqlite3
import os
from datetime import datetime

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
            estoque_inicial INTEGER DEFAULT 0
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

# ============ ESTOQUE ============
def get_estoque():
    conn = get_connection()
    rows = conn.execute("""
        SELECT 
            p.codigo,
            p.descricao,
            p.estoque_inicial,
            COALESCE(SUM(CASE WHEN n.tipo = 'entrada' THEN in2.quantidade ELSE 0 END), 0) as entradas,
            COALESCE(SUM(CASE WHEN n.tipo = 'saida' THEN in2.quantidade ELSE 0 END), 0) as saidas
        FROM produtos p
        LEFT JOIN itens_nota in2 ON p.codigo = in2.codigo_produto
        LEFT JOIN notas n ON in2.nota_id = n.id
        GROUP BY p.codigo, p.descricao, p.estoque_inicial
        ORDER BY p.codigo
    """).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d['estoque_atual'] = d['estoque_inicial'] + d['entradas'] - d['saidas']
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
