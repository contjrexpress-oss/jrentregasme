import streamlit as st
import pandas as pd
from datetime import datetime
import database
from styles import page_header, metric_card
from auth import (
    is_admin, get_username, get_user_perfil, verificar_acesso,
    PERFIL_LABELS
)


def render():
    """Renderiza o módulo de gestão de usuários (apenas ADM)."""
    if not verificar_acesso('usuarios'):
        return
    
    page_header("👤 Gestão de Usuários", "Cadastrar, editar e gerenciar acessos ao sistema")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Listar Usuários", 
        "➕ Cadastrar Usuário", 
        "✏️ Editar Usuário",
        "📊 Log de Ações"
    ])
    
    with tab1:
        _render_listar_usuarios()
    with tab2:
        _render_cadastrar_usuario()
    with tab3:
        _render_editar_usuario()
    with tab4:
        _render_log_acoes()


def _render_listar_usuarios():
    """Aba de listagem de usuários."""
    st.subheader("📋 Usuários Cadastrados")
    
    # Filtros
    col1, col2 = st.columns(2)
    with col1:
        filtro_perfil = st.selectbox(
            "Filtrar por perfil",
            ["Todos", "ADM", "FUNCIONARIOS", "CONVIDADOS"],
            key="filtro_perfil_lista"
        )
    with col2:
        filtro_status = st.selectbox(
            "Filtrar por status",
            ["Todos", "Ativos", "Inativos"],
            key="filtro_status_lista_usuarios"
        )
    
    # Buscar usuários
    perfil_filtro = None if filtro_perfil == "Todos" else filtro_perfil
    apenas_ativos = True if filtro_status == "Ativos" else False
    
    usuarios = database.obter_usuarios(apenas_ativos=apenas_ativos, perfil=perfil_filtro)
    
    if filtro_status == "Inativos":
        usuarios = [u for u in usuarios if not u['ativo']]
    
    # Métricas
    todos = database.obter_usuarios()
    total = len(todos)
    ativos = sum(1 for u in todos if u['ativo'])
    inativos = total - ativos
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("Total Usuários", str(total), "#3182CE")
    with col2:
        metric_card("Ativos", str(ativos), "#38A169")
    with col3:
        metric_card("Inativos", str(inativos), "#E53E3E")
    with col4:
        adms = sum(1 for u in todos if u['perfil'] == 'ADM' and u['ativo'])
        metric_card("Administradores", str(adms), "#F29F05")
    
    st.markdown("---")
    
    if not usuarios:
        st.info("Nenhum usuário encontrado com os filtros aplicados.")
        return
    
    # Tabela de usuários
    for user in usuarios:
        status_icon = "🟢" if user['ativo'] else "🔴"
        perfil_icon = PERFIL_LABELS.get(user['perfil'], '👤')
        
        with st.container():
            cols = st.columns([1, 3, 3, 2, 2, 2])
            with cols[0]:
                st.markdown(f"**{status_icon}**")
            with cols[1]:
                st.markdown(f"**{user['username']}**")
            with cols[2]:
                st.markdown(f"{user['nome']}")
            with cols[3]:
                st.markdown(f"{perfil_icon}")
            with cols[4]:
                st.markdown(f"📧 {user.get('email', '-') or '-'}")
            with cols[5]:
                data_str = user.get('data_criacao', '')
                if data_str:
                    try:
                        dt = datetime.strptime(data_str, "%Y-%m-%d %H:%M:%S")
                        st.markdown(f"📅 {dt.strftime('%d/%m/%Y')}")
                    except:
                        st.markdown(f"📅 {data_str}")
            st.markdown("---")


