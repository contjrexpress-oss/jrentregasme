import streamlit as st
import pandas as pd
from datetime import datetime

from styles import page_header, metric_card
import database
from utils import (
    validar_cpf_cnpj, formatar_cpf_cnpj, formatar_telefone,
    formatar_cep_display, buscar_cep
)


def render():
    """Renderiza o módulo de Cadastro de Clientes."""
    st.markdown(
        page_header("👥 Cadastros", "Gerenciamento de clientes e parceiros"),
        unsafe_allow_html=True
    )

    tab_cadastrar, tab_lista, tab_editar = st.tabs([
        "📝 Cadastrar Cliente",
        "📋 Lista de Clientes",
        "✏️ Editar / Gerenciar"
    ])

    with tab_cadastrar:
        _render_cadastrar_cliente()
    with tab_lista:
        _render_lista_clientes()
    with tab_editar:
        _render_editar_cliente()


def _render_cadastrar_cliente():
    """Formulário de cadastro de novo cliente."""
    st.markdown("#### 📝 Novo Cliente")
    st.caption("Preencha os dados do cliente. Campos com * são obrigatórios.")

    with st.form("form_novo_cliente", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome / Razão Social *", placeholder="Ex: Bar Baixo Horto Ltda")
            cpf_cnpj = st.text_input("CPF / CNPJ", placeholder="Ex: 11.538.414/0001-95 ou 123.456.789-00")
            telefone = st.text_input("Telefone", placeholder="Ex: (21) 97258-0043")
            email = st.text_input("E-mail", placeholder="Ex: contato@empresa.com")
        
        with col2:
            endereco = st.text_input("Endereço", placeholder="Ex: Rua Pacheco Leão, 780")
            cep_input = st.text_input("CEP", placeholder="Ex: 22460-030")
            
            # Busca automática de CEP
            bairro = st.text_input("Bairro", placeholder="Preenchido automaticamente pelo CEP")
            cidade = st.text_input("Cidade", placeholder="Preenchido automaticamente pelo CEP")
        
        observacoes = st.text_area("Observações", placeholder="Informações adicionais sobre o cliente...", height=80)

        col_btn1, col_btn2 = st.columns([1, 3])
        with col_btn1:
            submitted = st.form_submit_button("💾 Cadastrar Cliente", use_container_width=True, type="primary")

        if submitted:
            # Validações
            if not nome or not nome.strip():
                st.error("❌ Nome é obrigatório!")
                return
            
            # Validar CPF/CNPJ se informado
            if cpf_cnpj and cpf_cnpj.strip():
                ok, msg, tipo = validar_cpf_cnpj(cpf_cnpj)
                if not ok:
                    st.error(f"❌ {msg}")
                    return
            
            # Buscar bairro/cidade pelo CEP se não informados
            bairro_final = bairro
            cidade_final = cidade
            if cep_input and (not bairro or not cidade):
                b, c = buscar_cep(cep_input)
                if b and not bairro:
                    bairro_final = b
                if c and not cidade:
                    cidade_final = c
            
            sucesso, mensagem, cliente_id = database.inserir_cliente(
                nome=nome,
                cpf_cnpj=cpf_cnpj,
                telefone=telefone,
                email=email,
                endereco=endereco,
                bairro=bairro_final,
                cidade=cidade_final,
                cep=cep_input,
                observacoes=observacoes
            )
            
            if sucesso:
                st.success(f"✅ {mensagem} (ID: {cliente_id})")
                st.balloons()
            else:
                st.error(f"❌ {mensagem}")

    # Busca rápida de CEP fora do formulário
    st.markdown("---")
    st.markdown("##### 🔍 Consultar CEP")
    col_cep1, col_cep2 = st.columns([1, 2])
    with col_cep1:
        cep_consulta = st.text_input("Digite o CEP para consulta", placeholder="XXXXX-XXX", key="cep_consulta")
    with col_cep2:
        if cep_consulta and len(cep_consulta.replace("-", "").replace(".", "").strip()) >= 8:
            bairro_r, cidade_r = buscar_cep(cep_consulta)
            if bairro_r or cidade_r:
                st.info(f"📍 **Bairro:** {bairro_r or 'N/A'} | **Cidade:** {cidade_r or 'N/A'}")
            else:
                st.warning("CEP não encontrado na base do ViaCEP.")


def _render_lista_clientes():
    """Lista todos os clientes com filtros e busca."""
    st.markdown("#### 📋 Clientes Cadastrados")

    # Métricas
    stats = database.contar_clientes()
    cols = st.columns(3)
    with cols[0]:
        st.markdown(metric_card("Total de Clientes", stats['total'], "metric-blue"), unsafe_allow_html=True)
    with cols[1]:
        st.markdown(metric_card("Ativos", stats['ativos'], "metric-green"), unsafe_allow_html=True)
    with cols[2]:
        st.markdown(metric_card("Inativos", stats['inativos'], "metric-red"), unsafe_allow_html=True)
    
    st.markdown("")
    
    # Filtros
    col_f1, col_f2, col_f3 = st.columns([2, 1, 1])
    with col_f1:
        busca = st.text_input("🔍 Buscar cliente", placeholder="Nome, CPF/CNPJ, email ou telefone...", key="busca_lista")
    with col_f2:
        filtro_status = st.selectbox("Status", ["Ativos", "Todos", "Inativos"], key="filtro_status_lista")
    with col_f3:
        ordenar = st.selectbox("Ordenar por", ["Nome", "Data Cadastro", "Cidade"], key="ordenar_lista")

    apenas_ativos = filtro_status == "Ativos"
    if filtro_status == "Inativos":
        apenas_ativos = None  # buscar todos e filtrar depois

    clientes = database.obter_clientes(
        apenas_ativos=(filtro_status != "Todos" and filtro_status != "Inativos"),
        busca=busca
    )

    # Filtrar inativos se necessário
    if filtro_status == "Inativos":
        clientes_all = database.obter_clientes(apenas_ativos=False, busca=busca)
        clientes = [c for c in clientes_all if not c['ativo']]
    elif filtro_status == "Todos":
        clientes = database.obter_clientes(apenas_ativos=False, busca=busca)

    if not clientes:
        st.info("ℹ️ Nenhum cliente encontrado.")
        return

    # Preparar DataFrame para exibição
    df_data = []
    for c in clientes:
        df_data.append({
            'ID': c['id'],
            'Nome': c['nome'],
            'CPF/CNPJ': formatar_cpf_cnpj(c['cpf_cnpj']),
            'Telefone': formatar_telefone(c['telefone']),
            'E-mail': c['email'] or '',
            'Bairro': c['bairro'] or '',
            'Cidade': c['cidade'] or '',
            'CEP': formatar_cep_display(c['cep']),
            'Status': '✅ Ativo' if c['ativo'] else '❌ Inativo',
            'Cadastro': c['data_cadastro'][:10] if c['data_cadastro'] else ''
        })
    
    df = pd.DataFrame(df_data)
    
    # Ordenação
    if ordenar == "Data Cadastro":
        df = df.sort_values('Cadastro', ascending=False)
    elif ordenar == "Cidade":
        df = df.sort_values('Cidade')
    else:
        df = df.sort_values('Nome')

    st.markdown(f"**{len(df)} cliente(s) encontrado(s)**")
    
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            'ID': st.column_config.NumberColumn('ID', width='small'),
            'Nome': st.column_config.TextColumn('Nome', width='large'),
            'CPF/CNPJ': st.column_config.TextColumn('CPF/CNPJ', width='medium'),
            'Telefone': st.column_config.TextColumn('Telefone', width='medium'),
            'E-mail': st.column_config.TextColumn('E-mail', width='medium'),
            'Status': st.column_config.TextColumn('Status', width='small'),
        }
    )

    # Exportar para Excel
    if st.button("📥 Exportar para Excel", key="export_clientes"):
        import io
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False, sheet_name="Clientes")
        buffer.seek(0)
        st.download_button(
            "⬇️ Download Excel",
            data=buffer,
            file_name=f"clientes_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_clientes"
        )


