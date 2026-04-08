"""
utils_pdf.py — Módulo de geração de PDF profissional para JR ENTREGAS ME
Utiliza ReportLab para layout completo com identidade visual corporativa.
"""

import io
import os
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    Image, PageBreak, HRFlowable
)
from reportlab.pdfgen import canvas

# ══════════════════════════════════════════════════════════
# CORES CORPORATIVAS
# ══════════════════════════════════════════════════════════
COR_AZUL = colors.HexColor("#0B132B")
COR_AZUL_MEDIO = colors.HexColor("#1C2541")
COR_LARANJA = colors.HexColor("#F29F05")
COR_VERDE = colors.HexColor("#38A169")
COR_VERMELHO = colors.HexColor("#E53E3E")
COR_AMARELO = colors.HexColor("#D69E2E")
COR_CINZA_CLARO = colors.HexColor("#F4F7F6")
COR_CINZA = colors.HexColor("#718096")
COR_BRANCO = colors.white

LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "logo.png")

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

    return styles


# ══════════════════════════════════════════════════════════
# CABEÇALHO E RODAPÉ (Canvas callback)
# ══════════════════════════════════════════════════════════
class _CabecalhoRodape:
    """Callback para cabeçalho e rodapé em todas as páginas."""

    def __init__(self, titulo, subtitulo="", orientacao="retrato"):
        self.titulo = titulo
        self.subtitulo = subtitulo
        self.orientacao = orientacao
        self.paginas = []

    def _pagina_width(self, canvas_obj):
        return canvas_obj._pagesize[0]

    def _pagina_height(self, canvas_obj):
        return canvas_obj._pagesize[1]

    def cabecalho(self, canvas_obj, doc):
        canvas_obj.saveState()
        w = self._pagina_width(canvas_obj)
        h = self._pagina_height(canvas_obj)

        # Barra superior azul
        canvas_obj.setFillColor(COR_AZUL)
        canvas_obj.rect(0, h - 22 * mm, w, 22 * mm, fill=1, stroke=0)

        # Faixa laranja fina
        canvas_obj.setFillColor(COR_LARANJA)
        canvas_obj.rect(0, h - 23 * mm, w, 1 * mm, fill=1, stroke=0)

        # Logo
        if os.path.exists(LOGO_PATH):
            try:
                canvas_obj.drawImage(
                    LOGO_PATH, 8 * mm, h - 19 * mm, width=16 * mm, height=16 * mm,
                    preserveAspectRatio=True, mask='auto'
                )
            except Exception:
                pass

        # Título
        canvas_obj.setFillColor(COR_BRANCO)
        canvas_obj.setFont("Helvetica-Bold", 13)
        canvas_obj.drawString(28 * mm, h - 12 * mm, self.titulo)

        # Subtítulo
        if self.subtitulo:
            canvas_obj.setFont("Helvetica", 8)
            canvas_obj.setFillColor(colors.HexColor("#CCCCCC"))
            canvas_obj.drawString(28 * mm, h - 17 * mm, self.subtitulo)

        # Data de geração (canto direito)
        canvas_obj.setFont("Helvetica", 7)
        canvas_obj.setFillColor(colors.HexColor("#AAAAAA"))
        data_str = datetime.now().strftime("Gerado em %d/%m/%Y às %H:%M")
        canvas_obj.drawRightString(w - 8 * mm, h - 12 * mm, data_str)
        canvas_obj.drawRightString(w - 8 * mm, h - 17 * mm, "JR ENTREGAS ME")

        canvas_obj.restoreState()

    def rodape(self, canvas_obj, doc):
        canvas_obj.saveState()
        w = self._pagina_width(canvas_obj)

        # Linha separadora
        canvas_obj.setStrokeColor(COR_CINZA_CLARO)
        canvas_obj.setLineWidth(0.5)
        canvas_obj.line(8 * mm, 12 * mm, w - 8 * mm, 12 * mm)

        # Texto do rodapé
        canvas_obj.setFont("Helvetica", 7)
        canvas_obj.setFillColor(COR_CINZA)
        canvas_obj.drawString(8 * mm, 7 * mm, "JR ENTREGAS ME — Soluções em Logística | (21) 980531278")
        canvas_obj.drawRightString(w - 8 * mm, 7 * mm, f"Página {doc.page}")

        canvas_obj.restoreState()

    def on_page(self, canvas_obj, doc):
        self.cabecalho(canvas_obj, doc)
        self.rodape(canvas_obj, doc)


