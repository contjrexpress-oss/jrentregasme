import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

from styles import page_header, metric_card
from database import (get_notas, get_produtos, get_faturamento, get_custos, get_estoque,
                      obter_produtos_estoque_baixo, obter_contas_proximas_vencimento,
                      atualizar_status_contas_atrasadas, get_todos_custos_faturamento)
from config import Cores
from utils import formatar_moeda_br

# Aliases para manter compatibilidade
COR_AZUL = Cores.AZUL
COR_AZUL_CLARO = Cores.AZUL_CLARO
COR_LARANJA = Cores.LARANJA
COR_LARANJA_ESCURO = Cores.LARANJA_ESCURO
COR_VERDE = Cores.VERDE
COR_VERMELHO = Cores.VERMELHO
COR_AZUL_MEDIO = Cores.AZUL_MEDIO
COR_CINZA = Cores.CINZA

CORES_REGIOES = Cores.REGIOES
CORES_CUSTOS = Cores.CUSTOS


def _get_mes_atual_label():
    """Retorna o label do mês atual em português."""
    meses = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
        5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
        9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
    }
    hoje = datetime.now()
    return f"{meses[hoje.month]} {hoje.year}"


def _parse_data(data_str):
    """Tenta parsear uma data string em múltiplos formatos."""
    if pd.isna(data_str) or data_str is None:
        return None
    data_str = str(data_str).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(data_str, fmt)
        except ValueError:
            continue
    return None


def _carregar_dados():
    """Carrega todos os dados necessários para o dashboard."""
    notas = get_notas()
    produtos = get_produtos()
    faturamento = get_faturamento()
    custos_diretos = get_custos()
    custos_fat = get_todos_custos_faturamento()
    # Unificar custos diretos + custos associados a faturamento
    custos = list(custos_diretos)
    for cf in custos_fat:
        custos.append({
            'id': f"CF-{cf['id']}",
            'data': cf.get('data') or cf.get('fat_data', ''),
            'descricao': cf['descricao'],
            'categoria': cf.get('categoria', ''),
            'valor': cf['valor'],
            'origem': 'Faturamento',
        })
    estoque = get_estoque()

    hoje = datetime.now()
    mes_atual = hoje.month
    ano_atual = hoje.year

    # DataFrames
    df_notas = pd.DataFrame([dict(n) for n in notas]) if notas else pd.DataFrame()
    df_fat = pd.DataFrame([dict(f) for f in faturamento]) if faturamento else pd.DataFrame()
    df_custos = pd.DataFrame([dict(c) for c in custos]) if custos else pd.DataFrame()
    df_estoque = pd.DataFrame([dict(e) for e in estoque]) if estoque else pd.DataFrame()

    # Parse datas do faturamento
    if not df_fat.empty and 'data' in df_fat.columns:
        df_fat['data_parsed'] = df_fat['data'].apply(_parse_data)
    else:
        df_fat['data_parsed'] = pd.Series(dtype='datetime64[ns]')

    # Parse datas dos custos
    if not df_custos.empty and 'data' in df_custos.columns:
        df_custos['data_parsed'] = df_custos['data'].apply(_parse_data)
    else:
        df_custos['data_parsed'] = pd.Series(dtype='datetime64[ns]')

    # Parse datas das notas
    if not df_notas.empty and 'data_nota' in df_notas.columns:
        df_notas['data_parsed'] = df_notas['data_nota'].apply(_parse_data)
    else:
        df_notas['data_parsed'] = pd.Series(dtype='datetime64[ns]')

    # Filtros do mês atual
    fat_mes = df_fat[df_fat['data_parsed'].apply(
        lambda d: d is not None and d.month == mes_atual and d.year == ano_atual
    )] if not df_fat.empty else pd.DataFrame()

    custos_mes = df_custos[df_custos['data_parsed'].apply(
        lambda d: d is not None and d.month == mes_atual and d.year == ano_atual
    )] if not df_custos.empty else pd.DataFrame()

    return {
        'df_notas': df_notas,
        'df_fat': df_fat,
        'df_custos': df_custos,
        'df_estoque': df_estoque,
        'fat_mes': fat_mes,
        'custos_mes': custos_mes,
        'total_produtos': len(produtos),
        'mes_label': _get_mes_atual_label(),
    }