def _render_editar_cliente():
    """Interface para editar e gerenciar clientes."""
    st.markdown("#### ✏️ Editar / Gerenciar Cliente")

    # Seleção de cliente com autocomplete
    clientes = database.obter_clientes(apenas_ativos=False)
    if not clientes:
        st.info("ℹ️ Nenhum cliente cadastrado ainda.")
        return

    # Criar opções formatadas para selectbox
    opcoes = ["Selecione um cliente..."]
    cliente_map = {}
    for c in clientes:
        doc = formatar_cpf_cnpj(c['cpf_cnpj']) if c['cpf_cnpj'] else "Sem documento"
        status = "✅" if c['ativo'] else "❌"
        label = f"{status} {c['nome']} — {doc}"
        opcoes.append(label)
        cliente_map[label] = c['id']

    selecionado = st.selectbox(
        "🔍 Buscar e selecionar cliente",
        opcoes,
        key="select_editar_cliente"
    )

    if selecionado == "Selecione um cliente...":
        st.caption("Selecione um cliente acima para editar seus dados.")
        return

    cliente_id = cliente_map[selecionado]
    cliente = database.buscar_cliente_por_id(cliente_id)
    if not cliente:
        st.error("Cliente não encontrado.")
        return

    # Exibir dados atuais em card
    st.markdown("---")
    st.markdown(f"##### 📄 Dados do Cliente: **{cliente['nome']}**")
    
    col_info1, col_info2, col_info3 = st.columns(3)
    with col_info1:
        st.markdown(f"**CPF/CNPJ:** {formatar_cpf_cnpj(cliente['cpf_cnpj']) or 'Não informado'}")
        st.markdown(f"**Telefone:** {formatar_telefone(cliente['telefone']) or 'Não informado'}")
    with col_info2:
        st.markdown(f"**E-mail:** {cliente['email'] or 'Não informado'}")
        st.markdown(f"**CEP:** {formatar_cep_display(cliente['cep']) or 'Não informado'}")
    with col_info3:
        st.markdown(f"**Bairro:** {cliente['bairro'] or 'Não informado'}")
        st.markdown(f"**Cidade:** {cliente['cidade'] or 'Não informado'}")

    st.markdown("---")

    # Formulário de edição
    with st.form(f"form_editar_{cliente_id}"):
        st.markdown("##### ✏️ Editar Dados")
        col1, col2 = st.columns(2)
        with col1:
            novo_nome = st.text_input("Nome / Razão Social *", value=cliente['nome'])
            novo_cpf_cnpj = st.text_input("CPF / CNPJ", value=formatar_cpf_cnpj(cliente['cpf_cnpj']))
            novo_telefone = st.text_input("Telefone", value=cliente['telefone'] or '')
            novo_email = st.text_input("E-mail", value=cliente['email'] or '')
        with col2:
            novo_endereco = st.text_input("Endereço", value=cliente['endereco'] or '')
            novo_cep = st.text_input("CEP", value=formatar_cep_display(cliente['cep']) or '')
            novo_bairro = st.text_input("Bairro", value=cliente['bairro'] or '')
            nova_cidade = st.text_input("Cidade", value=cliente['cidade'] or '')
        
        novas_obs = st.text_area("Observações", value=cliente['observacoes'] or '', height=80)

        col_btn1, col_btn2, col_btn3 = st.columns(3)
        with col_btn1:
            salvar = st.form_submit_button("💾 Salvar Alterações", use_container_width=True, type="primary")
        with col_btn2:
            if cliente['ativo']:
                desativar = st.form_submit_button("🚫 Desativar Cliente", use_container_width=True)
            else:
                desativar = st.form_submit_button("✅ Reativar Cliente", use_container_width=True)

        if salvar:
            if not novo_nome or not novo_nome.strip():
                st.error("❌ Nome é obrigatório!")
                return
            
            # Validar CPF/CNPJ se informado
            if novo_cpf_cnpj and novo_cpf_cnpj.strip():
                ok, msg, tipo = validar_cpf_cnpj(novo_cpf_cnpj)
                if not ok:
                    st.error(f"❌ {msg}")
                    return

            # Buscar bairro/cidade pelo CEP se necessário
            bairro_f = novo_bairro
            cidade_f = nova_cidade
            if novo_cep and (not novo_bairro or not nova_cidade):
                b, c = buscar_cep(novo_cep)
                if b and not novo_bairro:
                    bairro_f = b
                if c and not nova_cidade:
                    cidade_f = c

            sucesso, mensagem = database.atualizar_cliente(
                cliente_id,
                nome=novo_nome,
                cpf_cnpj=novo_cpf_cnpj,
                telefone=novo_telefone,
                email=novo_email,
                endereco=novo_endereco,
                cep=novo_cep,
                bairro=bairro_f,
                cidade=cidade_f,
                observacoes=novas_obs
            )
            if sucesso:
                st.success(f"✅ {mensagem}")
                st.rerun()
            else:
                st.error(f"❌ {mensagem}")

        if desativar:
            if cliente['ativo']:
                sucesso, msg = database.deletar_cliente(cliente_id)
                if sucesso:
                    st.warning("⚠️ Cliente desativado com sucesso.")
                    st.rerun()
            else:
                sucesso, msg = database.reativar_cliente(cliente_id)
                if sucesso:
                    st.success("✅ Cliente reativado com sucesso.")
                    st.rerun()


