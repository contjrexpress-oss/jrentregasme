"""
Configurações centralizadas do sistema JR ENTREGAS ME.
Todas as constantes, cores, caminhos e valores padrão do sistema.
"""
import os
from typing import Dict, List, Tuple

# ============ CAMINHOS ============

BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))
DB_PATH: str = os.path.join(BASE_DIR, "jr_entregas.db")
LOGO_PATH: str = os.path.join(BASE_DIR, "assets", "logo.png")
ASSETS_DIR: str = os.path.join(BASE_DIR, "assets")
BACKUP_DIR: str = os.path.join(BASE_DIR, "backups")

# ============ CORES CORPORATIVAS ============

class Cores:
    """Paleta de cores corporativas da JR ENTREGAS ME."""
    # Primárias
    AZUL: str = "#0B132B"
    AZUL_CLARO: str = "#1C2541"
    AZUL_MEDIO: str = "#3182CE"
    LARANJA: str = "#F29F05"
    LARANJA_ESCURO: str = "#D98E04"

    # Status
    VERDE: str = "#38A169"
    VERMELHO: str = "#E53E3E"
    AMARELO: str = "#D69E2E"

    # Neutras
    CINZA: str = "#718096"
    CINZA_CLARO: str = "#F4F7F6"
    BRANCO: str = "#FFFFFF"

    # Categorias extras (gráficos)
    ROXO: str = "#805AD5"
    LARANJA_ESCURO_ALT: str = "#DD6B20"
    TEAL: str = "#319795"
    CINZA_MEDIO: str = "#A0AEC0"
    AZUL_CLARO_ALT: str = "#4299E1"

    # Listas de cores para gráficos
    REGIOES: List[str] = [LARANJA, AZUL, AZUL_CLARO, VERDE, AZUL_MEDIO]
    CUSTOS: List[str] = [LARANJA, AZUL_MEDIO, VERDE, VERMELHO, ROXO, LARANJA_ESCURO_ALT, TEAL]

    # Classes CSS para métricas
    METRIC_GREEN: str = "metric-green"
    METRIC_RED: str = "metric-red"
    METRIC_ORANGE: str = "metric-orange"
    METRIC_BLUE: str = "metric-blue"


# ============ DATAS ============

ANO_MINIMO: int = 2020
ANO_MAXIMO: int = 2099

# ============ ESTOQUE ============

ESTOQUE_CRITICO_FATOR: float = 1.0   # Abaixo do mínimo = crítico
ESTOQUE_ATENCAO_FATOR: float = 1.2   # Até 20% acima do mínimo = atenção

# Status de estoque
class StatusEstoque:
    CRITICO: str = "critico"
    ATENCAO: str = "atencao"
    OK: str = "ok"
    SEM_LIMITE: str = "sem_limite"

# ============ PERFIS E PERMISSÕES ============

class Perfis:
    ADM: str = "ADM"
    FUNCIONARIOS: str = "FUNCIONARIOS"
    CONVIDADOS: str = "CONVIDADOS"

PERFIL_LABELS: Dict[str, str] = {
    Perfis.ADM: "🔑 Administrador",
    Perfis.FUNCIONARIOS: "👷 Funcionário",
    Perfis.CONVIDADOS: "👁️ Convidado",
}

MODULOS_PERMITIDOS: Dict[str, List[str]] = {
    Perfis.ADM: ['dashboard', 'importacao', 'estoque', 'financeiro', 'cadastros', 'gestao_notas', 'backup', 'usuarios'],
    Perfis.FUNCIONARIOS: ['dashboard', 'importacao', 'estoque', 'financeiro', 'cadastros', 'gestao_notas'],
    Perfis.CONVIDADOS: ['estoque', 'gestao_notas'],
}

# ============ NOTAS FISCAIS ============

class TipoNota:
    ENTRADA: str = "entrada"
    SAIDA: str = "saida"

# ============ CONTAS ============

class StatusConta:
    PENDENTE: str = "pendente"
    PAGO: str = "pago"
    ATRASADO: str = "atrasado"
    CANCELADO: str = "cancelado"

# ============ GRÁFICOS ============

CHART_HEIGHT: int = 350
CHART_MARGINS: Dict[str, int] = {"l": 20, "r": 20, "t": 40, "b": 20}

# ============ PDF ============

PDF_FONT_TITLE: int = 18
PDF_FONT_SUBTITLE: int = 13
PDF_FONT_BODY: int = 10
PDF_FONT_SMALL: int = 9
PDF_FONT_FOOTER: int = 7

# ============ EMPRESA ============

EMPRESA_NOME: str = "JR ENTREGAS ME"
EMPRESA_RESPONSAVEL: str = "ITALO BRUNO DOS SANTOS AMORIM"
EMPRESA_CPF_RESPONSAVEL: str = "10957922701"
EMPRESA_CNPJ: str = "20.443.788/0001-18"
EMPRESA_IE: str = ""  # Inscrição Estadual (preencher se houver)
EMPRESA_ENDERECO: str = "Rua Orquideas, 22, 22 — Andrade Araujo"
EMPRESA_CIDADE: str = "Belford Roxo-RJ"
EMPRESA_CEP: str = "26140-447"
EMPRESA_TELEFONE: str = "+55 (21) 98053-1278"
EMPRESA_WHATSAPP: str = "21980531278"
EMPRESA_EMAIL: str = "contjrexpress@gmail.com"
EMPRESA_INSTAGRAM: str = "jrexpress_entregas"
EMPRESA_WEBSITE: str = "jrexpressbr.com.br"
EMPRESA_SLOGAN: str = "JR ENTREGAS — Soluções em Logística"

# Dados Bancários
EMPRESA_PIX: str = "20443788000118"  # CNPJ como chave PIX
EMPRESA_BANCO: str = "Nubank"
EMPRESA_AGENCIA: str = "0001"
EMPRESA_CONTA: str = "38577538-4"
EMPRESA_TIPO_CONTA: str = "Corrente"

# Mensagem padrão de encerramento PDF
EMPRESA_MSG_ENCERRAMENTO: str = "Obrigado por contar com a JR ENTREGAS ME, sua melhor empresa de logística. Obrigada pela confiança e conte sempre conosco!"

# ============ CATEGORIAS DE CUSTOS PADRÃO ============

CATEGORIAS_CUSTO_PADRAO: List[Tuple[str, str]] = [
    ("Veículo", "#3182CE"),
    ("Operacional", "#38A169"),
    ("Administrativo", "#805AD5"),
    ("Outros", "#718096"),
]

COR_CATEGORIA_PADRAO: str = "#718096"

# ============ SENHA PADRÃO ============

SENHA_PADRAO: str = "jr2026"
SENHA_MINIMA: int = 6
