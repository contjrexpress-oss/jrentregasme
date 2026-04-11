import streamlit as st

st.set_page_config(
    page_title="JR ENTREGAS ME - ERP",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed"
)

from styles import get_css, page_header
from database import (
    init_db,
    contar_produtos_total,
    contar_clientes,
    obter_faturamento_mes_atual,
    obter_custos_mes_atual,
    contar_produtos_estoque_critico,
    obter_contas_vencer_proximos_dias,
    obter_log_acoes,
)
from auth import (
    check_login, login_page, logout, is_admin,
    get_user_perfil, get_perfil_label, pode_visualizar,
    get_user_nome, get_username, eh_admin,
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
from utils import formatar_moeda_br

# Initialize database
init_db()

# Apply custom CSS
st.markdown(get_css(), unsafe_allow_html=True)

# Check authentication
if not check_login():
    login_page()
    st.stop()

# ===== HIDE SIDEBAR COMPLETELY =====
st.markdown("""
<style>
    section[data-testid="stSidebar"] { display: none !important; }
    [data-testid="stSidebarCollapsedControl"] { display: none !important; }
    [data-testid="collapsedControl"] { display: none !important; }
    button[kind="header"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ===== TOP BAR =====
def _render_top_bar():
    """Renderiza a barra superior com logo, info do usuário e botão sair."""
    col_logo, col_info, col_sair = st.columns([4, 4, 1])

    with col_logo:
        if os.path.exists(LOGO_PATH):
            with open(LOGO_PATH, "rb") as f:
                logo_b64 = base64.b64encode(f.read()).decode()
            st.markdown(
                f"""
                <div style="display: flex; align-items: center; gap: 12px; padding: 4px 0;">
                    <img src="data:image/png;base64,{logo_b64}" 
                         style="height: 48px; border-radius: 8px;" />
                    <div>
                        <span style="font-family: 'Poppins', sans-serif; font-size: 1.3rem; 
                              font-weight: 700; color: #0B132B;">
                            {EMPRESA_NOME}
                        </span>
                        <br/>
                        <span style="font-family: 'Inter', sans-serif; font-size: 0.8rem; 
                              color: #718096;">
                            Sistema de Gestão Empresarial
                        </span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(f"### 📦 {EMPRESA_NOME}")

    with col_info:
        nome = get_user_nome()
        perfil_label = get_perfil_label()
        st.markdown(
            f"""
            <div style="display: flex; align-items: center; justify-content: flex-end; 
                        height: 100%; gap: 16px; padding-top: 8px;">
                <span style="font-family: 'Inter', sans-serif; font-size: 0.92rem; color: #2D3748;">
                    👤 <strong>{nome}</strong>
                </span>
                <span style="background: #1C2541; color: #F29F05; padding: 4px 12px; 
                             border-radius: 20px; font-size: 0.8rem; font-weight: 600;
                             font-family: 'Inter', sans-serif;">
                    {perfil_label}
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_sair:
        st.markdown("<div style='padding-top: 6px;'></div>", unsafe_allow_html=True)
        if st.button("🚪 Sair", use_container_width=True, key="btn_sair_top"):
            logout()

    st.markdown("<hr style='margin: 8px 0 4px 0; border-color: rgba(0,0,0,0.08);'/>", unsafe_allow_html=True)


# ===== DASHBOARD PRINCIPAL =====
def render_dashboard_principal():
    """Renderiza o Dashboard Principal com métricas, alertas e atividades recentes."""
    st.markdown(
        page_header("📊 Dashboard Principal", f"Visão geral do sistema {EMPRESA_NOME}"),
        unsafe_allow_html=True,
    )

    # --- Métricas principais ---
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_produtos = contar_produtos_total()
        st.markdown(_metric_card_html("📦 Produtos", str(total_produtos), "metric-blue"), unsafe_allow_html=True)

    with col2:
        clientes_info = contar_clientes()
        total_clientes = clientes_info.get('ativos', 0)
        st.markdown(_metric_card_html("👥 Clientes", str(total_clientes), "metric-blue"), unsafe_allow_html=True)

    with col3:
        faturamento_mes = obter_faturamento_mes_atual()
        st.markdown(_metric_card_html("💰 Faturamento Mês", formatar_moeda_br(faturamento_mes), "metric-green"), unsafe_allow_html=True)

    with col4:
        produtos_criticos = contar_produtos_estoque_critico()
        cor_critico = "metric-red" if produtos_criticos > 0 else "metric-green"
        st.markdown(_metric_card_html("⚠️ Estoque Crítico", str(produtos_criticos), cor_critico), unsafe_allow_html=True)

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # --- Segunda linha: Custos e Lucro ---
    col5, col6, col7, col8 = st.columns(4)

    with col5:
        custos_mes = obter_custos_mes_atual()
        st.markdown(_metric_card_html("📉 Custos Mês", formatar_moeda_br(custos_mes), "metric-red"), unsafe_allow_html=True)

    with col6:
        lucro = faturamento_mes - custos_mes
        cor_lucro = "metric-green" if lucro >= 0 else "metric-red"
        st.markdown(_metric_card_html("📈 Lucro Líquido", formatar_moeda_br(lucro), cor_lucro), unsafe_allow_html=True)

    with col7:
        contas_vencer = obter_contas_vencer_proximos_dias(7)
        n_contas = len(contas_vencer)
        cor_contas = "metric-orange" if n_contas > 0 else "metric-green"
        st.markdown(_metric_card_html("📅 Contas a Vencer (7d)", str(n_contas), cor_contas), unsafe_allow_html=True)

    with col8:
        st.markdown(_metric_card_html("🏢 Sistema", "Ativo ✅", "metric-green"), unsafe_allow_html=True)

    st.divider()

    # --- Alertas ---
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("##### 🔔 Alertas e Notificações")
        if produtos_criticos > 0:
            st.warning(f"⚠️ **{produtos_criticos}** produto(s) com estoque crítico. Verifique o módulo de Estoque.")
        if n_contas > 0:
            st.info(f"📅 **{n_contas}** conta(s) a vencer nos próximos 7 dias. Verifique o módulo Financeiro.")
        if produtos_criticos == 0 and n_contas == 0:
            st.success("✅ Nenhum alerta no momento. Tudo em ordem!")

    with col_right:
        st.markdown("##### 📝 Últimas Atividades")
        ultimas = obter_log_acoes(limite=8)
        if ultimas:
            for acao in ultimas[:8]:
                data_str = acao.get('data_hora', '')[:16].replace('T', ' ') if acao.get('data_hora') else ''
                usuario_acao = acao.get('usuario', '')
                tipo = acao.get('acao', '')
                detalhe = acao.get('detalhes', '')
                # Truncar detalhes longos
                if len(detalhe) > 60:
                    detalhe = detalhe[:60] + "..."
                st.markdown(
                    f"<div style='font-size: 0.85rem; padding: 4px 0; border-bottom: 1px solid #EDF2F7;'>"
                    f"<strong style='color: #1C2541;'>{tipo}</strong> "
                    f"<span style='color: #718096;'>— {usuario_acao} — {data_str}</span>"
                    f"<br/><span style='color: #4A5568;'>{detalhe}</span></div>",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("Nenhuma atividade registrada.")


def _metric_card_html(label, value, color_class=""):
    """Gera HTML para um card de métrica."""
    return f"""
    <div class="metric-card {color_class}">
        <div class="value">{value}</div>
        <div class="label">{label}</div>
    </div>
    """


# ===== MAIN LAYOUT =====
_render_top_bar()

# Build tabs based on permissions
abas_disponiveis = []
modulos_disponiveis = []

# Dashboard sempre disponível
abas_disponiveis.append("📊 Dashboard")
modulos_disponiveis.append("dashboard")

if pode_visualizar('importacao'):
    abas_disponiveis.append("📥 Importação")
    modulos_disponiveis.append("importacao")

if pode_visualizar('estoque'):
    abas_disponiveis.append("📦 Estoque")
    modulos_disponiveis.append("estoque")

if pode_visualizar('financeiro'):
    abas_disponiveis.append("💰 Financeiro")
    modulos_disponiveis.append("financeiro")

if pode_visualizar('cadastros'):
    abas_disponiveis.append("👥 Cadastros")
    modulos_disponiveis.append("cadastros")

if pode_visualizar('gestao_notas'):
    abas_disponiveis.append("📄 Gestão de Notas")
    modulos_disponiveis.append("gestao_notas")

if eh_admin():
    abas_disponiveis.append("👤 Usuários")
    modulos_disponiveis.append("usuarios")

    abas_disponiveis.append("💾 Backup")
    modulos_disponiveis.append("backup")

# Create horizontal tabs
tabs = st.tabs(abas_disponiveis)

# Render each tab content
for idx, modulo in enumerate(modulos_disponiveis):
    with tabs[idx]:
        if modulo == "dashboard":
            render_dashboard_principal()
        elif modulo == "importacao":
            mod_importacao.render()
        elif modulo == "estoque":
            mod_estoque.render()
        elif modulo == "financeiro":
            mod_financeiro.render()
        elif modulo == "cadastros":
            mod_cadastros.render()
        elif modulo == "gestao_notas":
            mod_gestao_notas.render()
        elif modulo == "usuarios":
            mod_usuarios.render()
        elif modulo == "backup":
            mod_backup.render()
