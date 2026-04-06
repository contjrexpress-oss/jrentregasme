import streamlit as st
import pandas as pd
from styles import page_header, metric_card
from database import get_estoque, atualizar_estoque_inicial, get_produtos
from auth import is_admin


def render():
    st.markdown(page_header("📦 Controle de Estoque", "Visualize e gerencie o estoque de produtos"), unsafe_allow_html=True)
    
    estoque = get_estoque()
    
    if not estoque:
        st.info("ℹ️ Nenhum produto cadastrado. Importe os produtos primeiro no módulo de Importação.")
        return
    
    df = pd.DataFrame(estoque)
    
    # Metrics
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
    
    st.markdown("---")
    
    # Filters
    col_f1, col_f2, col_f3 = st.columns([2, 2, 1])
    with col_f1:
        filtro_texto = st.text_input("🔍 Buscar por código ou descrição", key="filtro_estoque")
    with col_f2:
        ordenar_por = st.selectbox("📊 Ordenar por", 
                                    ["Código", "Descrição", "Estoque Atual (↑)", "Estoque Atual (↓)"],
                                    key="ordenar_estoque")
    with col_f3:
        mostrar_zerados = st.checkbox("Mostrar zerados", value=True, key="mostrar_zerados")
    
    # Apply filters
    df_filtrado = df.copy()
    
    if filtro_texto:
        mask = (
            df_filtrado['codigo'].str.contains(filtro_texto, case=False, na=False) | 
            df_filtrado['descricao'].str.contains(filtro_texto, case=False, na=False)
        )
        df_filtrado = df_filtrado[mask]
    
    if not mostrar_zerados:
        df_filtrado = df_filtrado[df_filtrado['estoque_atual'] != 0]
    
    if ordenar_por == "Código":
        df_filtrado = df_filtrado.sort_values('codigo')
    elif ordenar_por == "Descrição":
        df_filtrado = df_filtrado.sort_values('descricao')
    elif ordenar_por == "Estoque Atual (↑)":
        df_filtrado = df_filtrado.sort_values('estoque_atual', ascending=True)
    elif ordenar_por == "Estoque Atual (↓)":
        df_filtrado = df_filtrado.sort_values('estoque_atual', ascending=False)
    
    st.markdown(f"**{len(df_filtrado)} produtos encontrados**")
    
    # Display table
    df_display = df_filtrado.rename(columns={
        'codigo': 'Código',
        'descricao': 'Descrição',
        'estoque_inicial': 'Est. Inicial',
        'entradas': '🟢 Entradas',
        'saidas': '🔴 Saídas',
        'estoque_atual': '📦 Est. Atual'
    })
    
    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            'Código': st.column_config.TextColumn(width="small"),
            'Descrição': st.column_config.TextColumn(width="large"),
            'Est. Inicial': st.column_config.NumberColumn(width="small"),
            '🟢 Entradas': st.column_config.NumberColumn(width="small"),
            '🔴 Saídas': st.column_config.NumberColumn(width="small"),
            '📦 Est. Atual': st.column_config.NumberColumn(width="small"),
        }
    )
    
    # Edit estoque inicial (admin only)
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
        
        # Get current value
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
