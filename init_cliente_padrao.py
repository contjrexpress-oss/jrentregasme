"""
Script de inicialização do cliente padrão G GARRAFEIRA.
Verifica se já existe no banco de dados e, se não, cadastra com dados completos.
Executar uma vez: python init_cliente_padrao.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import init_db, inserir_cliente, buscar_cliente_por_cnpj
from config import CLIENTE_PADRAO_CNPJ, CLIENTE_PADRAO_NOME


def inicializar_cliente_padrao():
    """Verifica e cadastra o cliente padrão G GARRAFEIRA se não existir."""
    # Inicializa banco se necessário
    init_db()

    # Verificar se já existe
    existente = buscar_cliente_por_cnpj(CLIENTE_PADRAO_CNPJ)
    if existente:
        print(f"✅ Cliente padrão já cadastrado:")
        print(f"   ID: {existente['id']}")
        print(f"   Nome: {existente['nome']}")
        print(f"   CNPJ: {existente['cpf_cnpj']}")
        print(f"   Bairro: {existente.get('bairro', '')}")
        print(f"   Cidade: {existente.get('cidade', '')}")
        return existente['id']

    # Cadastrar com dados completos
    sucesso, msg, cliente_id = inserir_cliente(
        nome=CLIENTE_PADRAO_NOME,
        cpf_cnpj=CLIENTE_PADRAO_CNPJ,
        telefone="+55 (21) 98121-4471",
        email="atendimento@grcaempresarial.com.br",
        endereco="Barra Olímpica",
        bairro="Barra Olímpica",
        cidade="Rio de Janeiro",
        cep="22775-024",
        observacoes="Cliente padrão do sistema. Tel2: +55 (21) 3195-3511 | Estado: RJ"
    )

    if sucesso:
        print(f"✅ Cliente padrão cadastrado com sucesso!")
        print(f"   ID: {cliente_id}")
        print(f"   Nome: {CLIENTE_PADRAO_NOME}")
        print(f"   CNPJ: {CLIENTE_PADRAO_CNPJ}")
        return cliente_id
    else:
        print(f"❌ Erro ao cadastrar cliente padrão: {msg}")
        return None


if __name__ == "__main__":
    resultado = inicializar_cliente_padrao()
    if resultado:
        print(f"\n🎯 Cliente padrão pronto (ID: {resultado})")
    else:
        print("\n⚠️ Falha ao inicializar cliente padrão")
        sys.exit(1)
