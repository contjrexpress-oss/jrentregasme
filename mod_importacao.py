import streamlit as st
import pandas as pd
from styles import page_header, metric_card
from database import (
    inserir_produtos, get_produtos, produto_existe,
    inserir_nota, inserir_faturamento, nota_existe,
    obter_clientes
)
from utils import (
    extrair_dados_danfe, buscar_cep, calcular_faturamento,
    validar_data, validar_cep, validar_numero_nota,
    validar_quantidade, validar_dados_nota,
    formatar_cpf_cnpj
)


def _selecionar_cliente_cadastrado(label="👤 Cliente", key_suffix="", placeholder="(Nenhum)"):
    """Renderiza seletor de cliente mostrando APENAS clientes cadastrados.
    
    Returns:
        str: Nome do cliente selecionado ou string vazia.
    """
    clientes = obter_clientes(apenas_ativos=True)
    
    if not clientes:
        st.warning("⚠️ Nenhum cliente cadastrado. Acesse **👥 Cadastros** para adicionar clientes.")
        return ""
    
    opcoes = [placeholder]
    mapa = {}
    for c in clientes:
        doc = formatar_cpf_cnpj(c.get('cpf_cnpj', '')) if c.get('cpf_cnpj') else ""
        bairro = f" — {c.get('bairro', '')}" if c.get('bairro') else ""
        label_cli = f"{c['nome']}{' | ' + doc if doc else ''}{bairro}"
        opcoes.append(label_cli)
        mapa[label_cli] = c['nome']
    
    selecionado = st.selectbox(
        label,
        opcoes,
        key=f"select_cliente_{key_suffix}",
    )
    
    if selecionado in mapa:
        return mapa[selecionado]
    
    return ""


