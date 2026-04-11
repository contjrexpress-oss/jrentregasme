def get_css():
    return """
    <style>
        /* ===== GOOGLE FONTS ===== */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Poppins:wght@400;500;600;700;800&display=swap');

        /* ===== GLOBAL TYPOGRAPHY & BASE ===== */
        .stApp {
            background-color: #F4F7F6;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }

        /* ===== HIERARQUIA TIPOGRÁFICA ===== */
        .stApp [data-testid="stAppViewContainer"] .stMarkdown h1 {
            font-family: 'Poppins', sans-serif !important;
            font-size: 2rem !important;
            font-weight: 700 !important;
            color: #0B132B !important;
            line-height: 1.3 !important;
            letter-spacing: -0.02em;
        }
        .stApp [data-testid="stAppViewContainer"] .stMarkdown h2 {
            font-family: 'Poppins', sans-serif !important;
            font-size: 1.5rem !important;
            font-weight: 600 !important;
            color: #0B132B !important;
            line-height: 1.35 !important;
            letter-spacing: -0.01em;
        }
        .stApp [data-testid="stAppViewContainer"] .stMarkdown h3 {
            font-family: 'Poppins', sans-serif !important;
            font-size: 1.25rem !important;
            font-weight: 500 !important;
            color: #0B132B !important;
            line-height: 1.4 !important;
        }
        .stApp [data-testid="stAppViewContainer"] .stMarkdown h4,
        .stApp [data-testid="stAppViewContainer"] .stMarkdown h5 {
            font-family: 'Poppins', sans-serif !important;
            font-weight: 600 !important;
            color: #0B132B !important;
            line-height: 1.4 !important;
        }
        .stApp [data-testid="stAppViewContainer"] .stMarkdown p,
        .stApp [data-testid="stAppViewContainer"] .stMarkdown li,
        .stApp [data-testid="stAppViewContainer"] .stMarkdown span {
            font-family: 'Inter', sans-serif;
            font-size: 1rem;
            color: #2D3748;
            line-height: 1.6;
        }
        .stApp [data-testid="stAppViewContainer"] .stMarkdown small,
        .stApp [data-testid="stAppViewContainer"] .stCaption {
            font-family: 'Inter', sans-serif;
            font-size: 0.875rem;
            color: #718096;
            line-height: 1.5;
        }

        /* ===== HIDE SIDEBAR COMPLETELY ===== */
        section[data-testid="stSidebar"] {
            display: none !important;
        }
        [data-testid="stSidebarCollapsedControl"],
        [data-testid="collapsedControl"] {
            display: none !important;
        }

        /* ===== HEADER ===== */
        .main-header {
            background: linear-gradient(135deg, #0B132B 0%, #1C2541 100%) !important;
            color: #FFFFFF !important;
            padding: 1.8rem 2rem;
            border-radius: 14px;
            margin-bottom: 1.5rem;
            border-left: 5px solid #F29F05;
            box-shadow: 0 4px 20px rgba(11, 19, 43, 0.18);
        }
        .main-header * {
            color: #FFFFFF !important;
        }
        .main-header h1 {
            font-family: 'Poppins', sans-serif !important;
            color: #F29F05 !important;
            margin: 0;
            font-size: 1.8rem;
            font-weight: 700;
            letter-spacing: -0.01em;
        }
        .main-header h2, .main-header h3,
        .main-header h4, .main-header h5 {
            font-family: 'Poppins', sans-serif !important;
            color: #F29F05 !important;
            font-weight: 600 !important;
        }
        .main-header p, .main-header span,
        .main-header div, .main-header label {
            font-family: 'Inter', sans-serif;
            color: #E2E8F0 !important;
            margin: 0.4rem 0 0 0;
            font-size: 0.95rem;
            font-weight: 400;
            line-height: 1.5;
        }

        /* ===== CARDS ===== */
        .card {
            background: #FFFFFF;
            border-radius: 14px;
            padding: 1.5rem;
            box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
            margin-bottom: 1rem;
            border: 1px solid #E2E8F0;
            transition: box-shadow 0.25s ease;
        }
        .card:hover {
            box-shadow: 0 4px 18px rgba(0, 0, 0, 0.09);
        }
        .card-header {
            font-family: 'Poppins', sans-serif;
            font-size: 1.1rem;
            font-weight: 600;
            color: #0B132B;
            margin-bottom: 0.8rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid #F29F05;
        }

        /* ===== METRIC CARDS ===== */
        .metric-card {
            background: #FFFFFF;
            border-radius: 14px;
            padding: 1.3rem 1rem;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.06);
            text-align: center;
            border-top: 4px solid #F29F05;
            min-height: 105px;
            transition: transform 0.25s ease, box-shadow 0.25s ease;
        }
        .metric-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.12);
        }
        .metric-card .value {
            font-family: 'Poppins', sans-serif;
            font-size: 1.9rem;
            font-weight: 700;
            color: #0B132B;
            line-height: 1.2;
        }
        .metric-card .label {
            font-family: 'Inter', sans-serif;
            font-size: 0.85rem;
            color: #718096;
            margin-top: 0.35rem;
            font-weight: 500;
            line-height: 1.4;
        }
        .metric-green { border-top-color: #38A169; }
        .metric-green .value { color: #38A169; }
        .metric-red { border-top-color: #E53E3E; }
        .metric-red .value { color: #E53E3E; }
        .metric-blue { border-top-color: #3182CE; }
        .metric-blue .value { color: #3182CE; }
        .metric-orange { border-top-color: #F29F05; }
        .metric-orange .value { color: #F29F05; }

        /* ===== DARK BACKGROUND CARDS ===== */
        .dark-card {
            background: linear-gradient(135deg, #0B132B 0%, #1C2541 100%) !important;
            border-radius: 14px;
            padding: 1.5rem;
            color: #FFFFFF !important;
        }
        .dark-card * {
            color: #FFFFFF !important;
        }
        .dark-card h1, .dark-card h2, .dark-card h3,
        .dark-card h4, .dark-card h5, .dark-card h6 {
            color: #F29F05 !important;
            font-family: 'Poppins', sans-serif !important;
            font-weight: 600 !important;
        }
        .dark-card p, .dark-card span, .dark-card li,
        .dark-card label, .dark-card div {
            color: #FFFFFF !important;
            font-weight: 500;
            line-height: 1.6;
        }

        /* ===== REGRA GERAL: fundo azul escuro = texto branco ===== */
        [style*="background"][style*="#0B132B"] *,
        [style*="background"][style*="#1C2541"] *,
        [style*="background-color"][style*="#0B132B"] *,
        [style*="background-color"][style*="#1C2541"] * {
            color: #FFFFFF !important;
        }

        /* ===== BUTTONS ===== */
        .stButton > button {
            font-family: 'Inter', sans-serif;
            border-radius: 8px;
            font-weight: 600;
            font-size: 0.9rem;
            padding: 0.55rem 1.5rem;
            border: none;
            transition: all 0.25s ease;
            letter-spacing: 0.01em;
        }
        .stButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.14);
        }
        .stButton > button[kind="primary"] {
            background-color: #F29F05 !important;
            color: #FFFFFF !important;
            font-weight: 700;
        }
        .stButton > button[kind="primary"]:hover {
            background-color: #FFAF1A !important;
            box-shadow: 0 4px 16px rgba(242, 159, 5, 0.35);
        }
        .stButton > button[kind="secondary"],
        .stButton > button:not([kind="primary"]) {
            background-color: #1C2541;
            color: #FFFFFF !important;
            border: 1px solid #2D3A5C;
        }
        .stButton > button[kind="secondary"]:hover,
        .stButton > button:not([kind="primary"]):hover {
            background-color: #243056;
            color: #FFFFFF !important;
        }

        /* ===== LOGIN ===== */
        .login-container {
            max-width: 420px;
            margin: 5rem auto;
            background: #FFFFFF;
            border-radius: 18px;
            padding: 2.5rem;
            box-shadow: 0 8px 40px rgba(11, 19, 43, 0.12);
            border-top: 5px solid #F29F05;
        }
        .login-container h2 {
            text-align: center;
            font-family: 'Poppins', sans-serif;
            color: #0B132B;
            margin-bottom: 0.3rem;
            font-weight: 700;
        }
        .login-container .subtitle {
            text-align: center;
            font-family: 'Inter', sans-serif;
            color: #718096;
            margin-bottom: 1.5rem;
            font-size: 0.9rem;
        }
        .login-logo {
            text-align: center;
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
        }

        /* ===== TABLES ===== */
        .stDataFrame {
            border-radius: 10px;
            overflow: hidden;
            font-family: 'Inter', sans-serif;
        }
        .stDataFrame [data-testid="stDataFrameResizable"] {
            border-radius: 12px;
            overflow: hidden;
        }

        /* ===== TAGS ===== */
        .tag-entrada {
            background-color: #C6F6D5;
            color: #22543D;
            padding: 0.2rem 0.8rem;
            border-radius: 20px;
            font-family: 'Inter', sans-serif;
            font-size: 0.8rem;
            font-weight: 600;
        }
        .tag-saida {
            background-color: #FED7D7;
            color: #742A2A;
            padding: 0.2rem 0.8rem;
            border-radius: 20px;
            font-family: 'Inter', sans-serif;
            font-size: 0.8rem;
            font-weight: 600;
        }

        /* ===== HIDE STREAMLIT DEFAULTS ===== */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}

        /* ===== FILE UPLOADER ===== */
        .stFileUploader {
            border-radius: 12px;
        }

        /* ===== MAIN NAVIGATION TABS ===== */
        .stTabs [data-baseweb="tab-list"] {
            gap: 4px;
            background: linear-gradient(135deg, #0B132B 0%, #1C2541 100%);
            border-radius: 12px;
            padding: 6px 8px;
            box-shadow: 0 2px 12px rgba(11, 19, 43, 0.15);
        }
        .stTabs [data-baseweb="tab"] {
            font-family: 'Inter', sans-serif;
            border-radius: 8px;
            padding: 0.6rem 1.2rem;
            font-weight: 600;
            font-size: 0.88rem;
            color: #A0AEC0 !important;
            background-color: transparent;
            transition: all 0.25s ease;
            border: none !important;
            white-space: nowrap;
        }
        .stTabs [data-baseweb="tab"]:hover {
            background-color: rgba(242, 159, 5, 0.15);
            color: #F29F05 !important;
        }
        .stTabs [aria-selected="true"] {
            background-color: #F29F05 !important;
            color: #0B132B !important;
            font-weight: 700;
            border-bottom: none;
            box-shadow: 0 2px 8px rgba(242, 159, 5, 0.3);
            border-radius: 8px;
        }
        /* Tab highlight bar */
        .stTabs [data-baseweb="tab-highlight"] {
            display: none !important;
        }
        .stTabs [data-baseweb="tab-border"] {
            display: none !important;
        }

        /* ===== EXPANDERS ===== */
        .streamlit-expanderHeader {
            font-family: 'Inter', sans-serif;
            background-color: #FFFFFF;
            border-radius: 8px;
            color: #0B132B !important;
            font-weight: 600;
        }

        /* ===== INFO/WARNING/SUCCESS BOXES ===== */
        .stAlert {
            border-radius: 10px;
            font-family: 'Inter', sans-serif;
            line-height: 1.6;
        }

        /* ===== CONTAINERS ===== */
        [data-testid="stAppViewContainer"] > .main > div {
            color: #2D3748;
            font-family: 'Inter', sans-serif;
        }

        /* ===== SELECTBOX & INPUTS ===== */
        [data-testid="stAppViewContainer"] .stSelectbox label,
        [data-testid="stAppViewContainer"] .stTextInput label,
        [data-testid="stAppViewContainer"] .stNumberInput label,
        [data-testid="stAppViewContainer"] .stDateInput label,
        [data-testid="stAppViewContainer"] .stFileUploader label,
        [data-testid="stAppViewContainer"] .stTextArea label,
        [data-testid="stAppViewContainer"] .stRadio > label,
        [data-testid="stAppViewContainer"] .stCheckbox label {
            font-family: 'Inter', sans-serif !important;
            color: #2D3748 !important;
            font-weight: 500 !important;
            font-size: 0.9rem;
        }
        .stTextInput input, .stNumberInput input,
        .stSelectbox [data-baseweb="select"],
        .stTextArea textarea {
            font-family: 'Inter', sans-serif;
            font-size: 0.95rem;
            border-radius: 8px;
        }

        /* ===== PLOTLY CHART CONTAINERS ===== */
        .js-plotly-plot {
            border-radius: 14px;
            background: #FFFFFF;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.06);
            padding: 10px;
        }

        /* ===== DASHBOARD SECTION HEADERS ===== */
        .stApp [data-testid="stAppViewContainer"] h4,
        .stApp [data-testid="stAppViewContainer"] h5 {
            font-family: 'Poppins', sans-serif !important;
            color: #0B132B !important;
            font-weight: 600 !important;
        }

        /* ===== RESPONSIVE ===== */
        @media (max-width: 768px) {
            .metric-card .value {
                font-size: 1.3rem;
            }
            .metric-card .label {
                font-size: 0.75rem;
            }
            .main-header h1 {
                font-size: 1.3rem;
            }
            .main-header p {
                font-size: 0.85rem;
            }
            .stTabs [data-baseweb="tab"] {
                padding: 0.4rem 0.6rem;
                font-size: 0.75rem;
            }
            .stTabs [data-baseweb="tab-list"] {
                padding: 4px;
                gap: 2px;
            }
        }

        /* ===== SCROLLBAR ===== */
        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }
        ::-webkit-scrollbar-track {
            background: #F4F7F6;
        }
        ::-webkit-scrollbar-thumb {
            background: #CBD5E0;
            border-radius: 3px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #A0AEC0;
        }

        /* ===== ACCESSIBILITY ===== */
        * {
            -webkit-tap-highlight-color: transparent;
        }
        a:focus, button:focus, input:focus, select:focus, textarea:focus {
            outline: 2px solid #F29F05;
            outline-offset: 2px;
        }
    </style>
    """

def metric_card(label, value, color_class=""):
    return f"""
    <div class="metric-card {color_class}">
        <div class="value">{value}</div>
        <div class="label">{label}</div>
    </div>
    """

def page_header(title, subtitle=""):
    return f"""
    <div class="main-header">
        <h1>{title}</h1>
        <p>{subtitle}</p>
    </div>
    """

def card_start(title=""):
    header = f'<div class="card-header">{title}</div>' if title else ""
    return f'<div class="card">{header}'

def card_end():
    return '</div>'

def dark_card_start(title=""):
    header = f'<h3>{title}</h3>' if title else ""
    return f'<div class="dark-card">{header}'

def dark_card_end():
    return '</div>'
