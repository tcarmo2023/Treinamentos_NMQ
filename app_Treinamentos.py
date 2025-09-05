import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import os
import re
import json
import base64
import sys

# Configuração da página
st.set_page_config(
    page_title="Sistema de Treinamentos - NORMAQ",
    page_icon="📚",
    layout="wide",
)

# Função para obter credenciais SIMPLIFICADA
def get_google_creds():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    try:
        # Primeiro tenta usar arquivo local
        if os.path.exists('credenciais.json'):
            try:
                return Credentials.from_service_account_file('credenciais.json', scopes=scopes)
            except Exception as e:
                st.sidebar.error(f"Erro no arquivo credenciais.json")
                return None
        
        # Se não encontrar arquivo, tenta Streamlit Secrets
        elif 'gcp_service_account' in st.secrets:
            try:
                creds_info = dict(st.secrets['gcp_service_account'])
                return Credentials.from_service_account_info(creds_info, scopes=scopes)
            except Exception as e:
                st.sidebar.error("Erro nas credenciais do Streamlit")
                return None
        
        return None
            
    except Exception as e:
        st.sidebar.error("Erro ao carregar credenciais")
        return None

# Dados fixos (bases)
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

BASE_COLABORADORES = [
    {"Colaborador": "Ivanildo Benvindo", "Classificação": "Mecânico I", "Unidades": "Recife", 
     "Email": "ivanildo.benvindo@normaq.com.br", "Telefone": "+55 81 9119-9240"},
    {"Colaborador": "Luiz Guilherme", "Classificação": "Mecânico II", "Unidades": "Recife", 
     "Email": "guilherme.santos@normaq.com.br", "Telefone": "+55 81 9786-0555"},
    {"Colaborador": "Jesse Pereira", "Classificação": "Mecânico II", "Unidades": "Recife", 
     "Email": "jesse.pereira@normaq.com.br", "Telefone": "+55 81 9200-9598"},
    {"Colaborador": "Clemerson Jose", "Classificação": "Mecânico I", "Unidades": "Recife", 
     "Email": "clemeson.jose@normaq.com.br", "Telefone": "+55 81 8942-1435"},
    {"Colaborador": "Leandro Tenorio", "Classificação": "Mecânico I", "Unidades": "Recife", 
     "Email": "leandro.tenorio@normaq.com.br", "Telefone": "+55 81 9847-0771"},
    {"Colaborador": "Roberto Gomes", "Classificação": "Mecânico I", "Unidades": "Recife", 
     "Email": "roberto.gomes@normaq.com.br", "Telefone": "+55 81 8621-6679"},
    {"Colaborador": "Rodolfo Monteiro", "Classificação": "Mecânico II", "Unidades": "Recife", 
     "Email": "rodolfo.monteiro@normaq.com.br", "Telefone": "+55 81 7330-9016"},
    {"Colaborador": "Sergio Gomes", "Classificação": "JTC", "Unidades": "Recife", 
     "Email": "sergio.gomes@normaq.com.br", "Telefone": "+55 81 9247-3552"},
    {"Colaborador": "Icaro Cruz", "Classificação": "Mecânico I", "Unidades": "Natal", 
     "Email": "icaro.cruz@normaq.com.br", "Telefone": "+55 84 9115-1029"},
    {"Colaborador": "Jeorge Rodrigues", "Classificação": "Mecânico I", "Unidades": "Natal", 
     "Email": "jeorge.rodrigues@normaq.com.br", "Telefone": "+55 84 9131-7495"},
    {"Colaborador": "Carlos Andre", "Classificação": "Mecânico I", "Unidades": "Fortaleza", 
     "Email": "carlos.andre@normaq.com.br", "Telefone": "+55 85 9281-2340"},
    {"Colaborador": "Cleison Santos", "Classificação": "Mecânico I", "Unidades": "Fortaleza", 
     "Email": "cleison.santos@normaq.com.br", "Telefone": "+55 85 9142-4501"},
    {"Colaborador": "Carlos Estevam", "Classificação": "Auxiliar de Mecânico", "Unidades": "Fortaleza", 
     "Email": "carlos.estevam@normaq.com.br", "Telefone": "+55 85 9265-5102"},
    {"Colaborador": "Emerson Almeida", "Classificação": "Mecânico Champion", "Unidades": "Fortaleza", 
     "Email": "emerson.almeida@normaq.com.br", "Telefone": "+55 85 9119-9171"},
    {"Colaborador": "Daniel Leite", "Classificação": "JTC", "Unidades": "Fortaleza", 
     "Email": "daniel.leite@normaq.com.br", "Telefone": "+55 85 9117-6864"},
    {"Colaborador": "Willian Lucas", "Classificação": "Mecânico I", "Unidades": "Petrolina", 
     "Email": "willian.lucas@normaq.com.br", "Telefone": "+55 87 8863-1640"},
    {"Colaborador": "Adriano Santos", "Classificação": "Mecânico I", "Unidades": "Petrolina", 
     "Email": "adriano.santos@normaq.com.br", "Telefone": "+55 87 9146-3338"},
    {"Colaborador": "Francisco Neto", "Classificação": "Auxiliar de Mecânico", "Unidades": "Recife", 
     "Email": "francisco.neto@normaq.com.br", "Telefone": ""},
    {"Colaborador": "Francisco Leonardo", "Classificação": "Auxiliar de Mecânico", "Unidades": "Fortaleza", 
     "Email": "francisco.batista@normaq.com.br", "Telefone": ""},
    {"Colaborador": "Francisco Gabriel", "Classificação": "Auxiliar de Mecânico", "Unidades": "Fortaleza", 
     "Email": "francisco.alves@normaq.com.br", "Telefone": ""}
]

