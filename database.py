import sqlite3
import os
import re
import logging
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple, Any

from config import (
    DB_PATH, Cores, StatusEstoque, Perfis, StatusConta,
    ESTOQUE_ATENCAO_FATOR, CATEGORIAS_CUSTO_PADRAO, COR_CATEGORIA_PADRAO,
    SENHA_PADRAO
)

logger = logging.getLogger(__name__)


@contextmanager
def get_connection() -> sqlite3.Connection:
    """Context manager para conexões com o banco de dados.
    Garante que conexões sejam sempre fechadas, mesmo em caso de erro.
    Uso: with get_connection() as conn:
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"Erro no banco de dados: {e}")
        raise
    finally:
        conn.close()

def criar_indices() -> None:
    """Cria índices para otimizar consultas frequentes no banco de dados."""
    with get_connection() as conn:
        indices = [
            "CREATE INDEX IF NOT EXISTS idx_notas_numero ON notas(numero)",
            "CREATE INDEX IF NOT EXISTS idx_notas_tipo ON notas(tipo)",
            "CREATE INDEX IF NOT EXISTS idx_notas_data_importacao ON notas(data_importacao)",
            "CREATE INDEX IF NOT EXISTS idx_produtos_codigo ON produtos(codigo)",
            "CREATE INDEX IF NOT EXISTS idx_itens_nota_nota_id ON itens_nota(nota_id)",
            "CREATE INDEX IF NOT EXISTS idx_itens_nota_codigo_produto ON itens_nota(codigo_produto)",
            "CREATE INDEX IF NOT EXISTS idx_faturamento_cliente_id ON faturamento(cliente_id)",
            "CREATE INDEX IF NOT EXISTS idx_faturamento_data ON faturamento(data)",
            "CREATE INDEX IF NOT EXISTS idx_faturamento_nota_id ON faturamento(nota_id)",
            "CREATE INDEX IF NOT EXISTS idx_custos_data ON custos(data)",
            "CREATE INDEX IF NOT EXISTS idx_custos_cliente_id ON custos(cliente_id)",
            "CREATE INDEX IF NOT EXISTS idx_custos_categoria_id ON custos(categoria_id)",
            "CREATE INDEX IF NOT EXISTS idx_clientes_cpf_cnpj ON clientes(cpf_cnpj)",
            "CREATE INDEX IF NOT EXISTS idx_clientes_nome ON clientes(nome)",
            "CREATE INDEX IF NOT EXISTS idx_clientes_ativo ON clientes(ativo)",
            "CREATE INDEX IF NOT EXISTS idx_usuarios_username ON usuarios(username)",
            "CREATE INDEX IF NOT EXISTS idx_usuarios_ativo ON usuarios(ativo)",
            "CREATE INDEX IF NOT EXISTS idx_contas_status ON contas(status)",
            "CREATE INDEX IF NOT EXISTS idx_contas_data_vencimento ON contas(data_vencimento)",
            "CREATE INDEX IF NOT EXISTS idx_contas_tipo ON contas(tipo)",
            "CREATE INDEX IF NOT EXISTS idx_log_acoes_usuario ON log_acoes(usuario)",
            "CREATE INDEX IF NOT EXISTS idx_log_acoes_data ON log_acoes(data)",
            "CREATE INDEX IF NOT EXISTS idx_custos_faturamento_fat_id ON custos_faturamento(faturamento_id)",
        ]
        for idx_sql in indices:
            try:
                conn.execute(idx_sql)
            except sqlite3.Error as e:
                logger.warning(f"Erro ao criar índice: {e}")
        conn.commit()
        logger.info("Índices do banco de dados criados/verificados com sucesso.")


def init_db() -> None:
    with get_connection() as conn:
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
                data TEXT DEFAULT '',
                FOREIGN KEY (faturamento_id) REFERENCES faturamento(id) ON DELETE CASCADE
            )
        """)
        # Migração: adicionar coluna data em custos_faturamento (se não existir)
        try:
            c.execute("SELECT data FROM custos_faturamento LIMIT 1")
        except sqlite3.OperationalError:
            c.execute("ALTER TABLE custos_faturamento ADD COLUMN data TEXT DEFAULT ''")

        
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
            senha_hash = hashlib.sha256(SENHA_PADRAO.encode()).hexdigest()
            c.execute("""
                INSERT INTO usuarios (username, password_hash, nome, email, perfil, data_criacao, ativo)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """, ("admin", senha_hash, "Administrador", "", Perfis.ADM, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        # Criar usuário equipe padrão se não existir
        equipe_exists = c.execute("SELECT id FROM usuarios WHERE username = 'equipe'").fetchone()
        if not equipe_exists:
            senha_hash = hashlib.sha256(SENHA_PADRAO.encode()).hexdigest()
            c.execute("""
                INSERT INTO usuarios (username, password_hash, nome, email, perfil, data_criacao, ativo)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """, ("equipe", senha_hash, "Equipe", "", Perfis.FUNCIONARIOS, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
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
    
    # Criar índices após todas as tabelas existirem
    criar_indices()

# ============ PRODUTOS ============
def inserir_produtos(lista_produtos: List[Tuple[str, str]]) -> Tuple[int, int]:
    """Insere ou atualiza produtos em lote. Retorna (inseridos, atualizados)."""
    with get_connection() as conn:
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
    return inseridos, atualizados

def get_produtos() -> List[Dict[str, Any]]:
    """Retorna todos os produtos cadastrados."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT codigo, descricao, estoque_inicial, estoque_minimo, estoque_maximo 
            FROM produtos ORDER BY codigo
        """).fetchall()
    return [dict(r) for r in rows]

def produto_existe(codigo: str) -> bool:
    """Verifica se um produto existe no banco de dados."""
    with get_connection() as conn:
        r = conn.execute("SELECT codigo FROM produtos WHERE codigo = ?", (str(codigo).strip(),)).fetchone()
    return r is not None

def atualizar_estoque_inicial(codigo: str, valor: int) -> None:
    """Atualiza o estoque_inicial de um produto diretamente."""
    with get_connection() as conn:
        conn.execute("UPDATE produtos SET estoque_inicial = ? WHERE codigo = ?", (valor, codigo))
        conn.commit()

def atualizar_limites_estoque(codigo: str, estoque_minimo: int, estoque_maximo: Optional[int] = None) -> None:
    """Atualiza os limites de estoque mínimo e máximo de um produto."""
    with get_connection() as conn:
        conn.execute("UPDATE produtos SET estoque_minimo = ?, estoque_maximo = ? WHERE codigo = ?",
                     (estoque_minimo, estoque_maximo, codigo))
        conn.commit()

def atualizar_limites_estoque_lote(lista_limites: List[Tuple[str, int, Optional[int]]]) -> Tuple[int, List[str]]:
    """Atualiza limites de estoque em lote. Retorna (atualizados, erros)."""
    with get_connection() as conn:
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
    return atualizados, erros

def obter_produtos_estoque_baixo() -> List[Dict[str, Any]]:
    """Retorna lista de produtos com estoque atual abaixo do estoque mínimo."""
    with get_connection() as conn:
        rows = conn.execute(f"""
            SELECT 
                p.codigo,
                p.descricao,
                p.estoque_inicial,
                p.estoque_minimo,
                p.estoque_maximo,
                {_SQL_MOVIMENTACOES_ESTOQUE}
            FROM produtos p
            {_SQL_JOIN_ESTOQUE}
            GROUP BY p.codigo, p.descricao, p.estoque_inicial, p.estoque_minimo, p.estoque_maximo
            HAVING (p.estoque_inicial + entradas - saidas) < p.estoque_minimo AND p.estoque_minimo > 0
            ORDER BY (p.estoque_inicial + entradas - saidas) - p.estoque_minimo ASC
        """).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d['estoque_atual'] = calcular_estoque_atual(d['estoque_inicial'], d['entradas'], d['saidas'])
        d['repor'] = d['estoque_minimo'] - d['estoque_atual']
        result.append(d)
    return result

# ============ NOTAS ============
def inserir_nota(numero: str, data_nota: str, cep: str, bairro: str, municipio: str, 
                 tipo: str, total_unidades: int, arquivo_nome: str, 
                 itens: List[Tuple[str, int]]) -> int:
    """Insere uma nota fiscal e seus itens. Retorna o ID da nota."""
    with get_connection() as conn:
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
    return nota_id

def get_notas() -> List[Dict[str, Any]]:
    """Retorna todas as notas fiscais."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT id, numero, data_nota, cep, bairro, municipio, tipo, 
                   total_unidades, data_importacao, arquivo_nome 
            FROM notas ORDER BY data_importacao DESC
        """).fetchall()
    return [dict(r) for r in rows]

def get_nota_by_id(nota_id: int) -> Optional[Dict[str, Any]]:
    """Retorna uma nota por ID ou None."""
    with get_connection() as conn:
        r = conn.execute("""
            SELECT id, numero, data_nota, cep, bairro, municipio, tipo,
                   total_unidades, data_importacao, arquivo_nome
            FROM notas WHERE id = ?
        """, (nota_id,)).fetchone()
    return dict(r) if r else None

def get_itens_nota(nota_id: int) -> List[Dict[str, Any]]:
    """Retorna os itens de uma nota fiscal."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT in2.id, in2.nota_id, in2.codigo_produto, in2.quantidade, p.descricao 
            FROM itens_nota in2 
            LEFT JOIN produtos p ON in2.codigo_produto = p.codigo 
            WHERE in2.nota_id = ?
        """, (nota_id,)).fetchall()
    return [dict(r) for r in rows]

def excluir_nota(nota_id: int, motivo: str = "", usuario: str = "") -> None:
    with get_connection() as conn:
        c = conn.cursor()
        nota = c.execute("""
            SELECT id, numero, data_nota, tipo, total_unidades, arquivo_nome
            FROM notas WHERE id = ?
        """, (nota_id,)).fetchone()
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

def get_notas_excluidas() -> List[Dict[str, Any]]:
    """Retorna histórico de notas excluídas."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT id, numero_nota, data_nota, tipo, total_unidades, 
                   arquivo_nome, motivo, data_exclusao, usuario 
            FROM notas_excluidas ORDER BY data_exclusao DESC
        """).fetchall()
    return [dict(r) for r in rows]

