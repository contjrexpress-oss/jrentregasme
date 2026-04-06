def get_css():
    return """
    <style>
        /* ===== GLOBAL ===== */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        .stApp {
            background-color: #F4F7F6;
            font-family: 'Inter', sans-serif;
        }
        
        /* ===== SIDEBAR ===== */
        section[data-testid="stSidebar"] {
            background-color: #0B132B;
            border-right: 4px solid #F29F05;
        }
        section[data-testid="stSidebar"] .stMarkdown h1,
        section[data-testid="stSidebar"] .stMarkdown h2,
        section[data-testid="stSidebar"] .stMarkdown h3,
        section[data-testid="stSidebar"] .stMarkdown p,
        section[data-testid="stSidebar"] .stMarkdown li,
        section[data-testid="stSidebar"] .stMarkdown span,
        section[data-testid="stSidebar"] .stMarkdown label,
        section[data-testid="stSidebar"] label {
            color: #F4F7F6 !important;
        }
        section[data-testid="stSidebar"] .stRadio label {
            color: #F4F7F6 !important;
        }
        section[data-testid="stSidebar"] hr {
            border-color: #F29F05;
        }
        
        /* ===== HEADER ===== */
        .main-header {
            background: linear-gradient(135deg, #0B132B 0%, #1C2541 100%);
            color: #F4F7F6;
            padding: 1.5rem 2rem;
            border-radius: 12px;
            margin-bottom: 1.5rem;
            border-left: 5px solid #F29F05;
        }
        .main-header h1 {
            color: #F29F05 !important;
            margin: 0;
            font-size: 1.8rem;
        }
        .main-header p {
            color: #a0aec0;
            margin: 0.3rem 0 0 0;
            font-size: 0.95rem;
        }
        
        /* ===== CARDS ===== */
        .card {
            background: #FFFFFF;
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
            margin-bottom: 1rem;
            border: 1px solid #e2e8f0;
        }
        .card-header {
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
            border-radius: 12px;
            padding: 1.2rem;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
            text-align: center;
            border-top: 4px solid #F29F05;
        }
        .metric-card .value {
            font-size: 1.8rem;
            font-weight: 700;
            color: #0B132B;
        }
        .metric-card .label {
            font-size: 0.85rem;
            color: #718096;
            margin-top: 0.3rem;
        }
        .metric-green { border-top-color: #38A169; }
        .metric-green .value { color: #38A169; }
        .metric-red { border-top-color: #E53E3E; }
        .metric-red .value { color: #E53E3E; }
        .metric-blue { border-top-color: #3182CE; }
        .metric-blue .value { color: #3182CE; }
        .metric-orange { border-top-color: #F29F05; }
        .metric-orange .value { color: #F29F05; }
        
        /* ===== BUTTONS ===== */
        .stButton > button {
            border-radius: 8px;
            font-weight: 600;
            padding: 0.5rem 1.5rem;
            border: none;
            transition: all 0.2s ease;
        }
        .stButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }
        .stButton > button[kind="primary"] {
            background-color: #F29F05;
            color: #0B132B;
        }
        
        /* ===== LOGIN ===== */
        .login-container {
            max-width: 400px;
            margin: 5rem auto;
            background: #FFFFFF;
            border-radius: 16px;
            padding: 2.5rem;
            box-shadow: 0 8px 32px rgba(11, 19, 43, 0.12);
            border-top: 5px solid #F29F05;
        }
        .login-container h2 {
            text-align: center;
            color: #0B132B;
            margin-bottom: 0.3rem;
        }
        .login-container .subtitle {
            text-align: center;
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
            border-radius: 8px;
            overflow: hidden;
        }
        
        /* ===== TAGS ===== */
        .tag-entrada {
            background-color: #C6F6D5;
            color: #22543D;
            padding: 0.2rem 0.8rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        .tag-saida {
            background-color: #FED7D7;
            color: #742A2A;
            padding: 0.2rem 0.8rem;
            border-radius: 20px;
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
        
        /* ===== TABS ===== */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 8px 8px 0 0;
            padding: 0.5rem 1.5rem;
            font-weight: 600;
        }
        .stTabs [aria-selected="true"] {
            background-color: #0B132B;
            color: #F29F05;
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
