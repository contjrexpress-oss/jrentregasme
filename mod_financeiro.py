import streamlit as st
import pandas as pd
from datetime import datetime, date
from styles import page_header, metric_card
from database import (
    get_faturamento, atualizar_faturamento, deletar_faturamento,
    get_custos, inserir_custo, atualizar_custo, deletar_custo
)


def render():
    st.markdown(page_header("💰 Financeiro", "Faturamento, custos e relatórios financeiros"), unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["📈 Faturamento", "📉 Custos", "📊 Relatórios"])
    
    with tab1:
        _render_faturamento()
    with tab2:
        _render_custos()
    with tab3:
        _render_relatorios()


def _render_faturamento():
    st.markdown("#### 📈 Tabela de Faturamento")
    st.caption("Faturamento gerado automaticamente pelas notas de saída. Valores editáveis.")
    
    faturamento = get_faturamento()
    
    if not faturamento:
        st.info("ℹ️ Nenhum faturamento registrado. Importe notas de saída para gerar faturamento automaticamente.")
        return
    
    df = pd.DataFrame(faturamento)
    
    # Metrics
    total_fat = df['valor'].sum()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(metric_card("Total Faturamento", f"R$ {total_fat:,.2f}", "metric-green"), unsafe_allow_html=True)
    with col2:
        st.markdown(metric_card("Total de Registros", len(df), "metric-blue"), unsafe_allow_html=True)
    with col3:
        media = total_fat / len(df) if len(df) > 0 else 0
        st.markdown(metric_card("Média por Nota", f"R$ {media:,.2f}", "metric-orange"), unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Editable table
    df_edit = df[['id', 'data', 'descricao', 'regiao', 'veiculo', 'valor', 'cep', 'bairro', 'municipio']].copy()
    df_edit = df_edit.rename(columns={
        'id': 'ID',
        'data': 'Data',
        'descricao': 'Descrição',
        'regiao': 'Região',
        'veiculo': 'Veículo',
        'valor': 'Valor (R$)',
        'cep': 'CEP',
        'bairro': 'Bairro',
        'municipio': 'Município'
    })
    
    edited_df = st.data_editor(
        df_edit,
        use_container_width=True,
        hide_index=True,
        disabled=['ID', 'Data', 'Região', 'Veículo', 'CEP', 'Bairro', 'Município'],
        column_config={
            'ID': st.column_config.NumberColumn(width="small"),
            'Valor (R$)': st.column_config.NumberColumn(format="R$ %.2f", min_value=0),
        },
        key="editor_faturamento"
    )
    
    if st.button("💾 Salvar Alterações", type="primary", key="btn_salvar_fat"):
        for _, row in edited_df.iterrows():
            original = next((f for f in faturamento if f['id'] == row['ID']), None)
            if original:
                if row['Descrição'] != original['descricao'] or row['Valor (R$)'] != original['valor']:
                    atualizar_faturamento(row['ID'], row['Descrição'], row['Valor (R$)'])
        st.success("✅ Alterações salvas com sucesso!")
        st.rerun()


def _render_custos():
    st.markdown("#### 📉 Tabela de Custos")
    st.caption("Lançamentos manuais de custos. Adicione, edite ou remova conforme necessário.")
    
    # Add new cost
    st.markdown("##### ➕ Novo Lançamento de Custo")
    with st.form("form_novo_custo"):
        col1, col2, col3, col4 = st.columns([2, 3, 2, 2])
        with col1:
            data_custo = st.date_input("Data", value=date.today(), key="data_novo_custo")
        with col2:
            desc_custo = st.text_input("Descrição", placeholder="Ex: Combustível, Aluguel, etc.", key="desc_novo_custo")
        with col3:
            cat_custo = st.text_input("Categoria", placeholder="Ex: Veículo, Operacional", key="cat_novo_custo")
        with col4:
            valor_custo = st.number_input("Valor (R$)", min_value=0.0, step=10.0, format="%.2f", key="valor_novo_custo")
        
        submit_custo = st.form_submit_button("➕ Adicionar Custo", type="primary", use_container_width=True)
        
        if submit_custo:
            if not desc_custo:
                st.error("❌ Informe a descrição do custo.")
            elif valor_custo <= 0:
                st.error("❌ O valor deve ser maior que zero.")
            else:
                inserir_custo(data_custo.strftime("%Y-%m-%d"), desc_custo, cat_custo, valor_custo)
                st.success("✅ Custo adicionado com sucesso!")
                st.rerun()
    
    st.markdown("---")
    
    custos = get_custos()
    
    if not custos:
        st.info("ℹ️ Nenhum custo registrado.")
        return
    
    df = pd.DataFrame(custos)
    
    # Metrics
    total_custos = df['valor'].sum()
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(metric_card("Total de Custos", f"R$ {total_custos:,.2f}", "metric-red"), unsafe_allow_html=True)
    with col2:
        st.markdown(metric_card("Total de Registros", len(df), "metric-blue"), unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Editable table
    df_edit = df[['id', 'data', 'descricao', 'categoria', 'valor']].copy()
    df_edit = df_edit.rename(columns={
        'id': 'ID',
        'data': 'Data',
        'descricao': 'Descrição',
        'categoria': 'Categoria',
        'valor': 'Valor (R$)'
    })
    
    edited_custos = st.data_editor(
        df_edit,
        use_container_width=True,
        hide_index=True,
        disabled=['ID'],
        column_config={
            'ID': st.column_config.NumberColumn(width="small"),
            'Valor (R$)': st.column_config.NumberColumn(format="R$ %.2f", min_value=0),
        },
        key="editor_custos"
    )
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("💾 Salvar Alterações", type="primary", key="btn_salvar_custos"):
            for _, row in edited_custos.iterrows():
                original = next((c for c in custos if c['id'] == row['ID']), None)
                if original:
                    changed = (
                        row['Data'] != original['data'] or
                        row['Descrição'] != original['descricao'] or
                        row['Categoria'] != original['categoria'] or
                        row['Valor (R$)'] != original['valor']
                    )
                    if changed:
                        atualizar_custo(row['ID'], row['Data'], row['Descrição'], row['Categoria'], row['Valor (R$)'])
            st.success("✅ Alterações salvas!")
            st.rerun()
    
    with col_btn2:
        custo_del_id = st.selectbox(
            "Excluir custo (ID)",
            options=[c['id'] for c in custos],
            format_func=lambda x: f"ID {x} - {next((c['descricao'] for c in custos if c['id'] == x), '')}",
            key="sel_del_custo"
        )
        if st.button("🗑️ Excluir Custo Selecionado", key="btn_del_custo"):
            deletar_custo(custo_del_id)
            st.success("✅ Custo excluído!")
            st.rerun()


def _render_relatorios():
    st.markdown("#### 📊 Relatórios Financeiros")
    
    faturamento = get_faturamento()
    custos = get_custos()
    
    if not faturamento and not custos:
        st.info("ℹ️ Nenhum dado financeiro disponível para gerar relatórios.")
        return
    
    # Period filter
    st.markdown("##### 📅 Filtro por Período")
    col1, col2 = st.columns(2)
    with col1:
        data_inicio = st.date_input("Data Início", value=date(date.today().year, 1, 1), key="rel_data_ini")
    with col2:
        data_fim = st.date_input("Data Fim", value=date.today(), key="rel_data_fim")
    
    data_ini_str = data_inicio.strftime("%Y-%m-%d")
    data_fim_str = data_fim.strftime("%Y-%m-%d")
    
    # Filter data
    df_fat = pd.DataFrame(faturamento) if faturamento else pd.DataFrame(columns=['data', 'valor', 'regiao', 'veiculo'])
    df_cus = pd.DataFrame(custos) if custos else pd.DataFrame(columns=['data', 'valor', 'categoria'])
    
    if not df_fat.empty:
        df_fat['data_parsed'] = pd.to_datetime(df_fat['data'], format='mixed', dayfirst=True, errors='coerce')
        df_fat = df_fat[df_fat['data_parsed'].notna()]
        mask_fat = (df_fat['data_parsed'].dt.date >= data_inicio) & (df_fat['data_parsed'].dt.date <= data_fim)
        df_fat = df_fat[mask_fat]
    
    if not df_cus.empty:
        df_cus['data_parsed'] = pd.to_datetime(df_cus['data'], errors='coerce')
        df_cus = df_cus[df_cus['data_parsed'].notna()]
        mask_cus = (df_cus['data_parsed'].dt.date >= data_inicio) & (df_cus['data_parsed'].dt.date <= data_fim)
        df_cus = df_cus[mask_cus]
    
    total_receita = df_fat['valor'].sum() if not df_fat.empty else 0
    total_custo = df_cus['valor'].sum() if not df_cus.empty else 0
    lucro = total_receita - total_custo
    margem = (lucro / total_receita * 100) if total_receita > 0 else 0
    
    st.markdown("---")
    st.markdown("##### 📋 Resumo do Período")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(metric_card("Receita Total", f"R$ {total_receita:,.2f}", "metric-green"), unsafe_allow_html=True)
    with col2:
        st.markdown(metric_card("Custos Totais", f"R$ {total_custo:,.2f}", "metric-red"), unsafe_allow_html=True)
    with col3:
        lucro_class = "metric-green" if lucro >= 0 else "metric-red"
        st.markdown(metric_card("Lucro Líquido", f"R$ {lucro:,.2f}", lucro_class), unsafe_allow_html=True)
    with col4:
        st.markdown(metric_card("Margem de Lucro", f"{margem:.1f}%", "metric-blue"), unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Charts
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        st.markdown("##### 📈 Faturamento por Região")
        if not df_fat.empty and 'regiao' in df_fat.columns:
            fat_regiao = df_fat.groupby('regiao')['valor'].sum().reset_index()
            fat_regiao.columns = ['Região', 'Valor']
            st.bar_chart(fat_regiao.set_index('Região'))
        else:
            st.info("Sem dados de faturamento no período.")
    
    with col_g2:
        st.markdown("##### 📊 Custos por Categoria")
        if not df_cus.empty and 'categoria' in df_cus.columns:
            cus_cat = df_cus.groupby('categoria')['valor'].sum().reset_index()
            cus_cat.columns = ['Categoria', 'Valor']
            st.bar_chart(cus_cat.set_index('Categoria'))
        else:
            st.info("Sem dados de custos no período.")
    
    # Monthly evolution
    st.markdown("##### 📈 Evolução Mensal")
    
    monthly_data = []
    
    if not df_fat.empty:
        df_fat['mes'] = df_fat['data_parsed'].dt.to_period('M').astype(str)
        fat_mensal = df_fat.groupby('mes')['valor'].sum().reset_index()
        fat_mensal.columns = ['Mês', 'Receita']
        monthly_data.append(fat_mensal.set_index('Mês'))
    
    if not df_cus.empty:
        df_cus['mes'] = df_cus['data_parsed'].dt.to_period('M').astype(str)
        cus_mensal = df_cus.groupby('mes')['valor'].sum().reset_index()
        cus_mensal.columns = ['Mês', 'Custos']
        monthly_data.append(cus_mensal.set_index('Mês'))
    
    if monthly_data:
        df_mensal = pd.concat(monthly_data, axis=1).fillna(0)
        if 'Receita' not in df_mensal.columns:
            df_mensal['Receita'] = 0
        if 'Custos' not in df_mensal.columns:
            df_mensal['Custos'] = 0
        df_mensal['Lucro'] = df_mensal['Receita'] - df_mensal['Custos']
        st.line_chart(df_mensal)
    else:
        st.info("Sem dados suficientes para evolução mensal.")
    
    # Vehicle breakdown
    if not df_fat.empty and 'veiculo' in df_fat.columns:
        st.markdown("##### 🚗 Faturamento por Tipo de Veículo")
        fat_veiculo = df_fat.groupby('veiculo')['valor'].agg(['sum', 'count']).reset_index()
        fat_veiculo.columns = ['Veículo', 'Valor Total', 'Qtde Entregas']
        fat_veiculo['Valor Total'] = fat_veiculo['Valor Total'].apply(lambda x: f"R$ {x:,.2f}")
        st.dataframe(fat_veiculo, use_container_width=True, hide_index=True)