def nota_existe(numero: str, data_nota: Optional[str] = None, tipo: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Verifica se uma nota com mesmo número já existe. Retorna dict ou None."""
    with get_connection() as conn:
        query = """SELECT id, numero, data_nota, tipo, total_unidades, data_importacao, arquivo_nome
                   FROM notas WHERE numero = ?"""
        params = [str(numero).strip()]
        if data_nota:
            query += " AND data_nota = ?"
            params.append(str(data_nota).strip())
        if tipo:
            query += " AND tipo = ?"
            params.append(str(tipo).strip())
        row = conn.execute(query, params).fetchone()
    return dict(row) if row else None

# ============ ESTOQUE - FUNÇÕES CENTRALIZADAS ============

# SQL base para cálculo de movimentações (entradas/saídas) de estoque.
# Usado por todas as funções de estoque para evitar duplicação.
_SQL_MOVIMENTACOES_ESTOQUE: str = """
    COALESCE(SUM(CASE WHEN n.tipo = 'entrada' THEN in2.quantidade ELSE 0 END), 0) as entradas,
    COALESCE(SUM(CASE WHEN n.tipo = 'saida' THEN in2.quantidade ELSE 0 END), 0) as saidas
"""

_SQL_JOIN_ESTOQUE: str = """
    LEFT JOIN itens_nota in2 ON p.codigo = in2.codigo_produto
    LEFT JOIN notas n ON in2.nota_id = n.id
"""


def calcular_estoque_atual(estoque_inicial: int, entradas: int, saidas: int) -> int:
    """Calcula o estoque atual com base na fórmula centralizada.
    
    Formula: estoque_atual = estoque_inicial + entradas - saidas
    
    Args:
        estoque_inicial: Quantidade inicial de estoque.
        entradas: Total de entradas (notas de entrada).
        saidas: Total de saídas (notas de saída).
    
    Returns:
        Estoque atual calculado.
    """
    return estoque_inicial + entradas - saidas


def calcular_estoque_inicial_necessario(quantidade_desejada: int, entradas: int, saidas: int) -> int:
    """Calcula o estoque_inicial necessário para atingir uma quantidade desejada.
    
    Formula inversa: estoque_inicial = quantidade_desejada - entradas + saidas
    
    Args:
        quantidade_desejada: Quantidade final desejada de estoque.
        entradas: Total de entradas (notas de entrada).
        saidas: Total de saídas (notas de saída).
    
    Returns:
        Valor de estoque_inicial a ser gravado no banco.
    """
    return int(quantidade_desejada) - entradas + saidas


def classificar_status_estoque(estoque_atual: int, estoque_minimo: int) -> str:
    """Classifica o status do estoque com base nos limites definidos.
    
    Args:
        estoque_atual: Quantidade atual em estoque.
        estoque_minimo: Limite mínimo configurado (0 = sem limite).
    
    Returns:
        Status: 'critico', 'atencao', 'ok' ou 'sem_limite'.
    """
    est_min = estoque_minimo or 0
    if est_min > 0:
        if estoque_atual < est_min:
            return StatusEstoque.CRITICO
        elif estoque_atual <= est_min * ESTOQUE_ATENCAO_FATOR:
            return StatusEstoque.ATENCAO
        else:
            return StatusEstoque.OK
    return StatusEstoque.SEM_LIMITE


def _obter_movimentacoes_produto(conn, codigo: str) -> Tuple[int, int]:
    """Obtém entradas e saídas de um produto específico (uso interno).
    
    Args:
        conn: Conexão ativa com o banco.
        codigo: Código do produto.
    
    Returns:
        Tupla (entradas, saidas).
    """
    row = conn.execute(f"""
        SELECT {_SQL_MOVIMENTACOES_ESTOQUE}
        FROM produtos p
        {_SQL_JOIN_ESTOQUE}
        WHERE p.codigo = ?
        GROUP BY p.codigo
    """, (str(codigo).strip(),)).fetchone()
    
    if row:
        return row['entradas'], row['saidas']
    return 0, 0


def get_estoque() -> List[Dict[str, Any]]:
    """Retorna todos os produtos com estoque atual calculado e status."""
    with get_connection() as conn:
        rows = conn.execute(f"""
            SELECT 
                p.codigo,
                p.descricao,
                p.estoque_inicial,
                COALESCE(p.estoque_minimo, 0) as estoque_minimo,
                p.estoque_maximo,
                {_SQL_MOVIMENTACOES_ESTOQUE}
            FROM produtos p
            {_SQL_JOIN_ESTOQUE}
            GROUP BY p.codigo, p.descricao, p.estoque_inicial, p.estoque_minimo, p.estoque_maximo
            ORDER BY p.codigo
        """).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d['estoque_atual'] = calcular_estoque_atual(d['estoque_inicial'], d['entradas'], d['saidas'])
        d['status'] = classificar_status_estoque(d['estoque_atual'], d['estoque_minimo'])
        result.append(d)
    return result


def atualizar_quantidade_estoque(codigo: str, nova_quantidade: int) -> bool:
    """Atualiza a quantidade real do estoque ajustando o estoque_inicial.
    
    Usa a fórmula inversa centralizada para calcular o novo estoque_inicial.
    """
    with get_connection() as conn:
        entradas, saidas = _obter_movimentacoes_produto(conn, codigo)
        novo_estoque_inicial = calcular_estoque_inicial_necessario(nova_quantidade, entradas, saidas)
        conn.execute("UPDATE produtos SET estoque_inicial = ? WHERE codigo = ?", 
                     (novo_estoque_inicial, str(codigo).strip()))
        conn.commit()
    return True


def atualizar_quantidade_estoque_lote(
    lista_atualizacoes: List[Tuple[str, int]],
    modo: str = 'substituir',
    descricoes: Optional[Dict[str, str]] = None,
    cadastrar_novos: bool = False
) -> Tuple[int, List[str], List[str]]:
    """Atualiza quantidades de estoque em lote, com opção de cadastrar produtos novos.
    
    Args:
        lista_atualizacoes: Lista de tuplas (codigo, quantidade).
        modo: 'substituir' (valor final) ou 'somar' (adiciona ao atual).
        descricoes: Dict {codigo: descricao} para cadastro de novos produtos.
        cadastrar_novos: Se True, cadastra automaticamente produtos não encontrados.
    
    Returns:
        Tupla (atualizados, novos_cadastrados, erros_list).
    """
    with get_connection() as conn:
        atualizados = 0
        novos_cadastrados: List[str] = []
        erros: List[str] = []
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
            
            entradas, saidas = _obter_movimentacoes_produto(conn, codigo)
            estoque_atual = calcular_estoque_atual(
                conn.execute("SELECT estoque_inicial FROM produtos WHERE codigo = ?", (codigo,)).fetchone()['estoque_inicial'],
                entradas, saidas
            )
            
            if modo == 'somar':
                nova_quantidade_val = estoque_atual + int(quantidade)
            else:
                nova_quantidade_val = int(quantidade)
            
            novo_estoque_inicial = calcular_estoque_inicial_necessario(nova_quantidade_val, entradas, saidas)
            conn.execute("UPDATE produtos SET estoque_inicial = ? WHERE codigo = ?", (novo_estoque_inicial, codigo))
            atualizados += 1
        
        conn.commit()
    return atualizados, novos_cadastrados, erros


# ============ FATURAMENTO ============
def inserir_faturamento(nota_id: Optional[int], data: str, descricao: str, regiao: str, veiculo: str, valor: float, cep: str, bairro: str, municipio: str, cliente: str = "", cliente_id: Optional[int] = None) -> Optional[int]:
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO faturamento (nota_id, data, descricao, regiao, veiculo, valor, cep, bairro, municipio, cliente, cliente_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (nota_id, data, descricao, regiao, veiculo, valor, cep, bairro, municipio, cliente or "", cliente_id))
        fat_id = c.lastrowid
        conn.commit()
    return fat_id

def get_faturamento() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT id, nota_id, data, descricao, regiao, veiculo, valor, 
                   cep, bairro, municipio, cliente, cliente_id 
            FROM faturamento ORDER BY data DESC
        """).fetchall()
    return [dict(r) for r in rows]

