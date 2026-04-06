import streamlit as st
import pandas as pd
from styles import page_header, metric_card
from database import inserir_produtos, get_produtos, produto_existe, inserir_nota, inserir_faturamento
from utils import extrair_dados_danfe, buscar_cep, calcular_faturamento


def render():
    st.markdown(page_header("📥 Importação", "Importar produtos e notas fiscais"), unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📋 Importar Produtos (Excel)", "📄 Importar Nota Fiscal (DANFE)"])
    
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
    st.markdown("#### 📄 Importar Nota Fiscal (DANFE PDF)")
    
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
    
    uploaded_pdf = st.file_uploader(
        "Selecione o PDF da DANFE",
        type=["pdf"],
        key=f"upload_pdf_{st.session_state.get('pdf_key', 0)}"
    )
    
    if uploaded_pdf:
        with st.spinner("🔍 Extraindo dados do PDF..."):
            dados = extrair_dados_danfe(uploaded_pdf)
        
        if 'erro' in dados:
            st.error(f"❌ Erro na extração: {dados['erro']}")
            return
        
        st.markdown("---")
        st.markdown("#### 📋 Dados Extraídos")
        
        col1, col2, col3 = st.columns(3)
        
        # Número da nota
        numero_nota = dados.get('numero', '') or ''
        with col1:
            numero_nota = st.text_input("Nº da Nota", value=numero_nota, key="num_nota_input")
        
        # Data
        data_nota = dados.get('data', '') or ''
        with col2:
            data_nota = st.text_input("Data da Nota", value=data_nota, key="data_nota_input")
        
        # CEP
        cep_extraido = dados.get('cep', '') or ''
        with col3:
            cep_nota = st.text_input("CEP do Destinatário", value=cep_extraido, key="cep_nota_input")
        
        # Buscar endereço via CEP
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
        
        # Itens
        st.markdown("#### 📦 Itens da Nota")
        itens_raw = dados.get('itens', [])
        
        if not itens_raw:
            st.warning("⚠️ Nenhum item foi extraído automaticamente do PDF. Adicione manualmente abaixo.")
        
        # Build editable items table
        codigos_produtos = [p['codigo'] for p in produtos]
        
        # Initialize manual items in session state
        if 'manual_itens' not in st.session_state:
            st.session_state['manual_itens'] = []
        
        # Show extracted items
        itens_validos = []
        itens_invalidos = []
        
        for codigo, qtd in itens_raw:
            if produto_existe(codigo):
                itens_validos.append({"codigo": codigo, "quantidade": qtd})
            else:
                itens_invalidos.append(codigo)
        
        if itens_invalidos:
            st.warning(f"⚠️ Códigos ignorados (não cadastrados no estoque): **{', '.join(set(itens_invalidos))}**")
        
        # Editable items
        if itens_validos:
            df_itens = pd.DataFrame(itens_validos)
            st.dataframe(df_itens, use_container_width=True, hide_index=True)
        
        # Manual item addition
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
        
        # Show manual items
        if st.session_state.get('manual_itens'):
            st.markdown("**Itens adicionados manualmente:**")
            df_manual = pd.DataFrame(st.session_state['manual_itens'])
            st.dataframe(df_manual, use_container_width=True, hide_index=True)
            if st.button("🗑️ Limpar itens manuais", key="btn_clear_manual"):
                st.session_state['manual_itens'] = []
                st.rerun()
        
        # Final items: extracted valid + manual
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
        
        # Show billing preview for exit notes
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
            
            # Insert note
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
            
            # Generate billing for exit notes
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
                        municipio=municipio or ""
                    )
            
            st.success(f"✅ Nota {numero_nota} processada com sucesso! (ID: {nota_id})")
            st.session_state['manual_itens'] = []
            st.session_state['pdf_key'] = st.session_state.get('pdf_key', 0) + 1
            st.rerun()
