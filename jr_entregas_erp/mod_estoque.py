import streamlit as st
import pandas as pd
import io
from styles import page_header, metric_card
from datetime import datetime as _dt
from database import (
    get_estoque, atualizar_estoque_inicial, get_produtos,
    atualizar_limites_estoque, atualizar_limites_estoque_lote,
    obter_produtos_estoque_baixo, produto_existe,
    atualizar_quantidade_estoque_lote
)
from auth import is_admin, pode_editar, pode_excluir, verificar_acesso, get_user_perfil

# Cores corporativas
COR_AZUL = "#0B132B"
COR_LARANJA = "#F29F05"
COR_VERDE = "#38A169"
COR_VERMELHO = "#E53E3E"
COR_AMARELO = "#D69E2E"


def _classificar_status(row):
    """Retorna ícone e texto de status baseado nos limites de estoque."""
    est_min = row.get('estoque_minimo', 0) or 0
    est_atual = row.get('estoque_atual', 0)
    status = row.get('status', 'sem_limite')
    
    if status == 'critico':
        return '🔴 CRÍTICO'
    elif status == 'atencao':
        return '🟡 ATENÇÃO'
    elif status == 'ok':
        return '🟢 OK'
    else:
        return '⚪ —'


def _estilo_linha(row):
    """Retorna estilos CSS por linha baseado no status do estoque."""
    status = row.get('status', 'sem_limite')
    if status == 'critico':
        return ['background-color: rgba(229, 62, 62, 0.15)'] * len(row)
    elif status == 'atencao':
        return ['background-color: rgba(214, 158, 46, 0.15)'] * len(row)
    elif status == 'ok':
        return ['background-color: rgba(56, 161, 105, 0.08)'] * len(row)
    return [''] * len(row)


def render():
    if not verificar_acesso('estoque'):
        return
    
    st.markdown(page_header("📦 Controle de Estoque", "Visualize e gerencie o estoque de produtos"), unsafe_allow_html=True)
    
    estoque = get_estoque()
    
    if not estoque:
        st.info("ℹ️ Nenhum produto cadastrado. Importe os produtos primeiro no módulo de Importação.")
        return
    
    df = pd.DataFrame(estoque)
    
    # CONVIDADOS: apenas Visão Geral (somente leitura)
    perfil = get_user_perfil()
    if perfil == 'CONVIDADOS':
        st.info("👁️ Modo somente visualização — seu perfil permite apenas consultar dados.")
        tab_visao, tab_relatorio = st.tabs(["📊 Visão Geral", "📈 Relatório"])
        with tab_visao:
            _render_visao_geral(df)
        with tab_relatorio:
            _render_relatorio(df)
        return
    
    # FUNCIONARIOS e ADM: todas as abas
    tab_visao, tab_limites, tab_lote, tab_relatorio = st.tabs([
        "📊 Visão Geral", "⚙️ Limites de Estoque", "📋 EDIÇÃO DE ESTOQUE", "📈 Relatório"
    ])
    
    with tab_visao:
        _render_visao_geral(df)
    
    with tab_limites:
        _render_limites_estoque(df)
    
    with tab_lote:
        _render_edicao_lote(df)
    
    with tab_relatorio:
        _render_relatorio(df)


