"""
Módulo de Backup - JR ENTREGAS ME ERP
Sistema de exportação, importação e histórico de backups do banco de dados.
"""

import streamlit as st
import pandas as pd
from datetime import datetime

from styles import page_header, metric_card
from auth import is_admin, get_username
import database


def render():
    """Renderiza o módulo de backup."""
    page_header("💾 Backup", "Exportar, importar e gerenciar backups do banco de dados")

    if not is_admin():
        st.warning("⚠️ Acesso restrito. Apenas administradores podem gerenciar backups.")
        return

    tab_exportar, tab_importar, tab_historico = st.tabs([
        "📤 Exportar Backup",
        "📥 Importar Backup",
        "📋 Histórico"
    ])

    with tab_exportar:
        _render_exportar()

    with tab_importar:
        _render_importar()

    with tab_historico:
        _render_historico()


def _formatar_tamanho(tamanho_bytes):
    """Formata tamanho em bytes para formato legível."""
    if tamanho_bytes < 1024:
        return f"{tamanho_bytes} B"
    elif tamanho_bytes < 1024 * 1024:
        return f"{tamanho_bytes / 1024:.1f} KB"
    else:
        return f"{tamanho_bytes / (1024 * 1024):.2f} MB"


def _render_exportar():
    """Aba de exportação de backup."""
    st.markdown("#### 📤 Exportar Backup do Banco de Dados")
    st.markdown("Faça o download de uma cópia completa do banco de dados para guardar em local seguro.")

    # Informações do banco atual
    info = database.obter_info_banco()

    if not info:
        st.error("❌ Banco de dados não encontrado.")
        return

    # Métricas do banco
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(metric_card(
            _formatar_tamanho(info['tamanho']),
            "Tamanho do Banco",
            "#3182CE"
        ), unsafe_allow_html=True)
    with col2:
        total_registros = sum(info['registros'].values())
        st.markdown(metric_card(
            f"{total_registros:,}".replace(",", "."),
            "Total de Registros",
            "#38A169"
        ), unsafe_allow_html=True)
    with col3:
        st.markdown(metric_card(
            str(len(info['tabelas'])),
            "Tabelas no Banco",
            "#805AD5"
        ), unsafe_allow_html=True)

    st.markdown("---")

    # Detalhes das tabelas
    with st.expander("📊 Detalhes das Tabelas", expanded=False):
        tabelas_info = []
        nomes_amigaveis = {
            'produtos': '📦 Produtos',
            'notas': '📄 Notas Fiscais',
            'itens_nota': '📋 Itens de Notas',
            'faturamento': '💰 Faturamento',
            'custos': '💸 Custos',
            'clientes': '👥 Clientes',
            'categorias_custos': '🏷️ Categorias',
            'subcategorias_custos': '🏷️ Subcategorias',
            'contas': '📅 Contas a Pagar/Receber',
            'custos_faturamento': '🔗 Custos por Faturamento',
            'notas_excluidas': '🗑️ Notas Excluídas',
            'log_backups': '💾 Log de Backups',
        }
        for tabela in sorted(info['tabelas']):
            nome = nomes_amigaveis.get(tabela, tabela)
            tabelas_info.append({
                'Tabela': nome,
                'Registros': info['registros'].get(tabela, 0)
            })

        if tabelas_info:
            df = pd.DataFrame(tabelas_info)
            st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown(f"🕐 **Última modificação:** {info['ultima_modificacao']}")

    # Último backup
    logs = database.obter_log_backups()
    export_logs = [l for l in logs if l['tipo'] == 'exportacao']
    if export_logs:
        ultimo = export_logs[0]
        st.markdown(f"💾 **Último backup exportado:** {ultimo['data']} por {ultimo['usuario'] or 'N/A'}")
    else:
        st.info("ℹ️ Nenhum backup exportado anteriormente.")

    st.markdown("---")

    # Botão de download
    st.markdown("##### ⬇️ Fazer Download do Backup")
    st.markdown(
        """
        <div style="background: #EBF8FF; border-left: 4px solid #3182CE; padding: 12px; border-radius: 4px; margin-bottom: 16px;">
            <strong>ℹ️ Dica de segurança:</strong> Guarde o backup em local seguro (Google Drive, HD externo, etc).
            Recomendamos fazer backup regularmente, especialmente antes de atualizações.
        </div>
        """,
        unsafe_allow_html=True
    )

    col_btn, _ = st.columns([1, 2])
    with col_btn:
        if st.button("🔄 Preparar Backup para Download", use_container_width=True, type="primary"):
            with st.spinner("Preparando backup..."):
                backup_data = database.criar_backup()
                if backup_data:
                    st.session_state['backup_pronto'] = backup_data
                    st.session_state['backup_tamanho'] = len(backup_data)
                    st.success("✅ Backup preparado com sucesso!")
                else:
                    st.error("❌ Erro ao preparar o backup.")

    if st.session_state.get('backup_pronto'):
        agora = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_arquivo = f"jr_entregas_backup_{agora}.db"

        st.download_button(
            label=f"⬇️ Download: {nome_arquivo} ({_formatar_tamanho(st.session_state['backup_tamanho'])})",
            data=st.session_state['backup_pronto'],
            file_name=nome_arquivo,
            mime="application/x-sqlite3",
            use_container_width=True,
            on_click=_registrar_exportacao
        )


