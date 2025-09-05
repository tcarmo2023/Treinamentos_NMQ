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

# Verifica se está sendo executado pelo Streamlit
def is_running_with_streamlit():
    return 'streamlit' in sys.modules

if not is_running_with_streamlit():
    st.error("""
    ❌ **ERRO DE EXECUÇÃO**
    
    Este aplicativo Streamlit deve ser executado com o comando:
    
    ```bash
    streamlit run app_Treinamentos.py
    ```
    
    Não use:
    ```bash
    python app_Treinamentos.py  # ← ERRADO!
    ```
    """)
    sys.exit(1)

# Função para corrigir padding base64
def fix_base64_padding(base64_string):
    """Corrige o padding de strings base64"""
    padding = len(base64_string) % 4
    if padding:
        base64_string += '=' * (4 - padding)
    return base64_string

# Função para obter credenciais CORRIGIDA
def get_google_creds():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    try:
        # Primeiro tenta usar arquivo local
        if os.path.exists('credenciais.json'):
            st.sidebar.success("✅ Usando credenciais do arquivo local")
            try:
                return Credentials.from_service_account_file('credenciais.json', scopes=scopes)
            except Exception as e:
                st.sidebar.error(f"❌ Erro no arquivo credenciais.json: {e}")
                return None
        
        # Se não encontrar arquivo, tenta Streamlit Secrets
        elif 'gcp_service_account' in st.secrets:
            st.sidebar.info("🔐 Tentando usar Streamlit Secrets...")
            creds_info = dict(st.secrets['gcp_service_account'])
            
            # Verifica e corrige a private_key se estiver em base64
            if 'private_key' in creds_info:
                private_key = creds_info['private_key']
                
                # Se não parece uma chave PEM, tenta decodificar base64
                if 'BEGIN PRIVATE KEY' not in private_key:
                    try:
                        # Corrige o padding primeiro
                        private_key = fix_base64_padding(private_key)
                        # Decodifica base64
                        decoded_key = base64.b64decode(private_key).decode('utf-8')
                        creds_info['private_key'] = decoded_key
                        st.sidebar.success("✅ Chave privada decodificada com sucesso")
                    except Exception as e:
                        st.sidebar.error(f"❌ Erro ao decodificar chave: {e}")
                        # Se falhar, tenta usar como está
                        st.sidebar.info("⚠️ Usando chave privada como texto simples")
            
            try:
                return Credentials.from_service_account_info(creds_info, scopes=scopes)
            except Exception as e:
                st.sidebar.error(f"❌ Erro nas credenciais: {e}")
                return None
        
        else:
            st.sidebar.warning("⚠️ Nenhuma credencial encontrada")
            return None
            
    except Exception as e:
        st.sidebar.error(f"❌ Erro ao carregar credenciais: {str(e)}")
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
     "Email": "Ivanildo.benvindo@normaq.com.br", "Telefone": "+55 81 9119-9240"},
    {"Colaborador": "Luiz Guilherme", "Classificação": "Mecânico II", "Unidades": "Recife", 
     "Email": "guilherme.santos@normaq.com.br", "Telefone": "+55 81 9786-0555"},
    {"Colaborador": "Jessé Pereira", "Classificação": "Mecânico II", "Unidades": "Recife", 
     "Email": "jesse.pereira@normaq.com.br", "Telefone": "+55 81 9200-9598"},
    {"Colaborador": "Clemerson José", "Classificação": "Mecânico I", "Unidades": "Recife", 
     "Email": "clemeson.jose@normaq.com.br", "Telefone": "+55 81 8942-1435"},
    {"Colaborador": "Leandro Tenório", "Classificação": "Mecânico I", "Unidades": "Recife", 
     "Email": "leandro.tenorio@normaq.com.br", "Telefone": "+55 81 9847-0771"},
    {"Colaborador": "Roberto Gomes", "Classificação": "Mecânico I", "Unidades": "Recife", 
     "Email": "roberto.gomes@normaq.com.br", "Telefone": "+55 81 8621-6679"},
    {"Colaborador": "Rodolfo Monteiro", "Classificação": "Mecânico II", "Unidades": "Recife", 
     "Email": "rodolfo.monteiro@normaq.com.br", "Telefone": "+55 81 7330-9016"},
    {"Colaborador": "Sérgio Gomes", "Classificação": "JTC", "Unidades": "Recife", 
     "Email": "sergio.gomes@normaq.com.br", "Telefone": "+55 81 9247-3552"},
    {"Colaborador": "Icaro Cruz", "Classificação": "Mecânico I", "Unidades": "Natal", 
     "Email": "icaro.cruz@normaq.com.br", "Telefone": "+55 84 9115-1029"},
    {"Colaborador": "Jeorge Rodrigues", "Classificação": "Mecânico I", "Unidades": "Natal", 
     "Email": "jeorge.rodrigues@normaq.com.br", "Telefone": "+55 84 9131-7495"},
    {"Colaborador": "Carlos André", "Classificação": "Mecânico I", "Unidades": "Fortaleza", 
     "Email": "carlos.andre@normaq.com.br", "Telefone": "+55 85 9281-2340"},
    {"Colaborador": "Cleison Santos", "Classificação": "Mecânico I", "Unidades": "Fortaleza", 
     "Email": "cleison.santos@normaq.com.br", "Telefone": "+55 85 9142-4501"},
    {"Colaborador": "Carlos Estevam", "Classificação": "Auxiliar de Mecânico", "Unidades": "Fortaleza", 
     "Email": "carlos.estevam@normaq.com.br", "Telefone": "+55 85 9265-5102"},
    {"Colaborador": "Emerson Almeida", "Classificação": "Mecânico Champion", "Unidades": "Fortaleza", 
     "Email": "ermeson.almeida@normaq.com.br", "Telefone": "+55 85 9119-9171"},
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
        st.error(f"Erro ao carregar dados: {e}")
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
        st.error(f"Erro ao salvar dados: {e}")
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
        st.error(f"Erro ao atualizar dados: {e}")
        return False

