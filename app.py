import streamlit as st

st.set_page_config(
    page_title="JR ENTREGAS ME - ERP",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

from styles import get_css
from database import init_db
from auth import (
    check_login, login_page, logout, is_admin, 
    get_user_perfil, get_perfil_label, pode_visualizar
)
import mod_dashboard
import mod_importacao
import mod_estoque
import mod_financeiro
import mod_cadastros
import mod_gestao_notas
import mod_backup
import mod_usuarios
import base64
import os
from config import LOGO_PATH, EMPRESA_NOME

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
    if os.path.exists(LOGO_PATH):
        with open(LOGO_PATH, "rb") as f:
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
        st.markdown(f"### 📦 {EMPRESA_NOME}")

    st.markdown("---")
    
    nome = st.session_state.get('nome', '')
    perfil_label = get_perfil_label()
    st.markdown(f"**{nome}** | {perfil_label}")
    st.markdown("---")
    
    # Menu dinâmico baseado em permissões
    menu_options = []
    
    # Dashboard sempre disponível para ADM e FUNCIONARIOS
    if pode_visualizar('dashboard'):
        menu_options.append("🏠 Dashboard")
    
    if pode_visualizar('importacao'):
        menu_options.append("📥 Importação")
    
    if pode_visualizar('estoque'):
        menu_options.append("📦 Controle de Estoque")
    
    if pode_visualizar('financeiro'):
        menu_options.append("💰 Financeiro")
    
    if pode_visualizar('cadastros'):
        menu_options.append("👥 Cadastros")
    
    if pode_visualizar('gestao_notas'):
        menu_options.append("📋 Gestão de Notas")
    
    if pode_visualizar('backup'):
        menu_options.append("💾 Backup")
    
    if pode_visualizar('usuarios'):
        menu_options.append("👤 Usuários")
    
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
elif pagina == "👤 Usuários":
    mod_usuarios.render()