def atualizar_faturamento(faturamento_id: int, descricao: Optional[str] = None, valor: Optional[float] = None, cliente: Optional[str] = None, data: Optional[str] = None, regiao: Optional[str] = None, veiculo: Optional[str] = None, cep: Optional[str] = None, bairro: Optional[str] = None, municipio: Optional[str] = None) -> None:
    with get_connection() as conn:
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

def deletar_faturamento(faturamento_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM faturamento WHERE id = ?", (faturamento_id,))
        conn.commit()

# ============ CUSTOS ============
def inserir_custo(data: str, descricao: str, categoria: str, valor: float, categoria_id: Optional[int] = None, subcategoria_id: Optional[int] = None, cliente_id: Optional[int] = None, faturamento_id: Optional[int] = None) -> Optional[int]:
    with get_connection() as conn:
        conn.execute("""INSERT INTO custos (data, descricao, categoria, valor, categoria_id, subcategoria_id, cliente_id, faturamento_id) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                     (data, descricao, categoria, valor, categoria_id, subcategoria_id, cliente_id, faturamento_id))
        conn.commit()

def get_custos(cliente_id: Optional[int] = None, faturamento_id: Optional[int] = None) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        query = """SELECT c.id, c.data, c.descricao, c.categoria, c.valor, 
                          c.categoria_id, c.subcategoria_id, c.cliente_id, c.faturamento_id,
                          cl.nome as cliente_nome 
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
    return [dict(r) for r in rows]

def atualizar_custo(custo_id: int, data: Optional[str] = None, descricao: Optional[str] = None, categoria: Optional[str] = None, valor: Optional[float] = None, cliente_id: Optional[int] = None, faturamento_id: Optional[int] = None) -> None:
    with get_connection() as conn:
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

def deletar_custo(custo_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM custos WHERE id = ?", (custo_id,))
        conn.commit()

# ============ CUSTOS ASSOCIADOS A FATURAMENTO ============
def inserir_custos_faturamento(faturamento_id: int, custos_lista: List[Dict[str, Any]]) -> None:
    """custos_lista: list of dict(descricao, valor, categoria)"""
    with get_connection() as conn:
        for c in custos_lista:
            conn.execute("""INSERT INTO custos_faturamento (faturamento_id, descricao, valor, categoria) 
                            VALUES (?, ?, ?, ?)""",
                         (faturamento_id, c['descricao'], c['valor'], c.get('categoria', '')))
        conn.commit()

def get_custos_faturamento(faturamento_id: int) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT id, faturamento_id, descricao, valor, categoria, data 
            FROM custos_faturamento WHERE faturamento_id = ? ORDER BY id
        """, (faturamento_id,)).fetchall()
    return [dict(r) for r in rows]

def atualizar_custo_faturamento(custo_id: int, descricao: str = None, valor: float = None,
                                 categoria: str = None, data: str = None) -> None:
    """Atualiza custo associado ao faturamento."""
    with get_connection() as conn:
        updates = []
        params = []
        if descricao is not None:
            updates.append("descricao = ?")
            params.append(descricao)
        if valor is not None:
            updates.append("valor = ?")
            params.append(valor)
        if categoria is not None:
            updates.append("categoria = ?")
            params.append(categoria)
        if data is not None:
            updates.append("data = ?")
            params.append(data)
        if updates:
            params.append(custo_id)
            conn.execute(f"UPDATE custos_faturamento SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()

def excluir_custo_faturamento(custo_id: int) -> None:
    """Exclui custo associado ao faturamento."""
    with get_connection() as conn:
        conn.execute("DELETE FROM custos_faturamento WHERE id = ?", (custo_id,))
        conn.commit()

def get_todos_custos_faturamento() -> List[Dict[str, Any]]:
    """Retorna TODOS os custos associados a faturamentos, com dados do faturamento pai."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT cf.id, cf.faturamento_id, cf.descricao, cf.valor, cf.categoria, cf.data,
                   f.data as fat_data, f.descricao as fat_descricao, f.cliente, f.cliente_id,
                   cl.nome as cliente_nome
            FROM custos_faturamento cf
            LEFT JOIN faturamento f ON cf.faturamento_id = f.id
            LEFT JOIN clientes cl ON f.cliente_id = cl.id
            ORDER BY COALESCE(NULLIF(cf.data, ''), f.data) DESC
        """).fetchall()
    return [dict(r) for r in rows]

def get_lucro_por_faturamento() -> List[Dict[str, Any]]:
    """Retorna faturamento com custos associados e lucro calculado."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT f.id, f.nota_id, f.data, f.descricao, f.regiao, f.veiculo, f.valor,
                   f.cep, f.bairro, f.municipio, f.cliente, f.cliente_id,
                   COALESCE((SELECT SUM(cf.valor) FROM custos_faturamento cf WHERE cf.faturamento_id = f.id), 0) as custos_associados,
                   cl.nome as cliente_nome
            FROM faturamento f
            LEFT JOIN clientes cl ON f.cliente_id = cl.id
            ORDER BY f.data DESC
        """).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d['lucro_liquido'] = d['valor'] - d['custos_associados']
        result.append(d)
    return result

def buscar_descricoes_servicos(termo: str = "") -> List[str]:
    """Retorna descrições de serviços já usadas no faturamento (autocomplete)."""
    with get_connection() as conn:
        if termo:
            rows = conn.execute(
                "SELECT DISTINCT descricao FROM faturamento WHERE descricao LIKE ? ORDER BY descricao LIMIT 20",
                (f"%{termo}%",)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT DISTINCT descricao FROM faturamento ORDER BY descricao LIMIT 50"
            ).fetchall()
    return [r['descricao'] for r in rows if r['descricao']]

def buscar_categorias_custos_texto() -> List[str]:
    """Retorna categorias de custos já usadas (texto livre)."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT categoria FROM custos WHERE categoria IS NOT NULL AND categoria != '' ORDER BY categoria"
        ).fetchall()
    return [r['categoria'] for r in rows]

def get_faturamento_por_cliente(cliente_id: int) -> List[Dict[str, Any]]:
    """Retorna faturamento de um cliente específico."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT id, nota_id, data, descricao, regiao, veiculo, valor, 
                   cep, bairro, municipio, cliente, cliente_id 
            FROM faturamento WHERE cliente_id = ? ORDER BY data DESC
        """, (cliente_id,)).fetchall()
    return [dict(r) for r in rows]

def get_custos_por_cliente(cliente_id: int) -> List[Dict[str, Any]]:
    """Retorna custos de um cliente específico."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT id, data, descricao, categoria, valor, categoria_id, 
                   subcategoria_id, cliente_id, faturamento_id 
            FROM custos WHERE cliente_id = ? ORDER BY data DESC
        """, (cliente_id,)).fetchall()
    return [dict(r) for r in rows]

