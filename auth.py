import streamlit as st
from styles import get_css

USERS = {
    "admin": {"senha": "jr2026", "role": "admin", "nome": "Administrador"},
    "equipe": {"senha": "jr2026", "role": "equipe", "nome": "Equipe"},
}

def check_login():
    """Returns True if user is logged in."""
    return st.session_state.get("logged_in", False)

def get_user_role():
    return st.session_state.get("role", "")

def get_username():
    return st.session_state.get("username", "")

def is_admin():
    return get_user_role() == "admin"

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
                if usuario in USERS and USERS[usuario]["senha"] == senha:
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = usuario
                    st.session_state["role"] = USERS[usuario]["role"]
                    st.session_state["nome"] = USERS[usuario]["nome"]
                    st.rerun()
                else:
                    st.error("❌ Usuário ou senha incorretos!")

def logout():
    for key in ["logged_in", "username", "role", "nome"]:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()