def render():
    from auth import verificar_acesso
    if not verificar_acesso('importacao'):
        return
    st.markdown(page_header("📥 Importação", "Importar produtos e notas fiscais"), unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📋 Importar Produtos (Excel)", "📄 Importar Notas Fiscais (DANFE)"])

    with tab1:
        _render_importar_produtos()

    with tab2:
        _render_importar_notas()


def _render_importar_produtos():
    st.markdown("#### 📋 Importar Produtos via Excel")
    st.info("📌 O arquivo deve conter as colunas **Código** (coluna 1) e **Descrição** (coluna 2).")

    uploaded = st.file_uploader(
        "Selecione o arquivo Excel (.xlsx)",
        type=["xlsx", "xls"],
        key=f"upload_excel_{st.session_state.get('excel_key', 0)}"
    )

    if uploaded:
        try:
            df = pd.read_excel(uploaded, header=0)
            if len(df.columns) < 2:
                st.error("❌ O arquivo precisa ter pelo menos 2 colunas (Código e Descrição).")
                return

            df = df.iloc[:, :2]
            df.columns = ["Código", "Descrição"]
            df["Código"] = df["Código"].astype(str).str.strip()
            df["Descrição"] = df["Descrição"].astype(str).str.strip()
            df = df[df["Código"].notna() & (df["Código"] != "") & (df["Código"] != "nan")]

            st.markdown(f"**{len(df)} produtos encontrados no arquivo:**")
            st.dataframe(df, use_container_width=True, hide_index=True)

            if st.button("✅ Importar Produtos", type="primary", key="btn_import_products"):
                lista = list(zip(df["Código"], df["Descrição"]))
                inseridos, atualizados = inserir_produtos(lista)
                st.success(f"✅ Importação concluída! {inseridos} novos produtos inseridos, {atualizados} atualizados.")
                st.session_state['excel_key'] = st.session_state.get('excel_key', 0) + 1
                st.rerun()
        except Exception as e:
            st.error(f"❌ Erro ao ler o arquivo: {e}")


def _render_importar_notas():
    st.markdown("#### 📄 Importar Notas Fiscais (DANFE PDF)")

    produtos = get_produtos()
    if not produtos:
        st.warning("⚠️ Nenhum produto cadastrado. Importe os produtos primeiro via Excel.")
        return

    col1, col2 = st.columns(2)
    with col1:
        tipo_nota = st.selectbox(
            "📌 Tipo da Nota",
            ["entrada", "saida"],
            format_func=lambda x: "🟢 ENTRADA" if x == "entrada" else "🔴 SAÍDA"
        )

    st.info("📌 Você pode selecionar **múltiplos arquivos PDF** de uma vez para processamento em lote.")

    uploaded_pdfs = st.file_uploader(
        "Selecione os PDFs das DANFEs",
        type=["pdf"],
        accept_multiple_files=True,
        key=f"upload_pdf_{st.session_state.get('pdf_key', 0)}"
    )

    if not uploaded_pdfs:
        return

    # Route: single file => interactive mode, multiple files => batch mode
    if len(uploaded_pdfs) == 1:
        _render_nota_individual(uploaded_pdfs[0], tipo_nota, produtos)
    else:
        _render_notas_batch(uploaded_pdfs, tipo_nota, produtos)


# ============================================================
# MODO INDIVIDUAL - fluxo interativo com edição manual
# ============================================================
def _render_nota_individual(uploaded_pdf, tipo_nota, produtos):
    """Modo individual - fluxo interativo com edição manual."""
    with st.spinner("🔍 Extraindo dados do PDF..."):
        dados = extrair_dados_danfe(uploaded_pdf)

    if 'erro' in dados:
        st.error(f"❌ Erro na extração: {dados['erro']}")
        return

    st.markdown("---")
    st.markdown("#### 📋 Dados Extraídos")

    col1, col2, col3 = st.columns(3)

    numero_nota = dados.get('numero', '') or ''
    with col1:
        numero_nota = st.text_input("Nº da Nota", value=numero_nota, key="num_nota_input")

    data_nota = dados.get('data', '') or ''
    with col2:
        data_nota = st.text_input("Data da Nota", value=data_nota, key="data_nota_input")

    cep_extraido = dados.get('cep', '') or ''
    with col3:
        cep_nota = st.text_input("CEP do Destinatário", value=cep_extraido, key="cep_nota_input")

    # === VALIDAÇÕES EM TEMPO REAL ===
    _render_validacoes_inline(numero_nota, data_nota, cep_nota)

    # === VERIFICAÇÃO DE DUPLICIDADE ===
    duplicada = False
    if numero_nota:
        nota_dup = nota_existe(numero_nota, data_nota if data_nota else None, tipo_nota)
        if nota_dup:
            duplicada = True
            st.markdown("""
            <div style="background: #FFF3CD; border-left: 4px solid #FFC107; padding: 12px; border-radius: 4px; margin: 8px 0;">
                <strong>⚠️ NOTA DUPLICADA DETECTADA</strong><br>
                Já existe uma nota com o número <strong>{}</strong> no sistema.<br>
                Data: {} | Tipo: {} | Importada em: {}
            </div>
            """.format(
                nota_dup['numero'],
                nota_dup.get('data_nota', 'N/A'),
                nota_dup.get('tipo', 'N/A').upper(),
                nota_dup.get('data_importacao', 'N/A')
            ), unsafe_allow_html=True)

            forcar = st.checkbox(
                "🔓 Forçar Importação (ignorar duplicidade)",
                value=False,
                key="forcar_individual",
                help="Marque esta opção para importar mesmo que a nota já exista no sistema."
            )
            if forcar:
                duplicada = False

    # Seleção de cliente cadastrado
    cliente_nome = _selecionar_cliente_cadastrado(
        label="👤 Cliente",
        key_suffix="nota_individual",
        placeholder="(Nenhum)"
    )

    bairro = ""
    municipio = ""
    if cep_nota and len(cep_nota.replace('-', '').replace('.', '')) >= 8:
        bairro, municipio = buscar_cep(cep_nota)
        if bairro and municipio:
            col1, col2 = st.columns(2)
            with col1:
                st.text_input("Bairro", value=bairro or "", disabled=True, key="bairro_display")
            with col2:
                st.text_input("Município", value=municipio or "", disabled=True, key="municipio_display")
        else:
            st.warning("⚠️ Não foi possível encontrar o endereço para este CEP.")

    st.markdown("#### 📦 Itens da Nota")
    itens_raw = dados.get('itens', [])

    if not itens_raw:
        st.warning("⚠️ Nenhum item foi extraído automaticamente do PDF. Adicione manualmente abaixo.")

    codigos_produtos = [p['codigo'] for p in produtos]

    if 'manual_itens' not in st.session_state:
        st.session_state['manual_itens'] = []

    itens_validos = []
    itens_invalidos = []

    for codigo, qtd in itens_raw:
        if produto_existe(codigo):
            ok_qtd, _ = validar_quantidade(qtd)
            if ok_qtd:
                itens_validos.append({"codigo": codigo, "quantidade": qtd})
            else:
                itens_invalidos.append({"codigo": codigo, "motivo": f"Quantidade inválida: {qtd}"})
        else:
            itens_invalidos.append({"codigo": codigo, "motivo": "Não cadastrado no estoque"})

    # === FEEDBACK DETALHADO DE ITENS NÃO CADASTRADOS ===
    if itens_invalidos:
        _render_itens_invalidos(itens_invalidos, itens_raw)

    if itens_validos:
        df_itens = pd.DataFrame(itens_validos)
        st.dataframe(df_itens, use_container_width=True, hide_index=True)

    st.markdown("##### ➕ Adicionar Item Manualmente")
    col_a, col_b, col_c = st.columns([3, 2, 1])
    with col_a:
        sel_produto = st.selectbox(
            "Produto",
            options=codigos_produtos,
            format_func=lambda x: f"{x} - {next((p['descricao'] for p in produtos if p['codigo'] == x), '')}",
            key="sel_produto_manual"
        )
    with col_b:
        qtd_manual = st.number_input("Quantidade", min_value=1, value=1, key="qtd_manual")
    with col_c:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Adicionar", key="btn_add_item"):
            st.session_state['manual_itens'].append({"codigo": sel_produto, "quantidade": qtd_manual})
            st.rerun()

    if st.session_state.get('manual_itens'):
        st.markdown("**Itens adicionados manualmente:**")
        df_manual = pd.DataFrame(st.session_state['manual_itens'])
        st.dataframe(df_manual, use_container_width=True, hide_index=True)
        if st.button("🗑️ Limpar itens manuais", key="btn_clear_manual"):
            st.session_state['manual_itens'] = []
            st.rerun()

    todos_itens = itens_validos + (st.session_state.get('manual_itens') or [])
    total_unidades = sum(i['quantidade'] for i in todos_itens)

    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(metric_card("Total de Itens", len(todos_itens), "metric-blue"), unsafe_allow_html=True)
    with c2:
        st.markdown(metric_card("Total de Unidades", total_unidades, "metric-orange"), unsafe_allow_html=True)
    with c3:
        tipo_label = "🟢 ENTRADA" if tipo_nota == "entrada" else "🔴 SAÍDA"
        st.markdown(metric_card("Tipo", tipo_label), unsafe_allow_html=True)

    if tipo_nota == "saida" and cep_nota and total_unidades > 0:
        valor, veiculo, regiao_nome, regiao_num = calcular_faturamento(cep_nota, total_unidades)
        if valor:
            st.markdown("#### 💰 Prévia do Faturamento")
            fc1, fc2, fc3 = st.columns(3)
            with fc1:
                st.markdown(metric_card("Valor", f"R$ {valor:.2f}", "metric-green"), unsafe_allow_html=True)
            with fc2:
                st.markdown(metric_card("Veículo", veiculo, "metric-blue"), unsafe_allow_html=True)
            with fc3:
                st.markdown(metric_card("Região", f"R{regiao_num} - {regiao_nome}"), unsafe_allow_html=True)
        else:
            st.info("ℹ️ CEP não pertence a nenhuma região cadastrada. Faturamento não será gerado automaticamente.")

    st.markdown("---")

    # Botão de processar (desabilitado se duplicada)
    btn_label = "🚀 Processar Nota Fiscal"
    if duplicada:
        st.warning("⚠️ Nota duplicada. Marque 'Forçar Importação' acima para prosseguir.")

    if st.button(btn_label, type="primary", use_container_width=True, key="btn_processar_nota", disabled=duplicada):
        # Validações finais
        erros_validacao = []
        ok_num, msg_num = validar_numero_nota(numero_nota)
        if not ok_num:
            erros_validacao.append(msg_num)
        if not todos_itens:
            erros_validacao.append("A nota precisa ter pelo menos um item.")

        if erros_validacao:
            for err in erros_validacao:
                st.error(f"❌ {err}")
            return

        itens_tuplas = [(i['codigo'], i['quantidade']) for i in todos_itens]
        nota_id = inserir_nota(
            numero=numero_nota,
            data_nota=data_nota,
            cep=cep_nota,
            bairro=bairro or "",
            municipio=municipio or "",
            tipo=tipo_nota,
            total_unidades=total_unidades,
            arquivo_nome=uploaded_pdf.name,
            itens=itens_tuplas
        )

        if tipo_nota == "saida" and cep_nota:
            valor, veiculo, regiao_nome, regiao_num = calcular_faturamento(cep_nota, total_unidades)
            if valor:
                desc_fat = f"Nota {numero_nota} - {regiao_nome} - {total_unidades} un"
                inserir_faturamento(
                    nota_id=nota_id,
                    data=data_nota,
                    descricao=desc_fat,
                    regiao=f"R{regiao_num} - {regiao_nome}",
                    veiculo=veiculo,
                    valor=valor,
                    cep=cep_nota,
                    bairro=bairro or "",
                    municipio=municipio or "",
                    cliente=cliente_nome
                )

        st.success(f"✅ Nota {numero_nota} processada com sucesso! (ID: {nota_id})")
        st.session_state['manual_itens'] = []
        st.session_state['pdf_key'] = st.session_state.get('pdf_key', 0) + 1
        st.rerun()


# ============================================================
# MODO BATCH - processamento automático de múltiplos PDFs
# ============================================================
def _render_notas_batch(uploaded_pdfs, tipo_nota, produtos):
    """Modo batch - processamento automático de múltiplos PDFs com log detalhado."""
    total_pdfs = len(uploaded_pdfs)

    st.markdown("---")
    st.markdown(f"#### 📦 Processamento em Lote — **{total_pdfs} arquivos** selecionados")

    tipo_label = "🟢 ENTRADA" if tipo_nota == "entrada" else "🔴 SAÍDA"
    st.markdown(f"**Tipo:** {tipo_label}")

    # Preview: extract data from all PDFs first
    batch_key = "batch_preview_data"
    if batch_key not in st.session_state or st.session_state.get('batch_file_count') != total_pdfs:
        preview_data = []
        progress_bar = st.progress(0, text="🔍 Extraindo dados dos PDFs...")

        for idx, pdf_file in enumerate(uploaded_pdfs):
            progress_bar.progress(
                (idx + 1) / total_pdfs,
                text=f"🔍 Extraindo dados: {idx + 1} de {total_pdfs} — {pdf_file.name}"
            )
            dados = extrair_dados_danfe(pdf_file)

            numero = dados.get('numero', '') or ''
            data = dados.get('data', '') or ''
            cep = dados.get('cep', '') or ''
            itens_raw = dados.get('itens', [])
            erro = dados.get('erro', None)

            # Validate items
            itens_validos = []
            itens_invalidos = []
            for codigo, qtd in itens_raw:
                if produto_existe(codigo):
                    ok_qtd, _ = validar_quantidade(qtd)
                    if ok_qtd:
                        itens_validos.append((codigo, qtd))
                    else:
                        itens_invalidos.append({"codigo": codigo, "motivo": f"Quantidade inválida: {qtd}"})
                else:
                    itens_invalidos.append({"codigo": codigo, "motivo": "Não cadastrado no estoque"})

            total_unidades = sum(qtd for _, qtd in itens_validos)

            # Buscar CEP
            bairro, municipio = "", ""
            if cep and len(cep.replace('-', '').replace('.', '')) >= 8:
                bairro, municipio = buscar_cep(cep)

            # Validações
            validacao = validar_dados_nota(numero, data, cep, itens_validos)

            # Verificar duplicidade
            duplicada = None
            if numero:
                duplicada = nota_existe(numero, data if data else None, tipo_nota)

            preview_data.append({
                'arquivo': pdf_file.name,
                'numero': numero,
                'data': data,
                'cep': cep,
                'bairro': bairro or '',
                'municipio': municipio or '',
                'itens_validos': itens_validos,
                'itens_invalidos': itens_invalidos,
                'itens_raw': itens_raw,
                'total_itens': len(itens_validos),
                'total_unidades': total_unidades,
                'erro': erro,
                'validacao': validacao,
                'duplicada': duplicada,
            })

        progress_bar.empty()
        st.session_state[batch_key] = preview_data
        st.session_state['batch_file_count'] = total_pdfs

    preview_data = st.session_state[batch_key]

    # Summary table - classify notes
    notas_ok = [p for p in preview_data if not p['erro'] and p['numero'] and p['itens_validos'] and not p['duplicada']]
    notas_dup = [p for p in preview_data if not p['erro'] and p['duplicada']]
    notas_warn = [p for p in preview_data if not p['erro'] and not p['duplicada'] and (not p['numero'] or not p['itens_validos'])]
    notas_erro = [p for p in preview_data if p['erro']]

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(metric_card("Total Arquivos", total_pdfs, "metric-blue"), unsafe_allow_html=True)
    with c2:
        st.markdown(metric_card("Prontas", len(notas_ok), "metric-green"), unsafe_allow_html=True)
    with c3:
        st.markdown(metric_card("Duplicadas", len(notas_dup), "metric-orange"), unsafe_allow_html=True)
    with c4:
        st.markdown(metric_card("Pendências", len(notas_warn), "metric-orange"), unsafe_allow_html=True)
    with c5:
        st.markdown(metric_card("Com Erro", len(notas_erro), "metric-red"), unsafe_allow_html=True)

    # === DUPLICIDADE NO BATCH ===
    if notas_dup:
        st.markdown("#### ⚠️ Notas Duplicadas Encontradas")
        st.markdown("""
        <div style="background: #FFF3CD; border-left: 4px solid #FFC107; padding: 12px; border-radius: 4px; margin: 8px 0;">
            <strong>As seguintes notas já existem no sistema e serão ignoradas:</strong>
        </div>
        """, unsafe_allow_html=True)
        df_dup = pd.DataFrame([{
            "Arquivo": p['arquivo'],
            "Nº Nota": p['numero'],
            "Data": p['data'],
            "Nota existente (ID)": p['duplicada']['id'] if p['duplicada'] else '',
            "Data importação anterior": p['duplicada'].get('data_importacao', '') if p['duplicada'] else ''
        } for p in notas_dup])
        st.dataframe(df_dup, use_container_width=True, hide_index=True)

        forcar_batch = st.checkbox(
            "🔓 Forçar importação de notas duplicadas",
            value=False,
            key="forcar_batch",
            help="Marque para incluir as notas duplicadas na importação."
        )
        if forcar_batch:
            # Move duplicadas para notas_ok
            notas_ok = [p for p in preview_data if not p['erro'] and p['numero'] and p['itens_validos']]
            notas_dup = []

    # === FEEDBACK SOBRE ITENS NÃO CADASTRADOS (consolidado) ===
    todos_invalidos = []
    for info in preview_data:
        for item in info.get('itens_invalidos', []):
            if item['motivo'] == "Não cadastrado no estoque":
                todos_invalidos.append(item['codigo'])

    if todos_invalidos:
        codigos_unicos = sorted(set(todos_invalidos))
        st.markdown("#### 📦 Produtos Não Cadastrados")
        st.markdown("""
        <div style="background: #FCE4EC; border-left: 4px solid #E53935; padding: 12px; border-radius: 4px; margin: 8px 0;">
            <strong>❌ {} código(s) de produto não encontrado(s) no estoque.</strong><br>
            Estes itens serão ignorados na importação. Cadastre-os primeiro via Excel.
        </div>
        """.format(len(codigos_unicos)), unsafe_allow_html=True)

        # Consolidar quantidades por código
        qtd_por_codigo = {}
        for info in preview_data:
            for cod_raw, qtd in info.get('itens_raw', []):
                if not produto_existe(cod_raw):
                    qtd_por_codigo[cod_raw] = qtd_por_codigo.get(cod_raw, 0) + qtd

        df_faltantes = pd.DataFrame([
            {"Código": cod, "Qtd Total (ignorada)": qtd, "Ação Sugerida": "📋 Cadastrar via Importar Produtos (Excel)"}
            for cod, qtd in sorted(qtd_por_codigo.items())
        ])
        st.dataframe(df_faltantes, use_container_width=True, hide_index=True)

    # Campo para seleção de cliente no modo batch
    st.markdown("#### 👤 Selecionar Cliente")
    modo_cliente = st.radio(
        "Como deseja definir o cliente?",
        ["cliente_padrao", "cliente_individual"],
        format_func=lambda x: "🏷️ Mesmo cliente para todas as notas" if x == "cliente_padrao" else "📝 Definir cliente por nota individualmente",
        key="batch_modo_cliente",
        horizontal=True
    )

    cliente_padrao = ""
    if modo_cliente == "cliente_padrao":
        cliente_padrao = _selecionar_cliente_cadastrado(
            label="👤 Cliente (para todas as notas)",
            key_suffix="batch_padrao",
            placeholder="(Nenhum)"
        )

    # === LOG DETALHADO POR ARQUIVO ===
    st.markdown("#### 📋 Log Detalhado por Arquivo")

    for idx, info in enumerate(preview_data):
        if info['erro']:
            icon = "❌"
            status = f"ERRO: {info['erro']}"
        elif info.get('duplicada'):
            icon = "🔁"
            status = f"DUPLICADA — Nota {info['numero']} já existe (ID: {info['duplicada']['id']})"
        elif not info['numero']:
            icon = "⚠️"
            status = "Nº da nota não identificado"
        elif not info['itens_validos']:
            icon = "⚠️"
            status = "Nenhum item válido encontrado"
        else:
            icon = "✅"
            status = f"Nota {info['numero']} — {info['total_itens']} itens, {info['total_unidades']} unidades"

        with st.expander(f"{icon} {info['arquivo']} — {status}", expanded=False):
            if info['erro']:
                st.error(f"Erro ao processar: {info['erro']}")
                continue

            # --- Status dos campos extraídos ---
            validacao = info.get('validacao', {})

            col_status1, col_status2 = st.columns(2)
            with col_status1:
                st.markdown("**Campos Extraídos:**")
                for campo_ok in validacao.get('campos_ok', []):
                    st.markdown(f"✅ {campo_ok}")
                for campo_aviso in validacao.get('campos_aviso', []):
                    st.markdown(f"⚠️ {campo_aviso}")
                for campo_erro in validacao.get('campos_erro', []):
                    st.markdown(f"❌ {campo_erro}")

            with col_status2:
                st.markdown("**Dados:**")
                st.markdown(f"📄 **Nº Nota:** {info['numero'] or '❌ Não identificado'}")
                st.markdown(f"📅 **Data:** {info['data'] or '⚠️ Não identificada'}")
                st.markdown(f"📍 **CEP:** {info['cep'] or '⚠️ Não identificado'}")
                if info['bairro']:
                    st.markdown(f"🏘️ **Bairro:** {info['bairro']}")
                if info['municipio']:
                    st.markdown(f"🏙️ **Município:** {info['municipio']}")

            # Duplicidade
            if info.get('duplicada'):
                st.warning(
                    f"🔁 Nota duplicada! Já existe no sistema (ID: {info['duplicada']['id']}, "
                    f"importada em: {info['duplicada'].get('data_importacao', 'N/A')})"
                )

            if modo_cliente == "cliente_individual":
                _cliente_nome = _selecionar_cliente_cadastrado(
                    label="👤 Cliente",
                    key_suffix=f"batch_{idx}",
                    placeholder="(Nenhum)"
                )
                st.session_state[f"batch_cliente_{idx}"] = _cliente_nome or ""

            # Itens válidos
            st.markdown("---")
            if info['itens_validos']:
                st.markdown(f"**📋 Itens válidos ({len(info['itens_validos'])}):**")
                df_itens = pd.DataFrame(info['itens_validos'], columns=["Código", "Quantidade"])
                st.dataframe(df_itens, use_container_width=True, hide_index=True)

            # Itens inválidos
            if info['itens_invalidos']:
                st.markdown(f"**❌ Itens ignorados ({len(info['itens_invalidos'])}):**")
                df_inv = pd.DataFrame(info['itens_invalidos'])
                df_inv.columns = ["Código", "Motivo"]
                st.dataframe(df_inv, use_container_width=True, hide_index=True)

            # Prévia faturamento
            if tipo_nota == "saida" and info['cep'] and info['total_unidades'] > 0:
                valor, veiculo, regiao_nome, regiao_num = calcular_faturamento(info['cep'], info['total_unidades'])
                if valor:
                    st.info(f"💰 Faturamento: **R$ {valor:.2f}** | Veículo: **{veiculo}** | Região: **R{regiao_num} - {regiao_nome}**")

    st.markdown("---")

    if not notas_ok:
        st.warning("⚠️ Nenhuma nota está pronta para importação. Verifique os arquivos acima.")
        return

    st.markdown(f"**{len(notas_ok)}** nota(s) pronta(s) para importação. Notas com erro, pendências ou duplicadas serão ignoradas.")

    if st.button(
        f"🚀 Importar {len(notas_ok)} Nota(s) Fiscal(is)",
        type="primary",
        use_container_width=True,
        key="btn_processar_batch"
    ):
        sucesso = 0
        erros_count = 0
        duplicadas_count = 0
        resultados = []

        progress = st.progress(0, text="Processando notas...")

        # Mapear índice original de cada nota_ok para recuperar o campo de cliente individual
        notas_ok_indices = []
        for i, p in enumerate(preview_data):
            if not p['erro'] and p['numero'] and p['itens_validos']:
                if not p.get('duplicada') or st.session_state.get('forcar_batch', False):
                    notas_ok_indices.append(i)

        for idx, info in enumerate(notas_ok):
            progress.progress(
                (idx + 1) / len(notas_ok),
                text=f"📝 Processando nota {idx + 1} de {len(notas_ok)} — Nota {info['numero']}"
            )

            # Determinar nome do cliente
            if modo_cliente == "cliente_padrao":
                cliente_nome = cliente_padrao
            else:
                original_idx = notas_ok_indices[idx] if idx < len(notas_ok_indices) else idx
                cliente_nome = st.session_state.get(f"batch_cliente_{original_idx}", '')

            try:
                total_unidades = info['total_unidades']
                nota_id = inserir_nota(
                    numero=info['numero'],
                    data_nota=info['data'],
                    cep=info['cep'],
                    bairro=info['bairro'],
                    municipio=info['municipio'],
                    tipo=tipo_nota,
                    total_unidades=total_unidades,
                    arquivo_nome=info['arquivo'],
                    itens=info['itens_validos']
                )

                if tipo_nota == "saida" and info['cep']:
                    valor, veiculo, regiao_nome, regiao_num = calcular_faturamento(info['cep'], total_unidades)
                    if valor:
                        desc_fat = f"Nota {info['numero']} - {regiao_nome} - {total_unidades} un"
                        inserir_faturamento(
                            nota_id=nota_id,
                            data=info['data'],
                            descricao=desc_fat,
                            regiao=f"R{regiao_num} - {regiao_nome}",
                            veiculo=veiculo,
                            valor=valor,
                            cep=info['cep'],
                            bairro=info['bairro'],
                            municipio=info['municipio'],
                            cliente=cliente_nome
                        )

                sucesso += 1
                resultados.append({
                    "tipo": "sucesso",
                    "msg": f"✅ Nota {info['numero']} ({info['arquivo']}) — importada com sucesso (ID: {nota_id})"
                })
            except Exception as e:
                erros_count += 1
                resultados.append({
                    "tipo": "erro",
                    "msg": f"❌ Nota {info['numero']} ({info['arquivo']}) — erro: {e}"
                })

        progress.empty()

        # === PAINEL DE NOTIFICAÇÕES FINAL ===
        _render_painel_resultados(
            total_pdfs=total_pdfs,
            sucesso=sucesso,
            erros=erros_count,
            duplicadas=len(notas_dup),
            pendencias=len(notas_warn),
            resultados=resultados
        )

        if sucesso > 0:
            st.balloons()

        # Clean up
        if batch_key in st.session_state:
            del st.session_state[batch_key]
        if 'batch_file_count' in st.session_state:
            del st.session_state['batch_file_count']
        st.session_state['pdf_key'] = st.session_state.get('pdf_key', 0) + 1
        st.rerun()


# ============================================================
# COMPONENTES DE UI AUXILIARES
# ============================================================

def _render_validacoes_inline(numero, data, cep):
    """Exibe validações em tempo real dos campos da nota."""
    erros = []
    avisos = []

    # Validar número
    if numero:
        ok, msg = validar_numero_nota(numero)
        if not ok:
            erros.append(f"📄 {msg}")

    # Validar data
    if data:
        ok, msg = validar_data(data)
        if not ok:
            erros.append(f"📅 {msg}")

    # Validar CEP
    if cep:
        ok, msg = validar_cep(cep)
        if not ok:
            erros.append(f"📍 {msg}")

    if erros:
        for e in erros:
            st.markdown(f"""
            <div style="background: #FFEBEE; border-left: 3px solid #E53935; padding: 8px 12px; border-radius: 4px; margin: 4px 0; font-size: 0.9em;">
                ❌ {e}
            </div>
            """, unsafe_allow_html=True)


def _render_itens_invalidos(itens_invalidos, itens_raw):
    """Exibe feedback detalhado sobre itens não cadastrados / inválidos."""
    # Separar por motivo
    nao_cadastrados = [i for i in itens_invalidos if "Não cadastrado" in i['motivo']]
    outros_erros = [i for i in itens_invalidos if "Não cadastrado" not in i['motivo']]

    if nao_cadastrados:
        st.markdown("""
        <div style="background: #FCE4EC; border-left: 4px solid #E53935; padding: 12px; border-radius: 4px; margin: 8px 0;">
            <strong>❌ Produtos não cadastrados no estoque</strong><br>
            Os seguintes códigos não foram encontrados e seus itens serão ignorados.
        </div>
        """, unsafe_allow_html=True)

        # Tabela com detalhes
        qtd_por_codigo = {}
        for cod, qtd in itens_raw:
            if not produto_existe(cod):
                qtd_por_codigo[cod] = qtd_por_codigo.get(cod, 0) + qtd

        df_faltantes = pd.DataFrame([
            {
                "Código": cod,
                "Quantidade (ignorada)": qtd,
                "Ação": "📋 Cadastrar via aba 'Importar Produtos (Excel)'"
            }
            for cod, qtd in sorted(qtd_por_codigo.items())
        ])
        st.dataframe(df_faltantes, use_container_width=True, hide_index=True)

    if outros_erros:
        for item in outros_erros:
            st.warning(f"⚠️ Código **{item['codigo']}**: {item['motivo']}")


def _render_painel_resultados(total_pdfs, sucesso, erros, duplicadas, pendencias, resultados):
    """Exibe painel de notificações com resumo do processamento em lote."""
    st.markdown("---")
    st.markdown("#### 📊 Resumo da Importação em Lote")

    # Cards de resumo
    r1, r2, r3, r4 = st.columns(4)
    with r1:
        st.markdown(metric_card("✅ Importadas", sucesso, "metric-green"), unsafe_allow_html=True)
    with r2:
        st.markdown(metric_card("❌ Erros", erros, "metric-red"), unsafe_allow_html=True)
    with r3:
        st.markdown(metric_card("🔁 Duplicadas", duplicadas, "metric-orange"), unsafe_allow_html=True)
    with r4:
        st.markdown(metric_card("⚠️ Ignoradas", pendencias, "metric-orange"), unsafe_allow_html=True)

    # Barra de progresso visual
    if total_pdfs > 0:
        pct_sucesso = (sucesso / total_pdfs) * 100
        st.markdown(f"""
        <div style="background: #e0e0e0; border-radius: 8px; overflow: hidden; height: 24px; margin: 12px 0;">
            <div style="background: linear-gradient(90deg, #2E7D32, #43A047); width: {pct_sucesso:.0f}%; height: 100%; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 0.85em;">
                {pct_sucesso:.0f}% concluído
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Resultados detalhados
    st.markdown("##### 📝 Detalhes do Processamento")
    for res in resultados:
        if res['tipo'] == 'sucesso':
            st.success(res['msg'])
        else:
            st.error(res['msg'])

    # Lista de erros detalhada
    erros_list = [r for r in resultados if r['tipo'] == 'erro']
    if erros_list:
        with st.expander("🔍 Ver detalhes dos erros", expanded=True):
            for err in erros_list:
                st.markdown(f"- {err['msg']}")
