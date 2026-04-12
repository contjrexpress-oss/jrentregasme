import streamlit as st
import pandas as pd
import re
from datetime import datetime

from styles import page_header, metric_card
import database
from utils import (
    validar_cpf_cnpj, formatar_cpf_cnpj, formatar_telefone,
    formatar_cep_display, buscar_cep, validar_email,
    validar_cliente_importacao, COLUNAS_TEMPLATE_CLIENTES,
    extrair_clientes_csv, extrair_clientes_xlsx,
    extrair_clientes_pdf, extrair_clientes_imagem
)


def render():
    """Renderiza o módulo de Cadastro de Clientes."""
    from auth import verificar_acesso
    if not verificar_acesso('cadastros'):
        return
    st.markdown(
        page_header("👥 Cadastros", "Gerenciamento de clientes e parceiros"),
        unsafe_allow_html=True
    )

    tab_cadastrar, tab_lista, tab_editar, tab_importacao = st.tabs([
        "📝 Cadastrar Cliente",
        "📋 Lista de Clientes",
        "✏️ Editar / Gerenciar",
        "📤 Importação em Lote"
    ])

    with tab_cadastrar:
        _render_cadastrar_cliente()
    with tab_lista:
        _render_lista_clientes()
    with tab_editar:
        _render_editar_cliente()
    with tab_importacao:
        _render_importacao_lote()


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

        from auth import pode_excluir
        if desativar:
            if not pode_excluir():
                st.warning("🔒 Apenas administradores podem desativar/reativar clientes.")
            elif cliente['ativo']:
                sucesso, msg = database.deletar_cliente(cliente_id)
                if sucesso:
                    st.warning("⚠️ Cliente desativado com sucesso.")
                    st.rerun()
            else:
                sucesso, msg = database.reativar_cliente(cliente_id)
                if sucesso:
                    st.success("✅ Cliente reativado com sucesso.")
                    st.rerun()


# ============ IMPORTAÇÃO EM LOTE ============

