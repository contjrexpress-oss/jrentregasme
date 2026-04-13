"""
utils_pdf.py — Módulo de geração de PDF profissional para JR ENTREGAS ME
Utiliza ReportLab para layout completo com identidade visual corporativa.

Padrão baseado no modelo "Agenda Boa.pdf":
  - Cabeçalho: logo + dados da empresa + slogan
  - Seção de cliente (quando aplicável)
  - Conteúdo (tabelas, métricas)
  - Rodapé: dados bancários + contatos + paginação
"""

import io
import os
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    Image, PageBreak, HRFlowable
)
from reportlab.pdfgen import canvas
from config import (
    Cores, LOGO_PATH,
    EMPRESA_NOME, EMPRESA_CNPJ, EMPRESA_ENDERECO, EMPRESA_CIDADE,
    EMPRESA_CEP, EMPRESA_TELEFONE, EMPRESA_EMAIL, EMPRESA_SLOGAN,
    EMPRESA_WHATSAPP, EMPRESA_INSTAGRAM, EMPRESA_WEBSITE,
    EMPRESA_RESPONSAVEL, EMPRESA_CPF_RESPONSAVEL, EMPRESA_IE,
    EMPRESA_PIX, EMPRESA_BANCO, EMPRESA_AGENCIA, EMPRESA_CONTA,
    EMPRESA_TIPO_CONTA, EMPRESA_MSG_ENCERRAMENTO,
)
from utils import formatar_moeda_br

# ══════════════════════════════════════════════════════════
# CORES CORPORATIVAS (ReportLab HexColor, derivadas de config)
# ══════════════════════════════════════════════════════════
COR_AZUL = colors.HexColor(Cores.AZUL)
COR_AZUL_MEDIO = colors.HexColor(Cores.AZUL_CLARO)
COR_LARANJA = colors.HexColor(Cores.LARANJA)
COR_VERDE = colors.HexColor(Cores.VERDE)
COR_VERMELHO = colors.HexColor(Cores.VERMELHO)
COR_AMARELO = colors.HexColor(Cores.AMARELO)
COR_CINZA_CLARO = colors.HexColor(Cores.CINZA_CLARO)
COR_CINZA = colors.HexColor(Cores.CINZA)
COR_BRANCO = colors.white