def _render_visao_geral(df):
    """Aba principal com visualização de estoque e alertas visuais."""
    
    # Métricas resumo
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(metric_card("Total de Produtos", len(df), "metric-blue"), unsafe_allow_html=True)
    with col2:
        total_entradas = int(df['entradas'].sum())
        st.markdown(metric_card("Total Entradas", f"🟢 {total_entradas}", "metric-green"), unsafe_allow_html=True)
    with col3:
        total_saidas = int(df['saidas'].sum())
        st.markdown(metric_card("Total Saídas", f"🔴 {total_saidas}", "metric-red"), unsafe_allow_html=True)
    with col4:
        total_estoque = int(df['estoque_atual'].sum())
        st.markdown(metric_card("Estoque Total", total_estoque, "metric-orange"), unsafe_allow_html=True)
    
    # Cards de alertas
    criticos = len(df[df['status'] == 'critico'])
    atencao = len(df[df['status'] == 'atencao'])
    ok_count = len(df[df['status'] == 'ok'])
    
    if criticos > 0 or atencao > 0:
        st.markdown("<div style='height: 8px'></div>", unsafe_allow_html=True)
        col_a1, col_a2, col_a3 = st.columns(3)
        with col_a1:
            st.markdown(metric_card("🔴 Estoque Crítico", criticos, "metric-red"), unsafe_allow_html=True)
        with col_a2:
            st.markdown(metric_card("🟡 Atenção", atencao, "metric-orange"), unsafe_allow_html=True)
        with col_a3:
            st.markdown(metric_card("🟢 Estoque OK", ok_count, "metric-green"), unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Filtros
    col_f1, col_f2, col_f3, col_f4 = st.columns([2, 2, 1, 1])
    with col_f1:
        filtro_texto = st.text_input("🔍 Buscar por código ou descrição", key="filtro_estoque")
    with col_f2:
        ordenar_por = st.selectbox("📊 Ordenar por", 
                                    ["Código", "Descrição", "Estoque Atual (↑)", "Estoque Atual (↓)", "Status (Críticos primeiro)"],
                                    key="ordenar_estoque")
    with col_f3:
        mostrar_zerados = st.checkbox("Mostrar zerados", value=True, key="mostrar_zerados")
    with col_f4:
        filtro_status = st.selectbox("Status", ["Todos", "🔴 Crítico", "🟡 Atenção", "🟢 OK", "⚪ Sem limite"],
                                      key="filtro_status")
    
    # Aplicar filtros
    df_filtrado = df.copy()
    
    if filtro_texto:
        mask = (
            df_filtrado['codigo'].str.contains(filtro_texto, case=False, na=False) | 
            df_filtrado['descricao'].str.contains(filtro_texto, case=False, na=False)
        )
        df_filtrado = df_filtrado[mask]
    
    if not mostrar_zerados:
        df_filtrado = df_filtrado[df_filtrado['estoque_atual'] != 0]
    
    if filtro_status == "🔴 Crítico":
        df_filtrado = df_filtrado[df_filtrado['status'] == 'critico']
    elif filtro_status == "🟡 Atenção":
        df_filtrado = df_filtrado[df_filtrado['status'] == 'atencao']
    elif filtro_status == "🟢 OK":
        df_filtrado = df_filtrado[df_filtrado['status'] == 'ok']
    elif filtro_status == "⚪ Sem limite":
        df_filtrado = df_filtrado[df_filtrado['status'] == 'sem_limite']
    
    # Ordenação
    if ordenar_por == "Código":
        df_filtrado = df_filtrado.sort_values('codigo')
    elif ordenar_por == "Descrição":
        df_filtrado = df_filtrado.sort_values('descricao')
    elif ordenar_por == "Estoque Atual (↑)":
        df_filtrado = df_filtrado.sort_values('estoque_atual', ascending=True)
    elif ordenar_por == "Estoque Atual (↓)":
        df_filtrado = df_filtrado.sort_values('estoque_atual', ascending=False)
    elif ordenar_por == "Status (Críticos primeiro)":
        status_order = {'critico': 0, 'atencao': 1, 'ok': 2, 'sem_limite': 3}
        df_filtrado = df_filtrado.copy()
        df_filtrado['_status_order'] = df_filtrado['status'].map(status_order)
        df_filtrado = df_filtrado.sort_values(['_status_order', 'estoque_atual'], ascending=[True, True])
        df_filtrado = df_filtrado.drop(columns=['_status_order'])
    
    st.markdown(f"**{len(df_filtrado)} produtos encontrados**")
    
    # Adicionar coluna de status visual
    df_display = df_filtrado.copy()
    df_display['status_label'] = df_display.apply(_classificar_status, axis=1)
    
    # Preparar DataFrame para exibição
    df_show = df_display[['status_label', 'codigo', 'descricao', 'estoque_inicial', 'estoque_minimo', 'entradas', 'saidas', 'estoque_atual']].copy()
    df_show['estoque_minimo'] = df_show['estoque_minimo'].fillna(0).astype(int)
    
    df_show = df_show.rename(columns={
        'status_label': '⚡ Status',
        'codigo': 'Código',
        'descricao': 'Descrição',
        'estoque_inicial': 'Est. Inicial',
        'estoque_minimo': 'Est. Mínimo',
        'entradas': '🟢 Entradas',
        'saidas': '🔴 Saídas',
        'estoque_atual': '📦 Est. Atual'
    })
    
    # Aplicar estilos condicionais via styler
    styled = df_show.style.apply(
        lambda row: _estilo_linha_display(row, df_display),
        axis=1
    )
    
    st.dataframe(
        df_show,
        use_container_width=True,
        hide_index=True,
        column_config={
            '⚡ Status': st.column_config.TextColumn(width="small"),
            'Código': st.column_config.TextColumn(width="small"),
            'Descrição': st.column_config.TextColumn(width="large"),
            'Est. Inicial': st.column_config.NumberColumn(width="small"),
            'Est. Mínimo': st.column_config.NumberColumn(width="small"),
            '🟢 Entradas': st.column_config.NumberColumn(width="small"),
            '🔴 Saídas': st.column_config.NumberColumn(width="small"),
            '📦 Est. Atual': st.column_config.NumberColumn(width="small"),
        }
    )
    
    # Produtos em estado crítico - destaque
    produtos_criticos = df_filtrado[df_filtrado['status'] == 'critico']
    if not produtos_criticos.empty:
        st.markdown("#### ⚠️ Produtos em Estado Crítico")
        for _, prod in produtos_criticos.iterrows():
            est_min = prod['estoque_minimo'] or 0
            repor = est_min - prod['estoque_atual']
            st.markdown(
                f"""<div style='background: rgba(229,62,62,0.1); border-left: 4px solid {COR_VERMELHO}; 
                padding: 10px 15px; margin: 5px 0; border-radius: 4px;'>
                <strong>🔴 {prod['codigo']}</strong> - {prod['descricao']} | 
                Estoque: <strong>{int(prod['estoque_atual'])}</strong> | 
                Mínimo: <strong>{int(est_min)}</strong> | 
                <span style='color:{COR_VERMELHO}; font-weight:bold;'>Repor: {int(repor)} unidades</span>
                </div>""",
                unsafe_allow_html=True
            )
    
    # Editar estoque inicial (admin only)
    if is_admin():
        st.markdown("---")
        st.markdown("#### ✏️ Editar Estoque Inicial")
        st.caption("🔒 Apenas administradores podem editar o estoque inicial.")
        
        col_e1, col_e2, col_e3 = st.columns([3, 2, 1])
        
        produtos = get_produtos()
        codigos = [p['codigo'] for p in produtos]
        
        with col_e1:
            sel_codigo = st.selectbox(
                "Selecione o produto",
                codigos,
                format_func=lambda x: f"{x} - {next((p['descricao'] for p in produtos if p['codigo'] == x), '')}",
                key="sel_edit_estoque"
            )
        
        current_val = next((p['estoque_inicial'] for p in produtos if p['codigo'] == sel_codigo), 0)
        
        with col_e2:
            novo_valor = st.number_input("Novo estoque inicial", min_value=0, value=int(current_val), key="novo_estoque_ini")
        
        with col_e3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("💾 Salvar", type="primary", key="btn_salvar_estoque"):
                atualizar_estoque_inicial(sel_codigo, novo_valor)
                st.success(f"✅ Estoque inicial de {sel_codigo} atualizado para {novo_valor}.")
                st.rerun()
    else:
        st.info("ℹ️ A edição do estoque inicial está disponível apenas para administradores.")


def _estilo_linha_display(row, df_original):
    """Aplica estilo de fundo baseado no status (para uso com styler)."""
    idx = row.name
    if idx < len(df_original):
        status = df_original.iloc[idx].get('status', 'sem_limite') if idx < len(df_original) else 'sem_limite'
    else:
        status = 'sem_limite'
    
    if status == 'critico':
        return ['background-color: rgba(229, 62, 62, 0.15)'] * len(row)
    elif status == 'atencao':
        return ['background-color: rgba(214, 158, 46, 0.15)'] * len(row)
    elif status == 'ok':
        return ['background-color: rgba(56, 161, 105, 0.08)'] * len(row)
    return [''] * len(row)


def _render_limites_estoque(df):
    """Aba para definir limites de estoque mínimo e máximo por produto."""
    st.markdown("#### ⚙️ Definir Limites de Estoque")
    st.caption("Configure os limites mínimo e máximo para cada produto. Os alertas serão gerados automaticamente.")
    
    if not is_admin():
        st.warning("🔒 Apenas administradores podem editar os limites de estoque.")
        return
    
    produtos = get_produtos()
    if not produtos:
        st.info("Nenhum produto cadastrado.")
        return
    
    # Seletor de produto
    codigos = [p['codigo'] for p in produtos]
    sel_codigo = st.selectbox(
        "Selecione o produto",
        codigos,
        format_func=lambda x: f"{x} - {next((p['descricao'] for p in produtos if p['codigo'] == x), '')}",
        key="sel_limites_estoque"
    )
    
    produto_sel = next((p for p in produtos if p['codigo'] == sel_codigo), None)
    if not produto_sel:
        return
    
    # Buscar estoque atual do produto
    estoque_info = next((e for e in df.to_dict('records') if e['codigo'] == sel_codigo), {})
    est_atual = estoque_info.get('estoque_atual', 0)
    
    st.markdown(f"""
    <div style='background: linear-gradient(135deg, {COR_AZUL}, #1C2541); padding: 15px 20px; 
    border-radius: 8px; color: white; margin: 10px 0;'>
    <strong>{sel_codigo}</strong> - {produto_sel.get('descricao', '')} | 
    Estoque Atual: <span style='color: {COR_LARANJA}; font-weight: bold;'>{int(est_atual)}</span>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    current_min = produto_sel.get('estoque_minimo', 0) or 0
    current_max = produto_sel.get('estoque_maximo', None)
    
    with col1:
        novo_min = st.number_input(
            "Estoque Mínimo",
            min_value=0,
            value=int(current_min),
            help="Quantidade mínima desejada. Abaixo disso, será gerado alerta CRÍTICO.",
            key="input_est_min"
        )
    
    with col2:
        usar_maximo = st.checkbox("Definir estoque máximo", value=current_max is not None, key="chk_usar_max")
        if usar_maximo:
            novo_max = st.number_input(
                "Estoque Máximo",
                min_value=1,
                value=int(current_max) if current_max else max(int(novo_min * 2), 1),
                help="Quantidade máxima recomendada em estoque.",
                key="input_est_max"
            )
        else:
            novo_max = None
    
    # Validação
    erro_validacao = False
    if usar_maximo and novo_max is not None and novo_min >= novo_max:
        st.error("❌ O estoque mínimo deve ser menor que o estoque máximo.")
        erro_validacao = True
    
    # Preview do impacto
    if novo_min > 0:
        if est_atual < novo_min:
            st.warning(f"⚠️ Com este limite mínimo ({novo_min}), o produto ficará em estado **CRÍTICO** (estoque atual: {int(est_atual)}).")
        elif est_atual <= novo_min * 1.2:
            st.info(f"ℹ️ Com este limite mínimo ({novo_min}), o produto ficará em estado de **ATENÇÃO** (estoque atual: {int(est_atual)}).")
        else:
            st.success(f"✅ Estoque atual ({int(est_atual)}) está acima do mínimo ({novo_min}).")
    
    if st.button("💾 Salvar Limites", type="primary", key="btn_salvar_limites", disabled=erro_validacao):
        atualizar_limites_estoque(sel_codigo, novo_min, novo_max)
        st.success(f"✅ Limites de estoque de {sel_codigo} atualizados com sucesso!")
        st.rerun()


def _render_edicao_lote(df):
    """Aba para edição de estoque (quantidades)."""
    st.markdown("#### 📋 EDIÇÃO DE ESTOQUE")
    st.caption("Atualize as quantidades do estoque via upload de planilha ou edição direta na tabela.")
    
    if not is_admin():
        st.warning("🔒 Apenas administradores podem editar o estoque.")
        return
    
    opcao = st.radio(
        "Escolha o método de edição:",
        ["📤 Upload via Excel", "✏️ Edição em massa (tabela)"],
        horizontal=True,
        key="radio_lote"
    )
    
    if opcao == "📤 Upload via Excel":
        _render_upload_lote(df)
    else:
        _render_tabela_editavel(df)


def _normalizar_coluna(colunas, aliases):
    """Busca uma coluna pelo nome, tentando vários aliases (case-insensitive)."""
    for col in colunas:
        if col.strip().lower() in [a.lower() for a in aliases]:
            return col
    return None


def _render_upload_lote(df):
    """Upload de arquivo Excel para atualização de quantidades de estoque."""
    st.markdown("##### 📤 Upload via Excel")
    st.info(
        "💡 O arquivo deve conter as colunas: **CÓDIGO** (coluna 1), **DESCRIÇÃO** (coluna 2) e **QUANTIDADE** (coluna 3).\n\n"
        "Outras colunas serão **ignoradas** automaticamente.\n\n"
        "➕ Produtos com códigos **novos** serão **cadastrados automaticamente** no sistema."
    )
    
    # Botão para baixar modelo
    modelo = pd.DataFrame({
        'CODIGO': df['codigo'].head(5).tolist() if not df.empty else ['P000001'],
        'DESCRICAO': [next((r['descricao'] for _, r in df.iterrows() if r['codigo'] == c), '') 
                      for c in (df['codigo'].head(5).tolist() if not df.empty else ['P000001'])],
        'QUANTIDADE': [0] * min(5, max(len(df), 1)),
    })
    
    buffer_modelo = io.BytesIO()
    modelo.to_excel(buffer_modelo, index=False, engine='openpyxl')
    buffer_modelo.seek(0)
    
    st.download_button(
        "📥 Baixar Modelo Excel",
        data=buffer_modelo,
        file_name="modelo_edicao_estoque.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="btn_modelo_lote"
    )
    
    uploaded = st.file_uploader("Selecione o arquivo Excel (.xlsx, .xls)", type=["xlsx", "xls"], key="upload_lote_estoque")
    
    if uploaded:
        try:
            df_upload = pd.read_excel(uploaded)
            
            # Mapear colunas com aliases flexíveis
            col_codigo = _normalizar_coluna(df_upload.columns, ['codigo', 'código', 'cod', 'code', 'CODIGO', 'CÓDIGO', 'COD', 'CODE'])
            col_descricao = _normalizar_coluna(df_upload.columns, ['descricao', 'descrição', 'descricão', 'produto', 'nome', 'DESCRICAO', 'DESCRIÇÃO', 'PRODUTO', 'NOME'])
            col_quantidade = _normalizar_coluna(df_upload.columns, ['quantidade', 'qtd', 'estoque', 'qty', 'QUANTIDADE', 'QTD', 'ESTOQUE', 'QTY'])
            
            if not col_codigo:
                st.error("❌ Coluna de **CÓDIGO** não encontrada. Use uma das variações: codigo, código, cod, code.")
                return
            if not col_quantidade:
                st.error("❌ Coluna de **QUANTIDADE** não encontrada. Use uma das variações: quantidade, qtd, estoque, qty.")
                return
            
            # Extrair apenas as 3 colunas necessárias
            cols_usar = [col_codigo]
            if col_descricao:
                cols_usar.append(col_descricao)
            cols_usar.append(col_quantidade)
            
            df_proc = df_upload[cols_usar].copy()
            df_proc = df_proc.rename(columns={
                col_codigo: 'CODIGO',
                col_quantidade: 'QUANTIDADE'
            })
            if col_descricao:
                df_proc = df_proc.rename(columns={col_descricao: 'DESCRICAO'})
            else:
                df_proc['DESCRICAO'] = ''
            
            # Limpar dados
            df_proc['CODIGO'] = df_proc['CODIGO'].astype(str).str.strip()
            df_proc['QUANTIDADE'] = pd.to_numeric(df_proc['QUANTIDADE'], errors='coerce').fillna(0).astype(int)
            
            # Validações
            erros_val = []
            nao_encontrados = []
            codigos_vazios = []
            codigos_duplicados = []
            
            # Criar mapa de estoque atual para referência
            estoque_map = {r['codigo']: r['estoque_atual'] for _, r in df.iterrows()}
            descricao_map = {r['codigo']: r['descricao'] for _, r in df.iterrows()}
            
            # Verificar códigos duplicados no Excel
            codigos_excel = df_proc['CODIGO'].tolist()
            vistos = set()
            for cod in codigos_excel:
                if cod in vistos and cod not in codigos_duplicados:
                    codigos_duplicados.append(cod)
                vistos.add(cod)
            
            if codigos_duplicados:
                st.warning(f"⚠️ Códigos **duplicados** no Excel (será usada a última ocorrência): {', '.join(codigos_duplicados)}")
                df_proc = df_proc.drop_duplicates(subset='CODIGO', keep='last')
            
            for idx, row in df_proc.iterrows():
                cod = row['CODIGO']
                qtd = row['QUANTIDADE']
                desc = row['DESCRICAO']
                
                # Validar código vazio
                if not cod or cod.lower() == 'nan':
                    codigos_vazios.append(f"Linha {idx+1}")
                    continue
                
                if qtd < 0:
                    erros_val.append(f"Linha {idx+1} - {cod}: quantidade não pode ser negativa ({qtd})")
                
                if not produto_existe(cod):
                    # Validar que produtos novos tenham descrição
                    if not desc or str(desc).strip() == '' or str(desc).lower() == 'nan':
                        erros_val.append(f"Linha {idx+1} - {cod}: produto novo precisa de **DESCRIÇÃO** preenchida")
                    else:
                        nao_encontrados.append(cod)
            
            if codigos_vazios:
                st.warning(f"⚠️ {len(codigos_vazios)} linha(s) com código vazio serão ignoradas: {', '.join(codigos_vazios)}")
                df_proc = df_proc[df_proc['CODIGO'].str.strip().ne('') & df_proc['CODIGO'].str.lower().ne('nan')]
            
            if erros_val:
                st.error("❌ Erros de validação encontrados:")
                for e in erros_val:
                    st.markdown(f"  - {e}")
                return
            
            # Adicionar info de estoque atual ao preview
            df_proc['EST. ATUAL'] = df_proc['CODIGO'].map(estoque_map).fillna(0).astype(int)
            # Preencher descrição do banco se produto já existe e não veio no Excel
            for idx, row in df_proc.iterrows():
                cod = row['CODIGO']
                if cod not in nao_encontrados and (not row['DESCRICAO'] or str(row['DESCRICAO']).strip() == ''):
                    df_proc.at[idx, 'DESCRICAO'] = descricao_map.get(cod, '')
            
            # Marcar status de cada produto para o preview
            df_proc['STATUS'] = df_proc['CODIGO'].apply(lambda c: '➕ NOVO' if c in nao_encontrados else '✅ Existente')
            
            # Informar sobre produtos novos
            if nao_encontrados:
                st.info(f"➕ **{len(nao_encontrados)}** produto(s) novo(s) serão **cadastrados automaticamente**: {', '.join(nao_encontrados)}")
            
            existentes = df_proc[~df_proc['CODIGO'].isin(nao_encontrados)]
            novos = df_proc[df_proc['CODIGO'].isin(nao_encontrados)]
            
            if df_proc.empty:
                st.error("❌ Nenhum produto válido para processar.")
                return
            
            # Preview dos dados
            st.markdown("##### 📋 Preview dos dados importados")
            st.dataframe(
                df_proc[['STATUS', 'CODIGO', 'DESCRICAO', 'EST. ATUAL', 'QUANTIDADE']],
                use_container_width=True,
                hide_index=True,
                column_config={
                    'STATUS': st.column_config.TextColumn("Status", width="small"),
                    'CODIGO': st.column_config.TextColumn("Código", width="small"),
                    'DESCRICAO': st.column_config.TextColumn("Descrição", width="large"),
                    'EST. ATUAL': st.column_config.NumberColumn("Est. Atual", width="small"),
                    'QUANTIDADE': st.column_config.NumberColumn("Qtd. Excel", width="small"),
                }
            )
            
            # Resumo quantitativo
            col_res1, col_res2 = st.columns(2)
            with col_res1:
                st.markdown(f"✅ **{len(existentes)}** produto(s) existente(s) para atualizar")
            with col_res2:
                st.markdown(f"➕ **{len(novos)}** produto(s) novo(s) para cadastrar")
            
            # Salvar dados no session_state para uso nos botões
            st.session_state['_upload_estoque_data'] = df_proc.copy()
            st.session_state['_upload_estoque_novos'] = nao_encontrados.copy()
            
            # Diálogo de escolha
            st.markdown("---")
            st.markdown("##### ⚡ Escolha como aplicar os dados:")
            st.caption("💡 Produtos **novos** serão cadastrados com a quantidade do Excel independente do modo escolhido.")
            
            col_info1, col_info2 = st.columns(2)
            with col_info1:
                st.markdown(
                    f"""<div style='background: rgba(56,161,105,0.1); border-left: 4px solid {COR_VERDE}; 
                    padding: 12px 15px; border-radius: 4px;'>
                    <strong>🔢 SOMAR DADOS</strong><br>
                    <small>Adiciona a quantidade do Excel à quantidade <strong>atual</strong> no banco.<br>
                    Ex: Atual 10 + Excel 5 = <strong>15</strong></small>
                    </div>""",
                    unsafe_allow_html=True
                )
            with col_info2:
                st.markdown(
                    f"""<div style='background: rgba(66,153,225,0.1); border-left: 4px solid #4299E1; 
                    padding: 12px 15px; border-radius: 4px;'>
                    <strong>🔄 INSERIR NOVO</strong><br>
                    <small>Substitui a quantidade atual pela quantidade do Excel.<br>
                    Ex: Atual 10 → Excel 5 = <strong>5</strong></small>
                    </div>""",
                    unsafe_allow_html=True
                )
            
            st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
            
            col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
            
            with col_btn1:
                btn_somar = st.button("🔢 SOMAR DADOS", type="primary", key="btn_somar_estoque", use_container_width=True)
            with col_btn2:
                btn_inserir = st.button("🔄 INSERIR NOVO", type="secondary", key="btn_inserir_estoque", use_container_width=True)
            
            if btn_somar or btn_inserir:
                dados = st.session_state.get('_upload_estoque_data', df_proc)
                lista_novos = st.session_state.get('_upload_estoque_novos', nao_encontrados)
                modo = 'somar' if btn_somar else 'substituir'
                modo_label = 'SOMAR DADOS' if btn_somar else 'INSERIR NOVO'
                
                # Montar dicionário de descrições para cadastro de novos
                descricoes_map = {row['CODIGO']: row['DESCRICAO'] for _, row in dados.iterrows()}
                
                lista = [(row['CODIGO'], row['QUANTIDADE']) for _, row in dados.iterrows()]
                atualizados, novos_cadastrados, erros = atualizar_quantidade_estoque_lote(
                    lista, modo=modo, descricoes=descricoes_map, cadastrar_novos=True
                )
                
                # Gerar log de atualização
                log_data = []
                estoque_novo_map = {r['codigo']: r['estoque_atual'] for r in get_estoque()}
                for _, row in dados.iterrows():
                    cod = row['CODIGO']
                    if cod in [e for e in erros]:
                        log_data.append({
                            'Código': cod,
                            'Descrição': row['DESCRICAO'],
                            'Qtd. Anterior': '-',
                            'Qtd. Excel': int(row['QUANTIDADE']),
                            'Qtd. Nova': '-',
                            'Modo': modo_label,
                            'Status': '❌ Erro'
                        })
                    elif cod in novos_cadastrados:
                        log_data.append({
                            'Código': cod,
                            'Descrição': row['DESCRICAO'],
                            'Qtd. Anterior': 0,
                            'Qtd. Excel': int(row['QUANTIDADE']),
                            'Qtd. Nova': int(row['QUANTIDADE']),
                            'Modo': modo_label,
                            'Status': '➕ Novo'
                        })
                    else:
                        ant = row['EST. ATUAL']
                        if modo == 'somar':
                            novo = ant + row['QUANTIDADE']
                        else:
                            novo = row['QUANTIDADE']
                        log_data.append({
                            'Código': cod,
                            'Descrição': row['DESCRICAO'],
                            'Qtd. Anterior': int(ant),
                            'Qtd. Excel': int(row['QUANTIDADE']),
                            'Qtd. Nova': int(novo),
                            'Modo': modo_label,
                            'Status': '✅ Atualizado'
                        })
                
                # Exibir resultados separados
                if novos_cadastrados:
                    st.success(f"➕ **{len(novos_cadastrados)}** produto(s) novo(s) cadastrado(s) automaticamente!")
                
                if atualizados > 0:
                    st.success(f"✅ **{atualizados}** produto(s) existente(s) atualizado(s) com sucesso! (Modo: {modo_label})")
                
                if erros:
                    st.error(f"❌ **{len(erros)}** código(s) com erro: {', '.join(erros)}")
                
                if not novos_cadastrados and atualizados == 0:
                    st.warning("⚠️ Nenhum produto foi processado.")
                
                # Tabela de resumo
                if log_data:
                    st.markdown("##### 📊 Resumo da Atualização")
                    df_log = pd.DataFrame(log_data)
                    st.dataframe(df_log, use_container_width=True, hide_index=True)
                    
                    # Download do log
                    buffer_log = io.BytesIO()
                    df_log.to_excel(buffer_log, index=False, engine='openpyxl')
                    buffer_log.seek(0)
                    
                    st.download_button(
                        "📥 Baixar Log de Atualização",
                        data=buffer_log,
                        file_name=f"log_atualizacao_estoque_{_dt.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="btn_download_log"
                    )
                
                # Limpar dados do session_state
                for key in ['_upload_estoque_data', '_upload_estoque_novos']:
                    if key in st.session_state:
                        del st.session_state[key]
                
        except Exception as e:
            st.error(f"❌ Erro ao processar arquivo: {str(e)}")


def _render_tabela_editavel(df):
    """Tabela editável para atualização em massa de quantidades."""
    st.markdown("##### ✏️ Edição em massa (tabela)")
    st.caption("Altere os valores na coluna **EST. ATUALIZADO** com a quantidade real final desejada e clique em 'Salvar Alterações'.")
    
    # Preparar DataFrame editável
    df_edit = df[['codigo', 'descricao', 'estoque_atual']].copy()
    df_edit['estoque_atualizado'] = df_edit['estoque_atual'].astype(int)
    
    df_edit = df_edit.rename(columns={
        'codigo': 'Código',
        'descricao': 'Descrição',
        'estoque_atual': 'Est. Atual',
        'estoque_atualizado': 'EST. ATUALIZADO'
    })
    
    edited_df = st.data_editor(
        df_edit,
        use_container_width=True,
        hide_index=True,
        disabled=['Código', 'Descrição', 'Est. Atual'],
        column_config={
            'Código': st.column_config.TextColumn(width="small"),
            'Descrição': st.column_config.TextColumn(width="large"),
            'Est. Atual': st.column_config.NumberColumn(width="small"),
            'EST. ATUALIZADO': st.column_config.NumberColumn(width="small", min_value=0),
        },
        key="editor_lote_estoque"
    )
    
    if st.button("💾 Salvar Alterações", type="primary", key="btn_salvar_lote_tabela"):
        # Filtrar apenas produtos que foram alterados
        erros_val = []
        lista = []
        log_data = []
        
        for idx, row in edited_df.iterrows():
            cod = row['Código']
            est_atual = int(row['Est. Atual'])
            est_novo = int(row['EST. ATUALIZADO']) if pd.notna(row['EST. ATUALIZADO']) else est_atual
            
            if est_novo < 0:
                erros_val.append(f"{cod}: quantidade não pode ser negativa ({est_novo})")
                continue
            
            # Só atualizar se houve alteração
            if est_novo != est_atual:
                lista.append((cod, est_novo))
                log_data.append({
                    'Código': cod,
                    'Descrição': row['Descrição'],
                    'Qtd. Anterior': est_atual,
                    'Qtd. Nova': est_novo,
                    'Diferença': est_novo - est_atual
                })
        
        if erros_val:
            st.error("❌ Erros de validação:")
            for e in erros_val:
                st.markdown(f"  - {e}")
        elif not lista:
            st.info("ℹ️ Nenhuma alteração detectada. Modifique os valores na coluna **EST. ATUALIZADO** antes de salvar.")
        else:
            # Confirmar antes de salvar
            atualizados, _novos, erros = atualizar_quantidade_estoque_lote(lista, modo='substituir')
            
            if atualizados > 0:
                st.success(f"✅ **{atualizados}** produtos atualizados com sucesso!")
                
                # Resumo
                if log_data:
                    st.markdown("##### 📊 Resumo da Atualização")
                    df_log = pd.DataFrame(log_data)
                    st.dataframe(df_log, use_container_width=True, hide_index=True)
                    
                    # Download do log
                    buffer_log = io.BytesIO()
                    df_log.to_excel(buffer_log, index=False, engine='openpyxl')
                    buffer_log.seek(0)
                    
                    st.download_button(
                        "📥 Baixar Log de Atualização",
                        data=buffer_log,
                        file_name=f"log_edicao_estoque_{_dt.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="btn_download_log_tabela"
                    )
            
            if erros:
                st.warning(f"⚠️ {len(erros)} código(s) não encontrados: {', '.join(erros)}")
            
            st.rerun()


def _render_relatorio(df):
    """Aba de relatório de estoque com filtros, gráfico e exportação."""
    st.markdown("#### 📈 Relatório de Estoque")
    
    # Filtro por status
    filtro_rel = st.multiselect(
        "Filtrar por status",
        options=["🔴 Crítico", "🟡 Atenção", "🟢 OK", "⚪ Sem limite definido"],
        default=["🔴 Crítico", "🟡 Atenção", "🟢 OK", "⚪ Sem limite definido"],
        key="filtro_relatorio"
    )
    
    status_map = {
        "🔴 Crítico": "critico",
        "🟡 Atenção": "atencao",
        "🟢 OK": "ok",
        "⚪ Sem limite definido": "sem_limite"
    }
    
    status_selecionados = [status_map[s] for s in filtro_rel]
    df_rel = df[df['status'].isin(status_selecionados)].copy()
    
    if df_rel.empty:
        st.info("Nenhum produto encontrado com os filtros selecionados.")
        return
    
    # Métricas do relatório
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(metric_card("Total Filtrado", len(df_rel), "metric-blue"), unsafe_allow_html=True)
    with col2:
        n_critico = len(df_rel[df_rel['status'] == 'critico'])
        st.markdown(metric_card("🔴 Críticos", n_critico, "metric-red"), unsafe_allow_html=True)
    with col3:
        n_atencao = len(df_rel[df_rel['status'] == 'atencao'])
        st.markdown(metric_card("🟡 Atenção", n_atencao, "metric-orange"), unsafe_allow_html=True)
    with col4:
        n_ok = len(df_rel[df_rel['status'] == 'ok'])
        st.markdown(metric_card("🟢 OK", n_ok, "metric-green"), unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Gráfico de distribuição de status
    st.markdown("##### 📊 Distribuição de Status do Estoque")
    
    # Contar por status
    status_counts = df['status'].value_counts().reset_index()
    status_counts.columns = ['status', 'quantidade']
    
    status_labels = {
        'critico': '🔴 Crítico',
        'atencao': '🟡 Atenção',
        'ok': '🟢 OK',
        'sem_limite': '⚪ Sem limite'
    }
    status_colors = {
        '🔴 Crítico': COR_VERMELHO,
        '🟡 Atenção': COR_AMARELO,
        '🟢 OK': COR_VERDE,
        '⚪ Sem limite': '#A0AEC0'
    }
    
    status_counts['label'] = status_counts['status'].map(status_labels)
    
    try:
        import plotly.express as px
        
        fig = px.pie(
            status_counts, values='quantidade', names='label',
            color='label',
            color_discrete_map=status_colors,
            hole=0.4,
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, sans-serif", color=COR_AZUL),
            margin=dict(l=20, r=20, t=40, b=20),
            height=350,
        )
        fig.update_traces(
            textinfo='percent+value',
            textfont_size=12,
            marker=dict(line=dict(color='#FFFFFF', width=2))
        )
        st.plotly_chart(fig, use_container_width=True)
    except ImportError:
        st.info("Instale o plotly para ver o gráfico: pip install plotly")
    
    st.markdown("---")
    
    # Tabela do relatório
    st.markdown("##### 📋 Detalhamento")
    
    df_rel_display = df_rel.copy()
    df_rel_display['status_label'] = df_rel_display.apply(_classificar_status, axis=1)
    df_rel_display['repor'] = df_rel_display.apply(
        lambda r: max(0, (r['estoque_minimo'] or 0) - r['estoque_atual']) if (r['estoque_minimo'] or 0) > 0 else 0,
        axis=1
    )
    
    df_export = df_rel_display[['status_label', 'codigo', 'descricao', 'estoque_atual', 'estoque_minimo', 'estoque_maximo', 'entradas', 'saidas', 'repor']].copy()
    df_export['estoque_minimo'] = df_export['estoque_minimo'].fillna(0).astype(int)
    
    df_export = df_export.rename(columns={
        'status_label': 'Status',
        'codigo': 'Código',
        'descricao': 'Descrição',
        'estoque_atual': 'Est. Atual',
        'estoque_minimo': 'Est. Mínimo',
        'estoque_maximo': 'Est. Máximo',
        'entradas': 'Entradas',
        'saidas': 'Saídas',
        'repor': 'Qtd. Repor'
    })
    
    st.dataframe(df_export, use_container_width=True, hide_index=True)
    
    # Exportar
    st.markdown("##### 📥 Exportar Relatório")
    
    col_exp1, col_exp2 = st.columns(2)
    
    with col_exp1:
        buffer = io.BytesIO()
        df_export.to_excel(buffer, index=False, engine='openpyxl', sheet_name='Relatório Estoque')
        buffer.seek(0)
        
        st.download_button(
            "📥 Baixar Relatório em Excel",
            data=buffer,
            file_name="relatorio_estoque.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            key="btn_export_relatorio"
        )
    
    with col_exp2:
        from utils_pdf import gerar_pdf_relatorio_estoque
        from datetime import datetime as _dt
        
        # Preparar dados para PDF
        dados_pdf = []
        for _, row in df_export.iterrows():
            dados_pdf.append({
                'status': row.get('Status', ''),
                'codigo': row.get('Código', ''),
                'descricao': row.get('Descrição', ''),
                'estoque_atual': row.get('Est. Atual', 0),
                'estoque_minimo': row.get('Est. Mínimo', 0),
                'estoque_maximo': row.get('Est. Máximo', 0),
                'entradas': row.get('Entradas', 0),
                'saidas': row.get('Saídas', 0),
                'repor': row.get('Qtd. Repor', 0),
            })
        
        metricas_pdf = {
            'total': len(df_rel),
            'critico': n_critico,
            'atencao': n_atencao,
            'ok': n_ok,
        }
        
        filtros_str = ", ".join(filtro_rel) if filtro_rel else "Todos"
        
        pdf_buffer = gerar_pdf_relatorio_estoque(dados_pdf, metricas_pdf, filtros_aplicados=filtros_str)
        
        nome_arquivo = f"relatorio_estoque_{_dt.now().strftime('%Y%m%d_%H%M')}.pdf"
        st.download_button(
            "📄 Baixar Relatório em PDF",
            data=pdf_buffer,
            file_name=nome_arquivo,
            mime="application/pdf",
            key="btn_export_relatorio_pdf"
        )
