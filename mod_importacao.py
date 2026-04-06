import streamlit as st
import pandas as pd
from styles import page_header, metric_card
from database import inserir_produtos, get_produtos, produto_existe, inserir_nota, inserir_faturamento
from utils import extrair_dados_danfe, buscar_cep, calcular_faturamento


def render():
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


def _render_nota_individual(uploaded_pdf, tipo_nota, produtos):
    """Modo individual - fluxo interativo com edição manual (comportamento original)."""
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
            itens_validos.append({"codigo": codigo, "quantidade": qtd})
        else:
            itens_invalidos.append(codigo)
    
    if itens_invalidos:
        st.warning(f"⚠️ Códigos ignorados (não cadastrados no estoque): **{', '.join(set(itens_invalidos))}**")
    
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
    
    if st.button("🚀 Processar Nota Fiscal", type="primary", use_container_width=True, key="btn_processar_nota"):
        if not numero_nota:
            st.error("❌ Informe o número da nota.")
            return
        if not todos_itens:
            st.error("❌ A nota precisa ter pelo menos um item.")
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
                cliente_nome = dados.get('cliente', '') or ''
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


def _render_notas_batch(uploaded_pdfs, tipo_nota, produtos):
    """Modo batch - processamento automático de múltiplos PDFs."""
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
                    itens_validos.append((codigo, qtd))
                else:
                    itens_invalidos.append(codigo)
            
            total_unidades = sum(qtd for _, qtd in itens_validos)
            
            # Buscar CEP
            bairro, municipio = "", ""
            if cep and len(cep.replace('-', '').replace('.', '')) >= 8:
                bairro, municipio = buscar_cep(cep)
            
            cliente = dados.get('cliente', '') or ''
            
            preview_data.append({
                'arquivo': pdf_file.name,
                'numero': numero,
                'data': data,
                'cep': cep,
                'bairro': bairro or '',
                'municipio': municipio or '',
                'cliente': cliente,
                'itens_validos': itens_validos,
                'itens_invalidos': itens_invalidos,
                'total_itens': len(itens_validos),
                'total_unidades': total_unidades,
                'erro': erro,
            })
        
        progress_bar.empty()
        st.session_state[batch_key] = preview_data
        st.session_state['batch_file_count'] = total_pdfs
    
    preview_data = st.session_state[batch_key]
    
    # Summary table
    notas_ok = [p for p in preview_data if not p['erro'] and p['numero'] and p['itens_validos']]
    notas_warn = [p for p in preview_data if not p['erro'] and (not p['numero'] or not p['itens_validos'])]
    notas_erro = [p for p in preview_data if p['erro']]
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(metric_card("Total de Arquivos", total_pdfs, "metric-blue"), unsafe_allow_html=True)
    with c2:
        st.markdown(metric_card("Prontas p/ Importar", len(notas_ok), "metric-green"), unsafe_allow_html=True)
    with c3:
        st.markdown(metric_card("Com Pendências", len(notas_warn), "metric-orange"), unsafe_allow_html=True)
    with c4:
        st.markdown(metric_card("Com Erro", len(notas_erro), "metric-red"), unsafe_allow_html=True)
    
    # Detail per PDF
    st.markdown("#### 📋 Detalhes por Arquivo")
    
    for idx, info in enumerate(preview_data):
        if info['erro']:
            icon = "❌"
            status = f"ERRO: {info['erro']}"
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
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.text_input("Nº Nota", value=info['numero'], disabled=True, key=f"batch_num_{idx}")
            with col2:
                st.text_input("Data", value=info['data'], disabled=True, key=f"batch_data_{idx}")
            with col3:
                st.text_input("CEP", value=info['cep'], disabled=True, key=f"batch_cep_{idx}")
            
            if info['bairro'] or info['municipio']:
                col_a, col_b = st.columns(2)
                with col_a:
                    st.text_input("Bairro", value=info['bairro'], disabled=True, key=f"batch_bairro_{idx}")
                with col_b:
                    st.text_input("Município", value=info['municipio'], disabled=True, key=f"batch_mun_{idx}")
            
            if info['itens_validos']:
                df_itens = pd.DataFrame(info['itens_validos'], columns=["Código", "Quantidade"])
                st.dataframe(df_itens, use_container_width=True, hide_index=True)
            
            if info['itens_invalidos']:
                st.warning(f"⚠️ Códigos ignorados (não cadastrados): **{', '.join(set(info['itens_invalidos']))}**")
            
            if tipo_nota == "saida" and info['cep'] and info['total_unidades'] > 0:
                valor, veiculo, regiao_nome, regiao_num = calcular_faturamento(info['cep'], info['total_unidades'])
                if valor:
                    st.info(f"💰 Faturamento: **R$ {valor:.2f}** | Veículo: **{veiculo}** | Região: **R{regiao_num} - {regiao_nome}**")
    
    st.markdown("---")
    
    if not notas_ok:
        st.warning("⚠️ Nenhuma nota está pronta para importação. Verifique os arquivos acima.")
        return
    
    st.markdown(f"**{len(notas_ok)}** nota(s) pronta(s) para importação. Notas com erro ou pendências serão ignoradas.")
    
    if st.button(
        f"🚀 Importar {len(notas_ok)} Nota(s) Fiscal(is)",
        type="primary",
        use_container_width=True,
        key="btn_processar_batch"
    ):
        sucesso = 0
        erros = 0
        resultados = []
        
        progress = st.progress(0, text="Processando notas...")
        
        for idx, info in enumerate(notas_ok):
            progress.progress(
                (idx + 1) / len(notas_ok),
                text=f"📝 Processando nota {idx + 1} de {len(notas_ok)} — Nota {info['numero']}"
            )
            
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
                            cliente=info.get('cliente', '')
                        )
                
                sucesso += 1
                resultados.append(f"✅ Nota {info['numero']} ({info['arquivo']}) — importada com sucesso (ID: {nota_id})")
            except Exception as e:
                erros += 1
                resultados.append(f"❌ Nota {info['numero']} ({info['arquivo']}) — erro: {e}")
        
        progress.empty()
        
        # Final summary
        st.markdown("---")
        st.markdown("#### 📊 Resumo da Importação em Lote")
        
        r1, r2, r3 = st.columns(3)
        with r1:
            st.markdown(metric_card("Importadas com Sucesso", sucesso, "metric-green"), unsafe_allow_html=True)
        with r2:
            st.markdown(metric_card("Erros", erros, "metric-red"), unsafe_allow_html=True)
        with r3:
            ignoradas = total_pdfs - len(notas_ok)
            st.markdown(metric_card("Ignoradas (pendências)", ignoradas, "metric-orange"), unsafe_allow_html=True)
        
        # Show individual results
        for res in resultados:
            if res.startswith("✅"):
                st.success(res)
            else:
                st.error(res)
        
        if sucesso > 0:
            st.balloons()
        
        # Clean up
        if batch_key in st.session_state:
            del st.session_state[batch_key]
        if 'batch_file_count' in st.session_state:
            del st.session_state['batch_file_count']
        st.session_state['pdf_key'] = st.session_state.get('pdf_key', 0) + 1
        st.rerun()
