import streamlit as st
import pandas as pd
from styles import page_header, metric_card
from database import get_notas, get_itens_nota, excluir_nota, get_notas_excluidas
from auth import get_username, pode_excluir, verificar_acesso, get_user_perfil


def render():
    if not verificar_acesso('gestao_notas'):
        return
    
    st.markdown(page_header("📋 Gestão de Notas", "Visualize, gerencie e exclua notas fiscais processadas"), unsafe_allow_html=True)
    
    perfil = get_user_perfil()
    
    if perfil == 'CONVIDADOS':
        st.info("👁️ Modo somente visualização — seu perfil permite apenas consultar dados.")
        # Apenas a lista de notas, sem ações
        _render_notas_processadas()
        return
    
    if pode_excluir():
        tab1, tab2 = st.tabs(["📄 Notas Processadas", "🗑️ Histórico de Exclusões"])
        with tab1:
            _render_notas_processadas()
        with tab2:
            _render_historico_exclusoes()
    else:
        # FUNCIONARIOS: sem aba de exclusões
        _render_notas_processadas()


def _render_notas_processadas():
    notas = get_notas()
    
    if not notas:
        st.info("ℹ️ Nenhuma nota fiscal processada.")
        return
    
    df = pd.DataFrame(notas)
    
    # Metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(metric_card("Total de Notas", len(df), "metric-blue"), unsafe_allow_html=True)
    with col2:
        entradas = len(df[df['tipo'] == 'entrada'])
        st.markdown(metric_card("Notas de Entrada", f"🟢 {entradas}", "metric-green"), unsafe_allow_html=True)
    with col3:
        saidas = len(df[df['tipo'] == 'saida'])
        st.markdown(metric_card("Notas de Saída", f"🔴 {saidas}", "metric-red"), unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Filter
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        filtro_tipo = st.selectbox("Filtrar por tipo", ["Todas", "Entrada", "Saída"], key="filtro_tipo_nota")
    with col_f2:
        filtro_busca = st.text_input("🔍 Buscar por nº da nota", key="busca_nota")
    
    df_filtrado = df.copy()
    if filtro_tipo == "Entrada":
        df_filtrado = df_filtrado[df_filtrado['tipo'] == 'entrada']
    elif filtro_tipo == "Saída":
        df_filtrado = df_filtrado[df_filtrado['tipo'] == 'saida']
    
    if filtro_busca:
        df_filtrado = df_filtrado[df_filtrado['numero'].str.contains(filtro_busca, case=False, na=False)]
    
    # Exportar PDF com filtros
    from utils_pdf import gerar_pdf_notas_fiscais
    from datetime import datetime as _dt_notas, date as _date_notas
    
    with st.expander("📄 Exportar Notas em PDF", expanded=False):
        st.caption("Filtre os dados antes de gerar o PDF.")
        col_pdf1, col_pdf2 = st.columns(2)
        with col_pdf1:
            exp_notas_ini = st.date_input(
                "📅 Data Início",
                value=_date_notas(_date_notas.today().year, 1, 1),
                key="exp_notas_data_ini"
            )
        with col_pdf2:
            exp_notas_fim = st.date_input(
                "📅 Data Fim",
                value=_date_notas.today(),
                key="exp_notas_data_fim"
            )
        
        # Filtrar por período
        df_pdf = df_filtrado.copy()
        if 'data_nota' in df_pdf.columns:
            df_pdf['_data_parsed'] = pd.to_datetime(df_pdf['data_nota'], format='mixed', dayfirst=True, errors='coerce')
            mask = df_pdf['_data_parsed'].notna()
            df_pdf = df_pdf[
                mask & (df_pdf['_data_parsed'].dt.date >= exp_notas_ini) &
                (df_pdf['_data_parsed'].dt.date <= exp_notas_fim)
            ]
        
        # Preparar dados para PDF
        notas_pdf = []
        for _, nota_r in df_pdf.iterrows():
            itens_nota = get_itens_nota(nota_r['id'])
            notas_pdf.append({
                'numero': nota_r.get('numero', ''),
                'data_nota': nota_r.get('data_nota', ''),
                'tipo': nota_r.get('tipo', ''),
                'total_unidades': nota_r.get('total_unidades', 0),
                'cep': nota_r.get('cep', ''),
                'bairro': nota_r.get('bairro', ''),
                'municipio': nota_r.get('municipio', ''),
                'itens': itens_nota or [],
            })
        
        metricas_notas_pdf = {
            'total': len(df_pdf),
            'entradas': len(df_pdf[df_pdf['tipo'] == 'entrada']) if not df_pdf.empty else 0,
            'saidas': len(df_pdf[df_pdf['tipo'] == 'saida']) if not df_pdf.empty else 0,
        }
        
        filtro_txt = [f"Período: {exp_notas_ini.strftime('%d/%m/%Y')} a {exp_notas_fim.strftime('%d/%m/%Y')}"]
        if filtro_tipo != "Todas":
            filtro_txt.append(f"Tipo: {filtro_tipo}")
        if filtro_busca:
            filtro_txt.append(f"Busca: {filtro_busca}")
        
        st.info(f"📊 {len(notas_pdf)} notas selecionadas")
        
        if notas_pdf:
            pdf_notas_buf = gerar_pdf_notas_fiscais(notas_pdf, metricas_notas_pdf, " | ".join(filtro_txt))
            
            st.download_button(
                "📥 Baixar Notas em PDF",
                data=pdf_notas_buf,
                file_name=f"notas_fiscais_{_dt_notas.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf",
                key="btn_export_notas_pdf"
            )
        else:
            st.warning("Nenhuma nota encontrada com os filtros selecionados.")
    
    st.markdown("---")
    
    # Display notes
    for _, nota in df_filtrado.iterrows():
        tipo_emoji = "🟢" if nota['tipo'] == 'entrada' else "🔴"
        tipo_label = "ENTRADA" if nota['tipo'] == 'entrada' else "SAÍDA"
        
        with st.expander(f"{tipo_emoji} Nota {nota['numero']} | {tipo_label} | {nota['data_nota'] or 'S/D'} | {nota['total_unidades']} un"):
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown(f"**Nº Nota:** {nota['numero']}")
                st.markdown(f"**Data:** {nota['data_nota'] or 'N/A'}")
            with col2:
                st.markdown(f"**CEP:** {nota['cep'] or 'N/A'}")
                st.markdown(f"**Bairro:** {nota['bairro'] or 'N/A'}")
            with col3:
                st.markdown(f"**Município:** {nota['municipio'] or 'N/A'}")
                st.markdown(f"**Total Un.:** {nota['total_unidades']}")
            with col4:
                st.markdown(f"**Arquivo:** {nota['arquivo_nome'] or 'N/A'}")
                st.markdown(f"**Importado em:** {nota['data_importacao']}")
            
            # Items
            itens = get_itens_nota(nota['id'])
            if itens:
                st.markdown("**Itens:**")
                df_itens = pd.DataFrame(itens)
                df_itens_display = df_itens[['codigo_produto', 'descricao', 'quantidade']].rename(columns={
                    'codigo_produto': 'Código',
                    'descricao': 'Descrição',
                    'quantidade': 'Quantidade'
                })
                st.dataframe(df_itens_display, use_container_width=True, hide_index=True)
            
            # Delete button - apenas ADM
            if pode_excluir():
                st.markdown("---")
                col_d1, col_d2 = st.columns([3, 1])
                with col_d1:
                    motivo = st.text_input("Motivo da exclusão (opcional)", key=f"motivo_{nota['id']}")
                with col_d2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🗑️ Excluir Nota", key=f"btn_del_{nota['id']}", type="primary"):
                        excluir_nota(nota['id'], motivo=motivo, usuario=get_username())
                        st.success(f"✅ Nota {nota['numero']} excluída com estorno automático no estoque e financeiro.")
                        st.rerun()


def _render_historico_exclusoes():
    st.markdown("#### 🗑️ Histórico de Notas Excluídas")
    
    excluidas = get_notas_excluidas()
    
    if not excluidas:
        st.info("ℹ️ Nenhuma nota foi excluída.")
        return
    
    df = pd.DataFrame(excluidas)
    
    st.markdown(metric_card("Total de Exclusões", len(df), "metric-red"), unsafe_allow_html=True)
    st.markdown("")
    
    df_display = df[['numero_nota', 'data_nota', 'tipo', 'total_unidades', 'arquivo_nome', 'motivo', 'data_exclusao', 'usuario']].rename(columns={
        'numero_nota': 'Nº Nota',
        'data_nota': 'Data Nota',
        'tipo': 'Tipo',
        'total_unidades': 'Unidades',
        'arquivo_nome': 'Arquivo',
        'motivo': 'Motivo',
        'data_exclusao': 'Data Exclusão',
        'usuario': 'Excluído por'
    })
    
    st.dataframe(df_display, use_container_width=True, hide_index=True)