# ══════════════════════════════════════════════════════════
# ESTILOS DE PARÁGRAFO
# ══════════════════════════════════════════════════════════
def _get_styles():
    """Retorna estilos customizados para o PDF."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name='TituloPrincipal',
        fontName='Helvetica-Bold',
        fontSize=18,
        textColor=COR_AZUL,
        spaceAfter=4 * mm,
        alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        name='Subtitulo',
        fontName='Helvetica',
        fontSize=10,
        textColor=COR_CINZA,
        spaceAfter=6 * mm,
        alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        name='SecaoTitulo',
        fontName='Helvetica-Bold',
        fontSize=13,
        textColor=COR_AZUL,
        spaceBefore=6 * mm,
        spaceAfter=3 * mm,
        alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        name='TextoNormal',
        fontName='Helvetica',
        fontSize=9,
        textColor=COR_AZUL,
        leading=12,
    ))
    styles.add(ParagraphStyle(
        name='TextoPequeno',
        fontName='Helvetica',
        fontSize=7.5,
        textColor=COR_CINZA,
        leading=10,
    ))
    styles.add(ParagraphStyle(
        name='TotalLinha',
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=COR_AZUL,
        alignment=TA_RIGHT,
    ))
    styles.add(ParagraphStyle(
        name='MetricaValor',
        fontName='Helvetica-Bold',
        fontSize=16,
        textColor=COR_LARANJA,
        alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name='MetricaLabel',
        fontName='Helvetica',
        fontSize=8,
        textColor=COR_CINZA,
        alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name='CelulaTabela',
        fontName='Helvetica',
        fontSize=8,
        textColor=COR_AZUL,
        leading=10,
    ))
    styles.add(ParagraphStyle(
        name='CelulaTabelaBold',
        fontName='Helvetica-Bold',
        fontSize=8,
        textColor=COR_AZUL,
        leading=10,
    ))
    styles.add(ParagraphStyle(
        name='CelulaTabelaVermelha',
        fontName='Helvetica-Bold',
        fontSize=8,
        textColor=COR_VERMELHO,
        leading=10,
    ))
    styles.add(ParagraphStyle(
        name='ClienteLabel',
        fontName='Helvetica-Bold',
        fontSize=9,
        textColor=COR_AZUL,
        leading=12,
    ))
    styles.add(ParagraphStyle(
        name='ClienteValor',
        fontName='Helvetica',
        fontSize=9,
        textColor=colors.HexColor("#333333"),
        leading=12,
    ))
    styles.add(ParagraphStyle(
        name='RodapeTexto',
        fontName='Helvetica',
        fontSize=7,
        textColor=COR_CINZA,
        leading=9,
    ))

    return styles


# ══════════════════════════════════════════════════════════
# CABEÇALHO E RODAPÉ PADRONIZADOS (Canvas callback)
# Baseado no modelo "Agenda Boa.pdf"
# ══════════════════════════════════════════════════════════
class _CabecalhoRodapePadrao:
    """
    Callback para cabeçalho e rodapé padronizados em todas as páginas.

    Cabeçalho:
    ┌──────────────────────────────────────────────────┐
    │ [LOGO]  JR ENTREGAS ME                           │
    │         Soluções em Logística                    │
    │         CNPJ: XX.XXX.XXX/XXXX-XX                │
    │         [Título do Relatório]     Data de geração│
    └──────────────────────────────────────────────────┘

    Rodapé:
    ┌──────────────────────────────────────────────────┐
    │ Dados Bancários: PIX: CNPJ | Nubank Ag 0001     │
    │ Contato: email | telefone | whatsapp | instagram │
    │ JR ENTREGAS ME — Todos os direitos    Página X/Y │
    └──────────────────────────────────────────────────┘
    """

    def __init__(self, titulo, subtitulo=""):
        self.titulo = titulo
        self.subtitulo = subtitulo

    def _pw(self, c):
        return c._pagesize[0]

    def _ph(self, c):
        return c._pagesize[1]

    def cabecalho(self, c, doc):
        c.saveState()
        w = self._pw(c)
        h = self._ph(c)

        # ── Barra superior azul escuro ──
        header_h = 28 * mm
        c.setFillColor(COR_AZUL)
        c.rect(0, h - header_h, w, header_h, fill=1, stroke=0)

        # ── Faixa laranja fina ──
        c.setFillColor(COR_LARANJA)
        c.rect(0, h - header_h - 1.2 * mm, w, 1.2 * mm, fill=1, stroke=0)

        # ── Logo ──
        logo_size = 18 * mm
        logo_x = 8 * mm
        logo_y = h - header_h + 5 * mm
        if os.path.exists(LOGO_PATH):
            try:
                c.drawImage(
                    LOGO_PATH, logo_x, logo_y,
                    width=logo_size, height=logo_size,
                    preserveAspectRatio=True, mask='auto'
                )
            except Exception:
                pass

        # ── Dados da empresa ──
        text_x = logo_x + logo_size + 4 * mm
        y_top = h - 7 * mm

        # Nome da empresa
        c.setFillColor(COR_BRANCO)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(text_x, y_top, EMPRESA_NOME)

        # Slogan
        c.setFont("Helvetica", 7.5)
        c.setFillColor(colors.HexColor("#CCCCCC"))
        c.drawString(text_x, y_top - 5 * mm, EMPRESA_SLOGAN)

        # CNPJ e contato
        c.setFont("Helvetica", 6.5)
        c.setFillColor(colors.HexColor("#AAAAAA"))
        info_line = f"CNPJ: {EMPRESA_CNPJ}  |  {EMPRESA_ENDERECO}, {EMPRESA_CIDADE} — CEP {EMPRESA_CEP}"
        c.drawString(text_x, y_top - 9 * mm, info_line)

        contact_line = f"Tel: {EMPRESA_TELEFONE}  |  Email: {EMPRESA_EMAIL}  |  {EMPRESA_WEBSITE}"
        c.drawString(text_x, y_top - 13 * mm, contact_line)

        # ── Título do relatório (canto direito) ──
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(COR_LARANJA)
        c.drawRightString(w - 8 * mm, y_top, self.titulo)

        if self.subtitulo:
            c.setFont("Helvetica", 7)
            c.setFillColor(colors.HexColor("#CCCCCC"))
            c.drawRightString(w - 8 * mm, y_top - 4.5 * mm, self.subtitulo)

        # Data de geração
        c.setFont("Helvetica", 6.5)
        c.setFillColor(colors.HexColor("#999999"))
        data_str = datetime.now().strftime("Gerado em %d/%m/%Y às %H:%M")
        c.drawRightString(w - 8 * mm, y_top - 13 * mm, data_str)

        c.restoreState()

    def rodape(self, c, doc):
        c.saveState()
        w = self._pw(c)

        rodape_top = 22 * mm

        # ── Linha separadora laranja ──
        c.setStrokeColor(COR_LARANJA)
        c.setLineWidth(0.8)
        c.line(8 * mm, rodape_top, w - 8 * mm, rodape_top)

        # ── Dados bancários ──
        c.setFont("Helvetica-Bold", 7)
        c.setFillColor(COR_AZUL)
        c.drawString(8 * mm, rodape_top - 4 * mm, "Dados Bancários:")

        c.setFont("Helvetica", 6.5)
        c.setFillColor(COR_CINZA)
        banco_info = (
            f"PIX: {EMPRESA_PIX} (CNPJ)  |  Banco: {EMPRESA_BANCO}  |  "
            f"Ag: {EMPRESA_AGENCIA}  |  Conta: {EMPRESA_CONTA} ({EMPRESA_TIPO_CONTA})"
        )
        c.drawString(8 * mm, rodape_top - 8 * mm, banco_info)

        # ── Contatos ──
        contato_info = (
            f"Email: {EMPRESA_EMAIL}  |  Tel: {EMPRESA_TELEFONE}  |  "
            f"WhatsApp: {EMPRESA_WHATSAPP}  |  Instagram: @{EMPRESA_INSTAGRAM}"
        )
        c.drawString(8 * mm, rodape_top - 12 * mm, contato_info)

        # ── Copyright + paginação ──
        c.setFont("Helvetica", 6)
        c.setFillColor(colors.HexColor("#999999"))
        c.drawString(8 * mm, rodape_top - 17 * mm,
                      f"{EMPRESA_NOME} — Todos os direitos reservados")
        c.drawRightString(w - 8 * mm, rodape_top - 17 * mm,
                          f"Página {doc.page}")

        c.restoreState()

    def on_page(self, c, doc):
        self.cabecalho(c, doc)
        self.rodape(c, doc)


# ══════════════════════════════════════════════════════════
# COMPONENTES REUTILIZÁVEIS
# ══════════════════════════════════════════════════════════

def _criar_secao_cliente(cliente_dados, styles):
    """
    Cria seção com dados do cliente como flowable (Table).

    Args:
        cliente_dados: dict com keys opcionais:
            nome, cpf_cnpj, ie, endereco, bairro, cidade_uf, cep,
            email, telefone, contato
    Returns:
        lista de flowables para adicionar ao elements
    """
    elements = []
    elements.append(Paragraph("DADOS DO CLIENTE", styles['SecaoTitulo']))

    # Monta pares label: valor
    campos = []
    if cliente_dados.get('nome'):
        campos.append(("Nome / Razão Social:", cliente_dados['nome']))
    if cliente_dados.get('cpf_cnpj'):
        campos.append(("CPF/CNPJ:", cliente_dados['cpf_cnpj']))
    if cliente_dados.get('ie'):
        campos.append(("Inscrição Estadual:", cliente_dados['ie']))
    if cliente_dados.get('endereco'):
        campos.append(("Endereço:", cliente_dados['endereco']))
    if cliente_dados.get('bairro'):
        campos.append(("Bairro:", cliente_dados['bairro']))
    if cliente_dados.get('cidade_uf'):
        campos.append(("Município/UF:", cliente_dados['cidade_uf']))
    if cliente_dados.get('cep'):
        campos.append(("CEP:", cliente_dados['cep']))
    if cliente_dados.get('email'):
        campos.append(("Email:", cliente_dados['email']))
    if cliente_dados.get('telefone'):
        campos.append(("Telefone:", cliente_dados['telefone']))
    if cliente_dados.get('contato'):
        campos.append(("Contato:", cliente_dados['contato']))

    if not campos:
        return elements

    # Criar tabela 2 colunas (lado a lado para compactar)
    # Divide em 2 colunas: esquerda e direita
    half = (len(campos) + 1) // 2
    left_campos = campos[:half]
    right_campos = campos[half:]

    table_data = []
    for i in range(max(len(left_campos), len(right_campos))):
        row = []
        if i < len(left_campos):
            row.append(Paragraph(left_campos[i][0], styles['ClienteLabel']))
            row.append(Paragraph(str(left_campos[i][1]), styles['ClienteValor']))
        else:
            row.extend(["", ""])

        if i < len(right_campos):
            row.append(Paragraph(right_campos[i][0], styles['ClienteLabel']))
            row.append(Paragraph(str(right_campos[i][1]), styles['ClienteValor']))
        else:
            row.extend(["", ""])

        table_data.append(row)

    col_widths = [30 * mm, 55 * mm, 30 * mm, 55 * mm]
    t = Table(table_data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ('BOX', (0, 0), (-1, -1), 0.5, COR_CINZA_CLARO),
        ('LINEBELOW', (0, 0), (-1, -1), 0.25, colors.HexColor("#E2E8F0")),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 3 * mm))

    return elements


def _criar_metricas_row(metricas, styles):
    """
    Cria uma linha de métricas (cards) como tabela.
    metricas: lista de dicts {"label": str, "valor": str, "cor": color}
    """
    data = []
    row_vals = []
    row_labels = []
    for m in metricas:
        cor = m.get("cor", COR_LARANJA)
        style_val = ParagraphStyle(
            name=f'mv_{m["label"][:10]}',
            parent=styles['MetricaValor'],
            textColor=cor,
        )
        row_vals.append(Paragraph(str(m["valor"]), style_val))
        row_labels.append(Paragraph(m["label"], styles['MetricaLabel']))
    data.append(row_vals)
    data.append(row_labels)

    n = len(metricas)
    col_w = 170 * mm / n if n > 0 else 170 * mm
    col_widths = [col_w] * n

    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 0.5, COR_CINZA_CLARO),
        ('INNERGRID', (0, 0), (-1, -1), 0.3, COR_CINZA_CLARO),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 2),
        ('TOPPADDING', (0, 1), (-1, 1), 1),
        ('BOTTOMPADDING', (0, 1), (-1, 1), 6),
        ('BACKGROUND', (0, 0), (-1, -1), COR_BRANCO),
        ('ROUNDEDCORNERS', [3, 3, 3, 3]),
    ]))
    return t


def criar_tabela_pdf(dados, colunas, col_widths=None, destaque_col=None, styles=None):
    """
    Cria uma tabela formatada profissionalmente.
    dados: lista de listas (linhas)
    colunas: lista de strings (cabeçalhos)
    col_widths: larguras personalizadas (opcional)
    destaque_col: índice da coluna para destacar vermelho se negativo (opcional)
    """
    if styles is None:
        styles = _get_styles()

    # Cabeçalho
    header = [Paragraph(str(c), ParagraphStyle(
        name=f'th_{i}',
        fontName='Helvetica-Bold',
        fontSize=8,
        textColor=COR_BRANCO,
        alignment=TA_CENTER,
        leading=10,
    )) for i, c in enumerate(colunas)]

    # Corpo
    body = []
    for row_idx, row in enumerate(dados):
        new_row = []
        for col_idx, cell in enumerate(row):
            cell_str = str(cell) if cell is not None else ""
            if destaque_col is not None and col_idx == destaque_col:
                if 'CRÍTICO' in cell_str.upper():
                    new_row.append(Paragraph(cell_str, styles['CelulaTabelaVermelha']))
                    continue
            new_row.append(Paragraph(cell_str, styles['CelulaTabela']))
        body.append(new_row)

    table_data = [header] + body

    if col_widths is None:
        n_cols = len(colunas)
        available = 180 * mm
        col_widths = [available / n_cols] * n_cols

    t = Table(table_data, colWidths=col_widths, repeatRows=1)

    style_commands = [
        # Cabeçalho
        ('BACKGROUND', (0, 0), (-1, 0), COR_AZUL),
        ('TEXTCOLOR', (0, 0), (-1, 0), COR_BRANCO),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, 0), 5),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 5),

        # Corpo
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),

        # Bordas
        ('BOX', (0, 0), (-1, -1), 0.5, COR_CINZA),
        ('LINEBELOW', (0, 0), (-1, 0), 1, COR_LARANJA),
        ('INNERGRID', (0, 1), (-1, -1), 0.25, colors.HexColor("#E2E8F0")),
    ]

    # Cores alternadas nas linhas
    for i in range(1, len(table_data)):
        if i % 2 == 0:
            style_commands.append(('BACKGROUND', (0, i), (-1, i), COR_CINZA_CLARO))
        else:
            style_commands.append(('BACKGROUND', (0, i), (-1, i), COR_BRANCO))

    t.setStyle(TableStyle(style_commands))
    return t


def _separador():
    """Retorna linha horizontal decorativa."""
    return HRFlowable(
        width="100%", thickness=0.5, color=COR_CINZA_CLARO,
        spaceBefore=3 * mm, spaceAfter=3 * mm,
    )


def _build_pdf(elements, titulo, subtitulo="", pagesize=A4):
    """Helper genérico para construir PDF com cabeçalho/rodapé padronizados."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=pagesize,
        topMargin=34 * mm, bottomMargin=26 * mm,
        leftMargin=12 * mm, rightMargin=12 * mm,
        title=f"{titulo} — {EMPRESA_NOME}",
    )
    handler = _CabecalhoRodapePadrao(titulo, subtitulo)
    doc.build(elements, onFirstPage=handler.on_page, onLaterPages=handler.on_page)
    buffer.seek(0)
    return buffer


