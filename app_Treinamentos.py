import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import os
import re
import json

# Configuração da página
st.set_page_config(
    page_title="Sistema de Treinamentos - NORMAQ",
    page_icon="📚",
    layout="wide",
)

# Função para obter credenciais
def get_google_creds():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    try:
        # 1. Tenta usar arquivo local JSON
        if os.path.exists('credentials.json'):
            return Credentials.from_service_account_file('credentials.json', scopes=scopes)
        
        # 2. Tenta usar Streamlit Secrets no formato TOML
        elif 'gcp_service_account' in st.secrets:
            creds_info = dict(st.secrets['gcp_service_account'])
            return Credentials.from_service_account_info(creds_info, scopes=scopes)
        
        # 3. Tenta usar JSON direto nas Secrets
        elif 'GOOGLE_CREDENTIALS' in st.secrets:
            creds_json = json.loads(st.secrets['GOOGLE_CREDENTIALS'])
            return Credentials.from_service_account_info(creds_json, scopes=scopes)
        
        return None
            
    except Exception as e:
        st.sidebar.error(f"❌ Erro geral: {str(e)}")
        return None

# ======================
# Dados fixos (bases)
# ======================
BASE_FUNCAO = ["Mecânico I", "Mecânico II", "JTC", "Auxiliar de Mecânico", "Mecânico Champion"]

BASE_CATEGORIA = {
    "THL": "MANIPULADOR TELESCOPICO",
    "SSL": "PA CARREGADEIRA",
    "EXC": "ESCAVADEIRA HIDRAULICA",
    "BHL": "RETROESCAVADEIRA",
    "MINI": "ESCAVADEIRA HIDRAULICA",
    "WLS": "PA CARREGADEIRA",
    "CPTN": "ROLO COMPACTADOR",
    "THL e BHL": "MANIPULADOR TELESCOPICO / RETROESCAVADEIRA",
    "WLS e EXC": "PA CARREGADEIRA / ESCAVADEIRA HIDRAULICA",
    "TODAS": "TODOS MODELOS",
    "OUTROS": "Sem Dados"
}

BASE_TIPO_TREINAMENTO = [
    "Integração - 8h", "Tecnologias - 8h", "Condução Máquinas - 8h", 
    "Sistema Operacional Produtos Nacionais / Importados - 8h", "PMP - 8h",
    "Conjunto Motriz - JCB - 40h", "Motores - JCB - 40h", 
    "Sistemas Eletro - Hidráulicos THL e BHL - 40h", 
    "Sistemas Eletro - Hidráulicos WLS e EXC - 40h", 
    "Diagnóstico Powetrain JCB - 40h", 
    "Diagnóstico Sistemas Eletro-Hidráulicos Nacional - 40h", 
    "Diagnóstico Sistemas Eletro-Hidráulicos Importados - 40h", "JTC",
    "Integração I - 8h", "Integração II - 8h", "Integração III - 8h", 
    "Integração IV - 8h", "Conceitos - 8h", "Metrologia - 8h", 
    "Básico I - 8h", "Básico II - 8h", "Integração V - 4h", 
    "Básico III - 8h", "Integração VII - 4h", "Integração VIII - 4h", 
    "Integração VI - 4h"
]

BASE_MODALIDADE = ["A Definir", "Presencial", "Online"]
BASE_ENTREVISTA = ["OK", "-"]
BASE_STATUS = ["Pendente", "Apto p/ Treinamento", "Concluído", "Convocado", "Aprovado via Entrevista"]
BASE_SITUACAO = ["OK", "PENDENTE"]
BASE_TREINAMENTO = ["JCB", "NMQ"]
BASE_REVENDA = ["Recife", "Natal", "Fortaleza", "Petrolina"]

# ======================
# Funções de Sheets
# ======================
def load_sheet_data(client, spreadsheet_name, sheet_name):
    try:
        spreadsheet = client.open(spreadsheet_name)
        worksheet = spreadsheet.worksheet(sheet_name)
        records = worksheet.get_all_records()
        if not records:
            return pd.DataFrame()
        df = pd.DataFrame(records).dropna(how="all")
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error("Erro ao carregar dados da planilha")
        return pd.DataFrame()

def save_to_sheet(client, spreadsheet_name, sheet_name, data):
    try:
        spreadsheet = client.open(spreadsheet_name)
        worksheet = spreadsheet.worksheet(sheet_name)
        headers = worksheet.row_values(1)
        if not headers:
            headers = list(data.keys())
            worksheet.append_row(headers)
        row_data = [str(data.get(header, "")) for header in headers]
        worksheet.append_row(row_data)
        return True
    except Exception as e:
        st.error("Erro ao salvar dados na planilha")
        return False

def update_sheet_data(client, spreadsheet_name, sheet_name, row_index, data):
    try:
        spreadsheet = client.open(spreadsheet_name)
        worksheet = spreadsheet.worksheet(sheet_name)
        headers = worksheet.row_values(1)
        for col_name, value in data.items():
            if col_name in headers:
                col_index = headers.index(col_name) + 1
                worksheet.update_cell(row_index, col_index, str(value))
        return True
    except Exception as e:
        st.error("Erro ao atualizar dados")
        return False

def delete_from_sheet(client, spreadsheet_name, sheet_name, row_index):
    try:
        spreadsheet = client.open(spreadsheet_name)
        worksheet = spreadsheet.worksheet(sheet_name)
        worksheet.delete_rows(row_index)
        return True
    except Exception as e:
        st.error("Erro ao excluir dados")
        return False

