import streamlit as st

st.set_page_config(
    page_title="JR ENTREGAS ME - ERP",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

from styles import get_css
from database import init_db
from auth import check_login, login_page, logout, is_admin, get_user_role
import mod_importacao
import mod_estoque
import mod_financeiro
import mod_gestao_notas

# Initialize database
init_db()

# Apply custom CSS
st.markdown(get_css(), unsafe_allow_html=True)

# Check authentication
if not check_login():
    login_page()
    st.stop()

# ===== SIDEBAR =====
with st.sidebar:
    st.markdown("### 📦 JR ENTREGAS ME")
    st.markdown("---")
    
    nome = st.session_state.get('nome', '')
    role = get_user_role()
    role_label = "🔑 Administrador" if role == "admin" else "👤 Equipe"
    st.markdown(f"**{nome}** | {role_label}")
    st.markdown("---")
    
    # Menu based on role
    if is_admin():
        menu_options = [
            "📥 Importação",
            "📦 Controle de Estoque",
            "💰 Financeiro",
            "📋 Gestão de Notas"
        ]
    else:
        menu_options = [
            "📦 Controle de Estoque"
        ]
    
    pagina = st.radio("Menu", menu_options, label_visibility="collapsed")
    
    st.markdown("---")
    if st.button("🚪 Sair", use_container_width=True):
        logout()

# ===== MAIN CONTENT =====
if pagina == "📥 Importação":
    mod_importacao.render()
elif pagina == "📦 Controle de Estoque":
    mod_estoque.render()
elif pagina == "💰 Financeiro":
    mod_financeiro.render()
elif pagina == "📋 Gestão de Notas":
    mod_gestao_notas.render()