# ============ CATEGORIAS DE CUSTOS ============
def get_categorias_custos(apenas_ativas: bool = True) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        query = "SELECT id, nome, cor, ativo FROM categorias_custos"
        if apenas_ativas:
            query += " WHERE ativo = 1"
        query += " ORDER BY nome"
        rows = conn.execute(query).fetchall()
    return [dict(r) for r in rows]

def get_subcategorias_custos(categoria_id: Optional[int] = None, apenas_ativas: bool = True) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        query = """SELECT s.id, s.categoria_id, s.nome, s.ativo, c.nome as categoria_nome 
                   FROM subcategorias_custos s 
                   LEFT JOIN categorias_custos c ON s.categoria_id = c.id"""
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
    return [dict(r) for r in rows]

def inserir_categoria_custo(nome: str, cor: str = "#718096") -> Optional[int]:
    with get_connection() as conn:
        try:
            conn.execute("INSERT INTO categorias_custos (nome, cor) VALUES (?, ?)", (nome.strip(), cor))
            conn.commit()
            return True, "Categoria criada com sucesso."
        except sqlite3.IntegrityError:
            return False, "Já existe uma categoria com esse nome."

def atualizar_categoria_custo(cat_id: int, nome: Optional[str] = None, cor: Optional[str] = None, ativo: Optional[int] = None) -> None:
    with get_connection() as conn:
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

