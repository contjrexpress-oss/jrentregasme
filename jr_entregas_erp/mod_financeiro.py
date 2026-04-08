import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import plotly.express as px
import plotly.graph_objects as go
from styles import page_header, metric_card
from database import (
    get_faturamento, inserir_faturamento, atualizar_faturamento, deletar_faturamento,
    get_custos, inserir_custo, atualizar_custo, deletar_custo,
    get_categorias_custos, get_subcategorias_custos,
    inserir_categoria_custo, atualizar_categoria_custo,
    inserir_subcategoria_custo, atualizar_subcategoria_custo,
    get_contas, inserir_conta, atualizar_conta, marcar_conta_paga,
    cancelar_conta, deletar_conta, atualizar_status_contas_atrasadas,
)

# Cores corporativas
COR_AZUL = "#0B132B"
COR_LARANJA = "#F29F05"
COR_VERDE = "#38A169"
COR_VERMELHO = "#E53E3E"
COR_AZUL_MEDIO = "#3182CE"


def render():
    st.markdown(page_header("💰 Financeiro", "Faturamento, custos, categorias, contas e relatórios financeiros"), unsafe_allow_html=True)
    
    # Atualizar status de contas atrasadas ao carregar
    atualizar_status_contas_atrasadas()
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Faturamento", "📉 Custos", "🏷️ Categorias", "💳 Contas", "📊 Relatórios"
    ])
    
    with tab1:
        _render_faturamento()
    with tab2:
        _render_custos()
    with tab3:
        _render_categorias()
    with tab4:
        _render_contas()
    with tab5:
        _render_relatorios()


# ============================================================
# FATURAMENTO (sem mudanças significativas)
# ============================================================
def _render_faturamento():
    st.markdown("#### 📈 Tabela de Faturamento")
    st.caption("Faturamento gerado automaticamente pelas notas de saída e lançamentos manuais. Valores editáveis.")
    
    # --- Formulário para lançamento manual ---
    st.markdown("##### ➕ Novo Lançamento de Faturamento")
    with st.form("form_novo_faturamento"):
        col1, col2, col3 = st.columns([2, 3, 2])
        with col1:
            fat_data = st.date_input("Data", value=date.today(), key="fat_data_novo")
        with col2:
            fat_desc = st.text_input("Descrição", placeholder="Ex: Entrega avulsa - Cliente X", key="fat_desc_novo")
        with col3:
            fat_cliente = st.text_input("Cliente", placeholder="Nome do cliente", key="fat_cliente_novo")
        
        col4, col5, col6, col7 = st.columns([2, 2, 2, 2])
        with col4:
            fat_regiao = st.text_input("Região", placeholder="Ex: R2 - Zona Sul", key="fat_regiao_novo")
        with col5:
            fat_veiculo = st.selectbox("Veículo", options=["Motoboy", "Carro", "Van", "Outro"], key="fat_veiculo_novo")
        with col6:
            fat_valor = st.number_input("Valor (R$)", min_value=0.0, step=10.0, format="%.2f", key="fat_valor_novo")
        with col7:
            fat_cep = st.text_input("CEP", placeholder="00000-000", key="fat_cep_novo")
        
        col8, col9 = st.columns(2)
        with col8:
            fat_bairro = st.text_input("Bairro", placeholder="Bairro", key="fat_bairro_novo")
        with col9:
            fat_municipio = st.text_input("Município", placeholder="Município", key="fat_municipio_novo")
        
        submit_fat = st.form_submit_button("➕ Adicionar Faturamento", type="primary", use_container_width=True)
        
        if submit_fat:
            if not fat_desc:
                st.error("❌ Informe a descrição do faturamento.")
            elif fat_valor <= 0:
                st.error("❌ O valor deve ser maior que zero.")
            else:
                inserir_faturamento(
                    nota_id=None,
                    data=fat_data.strftime("%d/%m/%Y"),
                    descricao=fat_desc,
                    regiao=fat_regiao,
                    veiculo=fat_veiculo,
                    valor=fat_valor,
                    cep=fat_cep,
                    bairro=fat_bairro,
                    municipio=fat_municipio,
                    cliente=fat_cliente
                )
                st.success("✅ Faturamento adicionado com sucesso!")
                st.rerun()
    
    st.markdown("---")
    
    # --- Tabela de faturamento existente ---
    faturamento = get_faturamento()
    
    if not faturamento:
        st.info("ℹ️ Nenhum faturamento registrado. Importe notas de saída ou adicione manualmente.")
        return
    
    df = pd.DataFrame(faturamento)
    
    if 'cliente' not in df.columns:
        df['cliente'] = ''
    df['cliente'] = df['cliente'].fillna('')
    
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
    
    df_edit = df[['id', 'data', 'descricao', 'cliente', 'regiao', 'veiculo', 'valor', 'cep', 'bairro', 'municipio']].copy()
    df_edit = df_edit.rename(columns={
        'id': 'ID', 'data': 'Data', 'descricao': 'Descrição', 'cliente': 'Cliente',
        'regiao': 'Região', 'veiculo': 'Veículo', 'valor': 'Valor (R$)',
        'cep': 'CEP', 'bairro': 'Bairro', 'municipio': 'Município'
    })
    
    edited_df = st.data_editor(
        df_edit, use_container_width=True, hide_index=True, disabled=['ID'],
        column_config={
            'ID': st.column_config.NumberColumn(width="small"),
            'Valor (R$)': st.column_config.NumberColumn(format="R$ %.2f", min_value=0),
            'Cliente': st.column_config.TextColumn(width="medium"),
        },
        key="editor_faturamento"
    )
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("💾 Salvar Alterações", type="primary", key="btn_salvar_fat"):
            alteracoes = 0
            for _, row in edited_df.iterrows():
                original = next((f for f in faturamento if f['id'] == row['ID']), None)
                if original:
                    kwargs = {}
                    for col_pt, col_db in [('Descrição', 'descricao'), ('Valor (R$)', 'valor'),
                                           ('Cliente', 'cliente'), ('Data', 'data'), ('Região', 'regiao'),
                                           ('Veículo', 'veiculo'), ('CEP', 'cep'), ('Bairro', 'bairro'),
                                           ('Município', 'municipio')]:
                        if str(row[col_pt]) != str(original.get(col_db) or ''):
                            kwargs[col_db] = row[col_pt]
                    if kwargs:
                        atualizar_faturamento(row['ID'], **kwargs)
                        alteracoes += 1
            if alteracoes:
                st.success(f"✅ {alteracoes} registro(s) atualizado(s)!")
            else:
                st.info("ℹ️ Nenhuma alteração detectada.")
            st.rerun()
    
    with col_btn2:
        fat_del_id = st.selectbox(
            "Excluir faturamento (ID)", options=[f['id'] for f in faturamento],
            format_func=lambda x: f"ID {x} - {next((f['descricao'] for f in faturamento if f['id'] == x), '')}",
            key="sel_del_fat"
        )
        if st.button("🗑️ Excluir Faturamento Selecionado", key="btn_del_fat"):
            deletar_faturamento(fat_del_id)
            st.success("✅ Faturamento excluído!")
            st.rerun()