def _render_importacao_lote():
    """Interface para importação em lote de clientes a partir de arquivos."""
    st.markdown("#### 📤 Importação em Lote de Clientes")
    st.caption("Importe clientes a partir de arquivos CSV, Excel, PDF ou Imagem.")

    # ── Template download ──
    col_tpl1, col_tpl2 = st.columns([1, 3])
    with col_tpl1:
        template_df = pd.DataFrame(columns=COLUNAS_TEMPLATE_CLIENTES)
        csv_template = template_df.to_csv(index=False)
        st.download_button(
            "📄 Baixar Template CSV",
            csv_template,
            "template_clientes.csv",
            "text/csv",
            key="download_template_clientes"
        )
    with col_tpl2:
        st.info(
            "💡 **Dica:** Baixe o template acima para preencher seus dados no formato correto. "
            "Colunas obrigatórias: **NOME**. Demais colunas são opcionais."
        )

    st.markdown("---")

    # ── Upload de arquivo ──
    col_up1, col_up2 = st.columns([1, 2])
    with col_up1:
        formato = st.selectbox(
            "📁 Formato do arquivo",
            ["CSV", "XLSX (Excel)", "PDF", "Imagem (OCR)"],
            key="formato_importacao_clientes"
        )
    
    # Mapear tipos aceitos
    tipos_map = {
        "CSV": ["csv"],
        "XLSX (Excel)": ["xlsx", "xls"],
        "PDF": ["pdf"],
        "Imagem (OCR)": ["png", "jpg", "jpeg", "bmp", "tiff"]
    }
    tipos_aceitos = tipos_map[formato]

    with col_up2:
        arquivo = st.file_uploader(
            "Selecione o arquivo",
            type=tipos_aceitos,
            key="upload_importacao_clientes"
        )

    if not arquivo:
        st.caption("Selecione um arquivo acima para iniciar a importação.")
        return

    # ── Processar arquivo ──
    dados = []
    erro_msg = ""

    with st.spinner("📊 Processando arquivo..."):
        if formato == "CSV":
            dados, erro_msg = extrair_clientes_csv(arquivo)
        elif formato == "XLSX (Excel)":
            dados, erro_msg = extrair_clientes_xlsx(arquivo)
        elif formato == "PDF":
            dados, erro_msg = extrair_clientes_pdf(arquivo)
        else:  # Imagem
            dados, erro_msg = extrair_clientes_imagem(arquivo)

    if erro_msg:
        st.error(f"❌ {erro_msg}")
        return

    if not dados:
        st.warning("⚠️ Nenhum dado de cliente encontrado no arquivo.")
        return

    st.success(f"✅ **{len(dados)}** cliente(s) encontrado(s) no arquivo.")

    # ── Preview e Edição ──
    st.markdown("---")
    st.markdown("##### 📋 Preview e Edição dos Dados")
    st.caption("Edite os dados abaixo antes de importar. Você pode adicionar ou remover linhas.")

    df_preview = pd.DataFrame(dados)
    
    # Garantir todas as colunas
    for col in COLUNAS_TEMPLATE_CLIENTES:
        if col not in df_preview.columns:
            df_preview[col] = ''

    df_preview = df_preview[COLUNAS_TEMPLATE_CLIENTES]

    # Data editor para edição interativa
    df_editado = st.data_editor(
        df_preview,
        num_rows="dynamic",
        use_container_width=True,
        key="editor_importacao_clientes",
        column_config={
            "NOME": st.column_config.TextColumn("Nome *", required=True, width="large"),
            "RAZAO_SOCIAL": st.column_config.TextColumn("Razão Social", width="large"),
            "EMAIL": st.column_config.TextColumn("E-mail", width="medium"),
            "SOURCE": st.column_config.TextColumn("Origem", width="small"),
            "TELEFONE": st.column_config.TextColumn("Telefone", width="medium"),
            "CNPJ": st.column_config.TextColumn("CNPJ", width="medium"),
            "CPF": st.column_config.TextColumn("CPF", width="medium"),
            "CEP": st.column_config.TextColumn("CEP", width="small"),
            "CIDADE": st.column_config.TextColumn("Cidade", width="medium"),
            "BAIRRO": st.column_config.TextColumn("Bairro", width="medium"),
            "NUMERO": st.column_config.TextColumn("Número", width="small"),
            "ESTADO": st.column_config.TextColumn("UF", width="small"),
            "RUA": st.column_config.TextColumn("Rua/Endereço", width="large"),
            "COMPLEMENTO": st.column_config.TextColumn("Complemento", width="medium"),
        }
    )

    st.markdown("---")

    # ── Validação ──
    col_val1, col_val2, col_val3 = st.columns(3)

    with col_val1:
        btn_validar = st.button("🔍 Validar Dados", use_container_width=True, key="btn_validar_importacao")
    with col_val2:
        btn_buscar_cep = st.button("📍 Autocompletar CEPs", use_container_width=True, key="btn_cep_importacao")
    with col_val3:
        btn_importar = st.button(
            "✅ Importar Clientes",
            use_container_width=True,
            type="primary",
            key="btn_importar_clientes"
        )

    # Autocompletar CEPs via ViaCEP
    if btn_buscar_cep:
        _processar_autocomplete_cep(df_editado)

    # Validar dados
    if btn_validar:
        _processar_validacao(df_editado)

    # Importar clientes
    if btn_importar:
        _processar_importacao(df_editado)


def _processar_autocomplete_cep(df_editado: pd.DataFrame):
    """Busca endereço automaticamente via ViaCEP para linhas com CEP preenchido."""
    atualizados = 0
    erros_cep = 0

    with st.spinner("📍 Buscando endereços via ViaCEP..."):
        for idx, row in df_editado.iterrows():
            cep = str(row.get('CEP', '') or '').strip()
            if not cep:
                continue
            
            cep_limpo = re.sub(r'\D', '', cep)
            if len(cep_limpo) != 8:
                continue
            
            bairro_api, cidade_api = buscar_cep(cep_limpo)
            if bairro_api or cidade_api:
                info_parts = []
                if bairro_api:
                    info_parts.append(f"Bairro: {bairro_api}")
                if cidade_api:
                    info_parts.append(f"Cidade: {cidade_api}")
                st.caption(f"📍 CEP {cep}: {' | '.join(info_parts)}")
                atualizados += 1
            else:
                erros_cep += 1

    if atualizados > 0:
        st.success(f"✅ {atualizados} CEP(s) encontrado(s). Os dados aparecem acima para referência.")
        st.info(
            "💡 **Dica:** Edite manualmente a tabela acima para preencher Bairro, Cidade e Estado "
            "com base nos resultados da consulta."
        )
    if erros_cep > 0:
        st.warning(f"⚠️ {erros_cep} CEP(s) não encontrado(s) no ViaCEP.")
    if atualizados == 0 and erros_cep == 0:
        st.info("ℹ️ Nenhuma linha com CEP preenchido para consultar.")