def _render_metricas(dados):
    """Renderiza os cards de métricas principais."""
    df_notas = dados['df_notas']
    fat_mes = dados['fat_mes']
    custos_mes = dados['custos_mes']

    # Contagens de notas
    total_notas = len(df_notas)
    notas_entrada = len(df_notas[df_notas['tipo'] == 'entrada']) if not df_notas.empty and 'tipo' in df_notas.columns else 0
    notas_saida = len(df_notas[df_notas['tipo'] == 'saida']) if not df_notas.empty and 'tipo' in df_notas.columns else 0

    # Produtos em estoque
    total_produtos = dados['total_produtos']
    df_estoque = dados['df_estoque']
    total_estoque = int(df_estoque['estoque_atual'].sum()) if not df_estoque.empty and 'estoque_atual' in df_estoque.columns else 0

    # Financeiro do mês
    faturamento_mes = float(fat_mes['valor'].sum()) if not fat_mes.empty and 'valor' in fat_mes.columns else 0.0
    custos_total_mes = float(custos_mes['valor'].sum()) if not custos_mes.empty and 'valor' in custos_mes.columns else 0.0
    lucro_mes = faturamento_mes - custos_total_mes

    st.markdown(f"#### 📅 Resumo de {dados['mes_label']}")

    # Linha 1 - Notas
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(metric_card("Total de Notas", f"{total_notas}", "metric-blue"), unsafe_allow_html=True)
    with col2:
        st.markdown(metric_card("Notas de Entrada", f"📥 {notas_entrada}", "metric-green"), unsafe_allow_html=True)
    with col3:
        st.markdown(metric_card("Notas de Saída", f"📤 {notas_saida}", "metric-orange"), unsafe_allow_html=True)
    with col4:
        st.markdown(metric_card("Produtos Cadastrados", f"📦 {total_produtos}", "metric-blue"), unsafe_allow_html=True)

    st.markdown("<div style='height: 12px'></div>", unsafe_allow_html=True)

    # Linha 2 - Financeiro
    col5, col6, col7, col8 = st.columns(4)
    with col5:
        st.markdown(metric_card("Itens em Estoque", f"🏭 {total_estoque:,}".replace(",", "."), "metric-blue"), unsafe_allow_html=True)
    with col6:
        st.markdown(metric_card(
            f"Faturamento ({dados['mes_label'][:3]})",
            formatar_moeda_br(faturamento_mes),
            "metric-green"
        ), unsafe_allow_html=True)
    with col7:
        st.markdown(metric_card(
            f"Custos ({dados['mes_label'][:3]})",
            formatar_moeda_br(custos_total_mes),
            "metric-red"
        ), unsafe_allow_html=True)
    with col8:
        lucro_class = "metric-green" if lucro_mes >= 0 else "metric-red"
        st.markdown(metric_card(
            f"Lucro Líquido ({dados['mes_label'][:3]})",
            formatar_moeda_br(lucro_mes),
            lucro_class
        ), unsafe_allow_html=True)


