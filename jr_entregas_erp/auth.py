import streamlit as st
from styles import get_css
import database

# Mapeamento de perfis para labels
PERFIL_LABELS = {
    'ADM': '🔑 Administrador',
    'FUNCIONARIOS': '👷 Funcionário',
    'CONVIDADOS': '👁️ Convidado',
}

# Mapeamento de módulos por perfil
# CONVIDADOS: apenas visualização de Estoque e Gestão de Notas
# FUNCIONARIOS: tudo exceto exclusões
# ADM: acesso total
MODULOS_PERMITIDOS = {
    'ADM': ['dashboard', 'importacao', 'estoque', 'financeiro', 'cadastros', 'gestao_notas', 'backup', 'usuarios'],
    'FUNCIONARIOS': ['dashboard', 'importacao', 'estoque', 'financeiro', 'cadastros', 'gestao_notas'],
    'CONVIDADOS': ['estoque', 'gestao_notas'],
}


def check_login():
    """Returns True if user is logged in."""
    return st.session_state.get("logged_in", False)


def get_user_role():
    """Retorna o role legado (admin/equipe) para compatibilidade."""
    return st.session_state.get("role", "")


def get_user_perfil():
    """Retorna o perfil do usuário (ADM, FUNCIONARIOS, CONVIDADOS)."""
    return st.session_state.get("perfil", "CONVIDADOS")


def get_username():
    return st.session_state.get("username", "")


def get_user_nome():
    return st.session_state.get("nome", "")


def is_admin():
    """Verifica se o usuário é administrador."""
    return get_user_perfil() == "ADM"


def eh_admin():
    """Alias para is_admin - verifica se é administrador."""
    return is_admin()


def pode_visualizar(modulo):
    """Verifica se o perfil atual pode visualizar o módulo."""
    perfil = get_user_perfil()
    modulos = MODULOS_PERMITIDOS.get(perfil, [])
    return modulo in modulos


def pode_editar():
    """Verifica se o perfil atual pode editar dados."""
    perfil = get_user_perfil()
    return perfil in ('ADM', 'FUNCIONARIOS')


def pode_excluir():
    """Verifica se o perfil atual pode excluir dados."""
    perfil = get_user_perfil()
    return perfil == 'ADM'


def get_perfil_label():
    """Retorna o label formatado do perfil do usuário."""
    perfil = get_user_perfil()
    return PERFIL_LABELS.get(perfil, '👤 Usuário')


def login_page():
    st.markdown(get_css(), unsafe_allow_html=True)
    
    st.markdown("""
    <div class="login-container">
        <div class="login-logo">📦</div>
        <h2>JR ENTREGAS ME</h2>
        <p class="subtitle">Sistema de Gestão Empresarial</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        with st.form("login_form"):
            st.markdown("##### 🔐 Acesso ao Sistema")
            usuario = st.text_input("Usuário", placeholder="Digite seu usuário")
            senha = st.text_input("Senha", type="password", placeholder="Digite sua senha")
            submit = st.form_submit_button("Entrar", use_container_width=True, type="primary")
            
            if submit:
                if not usuario or not senha:
                    st.error("❌ Preencha todos os campos!")
                    return
                
                # Autenticar via banco de dados
                user = database.verificar_senha(usuario, senha)
                
                if user:
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = user['username']
                    st.session_state["nome"] = user['nome']
                    st.session_state["perfil"] = user['perfil']
                    st.session_state["user_id"] = user['id']
                    # Manter compatibilidade com role legado
                    if user['perfil'] == 'ADM':
                        st.session_state["role"] = "admin"
                    elif user['perfil'] == 'FUNCIONARIOS':
                        st.session_state["role"] = "equipe"
                    else:
                        st.session_state["role"] = "convidado"
                    
                    # Registrar log de login
                    database.registrar_log_acao(user['username'], "LOGIN", f"Login realizado - Perfil: {user['perfil']}")
                    st.rerun()
                else:
                    st.error("❌ Usuário ou senha incorretos, ou conta desativada!")


def logout():
    username = get_username()
    if username:
        try:
            database.registrar_log_acao(username, "LOGOUT", "Logout realizado")
        except Exception:
            pass
    for key in ["logged_in", "username", "role", "nome", "perfil", "user_id"]:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()


def verificar_acesso(modulo, mostrar_erro=True):
    """Verifica se o usuário tem acesso ao módulo. 
    Se não tiver, mostra mensagem de erro e retorna False."""
    if pode_visualizar(modulo):
        return True
    if mostrar_erro:
        st.error("🚫 **Acesso Negado** — Você não tem permissão para acessar este módulo.")
        st.info(f"Seu perfil: **{get_perfil_label()}**. Entre em contato com o administrador para solicitar acesso.")
    return False


def verificar_edicao(mostrar_erro=True):
    """Verifica se o usuário pode editar. Se não, mostra aviso."""
    if pode_editar():
        return True
    if mostrar_erro:
        st.warning("🔒 Você está no modo **somente visualização**. Não é permitido editar dados com seu perfil atual.")
    return False


def verificar_exclusao(mostrar_erro=True):
    """Verifica se o usuário pode excluir. Se não, mostra aviso."""
    if pode_excluir():
        return True
    if mostrar_erro:
        st.warning("🔒 Exclusões são permitidas apenas para administradores.")
    return False