def _render_cadastrar_usuario():
    """Aba de cadastro de novo usuário."""
    st.subheader("➕ Cadastrar Novo Usuário")
    
    with st.form("form_cadastro_usuario", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            username = st.text_input("Username *", placeholder="ex: joao.silva", 
                                      help="Será usado para login. Apenas letras minúsculas, números e pontos.")
            senha = st.text_input("Senha *", type="password", placeholder="Mínimo 6 caracteres")
            confirmar_senha = st.text_input("Confirmar Senha *", type="password")
        
        with col2:
            nome = st.text_input("Nome Completo *", placeholder="ex: João da Silva")
            email = st.text_input("E-mail", placeholder="ex: joao@email.com")
            perfil = st.selectbox("Perfil de Acesso *", 
                                   ["CONVIDADOS", "FUNCIONARIOS", "ADM"],
                                   format_func=lambda x: PERFIL_LABELS.get(x, x))
        
        # Info sobre permissões
        st.markdown("---")
        st.markdown("##### ℹ️ Níveis de Acesso")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("""
            **🔑 ADM**
            - Acesso total ao sistema
            - Pode excluir registros
            - Gerencia usuários
            """)
        with col2:
            st.markdown("""
            **👷 FUNCIONÁRIOS**
            - Acesso a todos os módulos
            - Pode editar registros
            - ❌ Não pode excluir
            """)
        with col3:
            st.markdown("""
            **👁️ CONVIDADOS**
            - Apenas visualização
            - Estoque e Gestão de Notas
            - ❌ Sem edição/exclusão
            """)
        
        submitted = st.form_submit_button("✅ Cadastrar Usuário", type="primary", use_container_width=True)
        
        if submitted:
            # Validações
            erros = []
            if not username or not username.strip():
                erros.append("Username é obrigatório.")
            if not nome or not nome.strip():
                erros.append("Nome é obrigatório.")
            if not senha:
                erros.append("Senha é obrigatória.")
            elif len(senha) < 6:
                erros.append("Senha deve ter no mínimo 6 caracteres.")
            if senha != confirmar_senha:
                erros.append("As senhas não conferem.")
            
            if erros:
                for e in erros:
                    st.error(f"❌ {e}")
            else:
                sucesso, msg = database.inserir_usuario(
                    username=username.strip().lower(),
                    senha=senha,
                    nome=nome.strip(),
                    email=email.strip() if email else "",
                    perfil=perfil
                )
                if sucesso:
                    st.success(f"✅ {msg}")
                    database.registrar_log_acao(
                        get_username(), "CRIAR_USUARIO",
                        f"Criou usuário '{username}' com perfil {perfil}"
                    )
                    st.balloons()
                else:
                    st.error(f"❌ {msg}")


def _render_editar_usuario():
    """Aba de edição de usuário."""
    st.subheader("✏️ Editar Usuário")
    
    usuarios = database.obter_usuarios()
    if not usuarios:
        st.info("Nenhum usuário cadastrado.")
        return
    
    # Selectbox para escolher usuário
    opcoes = {f"{u['username']} - {u['nome']} ({PERFIL_LABELS.get(u['perfil'], u['perfil'])})": u for u in usuarios}
    selecionado = st.selectbox("Selecione o usuário", list(opcoes.keys()), key="sel_editar_usuario")
    
    if not selecionado:
        return
    
    user = opcoes[selecionado]
    usuario_logado = get_username()
    
    st.markdown("---")
    
    # Formulário de edição
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("##### 📝 Dados do Usuário")
        novo_nome = st.text_input("Nome", value=user['nome'], key="edit_nome")
        novo_email = st.text_input("E-mail", value=user.get('email', '') or '', key="edit_email")
        
        # Não permitir que mude seu próprio perfil
        if user['username'] == usuario_logado:
            st.selectbox("Perfil", [user['perfil']], 
                         format_func=lambda x: PERFIL_LABELS.get(x, x),
                         disabled=True, key="edit_perfil_disabled")
            st.caption("⚠️ Você não pode alterar seu próprio perfil.")
            novo_perfil = user['perfil']
        else:
            perfil_opcoes = ["ADM", "FUNCIONARIOS", "CONVIDADOS"]
            idx = perfil_opcoes.index(user['perfil']) if user['perfil'] in perfil_opcoes else 2
            novo_perfil = st.selectbox("Perfil", perfil_opcoes,
                                        index=idx,
                                        format_func=lambda x: PERFIL_LABELS.get(x, x),
                                        key="edit_perfil")
        
        if st.button("💾 Salvar Alterações", key="btn_salvar_usuario", type="primary"):
            sucesso, msg = database.atualizar_usuario(
                user['id'],
                nome=novo_nome.strip(),
                email=novo_email.strip(),
                perfil=novo_perfil
            )
            if sucesso:
                st.success(f"✅ {msg}")
                database.registrar_log_acao(
                    usuario_logado, "EDITAR_USUARIO",
                    f"Editou usuário '{user['username']}': nome={novo_nome}, perfil={novo_perfil}"
                )
                st.rerun()
            else:
                st.error(f"❌ {msg}")
    
    with col2:
        st.markdown("##### 🔐 Resetar Senha")
        nova_senha = st.text_input("Nova Senha", type="password", key="edit_nova_senha",
                                     placeholder="Mínimo 6 caracteres")
        confirmar_nova = st.text_input("Confirmar Nova Senha", type="password", key="edit_confirmar_senha")
        
        if st.button("🔄 Resetar Senha", key="btn_resetar_senha"):
            if not nova_senha:
                st.error("❌ Digite a nova senha.")
            elif len(nova_senha) < 6:
                st.error("❌ Senha deve ter no mínimo 6 caracteres.")
            elif nova_senha != confirmar_nova:
                st.error("❌ As senhas não conferem.")
            else:
                sucesso, msg = database.resetar_senha_usuario(user['id'], nova_senha)
                if sucesso:
                    st.success(f"✅ {msg}")
                    database.registrar_log_acao(
                        usuario_logado, "RESETAR_SENHA",
                        f"Resetou senha do usuário '{user['username']}'"
                    )
                else:
                    st.error(f"❌ {msg}")
        
        st.markdown("---")
        st.markdown("##### ⚡ Ações")
        
        # Ativar/Desativar
        if user['username'] == usuario_logado:
            st.info("Você não pode desativar sua própria conta.")
        else:
            if user['ativo']:
                if st.button("🔴 Desativar Usuário", key="btn_desativar"):
                    database.atualizar_usuario(user['id'], ativo=False)
                    database.registrar_log_acao(
                        usuario_logado, "DESATIVAR_USUARIO",
                        f"Desativou usuário '{user['username']}'"
                    )
                    st.success(f"Usuário '{user['username']}' desativado.")
                    st.rerun()
            else:
                if st.button("🟢 Reativar Usuário", key="btn_reativar"):
                    database.atualizar_usuario(user['id'], ativo=True)
                    database.registrar_log_acao(
                        usuario_logado, "REATIVAR_USUARIO",
                        f"Reativou usuário '{user['username']}'"
                    )
                    st.success(f"Usuário '{user['username']}' reativado.")
                    st.rerun()


def _render_log_acoes():
    """Aba de log de ações."""
    st.subheader("📊 Log de Ações do Sistema")
    
    col1, col2 = st.columns(2)
    with col1:
        usuarios = database.obter_usuarios()
        usernames = ["Todos"] + [u['username'] for u in usuarios]
        filtro_usuario = st.selectbox("Filtrar por usuário", usernames, key="filtro_log_usuario")
    with col2:
        limite = st.number_input("Quantidade de registros", min_value=10, max_value=500, value=50, step=10, key="log_limite")
    
    usuario_filtro = None if filtro_usuario == "Todos" else filtro_usuario
    logs = database.obter_log_acoes(limite=limite, usuario=usuario_filtro)
    
    if not logs:
        st.info("Nenhuma ação registrada.")
        return
    
    # Converter para DataFrame
    df = pd.DataFrame(logs)
    df = df[['data', 'usuario', 'acao', 'detalhes']]
    df.columns = ['Data/Hora', 'Usuário', 'Ação', 'Detalhes']
    
    st.dataframe(df, use_container_width=True, hide_index=True)