def inserir_subcategoria_custo(categoria_id: int, nome: str) -> Optional[int]:
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM subcategorias_custos WHERE categoria_id = ? AND nome = ?",
            (categoria_id, nome.strip())
        ).fetchone()
        if existing:
            return False, "Já existe uma subcategoria com esse nome nesta categoria."
        conn.execute("INSERT INTO subcategorias_custos (categoria_id, nome) VALUES (?, ?)",
                     (categoria_id, nome.strip()))
        conn.commit()
    return True, "Subcategoria criada com sucesso."

def atualizar_subcategoria_custo(sub_id: int, nome: Optional[str] = None, ativo: Optional[int] = None) -> None:
    with get_connection() as conn:
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

# ============ CONTAS A PAGAR/RECEBER ============
def inserir_conta(tipo: str, descricao: str, valor: float, data_vencimento: str, categoria_id: Optional[int] = None, observacoes: str = "") -> Optional[int]:
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO contas (tipo, descricao, valor, data_vencimento, status, categoria_id, observacoes, data_criacao)
            VALUES (?, ?, ?, ?, 'pendente', ?, ?, ?)
        """, (tipo, descricao, valor, data_vencimento, categoria_id, observacoes or "",
              datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()

def get_contas(tipo: Optional[str] = None, status: Optional[str] = None, data_inicio: Optional[str] = None, data_fim: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        query = """SELECT co.id, co.tipo, co.descricao, co.valor, co.data_vencimento, 
                          co.data_pagamento, co.status, co.categoria_id, co.observacoes, 
                          co.data_criacao, cc.nome as categoria_nome 
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
    return [dict(r) for r in rows]

def atualizar_conta(conta_id: int, **kwargs: Any) -> None:
    with get_connection() as conn:
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