# ============================================================
# CUSTOS (atualizado com seletores de categoria/subcategoria)
# ============================================================
def _render_custos():
    st.markdown("#### 📉 Tabela de Custos")
    st.caption("Lançamentos manuais de custos com categorias e subcategorias.")
    
    # Carregar categorias e subcategorias
    categorias = get_categorias_custos()
    cat_map = {c['id']: c['nome'] for c in categorias}
    cat_options = ["(Sem categoria)"] + [c['nome'] for c in categorias]
    cat_id_by_name = {c['nome']: c['id'] for c in categorias}
    
    st.markdown("##### ➕ Novo Lançamento de Custo")
    with st.form("form_novo_custo"):
        col1, col2 = st.columns([2, 4])
        with col1:
            data_custo = st.date_input("Data", value=date.today(), key="data_novo_custo")
        with col2:
            desc_custo = st.text_input("Descrição", placeholder="Ex: Combustível, Aluguel, etc.", key="desc_novo_custo")
        
        col3, col4, col5 = st.columns([2, 2, 2])
        with col3:
            cat_sel = st.selectbox("Categoria", options=cat_options, key="cat_novo_custo")
        with col4:
            # Subcategorias baseadas na categoria selecionada
            subcat_options = ["(Sem subcategoria)"]
            if cat_sel != "(Sem categoria)" and cat_sel in cat_id_by_name:
                subcats = get_subcategorias_custos(cat_id_by_name[cat_sel])
                subcat_options += [s['nome'] for s in subcats]
            subcat_sel = st.selectbox("Subcategoria", options=subcat_options, key="subcat_novo_custo")
        with col5:
            valor_custo = st.number_input("Valor (R$)", min_value=0.0, step=10.0, format="%.2f", key="valor_novo_custo")
        
        submit_custo = st.form_submit_button("➕ Adicionar Custo", type="primary", use_container_width=True)
        
        if submit_custo:
            if not desc_custo:
                st.error("❌ Informe a descrição do custo.")
            elif valor_custo <= 0:
                st.error("❌ O valor deve ser maior que zero.")
            else:
                # Determinar categoria_id e subcategoria_id
                cat_id_val = cat_id_by_name.get(cat_sel) if cat_sel != "(Sem categoria)" else None
                sub_id_val = None
                if cat_id_val and subcat_sel != "(Sem subcategoria)":
                    subcats = get_subcategorias_custos(cat_id_val)
                    sub_match = next((s for s in subcats if s['nome'] == subcat_sel), None)
                    if sub_match:
                        sub_id_val = sub_match['id']
                
                # Texto da categoria para manter compatibilidade
                cat_text = cat_sel if cat_sel != "(Sem categoria)" else ""
                if subcat_sel != "(Sem subcategoria)":
                    cat_text = f"{cat_sel} > {subcat_sel}"
                
                # Inserir custo com a categoria texto (compatibilidade) + IDs
                conn = __import__('database').get_connection()
                conn.execute("""
                    INSERT INTO custos (data, descricao, categoria, valor, categoria_id, subcategoria_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (data_custo.strftime("%Y-%m-%d"), desc_custo, cat_text, valor_custo, cat_id_val, sub_id_val))
                conn.commit()
                conn.close()
                st.success("✅ Custo adicionado com sucesso!")
                st.rerun()
    
    st.markdown("---")
    
    custos = get_custos()
    
    if not custos:
        st.info("ℹ️ Nenhum custo registrado.")
        return
    
    df = pd.DataFrame(custos)
    
    total_custos = df['valor'].sum()
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(metric_card("Total de Custos", f"R$ {total_custos:,.2f}", "metric-red"), unsafe_allow_html=True)
    with col2:
        st.markdown(metric_card("Total de Registros", len(df), "metric-blue"), unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Tabela editável
    cols_show = ['id', 'data', 'descricao', 'categoria', 'valor']
    df_edit = df[cols_show].copy()
    df_edit = df_edit.rename(columns={
        'id': 'ID', 'data': 'Data', 'descricao': 'Descrição',
        'categoria': 'Categoria', 'valor': 'Valor (R$)'
    })
    
    edited_custos = st.data_editor(
        df_edit, use_container_width=True, hide_index=True, disabled=['ID'],
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
                        row['Categoria'] != (original['categoria'] or '') or
                        row['Valor (R$)'] != original['valor']
                    )
                    if changed:
                        atualizar_custo(row['ID'], row['Data'], row['Descrição'], row['Categoria'], row['Valor (R$)'])
            st.success("✅ Alterações salvas!")
            st.rerun()
    
    with col_btn2:
        custo_del_id = st.selectbox(
            "Excluir custo (ID)", options=[c['id'] for c in custos],
            format_func=lambda x: f"ID {x} - {next((c['descricao'] for c in custos if c['id'] == x), '')}",
            key="sel_del_custo"
        )
        if st.button("🗑️ Excluir Custo Selecionado", key="btn_del_custo"):
            deletar_custo(custo_del_id)
            st.success("✅ Custo excluído!")
            st.rerun()


# ============================================================
# CATEGORIAS DE CUSTOS
# ============================================================
def _render_categorias():
    st.markdown("#### 🏷️ Gerenciamento de Categorias de Custos")
    st.caption("Crie, edite e organize categorias e subcategorias para classificar seus custos.")
    
    categorias = get_categorias_custos(apenas_ativas=False)
    
    # --- Criar nova categoria ---
    st.markdown("##### ➕ Nova Categoria")
    with st.form("form_nova_categoria"):
        col1, col2 = st.columns([4, 1])
        with col1:
            nova_cat_nome = st.text_input("Nome da Categoria", placeholder="Ex: Veículo, Operacional...", key="nova_cat_nome")
        with col2:
            nova_cat_cor = st.color_picker("Cor", value="#3182CE", key="nova_cat_cor")
        
        if st.form_submit_button("➕ Criar Categoria", type="primary", use_container_width=True):
            if not nova_cat_nome.strip():
                st.error("❌ Informe o nome da categoria.")
            else:
                ok, msg = inserir_categoria_custo(nova_cat_nome, nova_cat_cor)
                if ok:
                    st.success(f"✅ {msg}")
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")
    
    st.markdown("---")
    
    # --- Listar categorias com subcategorias ---
    if not categorias:
        st.info("ℹ️ Nenhuma categoria cadastrada.")
        return
    
    st.markdown("##### 📋 Categorias Cadastradas")
    
    for cat in categorias:
        status_icon = "🟢" if cat['ativo'] else "🔴"
        cor_badge = f"<span style='display:inline-block;width:14px;height:14px;border-radius:50%;background:{cat['cor']};margin-right:6px;vertical-align:middle;'></span>"
        
        with st.expander(f"{status_icon} {cor_badge} **{cat['nome']}**" + (" _(inativa)_" if not cat['ativo'] else ""), expanded=False):
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                novo_nome = st.text_input("Nome", value=cat['nome'], key=f"cat_nome_{cat['id']}")
            with col2:
                nova_cor = st.color_picker("Cor", value=cat['cor'], key=f"cat_cor_{cat['id']}")
            with col3:
                ativo_toggle = st.checkbox("Ativa", value=bool(cat['ativo']), key=f"cat_ativo_{cat['id']}")
            
            if st.button("💾 Salvar Categoria", key=f"btn_salvar_cat_{cat['id']}"):
                atualizar_categoria_custo(cat['id'], nome=novo_nome, cor=nova_cor, ativo=ativo_toggle)
                st.success(f"✅ Categoria '{novo_nome}' atualizada!")
                st.rerun()
            
            st.markdown("---")
            
            # Subcategorias desta categoria
            subcats = get_subcategorias_custos(cat['id'], apenas_ativas=False)
            
            st.markdown(f"###### Subcategorias de {cat['nome']}")
            
            if subcats:
                for sub in subcats:
                    sub_icon = "✅" if sub['ativo'] else "❌"
                    col_s1, col_s2, col_s3 = st.columns([4, 1, 1])
                    with col_s1:
                        sub_novo_nome = st.text_input("Nome", value=sub['nome'], key=f"sub_nome_{sub['id']}", label_visibility="collapsed")
                    with col_s2:
                        sub_ativo = st.checkbox("Ativa", value=bool(sub['ativo']), key=f"sub_ativo_{sub['id']}")
                    with col_s3:
                        if st.button("💾", key=f"btn_sub_{sub['id']}"):
                            atualizar_subcategoria_custo(sub['id'], nome=sub_novo_nome, ativo=sub_ativo)
                            st.success(f"✅ Subcategoria atualizada!")
                            st.rerun()
            else:
                st.caption("Nenhuma subcategoria cadastrada.")
            
            # Adicionar subcategoria
            col_add1, col_add2 = st.columns([4, 1])
            with col_add1:
                nova_sub_nome = st.text_input("Nova subcategoria", placeholder="Nome da subcategoria...", key=f"nova_sub_{cat['id']}", label_visibility="collapsed")
            with col_add2:
                if st.button("➕", key=f"btn_add_sub_{cat['id']}"):
                    if nova_sub_nome.strip():
                        ok, msg = inserir_subcategoria_custo(cat['id'], nova_sub_nome)
                        if ok:
                            st.success(f"✅ {msg}")
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")
                    else:
                        st.warning("⚠️ Informe o nome da subcategoria.")


# ============================================================
# CONTAS A PAGAR/RECEBER
# ============================================================
def _render_contas():
    st.markdown("#### 💳 Contas a Pagar / Receber")
    st.caption("Gerencie suas obrigações financeiras. Registre, acompanhe e controle vencimentos.")
    
    categorias = get_categorias_custos()
    cat_options_contas = ["(Sem categoria)"] + [c['nome'] for c in categorias]
    cat_id_by_name = {c['nome']: c['id'] for c in categorias}
    
    # --- Formulário nova conta ---
    st.markdown("##### ➕ Registrar Nova Conta")
    with st.form("form_nova_conta"):
        col1, col2 = st.columns(2)
        with col1:
            conta_tipo = st.selectbox("Tipo", options=["pagar", "receber"],
                                       format_func=lambda x: "💸 A Pagar" if x == "pagar" else "💰 A Receber",
                                       key="conta_tipo_novo")
        with col2:
            conta_desc = st.text_input("Descrição", placeholder="Ex: Aluguel mensal, Pagamento cliente X...", key="conta_desc_novo")
        
        col3, col4, col5 = st.columns(3)
        with col3:
            conta_valor = st.number_input("Valor (R$)", min_value=0.01, step=10.0, format="%.2f", key="conta_valor_novo")
        with col4:
            conta_vencimento = st.date_input("Data de Vencimento", value=date.today(), key="conta_venc_novo")
        with col5:
            conta_cat = st.selectbox("Categoria", options=cat_options_contas, key="conta_cat_novo")
        
        conta_obs = st.text_area("Observações (opcional)", placeholder="Detalhes adicionais...", key="conta_obs_novo", height=68)
        
        if st.form_submit_button("➕ Registrar Conta", type="primary", use_container_width=True):
            if not conta_desc.strip():
                st.error("❌ Informe a descrição da conta.")
            elif conta_valor <= 0:
                st.error("❌ O valor deve ser maior que zero.")
            else:
                cat_id_val = cat_id_by_name.get(conta_cat) if conta_cat != "(Sem categoria)" else None
                inserir_conta(
                    tipo=conta_tipo,
                    descricao=conta_desc,
                    valor=conta_valor,
                    data_vencimento=conta_vencimento.strftime("%Y-%m-%d"),
                    categoria_id=cat_id_val,
                    observacoes=conta_obs
                )
                st.success("✅ Conta registrada com sucesso!")
                st.rerun()
    
    st.markdown("---")
    
    # --- Filtros ---
    st.markdown("##### 🔍 Filtros")
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        filtro_tipo = st.selectbox("Tipo", options=["Todos", "pagar", "receber"],
                                    format_func=lambda x: {"Todos": "📋 Todos", "pagar": "💸 A Pagar", "receber": "💰 A Receber"}[x],
                                    key="filtro_tipo_conta")
    with col_f2:
        filtro_status = st.selectbox("Status", options=["Todos", "pendente", "atrasado", "pago", "cancelado"],
                                      format_func=lambda x: {
                                          "Todos": "📋 Todos", "pendente": "⏳ Pendente",
                                          "atrasado": "🔴 Atrasado", "pago": "✅ Pago", "cancelado": "❌ Cancelado"
                                      }[x], key="filtro_status_conta")
    with col_f3:
        filtro_data_ini = st.date_input("De", value=date(date.today().year, 1, 1), key="filtro_conta_ini")
    with col_f4:
        filtro_data_fim = st.date_input("Até", value=date(date.today().year, 12, 31), key="filtro_conta_fim")
    
    # Buscar contas
    tipo_param = filtro_tipo if filtro_tipo != "Todos" else None
    status_param = filtro_status if filtro_status != "Todos" else None
    contas = get_contas(
        tipo=tipo_param, status=status_param,
        data_inicio=filtro_data_ini.strftime("%Y-%m-%d"),
        data_fim=filtro_data_fim.strftime("%Y-%m-%d")
    )
    
    if not contas:
        st.info("ℹ️ Nenhuma conta encontrada com os filtros selecionados.")
        return
    
    # --- Métricas ---
    df_contas = pd.DataFrame(contas)
    
    total_pagar = df_contas[df_contas['tipo'] == 'pagar']['valor'].sum() if 'tipo' in df_contas.columns else 0
    total_receber = df_contas[df_contas['tipo'] == 'receber']['valor'].sum() if 'tipo' in df_contas.columns else 0
    pendentes = len(df_contas[df_contas['status'].isin(['pendente', 'atrasado'])]) if 'status' in df_contas.columns else 0
    atrasadas = len(df_contas[df_contas['status'] == 'atrasado']) if 'status' in df_contas.columns else 0
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(metric_card("Total a Pagar", f"R$ {total_pagar:,.2f}", "metric-red"), unsafe_allow_html=True)
    with col2:
        st.markdown(metric_card("Total a Receber", f"R$ {total_receber:,.2f}", "metric-green"), unsafe_allow_html=True)
    with col3:
        st.markdown(metric_card("Pendentes", str(pendentes), "metric-orange"), unsafe_allow_html=True)
    with col4:
        st.markdown(metric_card("Atrasadas", str(atrasadas), "metric-red"), unsafe_allow_html=True)
    
    st.markdown("---")
    
    # --- Tabela de contas com cores condicionais ---
    st.markdown("##### 📋 Lista de Contas")
    
    # Tabela resumo com cores condicionais
    df_display = df_contas[['id', 'tipo', 'descricao', 'valor', 'data_vencimento', 'status']].copy()
    df_display['data_vencimento'] = df_display['data_vencimento'].apply(
        lambda x: datetime.strptime(x, "%Y-%m-%d").strftime("%d/%m/%Y") if x else ''
    )
    df_display = df_display.rename(columns={
        'id': 'ID', 'tipo': 'Tipo', 'descricao': 'Descrição',
        'valor': 'Valor (R$)', 'data_vencimento': 'Vencimento', 'status': 'Status'
    })
    df_display['Tipo'] = df_display['Tipo'].map({'pagar': '💸 A Pagar', 'receber': '💰 A Receber'})
    df_display['Status'] = df_display['Status'].map({
        'pendente': '⏳ Pendente', 'atrasado': '🔴 Atrasado',
        'pago': '✅ Pago', 'cancelado': '❌ Cancelado'
    })
    df_display['Valor (R$)'] = df_display['Valor (R$)'].apply(lambda x: f"R$ {x:,.2f}")
    
    # Exibir tabela resumo colorida
    def _color_status(val):
        if '🔴' in str(val):
            return 'background-color: rgba(229,62,62,0.12); color: #E53E3E; font-weight: bold'
        elif '⏳' in str(val):
            return 'background-color: rgba(242,159,5,0.10); color: #D69E2E; font-weight: bold'
        elif '✅' in str(val):
            return 'background-color: rgba(56,161,105,0.10); color: #38A169; font-weight: bold'
        elif '❌' in str(val):
            return 'background-color: rgba(113,128,150,0.10); color: #718096'
        return ''
    
    styled = df_display.style.applymap(_color_status, subset=['Status'])
    st.dataframe(styled, use_container_width=True, hide_index=True)
    
    # Totalizador
    total_val = df_contas['valor'].sum()
    st.markdown(f"**📊 Total exibido: R$ {total_val:,.2f}** ({len(df_contas)} registros)")
    
    st.markdown("---")
    
    # --- Ações rápidas: Marcar como Pago ---
    contas_pendentes_list = [c for c in contas if c['status'] in ('pendente', 'atrasado')]
    if contas_pendentes_list:
        st.markdown("##### ⚡ Ações Rápidas — Marcar como Pago/Recebido")
        
        for conta in contas_pendentes_list:
            status_map = {
                'pendente': ('⏳', '#F29F05'),
                'atrasado': ('🔴', '#E53E3E'),
            }
            icon, cor = status_map.get(conta['status'], ('📋', '#718096'))
            tipo_icon = "💸" if conta['tipo'] == 'pagar' else "💰"
            cat_label = conta.get('categoria_nome') or 'Sem categoria'
            
            try:
                venc_dt = datetime.strptime(conta['data_vencimento'], "%Y-%m-%d")
                venc_str = venc_dt.strftime("%d/%m/%Y")
            except:
                venc_str = conta['data_vencimento']
            
            # Card visual com cor baseada no status
            border_color = cor
            st.markdown(f"""
            <div style="border-left: 4px solid {border_color}; padding: 8px 14px; margin: 6px 0; 
                        background: rgba(255,255,255,0.7); border-radius: 0 8px 8px 0;">
                <span style="font-size: 0.9em;">
                    {icon} {tipo_icon} <strong>{conta['descricao']}</strong> — 
                    <strong style="color: {cor};">R$ {conta['valor']:,.2f}</strong> — 
                    Venc: {venc_str} — <em>{conta['status'].upper()}</em> — {cat_label}
                </span>
            </div>
            """, unsafe_allow_html=True)
            
            col_a1, col_a2, col_a3, col_a4 = st.columns([2, 2, 1, 1])
            with col_a1:
                data_pag = st.date_input("Data pagamento", value=date.today(), key=f"pag_data_{conta['id']}", label_visibility="collapsed")
            with col_a2:
                if st.button("✅ Marcar como Pago", key=f"btn_pagar_{conta['id']}", type="primary", use_container_width=True):
                    marcar_conta_paga(conta['id'], data_pag.strftime("%Y-%m-%d"))
                    st.success(f"✅ Conta '{conta['descricao']}' marcada como paga!")
                    st.rerun()
            with col_a3:
                if st.button("❌ Cancelar", key=f"btn_cancelar_{conta['id']}", use_container_width=True):
                    cancelar_conta(conta['id'])
                    st.success("✅ Conta cancelada!")
                    st.rerun()
            with col_a4:
                if st.button("🗑️", key=f"btn_del_conta_{conta['id']}", use_container_width=True):
                    deletar_conta(conta['id'])
                    st.success("✅ Conta excluída!")
                    st.rerun()
        
        st.markdown("---")
    
    # --- Detalhes em expanders para contas pagas/canceladas ---
    contas_finalizadas = [c for c in contas if c['status'] in ('pago', 'cancelado')]
    if contas_finalizadas:
        st.markdown("##### 📁 Contas Finalizadas")
        for conta in contas_finalizadas:
            icon = "✅" if conta['status'] == 'pago' else "❌"
            tipo_icon = "💸" if conta['tipo'] == 'pagar' else "💰"
            with st.expander(f"{icon} {tipo_icon} {conta['descricao']} — R$ {conta['valor']:,.2f} — {conta['status'].upper()}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Tipo:** {'A Pagar' if conta['tipo'] == 'pagar' else 'A Receber'}")
                    st.markdown(f"**Valor:** R$ {conta['valor']:,.2f}")
                with col2:
                    pag_str = ""
                    if conta.get('data_pagamento'):
                        try:
                            pag_str = datetime.strptime(conta['data_pagamento'], "%Y-%m-%d").strftime("%d/%m/%Y")
                        except:
                            pag_str = conta['data_pagamento']
                    st.markdown(f"**Pagamento:** {pag_str or '—'}")
                    if conta.get('observacoes'):
                        st.markdown(f"**Obs:** {conta['observacoes']}")
                if st.button("🗑️ Excluir Conta", key=f"btn_del_conta_{conta['id']}"):
                    deletar_conta(conta['id'])
                    st.success("✅ Conta excluída!")
                    st.rerun()


# ============================================================
# RELATÓRIOS — Gráficos Interativos Plotly + Drill-down
# ============================================================

# Layout padrão para gráficos Plotly
_PLOTLY_LAYOUT = dict(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    font=dict(family='sans-serif', color=COR_AZUL),
    margin=dict(l=20, r=20, t=40, b=20),
    legend=dict(bgcolor='rgba(255,255,255,0.8)'),
)

# Paleta corporativa para gráficos
_PALETA = [COR_AZUL, COR_LARANJA, COR_VERDE, COR_VERMELHO, COR_AZUL_MEDIO,
           '#805AD5', '#DD6B20', '#2B6CB0', '#C53030', '#2F855A']


def _render_relatorios():
    st.markdown("#### 📊 Relatórios Financeiros")

    faturamento = get_faturamento()
    custos = get_custos()

    if not faturamento and not custos:
        st.info("ℹ️ Nenhum dado financeiro disponível para gerar relatórios.")
        return

    # ── Filtros ─────────────────────────────────────────────
    st.markdown("##### 📅 Filtros")
    col1, col2 = st.columns(2)
    with col1:
        data_inicio = st.date_input("Data Início", value=date(date.today().year, 1, 1), key="rel_data_ini")
    with col2:
        data_fim = st.date_input("Data Fim", value=date.today(), key="rel_data_fim")

    # Filtro por cliente
    df_fat_full = pd.DataFrame(faturamento) if faturamento else pd.DataFrame(columns=['data', 'valor', 'regiao', 'veiculo', 'cliente'])
    if 'cliente' not in df_fat_full.columns:
        df_fat_full['cliente'] = ''
    df_fat_full['cliente'] = df_fat_full['cliente'].fillna('').astype(str)
    clientes_unicos = sorted([c for c in df_fat_full['cliente'].unique() if c.strip()])
    clientes_selecionados = []
    if clientes_unicos:
        clientes_selecionados = st.multiselect(
            "🏢 Filtrar por Cliente(s)", options=clientes_unicos, default=[],
            placeholder="Todos os clientes", key="rel_filtro_clientes"
        )

    # ── Preparar DataFrames filtrados ───────────────────────
    df_fat = df_fat_full.copy()
    df_cus = pd.DataFrame(custos) if custos else pd.DataFrame(columns=['data', 'valor', 'categoria'])

    if not df_fat.empty:
        df_fat['data_parsed'] = pd.to_datetime(df_fat['data'], format='mixed', dayfirst=True, errors='coerce')
        df_fat = df_fat[df_fat['data_parsed'].notna()]
        df_fat = df_fat[(df_fat['data_parsed'].dt.date >= data_inicio) & (df_fat['data_parsed'].dt.date <= data_fim)]
    if clientes_selecionados and not df_fat.empty:
        df_fat = df_fat[df_fat['cliente'].isin(clientes_selecionados)]

    if not df_cus.empty:
        df_cus['data_parsed'] = pd.to_datetime(df_cus['data'], errors='coerce')
        df_cus = df_cus[df_cus['data_parsed'].notna()]
        df_cus = df_cus[(df_cus['data_parsed'].dt.date >= data_inicio) & (df_cus['data_parsed'].dt.date <= data_fim)]

    total_receita = df_fat['valor'].sum() if not df_fat.empty else 0
    total_custo = df_cus['valor'].sum() if not df_cus.empty else 0
    lucro = total_receita - total_custo
    margem = (lucro / total_receita * 100) if total_receita > 0 else 0

    # ── Métricas Resumo ─────────────────────────────────────
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

    # ── Contas Pendentes ────────────────────────────────────
    contas_pendentes = get_contas(status='pendente')
    contas_atrasadas = get_contas(status='atrasado')
    todas_pendentes = contas_pendentes + contas_atrasadas
    if todas_pendentes:
        st.markdown("---")
        st.markdown("##### 💳 Resumo de Contas Pendentes")
        pagar_pend = sum(c['valor'] for c in todas_pendentes if c['tipo'] == 'pagar')
        receber_pend = sum(c['valor'] for c in todas_pendentes if c['tipo'] == 'receber')
        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            st.markdown(metric_card("A Pagar (pendente)", f"R$ {pagar_pend:,.2f}", "metric-red"), unsafe_allow_html=True)
        with col_c2:
            st.markdown(metric_card("A Receber (pendente)", f"R$ {receber_pend:,.2f}", "metric-green"), unsafe_allow_html=True)
        with col_c3:
            saldo = receber_pend - pagar_pend
            saldo_class = "metric-green" if saldo >= 0 else "metric-red"
            st.markdown(metric_card("Saldo Previsto", f"R$ {saldo:,.2f}", saldo_class), unsafe_allow_html=True)

    st.markdown("---")

    # ════════════════════════════════════════════════════════
    # 1) GRÁFICO DE PIZZA — Distribuição de Custos por Categoria
    # ════════════════════════════════════════════════════════
    st.markdown("##### 🥧 Distribuição de Custos por Categoria")

    if not df_cus.empty and 'categoria' in df_cus.columns:
        df_cus['categoria_label'] = df_cus['categoria'].fillna('').apply(
            lambda x: x.split(' > ')[0] if x.strip() else 'Sem categoria'
        )
        cus_cat = df_cus.groupby('categoria_label')['valor'].sum().reset_index()
        cus_cat.columns = ['Categoria', 'Valor']
        cus_cat = cus_cat.sort_values('Valor', ascending=False)
        cus_cat['Percentual'] = (cus_cat['Valor'] / cus_cat['Valor'].sum() * 100).round(1)

        fig_pizza = px.pie(
            cus_cat, values='Valor', names='Categoria',
            color_discrete_sequence=_PALETA,
            hole=0.4,
        )
        fig_pizza.update_traces(
            textinfo='label+percent',
            hovertemplate='<b>%{label}</b><br>R$ %{value:,.2f}<br>%{percent}<extra></extra>',
        )
        fig_pizza.update_layout(
            **_PLOTLY_LAYOUT,
            title=dict(text='Custos por Categoria', font=dict(size=16, color=COR_AZUL)),
            showlegend=True,
        )
        st.plotly_chart(fig_pizza, use_container_width=True)

        # ── Drill-down: selecionar categoria para ver detalhes ──
        st.markdown("###### 🔍 Detalhes por Categoria")
        cat_filtro = st.selectbox(
            "Selecione uma categoria para ver lançamentos:",
            options=["Todas"] + cus_cat['Categoria'].tolist(),
            key="rel_drilldown_cat"
        )

        if cat_filtro != "Todas":
            df_drill = df_cus[df_cus['categoria_label'] == cat_filtro].copy()
        else:
            df_drill = df_cus.copy()

        with st.expander(f"📋 Lançamentos — {cat_filtro} ({len(df_drill)} registros, R$ {df_drill['valor'].sum():,.2f})", expanded=False):
            df_drill_show = df_drill[['data', 'descricao', 'categoria', 'valor']].copy()
            df_drill_show = df_drill_show.rename(columns={
                'data': 'Data', 'descricao': 'Descrição', 'categoria': 'Categoria', 'valor': 'Valor (R$)'
            })
            df_drill_show['Valor (R$)'] = df_drill_show['Valor (R$)'].apply(lambda x: f"R$ {x:,.2f}")
            st.dataframe(df_drill_show, use_container_width=True, hide_index=True)
            st.markdown(f"**Total: R$ {df_drill['valor'].sum():,.2f}**")
    else:
        st.info("Sem dados de custos no período para gerar gráfico de pizza.")

    st.markdown("---")

    # ════════════════════════════════════════════════════════
    # 2) GRÁFICO DE BARRAS EMPILHADAS — Faturamento vs Custos por Mês
    # ════════════════════════════════════════════════════════
    st.markdown("##### 📊 Faturamento vs Custos por Mês")

    fat_mensal = pd.DataFrame()
    cus_mensal = pd.DataFrame()

    if not df_fat.empty:
        df_fat['mes'] = df_fat['data_parsed'].dt.to_period('M').astype(str)
        fat_mensal = df_fat.groupby('mes')['valor'].sum().reset_index()
        fat_mensal.columns = ['Mês', 'Faturamento']

    if not df_cus.empty:
        df_cus['mes'] = df_cus['data_parsed'].dt.to_period('M').astype(str)
        cus_mensal = df_cus.groupby('mes')['valor'].sum().reset_index()
        cus_mensal.columns = ['Mês', 'Custos']

    if not fat_mensal.empty or not cus_mensal.empty:
        if not fat_mensal.empty and not cus_mensal.empty:
            df_mensal = pd.merge(fat_mensal, cus_mensal, on='Mês', how='outer').fillna(0)
        elif not fat_mensal.empty:
            df_mensal = fat_mensal.copy()
            df_mensal['Custos'] = 0
        else:
            df_mensal = cus_mensal.copy()
            df_mensal['Faturamento'] = 0

        df_mensal = df_mensal.sort_values('Mês')

        fig_barras = go.Figure()
        fig_barras.add_trace(go.Bar(
            x=df_mensal['Mês'], y=df_mensal['Faturamento'],
            name='Faturamento', marker_color=COR_AZUL,
            hovertemplate='<b>Faturamento</b><br>%{x}<br>R$ %{y:,.2f}<extra></extra>',
        ))
        fig_barras.add_trace(go.Bar(
            x=df_mensal['Mês'], y=df_mensal['Custos'],
            name='Custos', marker_color=COR_LARANJA,
            hovertemplate='<b>Custos</b><br>%{x}<br>R$ %{y:,.2f}<extra></extra>',
        ))
        fig_barras.update_layout(
            **_PLOTLY_LAYOUT,
            barmode='group',
            title=dict(text='Faturamento vs Custos Mensal', font=dict(size=16, color=COR_AZUL)),
            xaxis_title='Mês',
            yaxis_title='Valor (R$)',
            yaxis=dict(tickformat=',.0f', tickprefix='R$ '),
        )
        st.plotly_chart(fig_barras, use_container_width=True)

        # Tabela resumo mensal
        with st.expander("📋 Tabela Resumo Mensal"):
            df_mensal['Lucro'] = df_mensal['Faturamento'] - df_mensal['Custos']
            df_mensal_show = df_mensal.copy()
            for col in ['Faturamento', 'Custos', 'Lucro']:
                df_mensal_show[col] = df_mensal_show[col].apply(lambda x: f"R$ {x:,.2f}")
            st.dataframe(df_mensal_show, use_container_width=True, hide_index=True)
    else:
        st.info("Sem dados suficientes para gráfico mensal.")

    st.markdown("---")

    # ════════════════════════════════════════════════════════
    # 3) GRÁFICO DE LINHA — Tendência de Lucro Mensal (últimos 6 meses)
    # ════════════════════════════════════════════════════════
    st.markdown("##### 📈 Tendência de Lucro Mensal (Últimos 6 Meses)")

    # Gerar lista dos últimos 6 meses a partir de hoje
    hoje = date.today()
    meses_6 = []
    for i in range(5, -1, -1):
        d = date(hoje.year, hoje.month, 1) - timedelta(days=i * 30)
        meses_6.append(d.strftime("%Y-%m"))
    meses_6 = sorted(list(set(meses_6)))[-6:]

    df_lucro_6m = pd.DataFrame({'Mês': meses_6})
    df_lucro_6m['Faturamento'] = 0.0
    df_lucro_6m['Custos'] = 0.0

    if not df_fat.empty:
        df_fat_6 = df_fat[df_fat['mes'].isin(meses_6)].groupby('mes')['valor'].sum()
        for m in meses_6:
            if m in df_fat_6.index:
                df_lucro_6m.loc[df_lucro_6m['Mês'] == m, 'Faturamento'] = df_fat_6[m]

    if not df_cus.empty:
        df_cus_6 = df_cus[df_cus['mes'].isin(meses_6)].groupby('mes')['valor'].sum()
        for m in meses_6:
            if m in df_cus_6.index:
                df_lucro_6m.loc[df_lucro_6m['Mês'] == m, 'Custos'] = df_cus_6[m]

    df_lucro_6m['Lucro'] = df_lucro_6m['Faturamento'] - df_lucro_6m['Custos']

    # Cores para a linha de lucro: verde se positivo, vermelho se negativo
    cores_lucro = [COR_VERDE if v >= 0 else COR_VERMELHO for v in df_lucro_6m['Lucro']]

    fig_lucro = go.Figure()
    fig_lucro.add_trace(go.Scatter(
        x=df_lucro_6m['Mês'], y=df_lucro_6m['Lucro'],
        mode='lines+markers+text',
        name='Lucro',
        line=dict(color=COR_AZUL, width=3),
        marker=dict(size=10, color=cores_lucro, line=dict(width=2, color='white')),
        text=[f"R$ {v:,.0f}" for v in df_lucro_6m['Lucro']],
        textposition='top center',
        textfont=dict(size=11, color=COR_AZUL),
        hovertemplate='<b>%{x}</b><br>Lucro: R$ %{y:,.2f}<extra></extra>',
    ))
    # Linha zero de referência
    fig_lucro.add_hline(y=0, line_dash="dash", line_color="rgba(0,0,0,0.2)", line_width=1)
    fig_lucro.update_layout(
        **_PLOTLY_LAYOUT,
        title=dict(text='Tendência de Lucro — Últimos 6 Meses', font=dict(size=16, color=COR_AZUL)),
        xaxis_title='Mês',
        yaxis_title='Lucro (R$)',
        yaxis=dict(tickformat=',.0f', tickprefix='R$ '),
        showlegend=False,
    )
    st.plotly_chart(fig_lucro, use_container_width=True)

    st.markdown("---")

    # ════════════════════════════════════════════════════════
    # 4) GRÁFICOS ADICIONAIS
    # ════════════════════════════════════════════════════════
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.markdown("##### 📈 Faturamento por Região")
        if not df_fat.empty and 'regiao' in df_fat.columns:
            fat_regiao = df_fat.groupby('regiao')['valor'].sum().reset_index()
            fat_regiao.columns = ['Região', 'Valor']
            fat_regiao = fat_regiao.sort_values('Valor', ascending=True)
            fig_reg = px.bar(
                fat_regiao, x='Valor', y='Região', orientation='h',
                color_discrete_sequence=[COR_AZUL],
                text=fat_regiao['Valor'].apply(lambda x: f"R$ {x:,.0f}"),
            )
            fig_reg.update_layout(
                **_PLOTLY_LAYOUT,
                xaxis=dict(tickformat=',.0f', tickprefix='R$ '),
                yaxis_title='', xaxis_title='',
                height=max(250, len(fat_regiao) * 45 + 80),
            )
            fig_reg.update_traces(textposition='outside', hovertemplate='<b>%{y}</b><br>R$ %{x:,.2f}<extra></extra>')
            st.plotly_chart(fig_reg, use_container_width=True)
        else:
            st.info("Sem dados de faturamento no período.")

    with col_g2:
        st.markdown("##### 🚗 Faturamento por Veículo")
        if not df_fat.empty and 'veiculo' in df_fat.columns:
            fat_veic = df_fat.groupby('veiculo')['valor'].agg(['sum', 'count']).reset_index()
            fat_veic.columns = ['Veículo', 'Valor', 'Entregas']
            fig_veic = px.pie(
                fat_veic, values='Valor', names='Veículo',
                color_discrete_sequence=[COR_AZUL, COR_LARANJA, COR_VERDE, COR_VERMELHO],
                hole=0.35,
            )
            fig_veic.update_traces(
                textinfo='label+percent',
                hovertemplate='<b>%{label}</b><br>R$ %{value:,.2f}<br>%{percent}<extra></extra>',
            )
            fig_veic.update_layout(**_PLOTLY_LAYOUT, height=300, showlegend=True)
            st.plotly_chart(fig_veic, use_container_width=True)

            # Tabela resumo
            fat_veic_show = fat_veic.copy()
            fat_veic_show['Valor'] = fat_veic_show['Valor'].apply(lambda x: f"R$ {x:,.2f}")
            st.dataframe(fat_veic_show, use_container_width=True, hide_index=True)
        else:
            st.info("Sem dados de faturamento por veículo.")

    # ── Faturamento por Cliente ─────────────────────────────
    if not df_fat.empty and 'cliente' in df_fat.columns:
        clientes_com_dados = df_fat[df_fat['cliente'].str.strip() != '']
        if not clientes_com_dados.empty:
            st.markdown("---")
            st.markdown("##### 🏢 Faturamento por Cliente")
            fat_cliente = clientes_com_dados.groupby('cliente')['valor'].agg(['sum', 'count']).reset_index()
            fat_cliente.columns = ['Cliente', 'Valor Total', 'Entregas']
            fat_cliente = fat_cliente.sort_values('Valor Total', ascending=False)

            fig_cli = px.bar(
                fat_cliente.head(10), x='Cliente', y='Valor Total',
                color_discrete_sequence=[COR_LARANJA],
                text=fat_cliente.head(10)['Valor Total'].apply(lambda x: f"R$ {x:,.0f}"),
            )
            fig_cli.update_layout(
                **_PLOTLY_LAYOUT,
                xaxis_title='', yaxis_title='Valor (R$)',
                yaxis=dict(tickformat=',.0f', tickprefix='R$ '),
            )
            fig_cli.update_traces(textposition='outside', hovertemplate='<b>%{x}</b><br>R$ %{y:,.2f}<extra></extra>')
            st.plotly_chart(fig_cli, use_container_width=True)

            with st.expander(f"📋 Tabela completa — {len(fat_cliente)} clientes"):
                fat_cliente_d = fat_cliente.copy()
                fat_cliente_d['Valor Total'] = fat_cliente_d['Valor Total'].apply(lambda x: f"R$ {x:,.2f}")
                st.dataframe(fat_cliente_d, use_container_width=True, hide_index=True)
                st.markdown(f"**Total: R$ {clientes_com_dados['valor'].sum():,.2f}**")
