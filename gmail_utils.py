"""
Utilitário para buscar e baixar DANFEs (PDFs) do Gmail.
Usa a API REST do Gmail com o token OAuth armazenado pelo conector Abacus AI.
"""

import json
import os
import re
import base64
import requests
from datetime import datetime, timedelta
from io import BytesIO

AUTH_SECRETS_PATH = os.path.expanduser("~/.config/abacusai_auth_secrets.json")
GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"


def _get_access_token():
    """Lê o access_token do Gmail armazenado pelo conector OAuth."""
    try:
        with open(AUTH_SECRETS_PATH, "r") as f:
            data = json.load(f)
        return data["gmailuser"]["secrets"]["access_token"]["value"]
    except Exception as e:
        raise RuntimeError(f"Erro ao ler token do Gmail: {e}")


def _headers():
    token = _get_access_token()
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }


def buscar_emails_com_pdf(remetente="pedidos@grapy.com.br", dias=7, data_inicio=None, data_fim=None):
    """
    Busca emails do remetente com anexos, filtrados por período.
    
    Args:
        remetente: email do remetente
        dias: últimos N dias (usado se data_inicio/data_fim não fornecidos)
        data_inicio: datetime ou None
        data_fim: datetime ou None
    
    Returns:
        list of dict com informações dos emails encontrados
    """
    # Construir query do Gmail
    query_parts = [f"from:{remetente}", "has:attachment", "filename:pdf"]
    
    if data_inicio and data_fim:
        query_parts.append(f"after:{data_inicio.strftime('%Y/%m/%d')}")
        query_parts.append(f"before:{(data_fim + timedelta(days=1)).strftime('%Y/%m/%d')}")
    else:
        data_ref = datetime.now() - timedelta(days=dias)
        query_parts.append(f"after:{data_ref.strftime('%Y/%m/%d')}")
    
    query = " ".join(query_parts)
    
    # Buscar IDs dos emails
    params = {"q": query, "maxResults": 50}
    resp = requests.get(f"{GMAIL_API_BASE}/messages", headers=_headers(), params=params, timeout=30)
    resp.raise_for_status()
    result = resp.json()
    
    mensagens = result.get("messages", [])
    if not mensagens:
        return []
    
    # Para cada email, buscar detalhes
    emails_info = []
    for msg_ref in mensagens:
        msg_id = msg_ref["id"]
        try:
            msg_detail = _get_message_detail(msg_id)
            if msg_detail:
                emails_info.append(msg_detail)
        except Exception:
            continue
    
    return emails_info


def _get_message_detail(msg_id):
    """Obtém detalhes de um email específico (assunto, data, anexos PDF)."""
    resp = requests.get(
        f"{GMAIL_API_BASE}/messages/{msg_id}",
        headers=_headers(),
        params={"format": "full"},
        timeout=30
    )
    resp.raise_for_status()
    msg = resp.json()
    
    # Extrair headers
    headers_list = msg.get("payload", {}).get("headers", [])
    subject = ""
    date_str = ""
    from_addr = ""
    for h in headers_list:
        name = h.get("name", "").lower()
        if name == "subject":
            subject = h.get("value", "")
        elif name == "date":
            date_str = h.get("value", "")
        elif name == "from":
            from_addr = h.get("value", "")
    
    # Parsear data
    data_email = _parse_email_date(date_str)
    
    # Encontrar anexos PDF
    pdf_attachments = []
    _find_pdf_attachments(msg.get("payload", {}), msg_id, pdf_attachments)
    
    if not pdf_attachments:
        return None
    
    return {
        "msg_id": msg_id,
        "subject": subject,
        "from": from_addr,
        "date": data_email,
        "date_str": date_str,
        "pdf_attachments": pdf_attachments,  # list of {filename, attachment_id, size}
    }


def _find_pdf_attachments(payload, msg_id, results):
    """Recursivamente encontra anexos PDF no payload do email."""
    filename = payload.get("filename", "")
    mime = payload.get("mimeType", "")
    body = payload.get("body", {})
    attachment_id = body.get("attachmentId", "")
    size = body.get("size", 0)
    
    if filename and attachment_id and (
        mime == "application/pdf" or filename.lower().endswith(".pdf")
    ):
        results.append({
            "filename": filename,
            "attachment_id": attachment_id,
            "size": size,
            "msg_id": msg_id,
        })
    
    # Verificar partes recursivamente
    for part in payload.get("parts", []):
        _find_pdf_attachments(part, msg_id, results)


def baixar_anexo_pdf(msg_id, attachment_id, filename):
    """
    Baixa um anexo PDF do Gmail e retorna como BytesIO.
    
    Returns:
        BytesIO com o conteúdo do PDF
    """
    resp = requests.get(
        f"{GMAIL_API_BASE}/messages/{msg_id}/attachments/{attachment_id}",
        headers=_headers(),
        timeout=60
    )
    resp.raise_for_status()
    data = resp.json()
    
    # O Gmail retorna o conteúdo em base64url encoding
    file_data = data.get("data", "")
    # Converter base64url para bytes
    file_bytes = base64.urlsafe_b64decode(file_data + "==")
    
    return BytesIO(file_bytes)


def _parse_email_date(date_str):
    """Tenta parsear a data do email em formato legível."""
    if not date_str:
        return ""
    
    # Formatos comuns de data de email
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S",
    ]
    
    # Limpar possíveis parênteses no final ex: "(BRT)"
    clean = re.sub(r'\s*\([^)]*\)\s*$', '', date_str.strip())
    
    for fmt in formats:
        try:
            dt = datetime.strptime(clean, fmt)
            return dt.strftime("%d/%m/%Y %H:%M")
        except ValueError:
            continue
    
    return date_str


class PdfFileWrapper:
    """
    Wrapper para BytesIO que emula a interface de UploadedFile do Streamlit,
    necessária para ser usada com extrair_dados_danfe().
    """
    def __init__(self, bytesio, name):
        self._bytesio = bytesio
        self.name = name
    
    def read(self):
        return self._bytesio.read()
    
    def seek(self, pos):
        self._bytesio.seek(pos)
    
    def tell(self):
        return self._bytesio.tell()
