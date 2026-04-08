import streamlit as st
import pandas as pd
import io
from styles import page_header, metric_card
from database import (
    get_estoque, atualizar_estoque_inicial, get_produtos,
    atualizar_limites_estoque, atualizar_limites_estoque_lote,
    obter_produtos_estoque_baixo
)
from auth import is_admin

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
    st.markdown(page_header("📦 Controle de Estoque", "Visualize e gerencie o estoque de produtos"), unsafe_allow_html=True)
    
    estoque = get_estoque()
    
    if not estoque:
        st.info("ℹ️ Nenhum produto cadastrado. Importe os produtos primeiro no módulo de Importação.")
        return
    
    df = pd.DataFrame(estoque)
    
    # Tabs principais
    tab_visao, tab_limites, tab_lote, tab_relatorio = st.tabs([
        "📊 Visão Geral", "⚙️ Limites de Estoque", "📋 Edição em Lote", "📈 Relatório"
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
    """Aba para edição em lote dos limites de estoque."""
    st.markdown("#### 📋 Edição em Lote de Limites de Estoque")
    
    if not is_admin():
        st.warning("🔒 Apenas administradores podem editar os limites de estoque.")
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


def _render_upload_lote(df):
    """Upload de arquivo Excel para atualização em lote."""
    st.markdown("##### 📤 Upload de Arquivo Excel")
    st.info("💡 O arquivo deve conter as colunas: **codigo**, **estoque_minimo**, **estoque_maximo** (opcional).")
    
    # Botão para baixar modelo
    modelo = pd.DataFrame({
        'codigo': df['codigo'].head(5).tolist() if not df.empty else ['P000001'],
        'estoque_minimo': [10] * min(5, len(df)),
        'estoque_maximo': [100] * min(5, len(df)),
    })
    
    buffer_modelo = io.BytesIO()
    modelo.to_excel(buffer_modelo, index=False, engine='openpyxl')
    buffer_modelo.seek(0)
    
    st.download_button(
        "📥 Baixar Modelo Excel",
        data=buffer_modelo,
        file_name="modelo_limites_estoque.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="btn_modelo_lote"
    )
    
    uploaded = st.file_uploader("Selecione o arquivo Excel", type=["xlsx", "xls"], key="upload_lote_estoque")
    
    if uploaded:
        try:
            df_upload = pd.read_excel(uploaded)
            
            # Validar colunas
            if 'codigo' not in df_upload.columns or 'estoque_minimo' not in df_upload.columns:
                st.error("❌ O arquivo deve conter pelo menos as colunas 'codigo' e 'estoque_minimo'.")
                return
            
            # Preparar dados
            df_upload['codigo'] = df_upload['codigo'].astype(str).str.strip()
            df_upload['estoque_minimo'] = pd.to_numeric(df_upload['estoque_minimo'], errors='coerce').fillna(0).astype(int)
            
            if 'estoque_maximo' in df_upload.columns:
                df_upload['estoque_maximo'] = pd.to_numeric(df_upload['estoque_maximo'], errors='coerce')
            else:
                df_upload['estoque_maximo'] = None
            
            # Validar dados
            erros_val = []
            for _, row in df_upload.iterrows():
                cod = row['codigo']
                est_min = row['estoque_minimo']
                est_max = row.get('estoque_maximo', None)
                
                if est_min < 0:
                    erros_val.append(f"{cod}: estoque mínimo não pode ser negativo")
                if pd.notna(est_max) and est_max is not None and est_min >= est_max:
                    erros_val.append(f"{cod}: estoque mínimo ({est_min}) deve ser menor que máximo ({int(est_max)})")
            
            if erros_val:
                st.error("❌ Erros de validação encontrados:")
                for e in erros_val:
                    st.markdown(f"  - {e}")
                return
            
            # Preview
            st.markdown("##### 📋 Resumo das Alterações")
            st.dataframe(df_upload, use_container_width=True, hide_index=True)
            st.markdown(f"**{len(df_upload)} produtos** serão atualizados.")
            
            if st.button("✅ Confirmar Atualização em Lote", type="primary", key="btn_confirmar_lote"):
                lista = []
                for _, row in df_upload.iterrows():
                    est_max = row.get('estoque_maximo', None)
                    est_max_val = int(est_max) if pd.notna(est_max) else None
                    lista.append((row['codigo'], int(row['estoque_minimo']), est_max_val))
                
                atualizados, erros = atualizar_limites_estoque_lote(lista)
                
                if atualizados > 0:
                    st.success(f"✅ {atualizados} produtos atualizados com sucesso!")
                if erros:
                    st.warning(f"⚠️ {len(erros)} códigos não encontrados: {', '.join(erros)}")
                st.rerun()
                
        except Exception as e:
            st.error(f"❌ Erro ao processar arquivo: {str(e)}")


def _render_tabela_editavel(df):
    """Tabela editável para atualização em massa."""
    st.markdown("##### ✏️ Edição em Massa")
    st.caption("Edite os valores diretamente na tabela abaixo e clique em 'Salvar Alterações'.")
    
    # Preparar DataFrame editável
    df_edit = df[['codigo', 'descricao', 'estoque_atual', 'estoque_minimo', 'estoque_maximo']].copy()
    df_edit['estoque_minimo'] = df_edit['estoque_minimo'].fillna(0).astype(int)
    df_edit['estoque_maximo'] = df_edit['estoque_maximo'].apply(lambda x: int(x) if pd.notna(x) and x is not None else None)
    
    df_edit = df_edit.rename(columns={
        'codigo': 'Código',
        'descricao': 'Descrição',
        'estoque_atual': 'Est. Atual',
        'estoque_minimo': 'Est. Mínimo',
        'estoque_maximo': 'Est. Máximo'
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
            'Est. Mínimo': st.column_config.NumberColumn(width="small", min_value=0),
            'Est. Máximo': st.column_config.NumberColumn(width="small", min_value=0),
        },
        key="editor_lote_estoque"
    )
    
    if st.button("💾 Salvar Alterações", type="primary", key="btn_salvar_lote_tabela"):
        # Validar e salvar
        erros_val = []
        lista = []
        
        for _, row in edited_df.iterrows():
            cod = row['Código']
            est_min = int(row['Est. Mínimo']) if pd.notna(row['Est. Mínimo']) else 0
            est_max = int(row['Est. Máximo']) if pd.notna(row['Est. Máximo']) else None
            
            if est_min < 0:
                erros_val.append(f"{cod}: estoque mínimo não pode ser negativo")
            if est_max is not None and est_min >= est_max:
                erros_val.append(f"{cod}: estoque mínimo ({est_min}) deve ser menor que máximo ({est_max})")
            
            lista.append((cod, est_min, est_max))
        
        if erros_val:
            st.error("❌ Erros de validação:")
            for e in erros_val:
                st.markdown(f"  - {e}")
        else:
            atualizados, erros = atualizar_limites_estoque_lote(lista)
            if atualizados > 0:
                st.success(f"✅ {atualizados} produtos atualizados com sucesso!")
            if erros:
                st.warning(f"⚠️ {len(erros)} códigos não encontrados: {', '.join(erros)}")
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
    
    # Exportar Excel
    st.markdown("##### 📥 Exportar Relatório")
    
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