# ============ FUNÇÕES AUXILIARES PARA AUTOCOMPLETE ============

def selecionar_cliente_autocomplete(key_prefix="", label="🔍 Cliente"):
    """Componente reutilizável de seleção de cliente com busca.
    Retorna o ID do cliente selecionado ou None.
    Pode ser usado em outros módulos (faturamento, custos, etc.)
    """
    clientes = database.obter_clientes(apenas_ativos=True)
    
    if not clientes:
        st.caption("Nenhum cliente cadastrado.")
        return None, ""
    
    # Criar opções formatadas
    opcoes = ["(Nenhum / Digitar manualmente)"]
    cliente_map = {}
    for c in clientes:
        doc = formatar_cpf_cnpj(c['cpf_cnpj']) if c['cpf_cnpj'] else ""
        local = f" — {c['bairro']}" if c['bairro'] else ""
        label_txt = f"{c['nome']}{' | ' + doc if doc else ''}{local}"
        opcoes.append(label_txt)
        cliente_map[label_txt] = c

    selecionado = st.selectbox(
        label,
        opcoes,
        key=f"{key_prefix}_autocomplete_cliente"
    )
    
    if selecionado == "(Nenhum / Digitar manualmente)":
        return None, ""
    
    cliente = cliente_map.get(selecionado)
    if cliente:
        return cliente['id'], cliente['nome']
    return None, ""