# ══════════════════════════════════════════════════════════
# COMPONENTES REUTILIZÁVEIS
# ══════════════════════════════════════════════════════════
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
            # Destacar valores negativos ou status crítico
            if destaque_col is not None and col_idx == destaque_col:
                if 'CRÍTICO' in cell_str or 'CRÍTICO' in cell_str.upper():
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
    buffer = io.BytesIO()
    styles = _get_styles()

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=28 * mm, bottomMargin=18 * mm,
        leftMargin=12 * mm, rightMargin=12 * mm,
        title="Relatório de Estoque — JR ENTREGAS ME",
    )

    handler = _CabecalhoRodape("Relatório de Estoque", "Controle de produtos e alertas de reposição")
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

        # Destaque vermelho no fundo das linhas
        extra_style = TableStyle([
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#FFF5F5")),
        ])
        tabela_crit.setStyle(extra_style)
        elements.append(tabela_crit)

    # Build
    doc.build(elements, onFirstPage=handler.on_page, onLaterPages=handler.on_page)
    buffer.seek(0)
    return buffer


def gerar_pdf_relatorio_financeiro(
    metricas_resumo, df_faturamento=None, df_custos=None,
    df_mensal=None, filtros_texto="", chart_images=None
):
    """
    Gera PDF do relatório financeiro completo.
    metricas_resumo: dict com receita, custos, lucro, margem
    df_faturamento: DataFrame de faturamento
    df_custos: DataFrame de custos
    df_mensal: DataFrame resumo mensal
    filtros_texto: texto dos filtros aplicados
    chart_images: dict de {nome: bytes_io} com imagens de gráficos
    """
    buffer = io.BytesIO()
    styles = _get_styles()

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=28 * mm, bottomMargin=18 * mm,
        leftMargin=12 * mm, rightMargin=12 * mm,
        title="Relatório Financeiro — JR ENTREGAS ME",
    )

    handler = _CabecalhoRodape("Relatório Financeiro", "Faturamento, custos e análise de lucro")
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
        {"label": "Receita Total", "valor": f"R$ {receita:,.2f}", "cor": COR_VERDE},
        {"label": "Custos Totais", "valor": f"R$ {custos_val:,.2f}", "cor": COR_VERMELHO},
        {"label": "Lucro Líquido", "valor": f"R$ {lucro_val:,.2f}", "cor": COR_VERDE if lucro_val >= 0 else COR_VERMELHO},
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
            linhas_fat.append([data_val, desc, regiao, veiculo, cliente, f"R$ {valor:,.2f}"])

        col_w_fat = [22 * mm, 45 * mm, 28 * mm, 22 * mm, 30 * mm, 25 * mm]
        tabela_fat = criar_tabela_pdf(linhas_fat, colunas_fat, col_widths=col_w_fat, styles=styles)
        elements.append(tabela_fat)

        total_fat = df_faturamento['valor'].sum()
        elements.append(Spacer(1, 2 * mm))
        elements.append(Paragraph(f"Total Faturamento: R$ {total_fat:,.2f}", styles['TotalLinha']))
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
            linhas_cus.append([data_val, desc, cat, f"R$ {valor:,.2f}"])

        col_w_cus = [24 * mm, 60 * mm, 50 * mm, 28 * mm]
        tabela_cus = criar_tabela_pdf(linhas_cus, colunas_cus, col_widths=col_w_cus, styles=styles)
        elements.append(tabela_cus)

        total_cus = df_custos['valor'].sum()
        elements.append(Spacer(1, 2 * mm))
        elements.append(Paragraph(f"Total Custos: R$ {total_cus:,.2f}", styles['TotalLinha']))

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
                f"R$ {fat_v:,.2f}",
                f"R$ {cus_v:,.2f}",
                f"R$ {luc_v:,.2f}",
            ])
        col_w_men = [35 * mm, 42 * mm, 42 * mm, 42 * mm]
        tabela_men = criar_tabela_pdf(linhas_men, colunas_men, col_widths=col_w_men, styles=styles)
        elements.append(tabela_men)

    # Build
    doc.build(elements, onFirstPage=handler.on_page, onLaterPages=handler.on_page)
    buffer.seek(0)
    return buffer