# ══════════════════════════════════════════════════════════
# FUNÇÕES PÚBLICAS DE GERAÇÃO DE PDF
# ══════════════════════════════════════════════════════════

def gerar_pdf_relatorio_estoque(dados_produtos, metricas, filtros_aplicados=""):
    """
    Gera PDF do relatório de estoque.
    dados_produtos: lista de dicts com keys:
        status, codigo, descricao, estoque_atual, estoque_minimo, estoque_maximo,
        entradas, saidas, repor
    metricas: dict com total, critico, atencao, ok
    """
    styles = _get_styles()
    elements = []

    # Título
    elements.append(Paragraph("📦 Relatório de Estoque", styles['TituloPrincipal']))
    if filtros_aplicados:
        elements.append(Paragraph(f"Filtros: {filtros_aplicados}", styles['Subtitulo']))
    elements.append(Spacer(1, 3 * mm))

    # Métricas
    met_row = _criar_metricas_row([
        {"label": "Total Produtos", "valor": str(metricas.get('total', 0)), "cor": COR_AZUL},
        {"label": "🔴 Críticos", "valor": str(metricas.get('critico', 0)), "cor": COR_VERMELHO},
        {"label": "🟡 Atenção", "valor": str(metricas.get('atencao', 0)), "cor": COR_AMARELO},
        {"label": "🟢 OK", "valor": str(metricas.get('ok', 0)), "cor": COR_VERDE},
    ], styles)
    elements.append(met_row)
    elements.append(Spacer(1, 5 * mm))
    elements.append(_separador())

    # Tabela de produtos
    elements.append(Paragraph("Detalhamento de Produtos", styles['SecaoTitulo']))

    colunas = ['Status', 'Código', 'Descrição', 'Est. Atual', 'Mín.', 'Máx.', 'Entradas', 'Saídas', 'Repor']
    linhas = []
    for p in dados_produtos:
        linhas.append([
            str(p.get('status', '')),
            str(p.get('codigo', '')),
            str(p.get('descricao', '')),
            str(p.get('estoque_atual', 0)),
            str(p.get('estoque_minimo', 0)),
            str(p.get('estoque_maximo', 0)),
            str(p.get('entradas', 0)),
            str(p.get('saidas', 0)),
            str(p.get('repor', 0)),
        ])

    col_widths = [22 * mm, 20 * mm, 42 * mm, 16 * mm, 14 * mm, 14 * mm, 16 * mm, 16 * mm, 16 * mm]
    tabela = criar_tabela_pdf(linhas, colunas, col_widths=col_widths, destaque_col=0, styles=styles)
    elements.append(tabela)

    # Alertas de estoque crítico
    criticos = [p for p in dados_produtos if 'CRÍTICO' in str(p.get('status', '')).upper()]
    if criticos:
        elements.append(Spacer(1, 5 * mm))
        elements.append(_separador())
        elements.append(Paragraph("⚠️ Produtos com Estoque Crítico", styles['SecaoTitulo']))

        colunas_crit = ['Código', 'Descrição', 'Estoque Atual', 'Mínimo', 'Qtd. Repor']
        linhas_crit = []
        for p in criticos:
            linhas_crit.append([
                str(p.get('codigo', '')),
                str(p.get('descricao', '')),
                str(p.get('estoque_atual', 0)),
                str(p.get('estoque_minimo', 0)),
                str(p.get('repor', 0)),
            ])
        col_w_crit = [25 * mm, 60 * mm, 25 * mm, 25 * mm, 25 * mm]
        tabela_crit = criar_tabela_pdf(linhas_crit, colunas_crit, col_widths=col_w_crit, styles=styles)

        extra_style = TableStyle([
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#FFF5F5")),
        ])
        tabela_crit.setStyle(extra_style)
        elements.append(tabela_crit)

    return _build_pdf(elements, "Relatório de Estoque", "Controle de produtos e alertas de reposição")