def _registrar_exportacao():
    """Callback para registrar exportação no log."""
    tamanho = st.session_state.get('backup_tamanho', 0)
    database.registrar_log_backup(
        tipo="exportacao",
        tamanho=tamanho,
        usuario=get_username(),
        observacao="Exportação manual do banco de dados"
    )


def _render_importar():
    """Aba de importação/restauração de backup."""
    st.markdown("#### 📥 Importar e Restaurar Backup")

    # Aviso de segurança
    st.markdown(
        """
        <div style="background: #FFF5F5; border-left: 4px solid #E53E3E; padding: 12px; border-radius: 4px; margin-bottom: 16px;">
            <strong>⚠️ ATENÇÃO:</strong> A restauração de backup irá <strong>substituir todos os dados atuais</strong> 
            do sistema. Um backup automático do banco atual será criado antes da restauração, mas esta ação não pode 
            ser desfeita facilmente. Tenha certeza do que está fazendo.
        </div>
        """,
        unsafe_allow_html=True
    )

    # Upload do arquivo
    uploaded_file = st.file_uploader(
        "Selecione o arquivo de backup (.db)",
        type=["db"],
        help="Arquivo SQLite (.db) exportado anteriormente pelo sistema."
    )

    if uploaded_file is not None:
        arquivo_bytes = uploaded_file.read()
        tamanho = len(arquivo_bytes)

        st.markdown(f"📁 **Arquivo:** {uploaded_file.name}")
        st.markdown(f"📊 **Tamanho:** {_formatar_tamanho(tamanho)}")

        st.markdown("---")

        # Validar backup
        with st.spinner("Validando arquivo..."):
            valido, mensagem, info = database.validar_backup(arquivo_bytes)

        if not valido:
            st.error(f"❌ {mensagem}")
            return

        st.success(f"✅ {mensagem}")

        # Preview dos dados
        st.markdown("##### 📊 Preview dos Dados do Backup")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(metric_card(
                str(len(info.get('tabelas', []))),
                "Tabelas Encontradas",
                "#3182CE"
            ), unsafe_allow_html=True)
        with col2:
            total = sum(info.get('registros', {}).values())
            st.markdown(metric_card(
                f"{total:,}".replace(",", "."),
                "Total de Registros",
                "#38A169"
            ), unsafe_allow_html=True)

        # Tabela comparativa
        with st.expander("📋 Comparação: Banco Atual vs Backup", expanded=True):
            info_atual = database.obter_info_banco()
            comparacao = []

            todas_tabelas = sorted(set(
                info.get('tabelas', []) + (info_atual['tabelas'] if info_atual else [])
            ))

            nomes_amigaveis = {
                'produtos': '📦 Produtos',
                'notas': '📄 Notas Fiscais',
                'itens_nota': '📋 Itens de Notas',
                'faturamento': '💰 Faturamento',
                'custos': '💸 Custos',
                'clientes': '👥 Clientes',
                'categorias_custos': '🏷️ Categorias',
                'subcategorias_custos': '🏷️ Subcategorias',
                'contas': '📅 Contas',
                'custos_faturamento': '🔗 Custos Fat.',
                'notas_excluidas': '🗑️ Notas Excluídas',
                'log_backups': '💾 Log Backups',
            }

            for tabela in todas_tabelas:
                atual = info_atual['registros'].get(tabela, 0) if info_atual else 0
                backup = info.get('registros', {}).get(tabela, 0)
                diff = backup - atual
                diff_str = f"+{diff}" if diff > 0 else str(diff) if diff != 0 else "="
                comparacao.append({
                    'Tabela': nomes_amigaveis.get(tabela, tabela),
                    'Registros Atuais': atual,
                    'Registros no Backup': backup,
                    'Diferença': diff_str
                })

            if comparacao:
                df_comp = pd.DataFrame(comparacao)
                st.dataframe(df_comp, use_container_width=True, hide_index=True)

        st.markdown("---")

        # Confirmação com senha
        st.markdown("##### 🔐 Confirmação de Segurança")
        st.markdown("Para restaurar o backup, confirme sua senha de administrador.")

        senha_confirmacao = st.text_input(
            "Senha do Administrador",
            type="password",
            key="senha_restauracao",
            placeholder="Digite sua senha para confirmar"
        )

        confirmar = st.checkbox(
            "✅ Entendo que os dados atuais serão substituídos e desejo prosseguir.",
            key="confirmar_restauracao"
        )

        col_btn, _ = st.columns([1, 2])
        with col_btn:
            if st.button(
                "🔄 Restaurar Backup",
                type="primary",
                use_container_width=True,
                disabled=not confirmar
            ):
                # Validar senha
                username = get_username()
                user = database.verificar_senha(username, senha_confirmacao)
                if user is None:
                    st.error("❌ Senha incorreta. Restauração cancelada.")
                    return

                # Registrar backup de segurança no log
                info_antes = database.obter_info_banco()
                tamanho_antes = info_antes['tamanho'] if info_antes else 0
                database.registrar_log_backup(
                    tipo="backup_auto_pre_restauracao",
                    tamanho=tamanho_antes,
                    usuario=username,
                    observacao="Backup automático antes da restauração"
                )

                # Restaurar
                with st.spinner("Restaurando backup... Por favor aguarde."):
                    sucesso, msg = database.restaurar_backup(arquivo_bytes)

                if sucesso:
                    # Registrar no novo banco (se possível)
                    try:
                        database.registrar_log_backup(
                            tipo="importacao",
                            tamanho=tamanho,
                            usuario=username,
                            observacao=f"Restauração de backup: {uploaded_file.name}"
                        )
                    except Exception:
                        pass

                    st.success(f"✅ {msg}")
                    st.balloons()
                    st.info("ℹ️ Recarregue a página para ver os dados restaurados.")

                    if st.button("🔄 Recarregar Página"):
                        st.rerun()
                else:
                    st.error(f"❌ {msg}")


