def get_css():
    return """
    <style>
        /* ===== GLOBAL ===== */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        .stApp {
            background-color: #F4F7F6;
            font-family: 'Inter', sans-serif;
        }
        
        /* ===== SIDEBAR (clara) ===== */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #FFFFFF 0%, #F7F8FA 100%);
            border-right: 3px solid #F29F05;
            box-shadow: 2px 0 12px rgba(0, 0, 0, 0.06);
        }
        section[data-testid="stSidebar"] .stMarkdown h1,
        section[data-testid="stSidebar"] .stMarkdown h2,
        section[data-testid="stSidebar"] .stMarkdown h3 {
            color: #0B132B !important;
            font-weight: 700;
        }
        section[data-testid="stSidebar"] .stMarkdown p,
        section[data-testid="stSidebar"] .stMarkdown li,
        section[data-testid="stSidebar"] .stMarkdown span,
        section[data-testid="stSidebar"] .stMarkdown label,
        section[data-testid="stSidebar"] label {
            color: #2D3748 !important;
        }
        section[data-testid="stSidebar"] .stRadio label {
            color: #2D3748 !important;
            font-weight: 500;
            padding: 0.45rem 0.8rem;
            border-radius: 8px;
            transition: all 0.2s ease;
        }
        section[data-testid="stSidebar"] .stRadio label:hover {
            background-color: #FFF8E7;
            color: #0B132B !important;
        }
        section[data-testid="stSidebar"] .stRadio [data-checked="true"] + label,
        section[data-testid="stSidebar"] .stRadio label[data-checked="true"] {
            background-color: #FEF3CD;
            color: #0B132B !important;
            font-weight: 600;
        }
        section[data-testid="stSidebar"] hr {
            border-color: #E2E8F0;
            opacity: 0.7;
        }
        /* Sidebar button styling */
        section[data-testid="stSidebar"] .stButton > button {
            background-color: #FEF3CD;
            color: #0B132B;
            border: 1px solid #F29F05;
            font-weight: 600;
        }
        section[data-testid="stSidebar"] .stButton > button:hover {
            background-color: #F29F05;
            color: #FFFFFF;
        }
        
        /* ===== HEADER ===== */
        .main-header {
            background: #FFFFFF;
            color: #0B132B;
            padding: 1.5rem 2rem;
            border-radius: 12px;
            margin-bottom: 1.5rem;
            border-left: 5px solid #F29F05;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
        }
        .main-header h1 {
            color: #F29F05 !important;
            margin: 0;
            font-size: 1.8rem;
            font-weight: 700;
        }
        .main-header p {
            color: #4A5568;
            margin: 0.3rem 0 0 0;
            font-size: 0.95rem;
        }
        
        /* ===== CARDS ===== */
        .card {
            background: #FFFFFF;
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
            margin-bottom: 1rem;
            border: 1px solid #E2E8F0;
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
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
            text-align: center;
            border-top: 4px solid #F29F05;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .metric-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
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
            font-weight: 500;
        }
        .metric-green { border-top-color: #38A169; }
        .metric-green .value { color: #38A169; }
        .metric-red { border-top-color: #E53E3E; }
        .metric-red .value { color: #E53E3E; }
        .metric-blue { border-top-color: #3182CE; }
        .metric-blue .value { color: #3182CE; }
        .metric-orange { border-top-color: #F29F05; }
        .metric-orange .value { color: #F29F05; }
        
        /* ===== MAIN CONTENT TEXT ===== */
        .stApp [data-testid="stAppViewContainer"] .stMarkdown h1,
        .stApp [data-testid="stAppViewContainer"] .stMarkdown h2,
        .stApp [data-testid="stAppViewContainer"] .stMarkdown h3,
        .stApp [data-testid="stAppViewContainer"] .stMarkdown h4 {
            color: #0B132B !important;
        }
        .stApp [data-testid="stAppViewContainer"] .stMarkdown p,
        .stApp [data-testid="stAppViewContainer"] .stMarkdown li,
        .stApp [data-testid="stAppViewContainer"] .stMarkdown span {
            color: #2D3748;
        }

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
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
        }
        .stButton > button[kind="primary"] {
            background-color: #F29F05;
            color: #FFFFFF;
            font-weight: 700;
        }
        .stButton > button[kind="primary"]:hover {
            background-color: #D98E04;
        }
        
        /* ===== LOGIN ===== */
        .login-container {
            max-width: 400px;
            margin: 5rem auto;
            background: #FFFFFF;
            border-radius: 16px;
            padding: 2.5rem;
            box-shadow: 0 8px 32px rgba(11, 19, 43, 0.10);
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
            background-color: transparent;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 8px 8px 0 0;
            padding: 0.5rem 1.5rem;
            font-weight: 600;
            color: #4A5568;
            background-color: #EDF2F7;
            transition: all 0.2s ease;
        }
        .stTabs [data-baseweb="tab"]:hover {
            background-color: #E2E8F0;
        }
        .stTabs [aria-selected="true"] {
            background-color: #FFFFFF;
            color: #F29F05 !important;
            border-bottom: 3px solid #F29F05;
            box-shadow: 0 -2px 6px rgba(0, 0, 0, 0.04);
        }

        /* ===== EXPANDERS ===== */
        .streamlit-expanderHeader {
            background-color: #FFFFFF;
            border-radius: 8px;
            color: #0B132B !important;
            font-weight: 500;
        }

        /* ===== INFO/WARNING/SUCCESS BOXES ===== */
        .stAlert {
            border-radius: 8px;
        }

        /* ===== CONTAINERS / BLOCK CONTAINER ===== */
        [data-testid="stAppViewContainer"] > .main > div {
            color: #2D3748;
        }

        /* ===== SELECTBOX & INPUTS ===== */
        .stSelectbox label, .stTextInput label, .stNumberInput label,
        .stDateInput label, .stFileUploader label, .stTextArea label {
            color: #2D3748 !important;
            font-weight: 500;
        }

        /* ===== SCROLLBAR (sutil) ===== */
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