def gerar_pdf_relatorio_financeiro(
    metricas_resumo, df_faturamento=None, df_custos=None,
    df_mensal=None, filtros_texto="", chart_images=None
):
    """
    Gera PDF do relatório financeiro completo (unificado).
    metricas_resumo: dict com receita, custos, lucro, margem
    df_faturamento: DataFrame de faturamento
    df_custos: DataFrame de custos
    df_mensal: DataFrame resumo mensal
    filtros_texto: texto dos filtros aplicados
    chart_images: dict de {nome: bytes_io} com imagens de gráficos
    """
    styles = _get_styles()
    elements = []

    # Título
    elements.append(Paragraph("💰 Relatório Financeiro", styles['TituloPrincipal']))
    if filtros_texto:
        elements.append(Paragraph(f"Período / Filtros: {filtros_texto}", styles['Subtitulo']))
    elements.append(Spacer(1, 3 * mm))

    # Métricas
    receita = metricas_resumo.get('receita', 0)
    custos_val = metricas_resumo.get('custos', 0)
    lucro_val = metricas_resumo.get('lucro', 0)
    margem_val = metricas_resumo.get('margem', 0)

    met_row = _criar_metricas_row([
        {"label": "Receita Total", "valor": formatar_moeda_br(receita), "cor": COR_VERDE},
        {"label": "Custos Totais", "valor": formatar_moeda_br(custos_val), "cor": COR_VERMELHO},
        {"label": "Lucro Líquido", "valor": formatar_moeda_br(lucro_val), "cor": COR_VERDE if lucro_val >= 0 else COR_VERMELHO},
        {"label": "Margem", "valor": f"{margem_val:.1f}%", "cor": COR_AZUL},
    ], styles)
    elements.append(met_row)
    elements.append(Spacer(1, 5 * mm))
    elements.append(_separador())

    # Gráficos como imagem (se fornecidos)
    if chart_images:
        for nome, img_bytes in chart_images.items():
            elements.append(Paragraph(nome, styles['SecaoTitulo']))
            img_bytes.seek(0)
            img = Image(img_bytes, width=170 * mm, height=90 * mm)
            img.hAlign = 'CENTER'
            elements.append(img)
            elements.append(Spacer(1, 3 * mm))
        elements.append(_separador())

    # Tabela de Faturamento
    if df_faturamento is not None and not df_faturamento.empty:
        elements.append(Paragraph("📈 Detalhamento de Faturamento", styles['SecaoTitulo']))
        colunas_fat = ['Data', 'Descrição', 'Região', 'Veículo', 'Cliente', 'Valor (R$)']

        linhas_fat = []
        for _, row in df_faturamento.iterrows():
            data_val = str(row.get('data', ''))
            desc = str(row.get('descricao', ''))[:40]
            regiao = str(row.get('regiao', ''))
            veiculo = str(row.get('veiculo', ''))
            cliente = str(row.get('cliente', ''))[:25]
            valor = row.get('valor', 0)
            linhas_fat.append([data_val, desc, regiao, veiculo, cliente, formatar_moeda_br(valor)])

        col_w_fat = [22 * mm, 45 * mm, 28 * mm, 22 * mm, 30 * mm, 25 * mm]
        tabela_fat = criar_tabela_pdf(linhas_fat, colunas_fat, col_widths=col_w_fat, styles=styles)
        elements.append(tabela_fat)

        total_fat = df_faturamento['valor'].sum()
        elements.append(Spacer(1, 2 * mm))
        elements.append(Paragraph(f"Total Faturamento: {formatar_moeda_br(total_fat)}", styles['TotalLinha']))
        elements.append(Spacer(1, 4 * mm))

    # Tabela de Custos
    if df_custos is not None and not df_custos.empty:
        elements.append(_separador())
        elements.append(Paragraph("📉 Detalhamento de Custos", styles['SecaoTitulo']))
        colunas_cus = ['Data', 'Descrição', 'Categoria', 'Valor (R$)']

        linhas_cus = []
        for _, row in df_custos.iterrows():
            data_val = str(row.get('data', ''))
            desc = str(row.get('descricao', ''))[:45]
            cat = str(row.get('categoria', ''))[:30]
            valor = row.get('valor', 0)
            linhas_cus.append([data_val, desc, cat, formatar_moeda_br(valor)])

        col_w_cus = [24 * mm, 60 * mm, 50 * mm, 28 * mm]
        tabela_cus = criar_tabela_pdf(linhas_cus, colunas_cus, col_widths=col_w_cus, styles=styles)
        elements.append(tabela_cus)

        total_cus = df_custos['valor'].sum()
        elements.append(Spacer(1, 2 * mm))
        elements.append(Paragraph(f"Total Custos: {formatar_moeda_br(total_cus)}", styles['TotalLinha']))

    # Resumo Mensal
    if df_mensal is not None and not df_mensal.empty:
        elements.append(_separador())
        elements.append(Paragraph("📊 Resumo Mensal", styles['SecaoTitulo']))
        colunas_men = ['Mês', 'Faturamento', 'Custos', 'Lucro']
        linhas_men = []
        for _, row in df_mensal.iterrows():
            fat_v = row.get('Faturamento', 0)
            cus_v = row.get('Custos', 0)
            luc_v = row.get('Lucro', fat_v - cus_v)
            linhas_men.append([
                str(row.get('Mês', '')),
                formatar_moeda_br(fat_v),
                formatar_moeda_br(cus_v),
                formatar_moeda_br(luc_v),
            ])
        col_w_men = [35 * mm, 42 * mm, 42 * mm, 42 * mm]
        tabela_men = criar_tabela_pdf(linhas_men, colunas_men, col_widths=col_w_men, styles=styles)
        elements.append(tabela_men)

    return _build_pdf(elements, "Relatório Financeiro", "Faturamento, custos e análise de lucro")