def _render_historico():
    """Aba de histórico de backups."""
    st.markdown("#### 📋 Histórico de Backups")

    logs = database.obter_log_backups()

    if not logs:
        st.info("ℹ️ Nenhum backup registrado no histórico.")
        return

    # Métricas
    total_exports = len([l for l in logs if l['tipo'] == 'exportacao'])
    total_imports = len([l for l in logs if l['tipo'] == 'importacao'])
    total_autos = len([l for l in logs if 'auto' in l['tipo']])

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(metric_card(
            str(total_exports),
            "Exportações",
            "#3182CE"
        ), unsafe_allow_html=True)
    with col2:
        st.markdown(metric_card(
            str(total_imports),
            "Importações",
            "#38A169"
        ), unsafe_allow_html=True)
    with col3:
        st.markdown(metric_card(
            str(total_autos),
            "Backups Automáticos",
            "#805AD5"
        ), unsafe_allow_html=True)

    st.markdown("---")

    # Tabela de histórico
    tipo_icons = {
        'exportacao': '📤 Exportação',
        'importacao': '📥 Importação',
        'backup_auto_pre_restauracao': '🔄 Backup Automático (Pré-Restauração)',
    }

    historico = []
    for log in logs:
        historico.append({
            'ID': log['id'],
            'Data': log['data'],
            'Tipo': tipo_icons.get(log['tipo'], log['tipo']),
            'Usuário': log['usuario'] or 'N/A',
            'Tamanho': _formatar_tamanho(log['tamanho']) if log['tamanho'] else 'N/A',
            'Observação': log['observacao'] or ''
        })

    df = pd.DataFrame(historico)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            'ID': st.column_config.NumberColumn(width="small"),
            'Data': st.column_config.TextColumn(width="medium"),
            'Tipo': st.column_config.TextColumn(width="large"),
            'Usuário': st.column_config.TextColumn(width="small"),
            'Tamanho': st.column_config.TextColumn(width="small"),
            'Observação': st.column_config.TextColumn(width="large"),
        }
    )