def marcar_conta_paga(conta_id: int, data_pagamento: Optional[str] = None) -> None:
    if not data_pagamento:
        data_pagamento = datetime.now().strftime("%Y-%m-%d")
    atualizar_conta(conta_id, status='pago', data_pagamento=data_pagamento)

def cancelar_conta(conta_id: int) -> None:
    atualizar_conta(conta_id, status='cancelado')

def deletar_conta(conta_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM contas WHERE id = ?", (conta_id,))
        conn.commit()

def atualizar_status_contas_atrasadas() -> None:
    """Atualiza contas pendentes que já passaram da data de vencimento para 'atrasado'."""
    with get_connection() as conn:
        hoje = datetime.now().strftime("%Y-%m-%d")
        conn.execute("""
            UPDATE contas SET status = 'atrasado' 
            WHERE status = 'pendente' AND data_vencimento < ?
        """, (hoje,))
        conn.commit()

def obter_contas_proximas_vencimento(dias: int = 7) -> List[Dict[str, Any]]:
    """Retorna contas pendentes ou atrasadas que vencem nos próximos N dias (ou já venceram)."""
    with get_connection() as conn:
        hoje = datetime.now()
        data_limite = (hoje + timedelta(days=dias)).strftime("%Y-%m-%d")
        
        rows = conn.execute("""
            SELECT co.id, co.tipo, co.descricao, co.valor, co.data_vencimento, 
                   co.data_pagamento, co.status, co.categoria_id, co.observacoes, 
                   co.data_criacao, cc.nome as categoria_nome
            FROM contas co
            LEFT JOIN categorias_custos cc ON co.categoria_id = cc.id
            WHERE co.status IN ('pendente', 'atrasado')
            AND co.data_vencimento <= ?
            ORDER BY co.data_vencimento ASC
        """, (data_limite,)).fetchall()
    
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
        except (ValueError, TypeError) as e:
            logger.warning(f"Erro ao calcular dias restantes para conta {d.get('id')}: {e}")
            d['dias_restantes'] = 0
            d['urgencia'] = 'proximo'
        result.append(d)
    return result


# ============ CLIENTES ============

def inserir_cliente(nome: str, cpf_cnpj: str = "", telefone: str = "", email: str = "", endereco: str = "", bairro: str = "", cidade: str = "", cep: str = "", observacoes: str = "") -> Tuple[bool, str, Optional[int]]:
    """Insere um novo cliente. Retorna (sucesso, mensagem, id)."""
    with get_connection() as conn:
        cpf_cnpj_limpo = re.sub(r'\D', '', str(cpf_cnpj)) if cpf_cnpj else ""
        
        # Verificar duplicidade de CPF/CNPJ
        if cpf_cnpj_limpo:
            existing = conn.execute("SELECT id, nome FROM clientes WHERE cpf_cnpj = ?", (cpf_cnpj_limpo,)).fetchone()
            if existing:
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
            return True, "Cliente cadastrado com sucesso!", cliente_id
        except sqlite3.IntegrityError as e:
            return False, f"Erro ao cadastrar cliente: {str(e)}", None


def atualizar_cliente(cliente_id: int, **kwargs: Any) -> Tuple[bool, str]:
    """Atualiza dados de um cliente."""
    with get_connection() as conn:
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
                        return False, f"CPF/CNPJ já cadastrado para: {existing['nome']}"
            
            params.append(cliente_id)
            conn.execute(f"UPDATE clientes SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()
    return True, "Cliente atualizado com sucesso!"


def obter_clientes(apenas_ativos: bool = True, busca: str = "") -> List[Dict[str, Any]]:
    """Retorna lista de clientes com filtros opcionais."""
    with get_connection() as conn:
        query = """SELECT id, nome, cpf_cnpj, telefone, email, endereco, 
                          bairro, cidade, cep, observacoes, data_cadastro, ativo 
                   FROM clientes"""
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
    return [dict(r) for r in rows]


def buscar_cliente_por_id(cliente_id: int) -> Optional[Dict[str, Any]]:
    """Retorna um cliente por ID."""
    with get_connection() as conn:
        row = conn.execute("""
            SELECT id, nome, cpf_cnpj, telefone, email, endereco, 
                   bairro, cidade, cep, observacoes, data_cadastro, ativo 
            FROM clientes WHERE id = ?
        """, (cliente_id,)).fetchone()
    return dict(row) if row else None


def buscar_cliente_por_nome(nome: str) -> List[Dict[str, Any]]:
    """Busca clientes pelo nome (parcial)."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT id, nome, cpf_cnpj, telefone, email, endereco, 
                   bairro, cidade, cep, observacoes, data_cadastro, ativo 
            FROM clientes WHERE ativo = 1 AND nome LIKE ? ORDER BY nome LIMIT 20
        """, (f"%{nome}%",)).fetchall()
    return [dict(r) for r in rows]


def buscar_clientes_autocomplete(termo: str) -> List[Dict[str, Any]]:
    """Retorna clientes que começam com o termo para autocomplete.
    Busca em nome e CPF/CNPJ. Retorna lista formatada."""
    if not termo or len(termo) < 2:
        return []
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT id, nome, cpf_cnpj, telefone, cidade, bairro 
            FROM clientes 
            WHERE ativo = 1 AND (nome LIKE ? OR cpf_cnpj LIKE ?)
            ORDER BY nome ASC
            LIMIT 15
        """, (f"%{termo}%", f"%{termo}%")).fetchall()
    return [dict(r) for r in rows]


def buscar_cliente_por_cnpj(cnpj: str) -> Optional[Dict[str, Any]]:
    """Busca cliente ativo por CPF/CNPJ (apenas dígitos)."""
    cnpj_limpo = re.sub(r'\D', '', str(cnpj)) if cnpj else ""
    if not cnpj_limpo:
        return None
    with get_connection() as conn:
        row = conn.execute("""
            SELECT id, nome, cpf_cnpj, telefone, email, endereco, 
                   bairro, cidade, cep, observacoes, data_cadastro, ativo 
            FROM clientes WHERE cpf_cnpj = ? AND ativo = 1
        """, (cnpj_limpo,)).fetchone()
    return dict(row) if row else None


def obter_dados_completos_cliente(cliente_id: int) -> Dict[str, Any]:
    """Retorna todos os dados de um cliente por ID."""
    result = buscar_cliente_por_id(cliente_id)
    return result if result else {}


def deletar_cliente(cliente_id: int) -> None:
    """Desativa um cliente (soft delete)."""
    return atualizar_cliente(cliente_id, ativo=0)


def reativar_cliente(cliente_id: int) -> None:
    """Reativa um cliente desativado."""
    return atualizar_cliente(cliente_id, ativo=1)


def contar_clientes() -> Dict[str, int]:
    """Retorna contagem de clientes ativos e inativos."""
    with get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM clientes").fetchone()[0]
        ativos = conn.execute("SELECT COUNT(*) FROM clientes WHERE ativo = 1").fetchone()[0]
    inativos = total - ativos
    return {'total': total, 'ativos': ativos, 'inativos': inativos}


# ============ DASHBOARD METRICS ============

def contar_produtos_total() -> int:
    """Retorna total de produtos cadastrados."""
    with get_connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM produtos").fetchone()[0]


def contar_produtos_estoque_critico() -> int:
    """Retorna total de produtos com estoque abaixo do mínimo."""
    produtos = obter_produtos_estoque_baixo()
    return len(produtos)


def obter_faturamento_mes_atual() -> float:
    """Retorna o faturamento total do mês atual."""
    from datetime import datetime
    hoje = datetime.now()
    inicio_mes = hoje.strftime('%Y-%m-01')
    fim_mes = hoje.strftime('%Y-%m-31')
    with get_connection() as conn:
        result = conn.execute(
            "SELECT COALESCE(SUM(valor), 0.0) FROM faturamento WHERE data >= ? AND data <= ?",
            (inicio_mes, fim_mes)
        ).fetchone()
    return float(result[0]) if result else 0.0


def obter_custos_mes_atual() -> float:
    """Retorna os custos totais do mês atual."""
    from datetime import datetime
    hoje = datetime.now()
    inicio_mes = hoje.strftime('%Y-%m-01')
    fim_mes = hoje.strftime('%Y-%m-31')
    with get_connection() as conn:
        result = conn.execute(
            "SELECT COALESCE(SUM(valor), 0.0) FROM custos WHERE data >= ? AND data <= ?",
            (inicio_mes, fim_mes)
        ).fetchone()
    return float(result[0]) if result else 0.0


def obter_contas_vencer_proximos_dias(dias: int = 7) -> List[Dict[str, Any]]:
    """Retorna contas a vencer nos próximos N dias."""
    return obter_contas_proximas_vencimento(dias=dias)


# ============ FASE 7C: SISTEMA DE BACKUP ============

def _criar_tabela_log_backups() -> None:
    """Cria tabela de log de backups se não existir."""
    with get_connection() as conn:
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


def registrar_log_backup(tipo: str, tamanho: int, usuario: str = "", observacao: str = "") -> None:
    """Registra um backup no histórico."""
    _criar_tabela_log_backups()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO log_backups (data, tipo, usuario, tamanho, observacao) VALUES (?, ?, ?, ?, ?)",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), tipo, usuario, tamanho, observacao)
        )
        conn.commit()


def obter_log_backups() -> List[Dict[str, Any]]:
    """Retorna histórico de backups."""
    _criar_tabela_log_backups()
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT id, data, tipo, usuario, tamanho, observacao 
            FROM log_backups ORDER BY data DESC
        """).fetchall()
    return [dict(r) for r in rows]


