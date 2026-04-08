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
import mod_dashboard
import mod_importacao
import mod_estoque
import mod_financeiro
import mod_cadastros
import mod_gestao_notas
import mod_backup
import base64
import os

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
    # Logo da empresa
    logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            logo_b64 = base64.b64encode(f.read()).decode()
        st.markdown(
            f"""
            <div style="text-align:center; padding: 0.5rem 0 0.2rem 0;">
                <img src="data:image/png;base64,{logo_b64}" 
                     style="max-width: 160px; border-radius: 12px;" />
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown("### 📦 JR ENTREGAS ME")

    st.markdown("---")
    
    nome = st.session_state.get('nome', '')
    role = get_user_role()
    role_label = "🔑 Administrador" if role == "admin" else "👤 Equipe"
    st.markdown(f"**{nome}** | {role_label}")
    st.markdown("---")
    
    # Menu based on role - Dashboard always first
    if is_admin():
        menu_options = [
            "🏠 Dashboard",
            "📥 Importação",
            "📦 Controle de Estoque",
            "💰 Financeiro",
            "👥 Cadastros",
            "📋 Gestão de Notas",
            "💾 Backup"
        ]
    else:
        menu_options = [
            "🏠 Dashboard",
            "📦 Controle de Estoque",
            "👥 Cadastros"
        ]
    
    pagina = st.radio("Menu", menu_options, label_visibility="collapsed")
    
    st.markdown("---")
    if st.button("🚪 Sair", use_container_width=True):
        logout()

# ===== MAIN CONTENT =====
if pagina == "🏠 Dashboard":
    mod_dashboard.render()
elif pagina == "📥 Importação":
    mod_importacao.render()
elif pagina == "📦 Controle de Estoque":
    mod_estoque.render()
elif pagina == "💰 Financeiro":
    mod_financeiro.render()
elif pagina == "👥 Cadastros":
    mod_cadastros.render()
elif pagina == "📋 Gestão de Notas":
    mod_gestao_notas.render()
elif pagina == "💾 Backup":
    mod_backup.render()