def gerar_pdf_faturamento(dados_faturamento, metricas):
    """
    Gera PDF somente da tabela de faturamento.
    dados_faturamento: lista de dicts
    metricas: dict com total, registros, media
    """
    buffer = io.BytesIO()
    styles = _get_styles()

    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        topMargin=28 * mm, bottomMargin=18 * mm,
        leftMargin=12 * mm, rightMargin=12 * mm,
        title="Faturamento — JR ENTREGAS ME",
    )

    handler = _CabecalhoRodape("Tabela de Faturamento", "Detalhamento completo de faturamento")
    elements = []

    elements.append(Paragraph("📈 Faturamento", styles['TituloPrincipal']))
    elements.append(Spacer(1, 3 * mm))

    met_row = _criar_metricas_row([
        {"label": "Total Faturamento", "valor": f"R$ {metricas.get('total', 0):,.2f}", "cor": COR_VERDE},
        {"label": "Total Registros", "valor": str(metricas.get('registros', 0)), "cor": COR_AZUL},
        {"label": "Média por Nota", "valor": f"R$ {metricas.get('media', 0):,.2f}", "cor": COR_LARANJA},
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
            f"R$ {d.get('valor', 0):,.2f}",
        ])

    col_w = [12 * mm, 22 * mm, 50 * mm, 30 * mm, 22 * mm, 35 * mm, 22 * mm, 30 * mm, 25 * mm]
    tabela = criar_tabela_pdf(linhas, colunas, col_widths=col_w, styles=styles)
    elements.append(tabela)

    total = metricas.get('total', 0)
    elements.append(Spacer(1, 3 * mm))
    elements.append(Paragraph(f"Total: R$ {total:,.2f}", styles['TotalLinha']))

    doc.build(elements, onFirstPage=handler.on_page, onLaterPages=handler.on_page)
    buffer.seek(0)
    return buffer


def gerar_pdf_custos(dados_custos, metricas):
    """
    Gera PDF da tabela de custos.
    dados_custos: lista de dicts
    metricas: dict com total, registros
    """
    buffer = io.BytesIO()
    styles = _get_styles()

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=28 * mm, bottomMargin=18 * mm,
        leftMargin=12 * mm, rightMargin=12 * mm,
        title="Custos — JR ENTREGAS ME",
    )

    handler = _CabecalhoRodape("Relatório de Custos", "Detalhamento completo de custos")
    elements = []

    elements.append(Paragraph("📉 Custos", styles['TituloPrincipal']))
    elements.append(Spacer(1, 3 * mm))

    met_row = _criar_metricas_row([
        {"label": "Total Custos", "valor": f"R$ {metricas.get('total', 0):,.2f}", "cor": COR_VERMELHO},
        {"label": "Total Registros", "valor": str(metricas.get('registros', 0)), "cor": COR_AZUL},
    ], styles)
    elements.append(met_row)
    elements.append(Spacer(1, 5 * mm))
    elements.append(_separador())

    colunas = ['ID', 'Data', 'Descrição', 'Categoria', 'Valor (R$)']
    linhas = []
    for d in dados_custos:
        linhas.append([
            str(d.get('id', '')),
            str(d.get('data', '')),
            str(d.get('descricao', ''))[:45],
            str(d.get('categoria', ''))[:30],
            f"R$ {d.get('valor', 0):,.2f}",
        ])

    col_w = [14 * mm, 22 * mm, 60 * mm, 45 * mm, 28 * mm]
    tabela = criar_tabela_pdf(linhas, colunas, col_widths=col_w, styles=styles)
    elements.append(tabela)

    total = metricas.get('total', 0)
    elements.append(Spacer(1, 3 * mm))
    elements.append(Paragraph(f"Total: R$ {total:,.2f}", styles['TotalLinha']))

    doc.build(elements, onFirstPage=handler.on_page, onLaterPages=handler.on_page)
    buffer.seek(0)
    return buffer


def gerar_pdf_notas_fiscais(notas_dados, metricas, filtros_texto=""):
    """
    Gera PDF da lista de notas fiscais com seus itens.
    notas_dados: lista de dicts com keys:
        numero, data_nota, tipo, total_unidades, cep, bairro, municipio, itens (lista)
    metricas: dict com total, entradas, saidas
    """
    buffer = io.BytesIO()
    styles = _get_styles()

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=28 * mm, bottomMargin=18 * mm,
        leftMargin=12 * mm, rightMargin=12 * mm,
        title="Notas Fiscais — JR ENTREGAS ME",
    )

    handler = _CabecalhoRodape("Gestão de Notas Fiscais", "Notas processadas e detalhamento de itens")
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

    doc.build(elements, onFirstPage=handler.on_page, onLaterPages=handler.on_page)
    buffer.seek(0)
    return buffer


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