# Funções para manipulação de dados
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
        st.error(f"Erro ao carregar dados da planilha")
        return pd.DataFrame()

def save_to_sheet(client, spreadsheet_name, sheet_name, data):
    try:
        spreadsheet = client.open(spreadsheet_name)
        worksheet = spreadsheet.worksheet(sheet_name)
        
        # Obter cabeçalhos
        headers = worksheet.row_values(1)
        if not headers:
            headers = list(data.keys())
            worksheet.append_row(headers)
        
        # Preparar dados
        row_data = []
        for header in headers:
            row_data.append(data.get(header, ""))
        
        worksheet.append_row(row_data)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar dados")
        return False

def update_sheet_data(client, spreadsheet_name, sheet_name, row_index, data):
    try:
        spreadsheet = client.open(spreadsheet_name)
        worksheet = spreadsheet.worksheet(sheet_name)
        
        headers = worksheet.row_values(1)
        
        for col_name, value in data.items():
            if col_name in headers:
                col_index = headers.index(col_name) + 1
                worksheet.update_cell(row_index, col_index, value)
        
        return True
    except Exception as e:
        st.error(f"Erro ao atualizar dados")
        return False

def delete_from_sheet(client, spreadsheet_name, sheet_name, row_index):
    try:
        spreadsheet = client.open(spreadsheet_name)
        worksheet = spreadsheet.worksheet(sheet_name)
        worksheet.delete_rows(row_index)
        return True
    except Exception as e:
        st.error(f"Erro ao excluir dados")
        return False

# Função principal
def main():
    st.title("📚 Sistema de Gestão de Treinamentos de Técnicos - NORMAQ")
    
    # Sidebar simples apenas para modo desenvolvimento
    with st.sidebar:
        modo_desenvolvimento = st.checkbox("Modo de desenvolvimento (dados de exemplo)", value=True)
    
    # Dados de exemplo para modo desenvolvimento
    dados_exemplo = pd.DataFrame({
        "Técnico": ["Ivanildo Benvindo", "Luiz Guilherme", "Jesse Pereira"],
        "Treinamento": ["JCB", "NMQ", "JCB"],
        "Categoria": ["THL", "SSL", "EXC"],
        "Situação": ["OK", "PENDENTE", "OK"],
        "Status": ["Concluído", "Pendente", "Concluído"],
        "Tipo de Treinamento": ["Integração - 8h", "Tecnologias - 8h", "Condução Máquinas - 8h"],
        "Classificação do Técnico": ["Mecânico I", "Mecânico II", "Mecânico II"]
    })
    
    # Se estiver em modo desenvolvimento, mostrar dados de exemplo
    if modo_desenvolvimento:
        st.info("📊 **Modo de desenvolvimento ativado** - Dados de exemplo")
        mostrar_interface_completa(dados_exemplo, None, None, None)
        return
    
    # Se não estiver em modo desenvolvimento, tentar conectar ao Google Sheets
    try:
        creds = get_google_creds()
        if creds is None:
            st.warning("""
            🔧 **Configure as credenciais do Google Sheets**
            
            Para usar o sistema completo, você precisa:
            
            1. **Arquivo local:** Coloque `credenciais.json` na pasta do projeto
            2. **Streamlit Cloud:** Configure as secrets no painel administrativo
            
            **Enquanto isso, usando dados de exemplo:**
            """)
            mostrar_interface_completa(dados_exemplo, None, None, None)
            return
            
        client = gspread.authorize(creds)
        SPREADSHEET_NAME = "Treinamentos"
        SHEET_NAME = "Página1"
        
        # Carregar dados reais
        df_treinamentos = load_sheet_data(client, SPREADSHEET_NAME, SHEET_NAME)
        
        if df_treinamentos.empty:
            st.warning("📝 Nenhum dado encontrado na planilha. Usando dados de exemplo.")
            mostrar_interface_completa(dados_exemplo, client, SPREADSHEET_NAME, SHEET_NAME)
        else:
            st.success("✅ Conectado ao Google Sheets")
            mostrar_interface_completa(df_treinamentos, client, SPREADSHEET_NAME, SHEET_NAME)
        
    except Exception as e:
        st.error(f"❌ Erro de conexão com Google Sheets")
        st.info("📋 Usando dados de exemplo para demonstração")
        mostrar_interface_completa(dados_exemplo, None, None, None)