def gerar_pdf_faturamento(dados_faturamento, metricas, cliente_dados=None):
    """
    Gera PDF somente da tabela de faturamento.
    dados_faturamento: lista de dicts
    metricas: dict com total, registros, media
    cliente_dados: dict opcional com dados do cliente (nome, cpf_cnpj, etc.)
    """
    styles = _get_styles()
    elements = []

    elements.append(Paragraph("📈 Relatório de Faturamento", styles['TituloPrincipal']))
    elements.append(Spacer(1, 3 * mm))

    # Seção do cliente (se filtrado por cliente)
    if cliente_dados:
        elements.extend(_criar_secao_cliente(cliente_dados, styles))
        elements.append(_separador())

    # Métricas
    met_row = _criar_metricas_row([
        {"label": "Total Faturamento", "valor": formatar_moeda_br(metricas.get('total', 0)), "cor": COR_VERDE},
        {"label": "Total Registros", "valor": str(metricas.get('registros', 0)), "cor": COR_AZUL},
        {"label": "Média por Nota", "valor": formatar_moeda_br(metricas.get('media', 0)), "cor": COR_LARANJA},
    ], styles)
    elements.append(met_row)
    elements.append(Spacer(1, 5 * mm))
    elements.append(_separador())

    colunas = ['ID', 'Data', 'Descrição', 'Região', 'Veículo', 'Cliente', 'CEP', 'Bairro', 'Valor (R$)']
    linhas = []
    for d in dados_faturamento:
        linhas.append([
            str(d.get('id', '')),
            str(d.get('data', '')),
            str(d.get('descricao', ''))[:35],
            str(d.get('regiao', '')),
            str(d.get('veiculo', '')),
            str(d.get('cliente', ''))[:20],
            str(d.get('cep', '')),
            str(d.get('bairro', ''))[:15],
            formatar_moeda_br(d.get('valor', 0)),
        ])

    col_w = [12 * mm, 22 * mm, 50 * mm, 30 * mm, 22 * mm, 35 * mm, 22 * mm, 30 * mm, 25 * mm]
    tabela = criar_tabela_pdf(linhas, colunas, col_widths=col_w, styles=styles)
    elements.append(tabela)

    total = metricas.get('total', 0)
    elements.append(Spacer(1, 3 * mm))
    elements.append(Paragraph(f"Total: {formatar_moeda_br(total)}", styles['TotalLinha']))

    return _build_pdf(elements, "Relatório de Faturamento", "Detalhamento completo de faturamento",
                      pagesize=landscape(A4))