def _render_graficos(dados):
    """Renderiza os gráficos do dashboard."""
    df_fat = dados['df_fat']
    df_custos = dados['df_custos']

    plotly_layout = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=COR_AZUL),
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor=COR_LARANJA,
            borderwidth=1
        ),
    )

    col_left, col_right = st.columns(2)

    # ===== GRÁFICO 1: Faturamento por Região =====
    with col_left:
        st.markdown("##### 📊 Faturamento por Região")
        if not df_fat.empty and 'regiao' in df_fat.columns and 'valor' in df_fat.columns:
            fat_regiao = df_fat.groupby('regiao')['valor'].sum().reset_index()
            fat_regiao = fat_regiao.sort_values('regiao')

            fig_bar = px.bar(
                fat_regiao, x='regiao', y='valor',
                labels={'regiao': 'Região', 'valor': 'Valor (R$)'},
                color='regiao',
                color_discrete_sequence=CORES_REGIOES,
            )
            fig_bar.update_layout(**plotly_layout, showlegend=False, height=350)
            fig_bar.update_traces(
                texttemplate='R$ %{y:,.2f}', textposition='outside',
                marker_line_color=COR_AZUL, marker_line_width=1
            )
            fig_bar.update_yaxes(gridcolor="rgba(0,0,0,0.05)")
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("📭 Sem dados de faturamento para exibir.")

    # ===== GRÁFICO 2: Distribuição de Custos =====
    with col_right:
        st.markdown("##### 🥧 Distribuição de Custos por Tipo")
        if not df_custos.empty and 'categoria' in df_custos.columns and 'valor' in df_custos.columns:
            custos_cat = df_custos.groupby('categoria')['valor'].sum().reset_index()
            custos_cat = custos_cat.sort_values('valor', ascending=False)

            fig_pie = px.pie(
                custos_cat, values='valor', names='categoria',
                color_discrete_sequence=CORES_CUSTOS,
                hole=0.4,
            )
            fig_pie.update_layout(**plotly_layout, height=350)
            fig_pie.update_traces(
                textinfo='percent+label',
                textfont_size=12,
                marker=dict(line=dict(color='#FFFFFF', width=2))
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("📭 Sem dados de custos para exibir.")

    st.markdown("<div style='height: 16px'></div>", unsafe_allow_html=True)

    # ===== GRÁFICO 3: Evolução do Faturamento (6 meses) =====
    st.markdown("##### 📈 Evolução do Faturamento - Últimos 6 Meses")
    if not df_fat.empty and 'data_parsed' in df_fat.columns and 'valor' in df_fat.columns:
        df_fat_valid = df_fat[df_fat['data_parsed'].notna()].copy()
        if not df_fat_valid.empty:
            df_fat_valid['mes_ano'] = df_fat_valid['data_parsed'].apply(
                lambda d: d.strftime('%Y-%m') if d else None
            )
            df_fat_valid = df_fat_valid[df_fat_valid['mes_ano'].notna()]

            # Gerar os últimos 6 meses
            hoje = datetime.now()
            meses_labels = {}
            meses_nomes = {
                1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
                7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"
            }
            for i in range(5, -1, -1):
                d = hoje - timedelta(days=30 * i)
                key = d.strftime('%Y-%m')
                meses_labels[key] = f"{meses_nomes[d.month]}/{d.strftime('%y')}"

            fat_mensal = df_fat_valid.groupby('mes_ano')['valor'].sum().reset_index()
            
            # Preencher meses sem dados
            all_meses = pd.DataFrame({'mes_ano': list(meses_labels.keys())})
            fat_mensal = all_meses.merge(fat_mensal, on='mes_ano', how='left').fillna(0)
            fat_mensal['mes_label'] = fat_mensal['mes_ano'].map(meses_labels)
            fat_mensal = fat_mensal[fat_mensal['mes_ano'].isin(meses_labels.keys())]
            fat_mensal = fat_mensal.sort_values('mes_ano')

            fig_line = go.Figure()
            fig_line.add_trace(go.Scatter(
                x=fat_mensal['mes_label'],
                y=fat_mensal['valor'],
                mode='lines+markers+text',
                line=dict(color=COR_LARANJA, width=3),
                marker=dict(size=10, color=COR_LARANJA, line=dict(color=COR_AZUL, width=2)),
                text=[f"R$ {v:,.0f}".replace(",", ".") for v in fat_mensal['valor']],
                textposition="top center",
                textfont=dict(size=11, color=COR_AZUL),
                fill='tozeroy',
                fillcolor='rgba(242, 159, 5, 0.1)',
                name='Faturamento',
            ))
            fig_line.update_layout(
                **plotly_layout,
                height=350,
                xaxis=dict(showgrid=False),
                yaxis=dict(gridcolor="rgba(0,0,0,0.05)", title="Valor (R$)"),
                showlegend=False,
            )
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("📭 Sem dados de faturamento com datas válidas.")
    else:
        st.info("📭 Sem dados de faturamento para exibir evolução.")


def _render_tabela_recente(dados):
    """Renderiza uma tabela com as últimas notas importadas."""
    df_notas = dados['df_notas']
    if df_notas.empty:
        return

    st.markdown("##### 📋 Últimas Notas Importadas")
    
    df_recente = df_notas.copy()
    if 'data_parsed' in df_recente.columns:
        df_recente = df_recente.sort_values('data_parsed', ascending=False)
    
    df_recente = df_recente.head(10)

    colunas_exibir = []
    rename_map = {}
    for col, label in [('numero', 'Nº Nota'), ('data_nota', 'Data'), ('tipo', 'Tipo'),
                        ('total_unidades', 'Unidades'), ('bairro', 'Bairro'),
                        ('municipio', 'Município'), ('cep', 'CEP')]:
        if col in df_recente.columns:
            colunas_exibir.append(col)
            rename_map[col] = label

    if colunas_exibir:
        df_show = df_recente[colunas_exibir].rename(columns=rename_map)
        if 'Tipo' in df_show.columns:
            df_show['Tipo'] = df_show['Tipo'].map({'entrada': '📥 Entrada', 'saida': '📤 Saída'}).fillna(df_show['Tipo'])
        st.dataframe(df_show, use_container_width=True, hide_index=True)


def _render_alertas_estoque():
    """Renderiza alertas de produtos com estoque abaixo do mínimo."""
    produtos_baixo = obter_produtos_estoque_baixo()
    
    if not produtos_baixo:
        return
    
    st.markdown(f"""
    <div style='background: linear-gradient(135deg, rgba(242,159,5,0.1), rgba(242,159,5,0.05)); 
    border-left: 4px solid {COR_LARANJA}; padding: 15px 20px; border-radius: 8px; margin-bottom: 16px;'>
    <h5 style='color: {COR_LARANJA}; margin: 0 0 10px 0;'>⚠️ Alertas de Estoque Baixo — {len(produtos_baixo)} produto(s)</h5>
    </div>
    """, unsafe_allow_html=True)
    
    for prod in produtos_baixo[:10]:  # Limitar a 10 alertas
        est_min = prod.get('estoque_minimo', 0) or 0
        est_atual = prod.get('estoque_atual', 0)
        repor = prod.get('repor', 0)
        pct = (est_atual / est_min * 100) if est_min > 0 else 0
        
        cor_barra = COR_VERMELHO if pct < 50 else COR_LARANJA
        
        st.markdown(f"""
        <div style='background: white; border: 1px solid rgba(242,159,5,0.3); border-radius: 8px; 
        padding: 12px 16px; margin: 6px 0; display: flex; align-items: center; justify-content: space-between;'>
            <div>
                <strong style='color: {COR_AZUL};'>🔴 {prod['codigo']}</strong> 
                <span style='color: #718096;'>— {prod['descricao']}</span>
            </div>
            <div style='text-align: right;'>
                <span style='color: {COR_VERMELHO}; font-weight: bold;'>Estoque: {int(est_atual)}</span> / 
                <span style='color: {COR_AZUL};'>Mín: {int(est_min)}</span> | 
                <span style='background: {COR_LARANJA}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.85em;'>
                    Repor: {int(repor)} un.
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    if len(produtos_baixo) > 10:
        st.caption(f"... e mais {len(produtos_baixo) - 10} produto(s). Veja detalhes no módulo de Estoque.")


def _render_alertas_contas():
    """Renderiza alertas de contas próximas do vencimento ou atrasadas."""
    atualizar_status_contas_atrasadas()
    contas = obter_contas_proximas_vencimento(dias=7)
    
    if not contas:
        return
    
    # Separar por urgência
    atrasadas = [c for c in contas if c['urgencia'] == 'atrasado']
    urgentes = [c for c in contas if c['urgencia'] == 'urgente']
    proximas = [c for c in contas if c['urgencia'] == 'proximo']
    
    total_pagar = sum(c['valor'] for c in contas if c['tipo'] == 'pagar')
    total_receber = sum(c['valor'] for c in contas if c['tipo'] == 'receber')
    
    st.markdown(f"""
    <div style='background: linear-gradient(135deg, rgba(229,62,62,0.08), rgba(242,159,5,0.05)); 
    border-left: 4px solid {COR_VERMELHO if atrasadas else COR_LARANJA}; padding: 15px 20px; border-radius: 8px; margin-bottom: 16px;'>
    <h5 style='color: {COR_VERMELHO if atrasadas else COR_LARANJA}; margin: 0 0 10px 0;'>
        💳 Contas a Vencer — {len(contas)} conta(s)
    </h5>
    <div style='display: flex; gap: 20px; flex-wrap: wrap;'>
        <span style='color: {COR_VERMELHO}; font-weight: 600;'>A Pagar: {formatar_moeda_br(total_pagar)}</span>
        <span style='color: {COR_VERDE}; font-weight: 600;'>A Receber: {formatar_moeda_br(total_receber)}</span>
    </div>
    </div>
    """, unsafe_allow_html=True)
    
    for conta in contas[:10]:
        tipo_icon = "💸" if conta['tipo'] == 'pagar' else "💰"
        
        if conta['urgencia'] == 'atrasado':
            cor_borda = COR_VERMELHO
            badge_text = f"ATRASADO ({abs(conta['dias_restantes'])} dias)"
            badge_bg = COR_VERMELHO
        elif conta['urgencia'] == 'urgente':
            cor_borda = "#DD6B20"
            dias = conta['dias_restantes']
            badge_text = f"Vence {'hoje' if dias == 0 else f'em {dias} dia(s)'}"
            badge_bg = "#DD6B20"
        else:
            cor_borda = COR_LARANJA
            badge_text = f"Vence em {conta['dias_restantes']} dia(s)"
            badge_bg = COR_LARANJA
        
        try:
            venc_str = datetime.strptime(conta['data_vencimento'], "%Y-%m-%d").strftime("%d/%m/%Y")
        except:
            venc_str = conta['data_vencimento']
        
        st.markdown(f"""
        <div style='background: white; border: 1px solid {cor_borda}40; border-left: 3px solid {cor_borda}; border-radius: 8px; 
        padding: 10px 16px; margin: 5px 0; display: flex; align-items: center; justify-content: space-between;'>
            <div>
                <strong style='color: {COR_AZUL};'>{tipo_icon} {conta['descricao']}</strong>
                <span style='color: #718096; font-size: 0.85em;'> — Venc: {venc_str}</span>
            </div>
            <div style='text-align: right; display: flex; align-items: center; gap: 10px;'>
                <span style='color: {COR_AZUL}; font-weight: bold;'>{formatar_moeda_br(conta['valor'])}</span>
                <span style='background: {badge_bg}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; font-weight: 600;'>
                    {badge_text}
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    if len(contas) > 10:
        st.caption(f"... e mais {len(contas) - 10} conta(s). Veja detalhes no módulo Financeiro > Contas.")


def render():
    """Renderiza o dashboard principal."""
    st.markdown(
        page_header("🏠 Dashboard", "Visão geral do sistema JR ENTREGAS ME"),
        unsafe_allow_html=True
    )

    dados = _carregar_dados()

    # Métricas principais
    _render_metricas(dados)

    st.markdown("<div style='height: 24px'></div>", unsafe_allow_html=True)
    st.markdown("---")

    # Gráficos
    _render_graficos(dados)

    st.markdown("---")

    # Alertas de contas a vencer
    _render_alertas_contas()

    # Alertas de estoque baixo
    _render_alertas_estoque()

    st.markdown("---")

    # Tabela de notas recentes
    _render_tabela_recente(dados)