def criar_backup() -> Optional[bytes]:
    """Cria cópia do banco de dados para exportação. Retorna bytes do arquivo."""
    import shutil
    import tempfile
    
    db_abs = os.path.abspath(DB_PATH)
    if not os.path.exists(db_abs):
        return None
    
    # Garantir WAL checkpoint antes de copiar
    with get_connection() as conn:
        conn.execute("PRAGMA wal_checkpoint(FULL)")
    
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tmp_path = tmp.name
    tmp.close()
    
    shutil.copy2(db_abs, tmp_path)
    
    with open(tmp_path, "rb") as f:
        data = f.read()
    
    os.unlink(tmp_path)
    return data


def validar_backup(arquivo_bytes: bytes) -> Tuple[bool, str, Dict[str, Any]]:
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
            except sqlite3.Error:
                info['registros'][tabela] = 0
        
        info['tamanho'] = len(arquivo_bytes)
        conn.close()
        return True, "Backup válido.", info
        
    except sqlite3.Error as e:
        logger.error(f"Erro ao validar backup: {e}")
        return False, f"Erro ao validar: {str(e)}", {}
    except OSError as e:
        logger.error(f"Erro de I/O ao validar backup: {e}")
        return False, f"Erro ao validar: {str(e)}", {}
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def obter_info_banco() -> Dict[str, Any]:
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
    
    with get_connection() as conn:
        tabelas = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()]
        info['tabelas'] = tabelas
        
        for tabela in tabelas:
            try:
                count = conn.execute(f"SELECT COUNT(*) FROM [{tabela}]").fetchone()[0]
                info['registros'][tabela] = count
            except sqlite3.Error:
                info['registros'][tabela] = 0
    
    return info