def mostrar_interface_completa(df_treinamentos, client, spreadsheet_name, sheet_name):
    """Mostra a interface completa do sistema"""
    
    # Abas do sistema
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Consulta", "➕ Cadastro", "✏️ Atualização", "🗑️ Exclusão"])
    
    with tab1:
        st.header("📊 Consulta de Treinamentos")
        
        consulta_por = st.radio("Consultar por:", ["Técnicos", "Categoria"], horizontal=True)
        
        if consulta_por == "Técnicos":
            tecnicos = [t["Colaborador"] for t in BASE_COLABORADORES]
            tecnico_selecionado = st.selectbox("Selecione o técnico:", tecnicos)
            
            if tecnico_selecionado:
                tecnico_info = next((t for t in BASE_COLABORADORES if t["Colaborador"] == tecnico_selecionado), None)
                
                if tecnico_info:
                    st.subheader(f"Informações do Técnico: {tecnico_info['Colaborador']}")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.info(f"**Classificação:** {tecnico_info['Classificação']}")
                    with col2:
                        st.info(f"**Unidade:** {tecnico_info['Unidades']}")
                    with col3:
                        telefone = tecnico_info['Telefone']
                        if telefone:
                            st.info(f"**Telefone:** {telefone}")
                        else:
                            st.info("**Telefone:** Não informado")
                    
                    st.info(f"**Email:** {tecnico_info['Email']}")
                    
                    # Filtrar treinamentos do técnico
                    treinamentos_tecnico = df_treinamentos[df_treinamentos["Técnico"] == tecnico_selecionado]
                    
                    if not treinamentos_tecnico.empty:
                        treinamentos_ok = treinamentos_tecnico[treinamentos_tecnico["Situação"] == "OK"]
                        treinamentos_pendentes = treinamentos_tecnico[treinamentos_tecnico["Situação"] == "PENDENTE"]
                        
                        if not treinamentos_ok.empty:
                            st.subheader("✅ Treinamentos Concluídos (OK)")
                            st.dataframe(treinamentos_ok)
                        
                        if not treinamentos_pendentes.empty:
                            st.subheader("⏳ Treinamentos Pendentes")
                            st.dataframe(treinamentos_pendentes)
                        
                        col_stat1, col_stat2, col_stat3 = st.columns(3)
                        with col_stat1:
                            st.metric("Total", len(treinamentos_tecnico))
                        with col_stat2:
                            st.metric("Concluídos", len(treinamentos_ok))
                        with col_stat3:
                            st.metric("Pendentes", len(treinamentos_pendentes))
                    else:
                        st.warning("Nenhum treinamento encontrado para este técnico.")
        
        else:
            categorias = list(BASE_CATEGORIA.keys())
            categoria_selecionada = st.selectbox("Selecione a categoria:", categorias)
            
            if categoria_selecionada:
                treinamentos_categoria = df_treinamentos[df_treinamentos["Categoria"] == categoria_selecionada]
                
                if not treinamentos_categoria.empty:
                    tecnicos_com_treinamento = treinamentos_categoria["Técnico"].unique().tolist()
                    todos_tecnicos = [t["Colaborador"] for t in BASE_COLABORADORES]
                    tecnicos_sem_treinamento = [t for t in todos_tecnicos if t not in tecnicos_com_treinamento]
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader("✅ Técnicos com Treinamento")
                        if tecnicos_com_treinamento:
                            for tecnico in tecnicos_com_treinamento:
                                st.write(f"• {tecnico}")
                        else:
                            st.write("Nenhum técnico com treinamento")
                    
                    with col2:
                        st.subheader("❌ Técnicos sem Treinamento")
                        if tecnicos_sem_treinamento:
                            for tecnico in tecnicos_sem_treinamento:
                                st.write(f"• {tecnico}")
                        else:
                            st.write("Todos os técnicos possuem treinamento")
                    
                    st.metric("Técnicos com Treinamento", len(tecnicos_com_treinamento))
                else:
                    st.warning("Nenhum treinamento encontrado para esta categoria")
    
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
                tecnico = st.selectbox("Técnico*", [t["Colaborador"] for t in BASE_COLABORADORES])
            
            submitted = st.form_submit_button("✅ Cadastrar Treinamento")
            
            if submitted:
                if client is None:
                    st.success("🎉 Modo demonstração: Dados simulados com sucesso!")
                else:
                    try:
                        novo_treinamento = {
                            "Treinamento": treinamento,
                            "Classificação do Técnico": classificacao,
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
                        
                        if save_to_sheet(client, spreadsheet_name, sheet_name, novo_treinamento):
                            st.success("🎉 Treinamento cadastrado com sucesso!")
                        else:
                            st.error("❌ Erro ao cadastrar")
                    except Exception as e:
                        st.error("❌ Erro ao salvar dados")
    
    with tab3:
        st.header("✏️ Atualização de Treinamentos")
        
        if client is None:
            st.info("📝 Funcionalidade disponível apenas com Google Sheets")
            return
        
        if not df_treinamentos.empty:
            treinamentos_lista = df_treinamentos.apply(
                lambda x: f"{x['Técnico']} - {x['Tipo de Treinamento']}", axis=1
            ).tolist()
            
            treinamento_selecionado = st.selectbox("Selecione o treinamento:", treinamentos_lista)
            
            if treinamento_selecionado:
                idx = treinamentos_lista.index(treinamento_selecionado)
                treinamento_data = df_treinamentos.iloc[idx]
                
                with st.form("form_atualizacao"):
                    st.subheader(f"Editando: {treinamento_selecionado}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        nova_situacao = st.selectbox("Situação", BASE_SITUACAO, 
                                                   index=BASE_SITUACAO.index(treinamento_data["Situação"]) if treinamento_data["Situação"] in BASE_SITUACAO else 0)
                        novo_status = st.selectbox("Status", BASE_STATUS,
                                                 index=BASE_STATUS.index(treinamento_data["Status"]) if treinamento_data["Status"] in BASE_STATUS else 0)
                    
                    with col2:
                        nova_modalidade = st.selectbox("Modalidade", BASE_MODALIDADE,
                                                     index=BASE_MODALIDADE.index(treinamento_data["Modalidade"]) if treinamento_data["Modalidade"] in BASE_MODALIDADE else 0)
                    
                    submitted = st.form_submit_button("💾 Atualizar")
                    
                    if submitted:
                        dados_atualizados = {
                            "Situação": nova_situacao,
                            "Status": novo_status,
                            "Modalidade": nova_modalidade,
                            "Data Atualização": datetime.now().strftime("%d/%m/%Y %H:%M")
                        }
                        
                        if update_sheet_data(client, spreadsheet_name, sheet_name, idx + 2, dados_atualizados):
                            st.success("✅ Atualizado com sucesso!")
                        else:
                            st.error("❌ Erro ao atualizar")
        else:
            st.warning("Nenhum treinamento cadastrado")
    
    with tab4:
        st.header("🗑️ Exclusão de Treinamentos")
        st.warning("⚠️ Área restrita - apenas administradores")
        
        if client is None:
            st.info("🔒 Funcionalidade disponível apenas com Google Sheets")
            return
        
        senha = st.text_input("Digite a senha para acesso:", type="password")
        
        if senha == "NMQ@2025":
            if not df_treinamentos.empty:
                treinamentos_lista = df_treinamentos.apply(
                    lambda x: f"{x['Técnico']} - {x['Tipo de Treinamento']}", axis=1
                ).tolist()
                
                treinamento_selecionado = st.selectbox("Selecione o treinamento para excluir:", treinamentos_lista)
                
                if treinamento_selecionado and st.button("🗑️ Confirmar Exclusão"):
                    idx = treinamentos_lista.index(treinamento_selecionado)
                    if delete_from_sheet(client, spreadsheet_name, sheet_name, idx + 2):
                        st.success("✅ Excluído com sucesso!")
                    else:
                        st.error("❌ Erro ao excluir")
            else:
                st.warning("Nenhum treinamento para excluir")
        elif senha != "":
            st.error("❌ Senha incorreta!")
    
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