def _processar_validacao(df_editado: pd.DataFrame):
    """Valida todos os dados da tabela e mostra resultados."""
    resultados = []
    
    for idx, row in df_editado.iterrows():
        row_dict = row.to_dict()
        # Pular linhas completamente vazias
        if all(not str(v).strip() for v in row_dict.values()):
            continue
        valido, erros = validar_cliente_importacao(row_dict)
        resultados.append({
            'linha': idx + 1,
            'nome': str(row_dict.get('NOME', '') or '').strip(),
            'valido': valido,
            'erros': erros
        })

    if not resultados:
        st.info("ℹ️ Nenhum dado para validar.")
        return

    validos = [r for r in resultados if r['valido']]
    invalidos = [r for r in resultados if not r['valido']]

    col_r1, col_r2 = st.columns(2)
    with col_r1:
        st.markdown(metric_card("Válidos", f"{len(validos)}", "metric-green"), unsafe_allow_html=True)
    with col_r2:
        st.markdown(metric_card("Com Erros", f"{len(invalidos)}", "metric-red"), unsafe_allow_html=True)

    if invalidos:
        st.markdown("##### ❌ Detalhes dos Erros")
        for r in invalidos:
            nome_display = r['nome'] or f"(Linha {r['linha']})"
            with st.expander(f"⚠️ Linha {r['linha']}: {nome_display}", expanded=False):
                for erro in r['erros']:
                    st.error(f"• {erro}")
    
    if validos and not invalidos:
        st.success("🎉 Todos os dados estão válidos! Clique em **Importar Clientes** para prosseguir.")
    elif validos:
        st.warning(
            f"⚠️ {len(validos)} cliente(s) válido(s) e {len(invalidos)} com erros. "
            "Corrija os erros na tabela acima ou importe apenas os válidos."
        )