def restaurar_backup(arquivo_bytes: bytes) -> Tuple[bool, str]:
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
    backup_auto = None
    if os.path.exists(db_abs):
        backup_auto = db_abs + f".auto_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        try:
            # Checkpoint WAL
            with get_connection() as conn:
                conn.execute("PRAGMA wal_checkpoint(FULL)")
            shutil.copy2(db_abs, backup_auto)
        except (sqlite3.Error, OSError) as e:
            logger.error(f"Erro ao criar backup de segurança: {e}")
            return False, f"Erro ao criar backup de segurança: {str(e)}"
    
    # 3. Substituir banco
    try:
        with open(db_abs, "wb") as f:
            f.write(arquivo_bytes)
        return True, "Backup restaurado com sucesso!"
    except OSError as e:
        # Tentar restaurar backup automático
        if backup_auto and os.path.exists(backup_auto):
            shutil.copy2(backup_auto, db_abs)
        logger.error(f"Erro ao restaurar backup: {e}")
        return False, f"Erro ao restaurar: {str(e)}"


# ============ FASE 8: USUÁRIOS E PERMISSÕES ============

def _hash_senha(senha: str) -> str:
    """Gera hash SHA-256 da senha."""
    import hashlib
    return hashlib.sha256(senha.encode()).hexdigest()


def inserir_usuario(username: str, senha: str, nome: str, email: str = "", perfil: str = "CONVIDADOS") -> Tuple[bool, str]:
    """Insere um novo usuário. Retorna (sucesso, mensagem)."""
    with get_connection() as conn:
        # Verificar username único
        existing = conn.execute("SELECT id FROM usuarios WHERE username = ?", (username.strip().lower(),)).fetchone()
        if existing:
            return False, "Já existe um usuário com esse username."
        
        if len(senha) < 6:
            return False, "A senha deve ter no mínimo 6 caracteres."
        
        if perfil not in ('ADM', 'FUNCIONARIOS', 'CONVIDADOS'):
            return False, "Perfil inválido."
        
        try:
            conn.execute("""
                INSERT INTO usuarios (username, password_hash, nome, email, perfil, data_criacao, ativo)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (username.strip().lower(), _hash_senha(senha), nome.strip(), email.strip(), 
                  perfil, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            return True, "Usuário criado com sucesso!"
        except sqlite3.IntegrityError as e:
            return False, f"Erro ao criar usuário: {str(e)}"


def atualizar_usuario(usuario_id: int, **kwargs: Any) -> Tuple[bool, str]:
    """Atualiza dados de um usuário."""
    with get_connection() as conn:
        updates = []
        params = []
        campos_permitidos = ['nome', 'email', 'perfil', 'ativo']
        
        for campo in campos_permitidos:
            if campo in kwargs:
                valor = kwargs[campo]
                if campo == 'ativo':
                    valor = 1 if valor else 0
                elif campo == 'perfil' and valor not in ('ADM', 'FUNCIONARIOS', 'CONVIDADOS'):
                    return False, "Perfil inválido."
                else:
                    valor = str(valor).strip() if valor else ""
                updates.append(f"{campo} = ?")
                params.append(valor)
        
        if updates:
            params.append(usuario_id)
            conn.execute(f"UPDATE usuarios SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()
    return True, "Usuário atualizado com sucesso!"


def resetar_senha_usuario(usuario_id: int, nova_senha: str) -> Tuple[bool, str]:
    """Reseta a senha de um usuário."""
    if len(nova_senha) < 6:
        return False, "A senha deve ter no mínimo 6 caracteres."
    with get_connection() as conn:
        conn.execute("UPDATE usuarios SET password_hash = ? WHERE id = ?", 
                     (_hash_senha(nova_senha), usuario_id))
        conn.commit()
    return True, "Senha resetada com sucesso!"


def obter_usuarios(apenas_ativos: bool = False, perfil: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retorna lista de usuários."""
    with get_connection() as conn:
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
    return [dict(r) for r in rows]


def buscar_usuario_por_username(username: str) -> Optional[Dict[str, Any]]:
    """Busca usuário pelo username. Retorna dict com todos os campos."""
    with get_connection() as conn:
        row = conn.execute("""
            SELECT id, username, password_hash, nome, email, perfil, data_criacao, ativo 
            FROM usuarios WHERE username = ?
        """, (username.strip().lower(),)).fetchone()
    return dict(row) if row else None


def buscar_usuario_por_id(usuario_id: int) -> Optional[Dict[str, Any]]:
    """Busca usuário pelo ID."""
    with get_connection() as conn:
        row = conn.execute("""
            SELECT id, username, password_hash, nome, email, perfil, data_criacao, ativo 
            FROM usuarios WHERE id = ?
        """, (usuario_id,)).fetchone()
    return dict(row) if row else None


def verificar_senha(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Verifica credenciais do usuário. Retorna dict do usuário se válido, None se inválido."""
    user = buscar_usuario_por_username(username)
    if not user:
        return None
    if not user['ativo']:
        return None
    if user['password_hash'] == _hash_senha(password):
        return user
    return None


def registrar_log_acao(usuario: str, acao: str, detalhes: str = "") -> None:
    """Registra uma ação no log."""
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO log_acoes (usuario, acao, detalhes, data) VALUES (?, ?, ?, ?)",
            (usuario, acao, detalhes, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()


def obter_log_acoes(limite: int = 100, usuario: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retorna log de ações."""
    with get_connection() as conn:
        query = "SELECT id, usuario, acao, detalhes, data FROM log_acoes"
        params = []
        if usuario:
            query += " WHERE usuario = ?"
            params.append(usuario)
        query += " ORDER BY data DESC LIMIT ?"
        params.append(limite)
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]