def gerar_pdf_custos(dados_custos, metricas, cliente_dados=None):
    """
    Gera PDF da tabela de custos.
    dados_custos: lista de dicts
    metricas: dict com total, registros
    cliente_dados: dict opcional com dados do cliente (nome, cpf_cnpj, etc.)
    """
    styles = _get_styles()
    elements = []

    elements.append(Paragraph("📉 Relatório de Custos", styles['TituloPrincipal']))
    elements.append(Spacer(1, 3 * mm))

    # Seção do cliente (se filtrado por cliente)
    if cliente_dados:
        elements.extend(_criar_secao_cliente(cliente_dados, styles))
        elements.append(_separador())

    # Métricas
    met_row = _criar_metricas_row([
        {"label": "Total Custos", "valor": formatar_moeda_br(metricas.get('total', 0)), "cor": COR_VERMELHO},
        {"label": "Total Registros", "valor": str(metricas.get('registros', 0)), "cor": COR_AZUL},
    ], styles)
    elements.append(met_row)
    elements.append(Spacer(1, 5 * mm))
    elements.append(_separador())

    # Verificar se há coluna de origem (custos unificados)
    tem_origem = any(d.get('origem') for d in dados_custos)
    if tem_origem:
        colunas = ['ID', 'Data', 'Descrição', 'Categoria', 'Valor (R$)', 'Origem']
    else:
        colunas = ['ID', 'Data', 'Descrição', 'Categoria', 'Valor (R$)']
    linhas = []
    for d in dados_custos:
        linha = [
            str(d.get('id', '')),
            str(d.get('data', '')),
            str(d.get('descricao', ''))[:45],
            str(d.get('categoria', ''))[:30],
            formatar_moeda_br(d.get('valor', 0)),
        ]
        if tem_origem:
            linha.append(str(d.get('origem', 'Direto')))
        linhas.append(linha)

    if tem_origem:
        col_w = [14 * mm, 22 * mm, 50 * mm, 35 * mm, 28 * mm, 20 * mm]
    else:
        col_w = [14 * mm, 22 * mm, 60 * mm, 45 * mm, 28 * mm]
    tabela = criar_tabela_pdf(linhas, colunas, col_widths=col_w, styles=styles)
    elements.append(tabela)

    total = metricas.get('total', 0)
    elements.append(Spacer(1, 3 * mm))
    elements.append(Paragraph(f"Total: {formatar_moeda_br(total)}", styles['TotalLinha']))

    return _build_pdf(elements, "Relatório de Custos", "Detalhamento completo de custos")