def _processar_importacao(df_editado: pd.DataFrame):
    """Processa a importação de clientes para o banco de dados."""
    from auth import get_username

    # Coletar linhas não-vazias
    linhas_para_importar = []
    for idx, row in df_editado.iterrows():
        row_dict = row.to_dict()
        if all(not str(v).strip() for v in row_dict.values()):
            continue
        linhas_para_importar.append((idx, row_dict))

    if not linhas_para_importar:
        st.warning("⚠️ Nenhum dado para importar.")
        return

    # Confirmar importação
    total = len(linhas_para_importar)
    st.warning(f"⚡ Serão importados até **{total}** cliente(s). Apenas os válidos serão inseridos.")

    sucessos = 0
    erros_importacao = 0
    erros_detalhes = []
    duplicatas = 0

    progress_bar = st.progress(0, text="Importando clientes...")
    
    for i, (idx, row_dict) in enumerate(linhas_para_importar):
        progress_bar.progress((i + 1) / total, text=f"Importando {i + 1}/{total}...")
        
        # Validar
        valido, erros = validar_cliente_importacao(row_dict)
        if not valido:
            erros_importacao += 1
            nome = str(row_dict.get('NOME', '') or '').strip()
            erros_detalhes.append(f"Linha {idx + 1} ({nome}): {'; '.join(erros)}")
            continue

        # Montar dados para inserção
        nome = str(row_dict.get('NOME', '') or '').strip()
        razao_social = str(row_dict.get('RAZAO_SOCIAL', '') or '').strip()
        nome_final = razao_social if razao_social else nome

        cnpj = str(row_dict.get('CNPJ', '') or '').strip()
        cpf = str(row_dict.get('CPF', '') or '').strip()
        documento = cnpj or cpf

        email = str(row_dict.get('EMAIL', '') or '').strip()
        telefone = str(row_dict.get('TELEFONE', '') or '').strip()
        cep = str(row_dict.get('CEP', '') or '').strip()
        cidade = str(row_dict.get('CIDADE', '') or '').strip()
        bairro = str(row_dict.get('BAIRRO', '') or '').strip()
        estado = str(row_dict.get('ESTADO', '') or '').strip()
        rua = str(row_dict.get('RUA', '') or '').strip()
        numero = str(row_dict.get('NUMERO', '') or '').strip()
        complemento = str(row_dict.get('COMPLEMENTO', '') or '').strip()
        source = str(row_dict.get('SOURCE', '') or '').strip()

        # Montar endereço completo
        endereco_parts = [rua]
        if numero:
            endereco_parts.append(numero)
        if complemento:
            endereco_parts.append(complemento)
        endereco = ', '.join([p for p in endereco_parts if p])

        # Autocompletar via CEP se bairro/cidade não informados
        if cep and (not bairro or not cidade):
            b, c = buscar_cep(cep)
            if b and not bairro:
                bairro = b
            if c and not cidade:
                cidade = c

        # Montar observações
        obs_parts = []
        if source:
            obs_parts.append(f"Origem: {source}")
        if estado:
            obs_parts.append(f"UF: {estado}")
        if razao_social and nome and razao_social != nome:
            obs_parts.append(f"Nome fantasia: {nome}")
        observacoes = ' | '.join(obs_parts)

        # Inserir no banco
        try:
            sucesso, mensagem, cliente_id = database.inserir_cliente(
                nome=nome_final,
                cpf_cnpj=documento,
                telefone=telefone,
                email=email,
                endereco=endereco,
                bairro=bairro,
                cidade=cidade,
                cep=cep,
                observacoes=observacoes
            )
            if sucesso:
                sucessos += 1
            else:
                if "já cadastrado" in mensagem.lower():
                    duplicatas += 1
                else:
                    erros_importacao += 1
                erros_detalhes.append(f"Linha {idx + 1} ({nome_final}): {mensagem}")
        except Exception as e:
            erros_importacao += 1
            erros_detalhes.append(f"Linha {idx + 1} ({nome_final}): {str(e)}")

    progress_bar.empty()

    # ── Resumo ──
    st.markdown("---")
    st.markdown("##### 📊 Resumo da Importação")

    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        st.markdown(metric_card("Importados", str(sucessos), "metric-green"), unsafe_allow_html=True)
    with col_s2:
        st.markdown(metric_card("Duplicatas", str(duplicatas), "metric-orange"), unsafe_allow_html=True)
    with col_s3:
        st.markdown(metric_card("Erros", str(erros_importacao), "metric-red"), unsafe_allow_html=True)

    if sucessos > 0:
        st.success(f"🎉 **{sucessos}** cliente(s) importado(s) com sucesso!")
        # Registrar log
        try:
            usuario = get_username()
            database.registrar_log_acao(
                usuario,
                "Importação em Lote de Clientes",
                f"{sucessos} importados, {duplicatas} duplicatas, {erros_importacao} erros"
            )
        except Exception:
            pass

    if duplicatas > 0:
        st.warning(f"⚠️ **{duplicatas}** cliente(s) ignorado(s) por CPF/CNPJ já cadastrado.")

    if erros_detalhes:
        with st.expander(f"❌ Detalhes dos erros ({len(erros_detalhes)})", expanded=False):
            for detalhe in erros_detalhes:
                st.error(f"• {detalhe}")

    if sucessos > 0:
        st.balloons()


# ============ FUNÇÕES AUXILIARES PARA AUTOCOMPLETE ============

def selecionar_cliente_autocomplete(key_prefix="", label="🔍 Cliente"):
    """Componente reutilizável de seleção de cliente com busca.
    Mostra APENAS clientes cadastrados no banco de dados.
    Retorna o ID do cliente selecionado ou None.
    Pode ser usado em outros módulos (faturamento, custos, etc.)
    """
    clientes = database.obter_clientes(apenas_ativos=True)
    
    if not clientes:
        st.warning("⚠️ Nenhum cliente cadastrado. Acesse **👥 Cadastros** para adicionar clientes.")
        return None, ""
    
    # Criar opções formatadas
    opcoes = ["(Nenhum)"]
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
    
    if selecionado == "(Nenhum)":
        return None, ""
    
    cliente = cliente_map.get(selecionado)
    if cliente:
        return cliente['id'], cliente['nome']
    return None, ""