def delete_from_sheet(client, spreadsheet_name, sheet_name, row_index):
    try:
        spreadsheet = client.open(spreadsheet_name)
        worksheet = spreadsheet.worksheet(sheet_name)
        worksheet.delete_rows(row_index)
        return True
    except Exception as e:
        st.error(f"Erro ao excluir dados: {e}")
        return False

# Função principal
def main():
    st.title("📚 Sistema de Gestão de Treinamentos de Técnicos - NORMAQ")
    
    # Sidebar com informações
    with st.sidebar:
        st.header("🔧 Configuração")
        
        # Modo offline para testes
        modo_desenvolvimento = st.checkbox("Modo de desenvolvimento (dados de exemplo)", value=True)
        
        if modo_desenvolvimento:
            st.success("✅ Modo de desenvolvimento ativado")
            st.info("Usando dados de exemplo para demonstração")
            
            # Dados de exemplo
            df_exemplo = pd.DataFrame({
                "Técnico": ["Ivanildo Benvindo", "Luiz Guilherme", "Jessé Pereira"],
                "Treinamento": ["JCB", "NMQ", "JCB"],
                "Categoria": ["THL", "SSL", "EXC"],
                "Situação": ["OK", "PENDENTE", "OK"],
                "Status": ["Concluído", "Pendente", "Concluído"],
                "Tipo de Treinamento": ["Integração - 8h", "Tecnologias - 8h", "Condução Máquinas - 8h"]
            })
            
            st.dataframe(df_exemplo)
            
            # Mostrar instruções para configurar credenciais
            st.markdown("---")
            st.subheader("📋 Configurar Credenciais")
            st.info("""
            Para usar o Google Sheets, você precisa:
            
            1. **Arquivo local:** Coloque `credenciais.json` na pasta do projeto
            2. **Streamlit Cloud:** Configure as secrets no painel administrativo
            
            **Formato das secrets:**
            ```toml
            [gcp_service_account]
            type = "service_account"
            project_id = "seu-projeto"
            private_key_id = "sua-chave-id"
            private_key = "-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n"
            client_email = "seu-email@projeto.iam.gserviceaccount.com"
            client_id = "123456"
            auth_uri = "https://accounts.google.com/o/oauth2/auth"
            token_uri = "https://oauth2.googleapis.com/token"
            auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
            client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/..."
            ```
            """)
            return
    
    # Inicializar cliente Google
    try:
        creds = get_google_creds()
        if creds is None:
            st.warning("""
            ⚠️ **Modo de demonstração ativado**
            
            O sistema está funcionando com dados de exemplo. 
            Para conectar com Google Sheets:
            
            1. **Desmarque** "Modo de desenvolvimento" na sidebar
            2. **Configure** as credenciais do Google Sheets
            """)
            
            # Mostrar dados de exemplo mesmo no modo online sem credenciais
            df_exemplo = pd.DataFrame({
                "Técnico": ["Ivanildo Benvindo", "Luiz Guilherme"],
                "Treinamento": ["JCB", "NMQ"],
                "Situação": ["OK", "PENDENTE"],
                "Status": ["Concluído", "Pendente"]
            })
            
            st.dataframe(df_exemplo)
            return
            
        client = gspread.authorize(creds)
        SPREADSHEET_NAME = "Treinamentos"
        SHEET_NAME = "Página1"
        
        st.sidebar.success("✅ Conectado ao Google Sheets")
        
    except Exception as e:
        st.error(f"❌ Erro de autenticação: {e}")
        st.info("💡 Use o modo de desenvolvimento na sidebar para testar")
        return
    
    # Abas do sistema
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Consulta", "➕ Cadastro", "✏️ Atualização", "🗑️ Exclusão"])
    
    with tab1:
        st.header("Consulta de Treinamentos")
        st.info("Selecione abaixo como deseja consultar os treinamentos")
        
        consulta_por = st.radio("Consultar por:", ["Técnicos", "Categoria"], horizontal=True)
        
        if consulta_por == "Técnicos":
            # Lista de técnicos para seleção
            tecnicos = [t["Colaborador"] for t in BASE_COLABORADORES]
            tecnico_selecionado = st.selectbox("Selecione o técnico:", tecnicos)
            
            if tecnico_selecionado:
                # Encontrar dados do técnico
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
                            telefone_limpo = re.sub(r'\D', '', telefone)
                            whatsapp_link = f"https://wa.me/{telefone_limpo}" if telefone_limpo else "#"
                            st.info(f"**Telefone:** [{telefone}]({whatsapp_link})")
                        else:
                            st.info("**Telefone:** Não informado")
                    
                    st.info(f"**Email:** {tecnico_info['Email']}")
                    
                    # Carregar treinamentos
                    df_treinamentos = load_sheet_data(client, SPREADSHEET_NAME, SHEET_NAME)
                    
                    if not df_treinamentos.empty:
                        # Filtrar treinamentos do técnico
                        treinamentos_tecnico = df_treinamentos[df_treinamentos["Técnico"] == tecnico_selecionado]
                        
                        if not treinamentos_tecnico.empty:
                            # Separar por situação
                            treinamentos_ok = treinamentos_tecnico[treinamentos_tecnico["Situação"] == "OK"]
                            treinamentos_pendentes = treinamentos_tecnico[treinamentos_tecnico["Situação"] == "PENDENTE"]
                            
                            # Exibir treinamentos OK
                            if not treinamentos_ok.empty:
                                st.subheader("✅ Treinamentos Concluídos (OK)")
                                st.dataframe(treinamentos_ok[["Treinamento", "Categoria", "Status", "Tipo de Treinamento", "Classificação do Técnico"]])
                            
                            # Exibir treinamentos pendentes
                            if not treinamentos_pendentes.empty:
                                st.subheader("⏳ Treinamentos Pendentes")
                                st.dataframe(treinamentos_pendentes[["Treinamento", "Categoria", "Status", "Tipo de Treinamento", "Classificação do Técnico"]])
                            
                            # Estatísticas
                            col_stat1, col_stat2, col_stat3 = st.columns(3)
                            with col_stat1:
                                st.metric("Total de Treinamentos", len(treinamentos_tecnico))
                            with col_stat2:
                                st.metric("Concluídos", len(treinamentos_ok))
                            with col_stat3:
                                st.metric("Pendentes", len(treinamentos_pendentes))
                                
                        else:
                            st.warning("Nenhum treinamento encontrado para este técnico.")
                    else:
                        st.warning("Nenhum treinamento cadastrado no sistema.")
        
        else:  # Consulta por Categoria
            categorias = list(BASE_CATEGORIA.keys())
            categoria_selecionada = st.selectbox("Selecione a categoria:", categorias)
            
            if categoria_selecionada:
                # Carregar treinamentos
                df_treinamentos = load_sheet_data(client, SPREADSHEET_NAME, SHEET_NAME)
                
                if not df_treinamentos.empty:
                    # Filtrar treinamentos da categoria
                    treinamentos_categoria = df_treinamentos[df_treinamentos["Categoria"] == categoria_selecionada]
                    
                    # Técnicos com treinamento na categoria
                    tecnicos_com_treinamento = treinamentos_categoria["Técnico"].unique().tolist()
                    
                    # Todos os técnicos
                    todos_tecnicos = [t["Colaborador"] for t in BASE_COLABORADORES]
                    
                    # Técnicos sem treinamento na categoria
                    tecnicos_sem_treinamento = [t for t in todos_tecnicos if t not in tecnicos_com_treinamento]
                    
                    # Exibir resultados
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("✅ Técnicos com Treinamento")
                        if tecnicos_com_treinamento:
                            for tecnico in tecnicos_com_treinamento:
                                st.write(f"• {tecnico}")
                        else:
                            st.write("Nenhum técnico com treinamento nesta categoria")
                    
                    with col2:
                        st.subheader("❌ Técnicos sem Treinamento")
                        if tecnicos_sem_treinamento:
                            for tecnico in tecnicos_sem_treinamento:
                                st.write(f"• {tecnico}")
                        else:
                            st.write("Todos os técnicos possuem treinamento nesta categoria")
                    
                    # Estatísticas
                    st.metric("Total de Técnicos com Treinamento", len(tecnicos_com_treinamento))
                    
                else:
                    st.warning("Nenhum treinamento cadastrado no sistema.")
    
    with tab2:
        st.header("Cadastro de Novo Treinamento")
        
        with st.form("form_cadastro_treinamento"):
            col1, col2 = st.columns(2)
            
            with col1:
                treinamento = st.selectbox("Treinamento*", BASE_TREINAMENTO)
                classificacao_tecnico = st.selectbox("Classificação do Técnico*", BASE_FUNCAO)
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
                try:
                    # Preparar dados
                    novo_treinamento = {
                        "Treinamento": treinamento,
                        "Classificação do Técnico": classificacao_tecnico,
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
                    
                    # Salvar na planilha
                    if save_to_sheet(client, SPREADSHEET_NAME, SHEET_NAME, novo_treinamento):
                        st.success("🎉 Treinamento cadastrado com sucesso!")
                        st.balloons()
                    else:
                        st.error("❌ Erro ao cadastrar treinamento.")
                        
                except Exception as e:
                    st.error(f"❌ Erro: {e}")
    
    with tab3:
        st.header("Atualização de Treinamentos")
        
        # Carregar treinamentos
        df_treinamentos = load_sheet_data(client, SPREADSHEET_NAME, SHEET_NAME)
        
        if not df_treinamentos.empty:
            # Selecionar treinamento para atualizar
            treinamentos_lista = df_treinamentos.apply(
                lambda x: f"{x['Técnico']} - {x['Tipo de Treinamento']} - {x['Situação']}", axis=1
            ).tolist()
            
            treinamento_selecionado = st.selectbox("Selecione o treinamento para atualizar:", treinamentos_lista)
            
            if treinamento_selecionado:
                # Encontrar índice do treinamento
                idx = treinamentos_lista.index(treinamento_selecionado)
                treinamento_data = df_treinamentos.iloc[idx]
                
                with st.form("form_atualizacao_treinamento"):
                    st.subheader(f"Editando: {treinamento_selecionado}")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        nova_situacao = st.selectbox("Situação", BASE_SITUACAO, 
                                                   index=BASE_SITUACAO.index(treinamento_data["Situação"]) if treinamento_data["Situação"] in BASE_SITUACAO else 0)
                        novo_status = st.selectbox("Status", BASE_STATUS,
                                                 index=BASE_STATUS.index(treinamento_data["Status"]) if treinamento_data["Status"] in BASE_STATUS else 0)
                        nova_entrevista = st.selectbox("Entrevista", BASE_ENTREVISTA,
                                                     index=BASE_ENTREVISTA.index(treinamento_data["Entrevista"]) if treinamento_data["Entrevista"] in BASE_ENTREVISTA else 0)
                    
                    with col2:
                        nova_modalidade = st.selectbox("Modalidade", BASE_MODALIDADE,
                                                     index=BASE_MODALIDADE.index(treinamento_data["Modalidade"]) if treinamento_data["Modalidade"] in BASE_MODALIDADE else 0)
                        nova_revenda = st.selectbox("Revenda", BASE_REVENDA,
                                                  index=BASE_REVENDA.index(treinamento_data["Revenda"]) if treinamento_data["Revenda"] in BASE_REVENDA else 0)
                    
                    submitted = st.form_submit_button("💾 Atualizar Treinamento")
                    
                    if submitted:
                        try:
                            # Preparar dados para atualização
                            dados_atualizados = {
                                "Situação": nova_situacao,
                                "Status": novo_status,
                                "Entrevista": nova_entrevista,
                                "Modalidade": nova_modalidade,
                                "Revenda": nova_revenda,
                                "Data Atualização": datetime.now().strftime("%d/%m/%Y %H:%M")
                            }
                            
                            # Atualizar na planilha (linha +2 porque a planilha tem cabeçalho e índice começa em 1)
                            if update_sheet_data(client, SPREADSHEET_NAME, SHEET_NAME, idx + 2, dados_atualizados):
                                st.success("✅ Treinamento atualizado com sucesso!")
                            else:
                                st.error("❌ Erro ao atualizar treinamento.")
                                
                        except Exception as e:
                            st.error(f"❌ Erro: {e}")
        else:
            st.warning("ℹ️ Nenhum treinamento cadastrado para atualizar.")
    
    with tab4:
        st.header("Exclusão de Treinamentos")
        st.warning("⚠️ Área restrita - apenas para administradores")
        
        # Verificar senha
        senha = st.text_input("Digite a senha para acesso:", type="password")
        
        if senha == "NMQ@2025":
            # Carregar treinamentos
            df_treinamentos = load_sheet_data(client, SPREADSHEET_NAME, SHEET_NAME)
            
            if not df_treinamentos.empty:
                # Selecionar treinamento para excluir
                treinamentos_lista = df_treinamentos.apply(
                    lambda x: f"{x['Técnico']} - {x['Tipo de Treinamento']} - {x['Situação']}", axis=1
                ).tolist()
                
                treinamento_selecionado = st.selectbox("Selecione o treinamento para excluir:", treinamentos_lista)
                
                if treinamento_selecionado:
                    # Mostrar preview do treinamento selecionado
                    idx = treinamentos_lista.index(treinamento_selecionado)
                    treinamento_data = df_treinamentos.iloc[idx]
                    
                    st.warning(f"📋 Treinamento selecionado para exclusão:")
                    st.json(treinamento_data.to_dict())
                    
                    if st.button("🗑️ Excluir Treinamento", type="secondary"):
                        try:
                            # Excluir da planilha (linha +2 porque a planilha tem cabeçalho e índice começa em 1)
                            if delete_from_sheet(client, SPREADSHEET_NAME, SHEET_NAME, idx + 2):
                                st.success("✅ Treinamento excluído com sucesso!")
                                st.rerun()
                            else:
                                st.error("❌ Erro ao excluir treinamento.")
                                
                        except Exception as e:
                            st.error(f"❌ Erro: {e}")
            else:
                st.warning("ℹ️ Nenhum treinamento cadastrado para excluir.")
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