# ======================
# Função principal
# ======================
def main():
    st.title("📚 Sistema de Gestão de Treinamentos de Técnicos - NORMAQ")
    
    # Inicializar cliente Google
    try:
        creds = get_google_creds()
        if creds is None:
            st.error("❌ Credenciais não encontradas. Configure o arquivo `credentials.json` ou as Secrets.")
            return
        
        client = gspread.authorize(creds)
        SPREADSHEET_NAME = "Treinamentos"
        SHEET_NAME = "Página1"
        df_treinamentos = load_sheet_data(client, SPREADSHEET_NAME, SHEET_NAME)
        st.success("✅ Conectado ao Google Sheets com sucesso!")
        
    except Exception as e:
        st.error("❌ Erro de conexão. Verifique credenciais e permissões do service account.")
        return
    
    # Abas do sistema
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Consulta", "➕ Cadastro", "✏️ Atualização", "🗑️ Exclusão"])
    
    # ======================
    # 📊 Consulta
    # ======================
    with tab1:
        st.header("📊 Consulta de Treinamentos")
        if not df_treinamentos.empty:
            st.dataframe(df_treinamentos)
        else:
            st.warning("Nenhum treinamento cadastrado.")

    # ======================
    # ➕ Cadastro
    # ======================
    with tab2:
        st.header("➕ Cadastro de Novo Treinamento")
        with st.form("form_cadastro"):
            col1, col2 = st.columns(2)
            with col1:
                treinamento = st.selectbox("Treinamento*", BASE_TREINAMENTO)
                classificacao = st.selectbox("Classificação*", BASE_FUNCAO)
                situacao = st.selectbox("Situação*", BASE_SITUACAO)
                categoria = st.selectbox("Categoria*", list(BASE_CATEGORIA.keys()))
                revenda = st.selectbox("Revenda*", BASE_REVENDA)
            with col2:
                tipo_treinamento = st.selectbox("Tipo de Treinamento*", BASE_TIPO_TREINAMENTO)
                modalidade = st.selectbox("Modalidade*", BASE_MODALIDADE)
                entrevista = st.selectbox("Entrevista*", BASE_ENTREVISTA)
                status = st.selectbox("Status*", BASE_STATUS)
                tecnico = st.text_input("Técnico*")
            submitted = st.form_submit_button("✅ Cadastrar Treinamento")
            if submitted:
                novo_treinamento = {
                    "Treinamento": treinamento,
                    "Classificação": classificacao,
                    "Situação": situacao,
                    "Categoria": categoria,
                    "Revenda": revenda,
                    "Tipo de Treinamento": tipo_treinamento,
                    "Modalidade": modalidade,
                    "Entrevista": entrevista,
                    "Status": status,
                    "Técnico": tecnico,
                    "Data Cadastro": datetime.now().strftime("%d/%m/%Y %H:%M")
                }
                if save_to_sheet(client, SPREADSHEET_NAME, SHEET_NAME, novo_treinamento):
                    st.success("🎉 Treinamento cadastrado com sucesso!")
                    st.balloons()
                else:
                    st.error("❌ Erro ao cadastrar treinamento.")

    # ======================
    # ✏️ Atualização
    # ======================
    with tab3:
        st.header("✏️ Atualização de Treinamentos")
        if not df_treinamentos.empty:
            treinamentos_lista = df_treinamentos.apply(
                lambda x: f"{x['Técnico']} - {x['Treinamento']}", axis=1
            ).tolist()
            treinamento_selecionado = st.selectbox("Selecione:", treinamentos_lista)
            if treinamento_selecionado:
                idx = treinamentos_lista.index(treinamento_selecionado)
                with st.form("form_atualizacao"):
                    nova_situacao = st.selectbox("Situação", BASE_SITUACAO)
                    novo_status = st.selectbox("Status", BASE_STATUS)
                    submitted = st.form_submit_button("💾 Atualizar")
                    if submitted:
                        dados_atualizados = {
                            "Situação": nova_situacao,
                            "Status": novo_status,
                            "Data Atualização": datetime.now().strftime("%d/%m/%Y %H:%M")
                        }
                        if update_sheet_data(client, SPREADSHEET_NAME, SHEET_NAME, idx + 2, dados_atualizados):
                            st.success("✅ Atualizado com sucesso!")
                        else:
                            st.error("❌ Erro ao atualizar treinamento.")
        else:
            st.warning("Nenhum treinamento para atualizar.")

    # ======================
    # 🗑️ Exclusão
    # ======================
    with tab4:
        st.header("🗑️ Exclusão de Treinamentos")
        if not df_treinamentos.empty:
            senha = st.text_input("Senha:", type="password")
            if senha == "NMQ@2025":
                treinamentos_lista = df_treinamentos.apply(
                    lambda x: f"{x['Técnico']} - {x['Treinamento']}", axis=1
                ).tolist()
                treinamento_selecionado = st.selectbox("Selecione para excluir:", treinamentos_lista)
                if treinamento_selecionado:
                    idx = treinamentos_lista.index(treinamento_selecionado)
                    if st.button("🗑️ Confirmar Exclusão"):
                        if delete_from_sheet(client, SPREADSHEET_NAME, SHEET_NAME, idx + 2):
                            st.success("✅ Excluído com sucesso!")
                        else:
                            st.error("❌ Erro ao excluir treinamento.")
            elif senha != "":
                st.error("❌ Senha incorreta!")
        else:
            st.warning("Nenhum treinamento para excluir.")

    # Rodapé
    st.markdown("---")
    st.markdown(
        f"""
        <div style='text-align: center; font-size: 11px; color: #666; margin-top: 30px;'>
        © {datetime.now().year} NORMAQ - Sistema de Gestão de Treinamentos • 
        Versão 1.0 • Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M')}
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