def gerar_pdf_notas_fiscais(notas_dados, metricas, filtros_texto=""):
    """
    Gera PDF da lista de notas fiscais com seus itens.
    notas_dados: lista de dicts com keys:
        numero, data_nota, tipo, total_unidades, cep, bairro, municipio, itens (lista)
    metricas: dict com total, entradas, saidas
    """
    styles = _get_styles()
    elements = []

    elements.append(Paragraph("📋 Notas Fiscais Processadas", styles['TituloPrincipal']))
    if filtros_texto:
        elements.append(Paragraph(f"Filtros: {filtros_texto}", styles['Subtitulo']))
    elements.append(Spacer(1, 3 * mm))

    # Métricas
    met_row = _criar_metricas_row([
        {"label": "Total de Notas", "valor": str(metricas.get('total', 0)), "cor": COR_AZUL},
        {"label": "Notas de Entrada", "valor": str(metricas.get('entradas', 0)), "cor": COR_VERDE},
        {"label": "Notas de Saída", "valor": str(metricas.get('saidas', 0)), "cor": COR_VERMELHO},
    ], styles)
    elements.append(met_row)
    elements.append(Spacer(1, 5 * mm))
    elements.append(_separador())

    # Tabela resumo de notas
    elements.append(Paragraph("Resumo de Notas", styles['SecaoTitulo']))
    colunas_notas = ['Nº Nota', 'Data', 'Tipo', 'Unidades', 'CEP', 'Bairro', 'Município']
    linhas_notas = []
    for n in notas_dados:
        tipo_label = "ENTRADA" if n.get('tipo') == 'entrada' else "SAÍDA"
        linhas_notas.append([
            str(n.get('numero', '')),
            str(n.get('data_nota', '')),
            tipo_label,
            str(n.get('total_unidades', 0)),
            str(n.get('cep', '')),
            str(n.get('bairro', ''))[:20],
            str(n.get('municipio', ''))[:20],
        ])

    col_w_notas = [22 * mm, 22 * mm, 20 * mm, 18 * mm, 22 * mm, 35 * mm, 35 * mm]
    tabela_notas = criar_tabela_pdf(linhas_notas, colunas_notas, col_widths=col_w_notas, styles=styles)
    elements.append(tabela_notas)

    # Detalhamento de itens por nota
    elements.append(Spacer(1, 5 * mm))
    elements.append(_separador())
    elements.append(Paragraph("Detalhamento de Itens por Nota", styles['SecaoTitulo']))

    for n in notas_dados:
        itens = n.get('itens', [])
        tipo_emoji = "🟢" if n.get('tipo') == 'entrada' else "🔴"
        tipo_label = "ENTRADA" if n.get('tipo') == 'entrada' else "SAÍDA"

        elements.append(Spacer(1, 3 * mm))
        elements.append(Paragraph(
            f"{tipo_emoji} Nota {n.get('numero', '')} — {tipo_label} — {n.get('data_nota', '')} — {n.get('total_unidades', 0)} un",
            styles['SecaoTitulo']
        ))

        if itens:
            colunas_itens = ['Código', 'Descrição', 'Quantidade']
            linhas_itens = [[
                str(item.get('codigo_produto', '')),
                str(item.get('descricao', '')),
                str(item.get('quantidade', 0)),
            ] for item in itens]
            col_w_itens = [30 * mm, 100 * mm, 30 * mm]
            tabela_itens = criar_tabela_pdf(linhas_itens, colunas_itens, col_widths=col_w_itens, styles=styles)
            elements.append(tabela_itens)
        else:
            elements.append(Paragraph("Sem itens registrados.", styles['TextoNormal']))

    return _build_pdf(elements, "Gestão de Notas Fiscais", "Notas processadas e detalhamento de itens")


def exportar_grafico_como_imagem(fig, width=800, height=400):
    """
    Exporta um gráfico Plotly como imagem PNG em BytesIO.
    Requer kaleido instalado. Retorna None se falhar.
    """
    try:
        img_bytes = io.BytesIO()
        fig.write_image(img_bytes, format='png', width=width, height=height, scale=2)
        img_bytes.seek(0)
        return img_bytes
    except Exception:
        return None