def cadastro_rapido_cliente(key_prefix=""):
    """Mini formulário para cadastro rápido de cliente inline.
    Retorna (cliente_id, nome) se cadastrado, (None, '') caso contrário.
    """
    with st.expander("➕ Cadastrar Novo Cliente Rapidamente", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            nome_rap = st.text_input("Nome *", key=f"{key_prefix}_nome_rapido", placeholder="Nome do cliente")
            cpf_rap = st.text_input("CPF/CNPJ", key=f"{key_prefix}_cpf_rapido", placeholder="Opcional")
        with col2:
            tel_rap = st.text_input("Telefone", key=f"{key_prefix}_tel_rapido", placeholder="Opcional")
            email_rap = st.text_input("E-mail", key=f"{key_prefix}_email_rapido", placeholder="Opcional")
        
        if st.button("💾 Cadastrar", key=f"{key_prefix}_btn_rapido", type="primary"):
            if not nome_rap or not nome_rap.strip():
                st.error("❌ Nome é obrigatório!")
                return None, ""
            
            if cpf_rap:
                ok, msg, tipo = validar_cpf_cnpj(cpf_rap)
                if not ok:
                    st.error(f"❌ {msg}")
                    return None, ""
            
            sucesso, mensagem, cliente_id = database.inserir_cliente(
                nome=nome_rap, cpf_cnpj=cpf_rap, telefone=tel_rap, email=email_rap
            )
            if sucesso:
                st.success(f"✅ {mensagem}")
                st.rerun()
                return cliente_id, nome_rap
            else:
                st.error(f"❌ {mensagem}")
    
    return None, ""
