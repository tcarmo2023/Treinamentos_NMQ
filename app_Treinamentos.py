import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timezone, timedelta
import os
import re
import json
import time

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
        if os.path.exists('credentials.json'):
            try:
                return Credentials.from_service_account_file('credentials.json', scopes=scopes)
            except:
                st.sidebar.error("❌ Erro no arquivo credentials.json")
                return None
        elif 'gcp_service_account' in st.secrets:
            try:
                creds_info = dict(st.secrets['gcp_service_account'])
                return Credentials.from_service_account_info(creds_info, scopes=scopes)
            except:
                st.sidebar.error("❌ Erro nas credenciais TOML do Streamlit")
                return None
        elif 'GOOGLE_CREDENTIALS' in st.secrets:
            try:
                creds_json = json.loads(st.secrets['GOOGLE_CREDENTIALS'])
                return Credentials.from_service_account_info(creds_json, scopes=scopes)
            except:
                st.sidebar.error("❌ Erro no JSON das credenciais")
                return None
        return None
    except Exception as e:
        st.sidebar.error(f"❌ Erro geral: {str(e)}")
        return None

# Função para obter data/hora no fuso horário de Brasília
def get_brasilia_time():
    brasilia_tz = timezone(timedelta(hours=-3))
    return datetime.now(brasilia_tz)

# Dados fixos
CLASSIFICACAO_TECNICO = [
    "Mecânico I",
    "Mecânico II", 
    "JTC",
    "Auxiliar de Mecânico",
    "Mecânico Champion"
]

NIVEL_TREINAMENTO = [
    "Auxiliar Técnico 40h",
    "Técnico 160h", 
    "Técnico Diagnóstico 120h",
    "Técnico Master",
    "Formação JTC"
]

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

# Níveis das categorias - AGORA BASEADO NA CLASSIFICAÇÃO DO TÉCNICO
CATEGORIA_NIVEIS = {
    "Mecânico I": "Técnico 160h",
    "Mecânico II": "Técnico 160h", 
    "JTC": "JTC",
    "Auxiliar de Mecânico": "Auxiliar Técnico 40h",
    "Mecânico Champion": "Técnico Master"
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

# Matriz de tipos de treinamento com níveis, status e CLASSIFICAÇÃO
MATRIZ_TREINAMENTOS = {
    "Integração - 8h": {
        "classificação": "Auxiliar de Mecânico",
        "nível": "Auxiliar Técnico 40h",
        "status": [
            "História e Evolução JCB",
            "Missão / Visão / Cultura", 
            "S.S.M.A",
            "Tipos Modelos de Máquinas Nacionais e Importadas"
        ]
    },
    "Tecnologias - 8h": {
        "classificação": "Auxiliar de Mecânico",
        "nível": "Auxiliar Técnico 40h", 
        "status": [
            "Hidráulica / Elétrica",
            "Grandezas e Medições",
            "Mecânicas",
            "Grandezas, Medições, Elementos de Máquinas, Fixação, Ferramentas"
        ]
    },
    "Condução Máquinas - 8h": {
        "classificação": "Auxiliar de Mecânico",
        "nível": "Auxiliar Técnico 40h",
        "status": [
            "Segurança",
            "Check List", 
            "Condução 1 de Cada Família - Nacional e Importados"
        ]
    },
    "Sistema Operacional Produtos Nacionais / Importados - 8h": {
        "classificação": "Auxiliar de Mecânico",
        "nível": "Auxiliar Técnico 40h",
        "status": [
            "Testes Funcionamento",
            "Documentação",
            "Acessórios",
            "Suporte Técnico",
            "Machine Health Check"
        ]
    },
    "PMP - 8h": {
        "classificação": "Auxiliar de Mecânico",
        "nível": "Auxiliar Técnico 40h",
        "status": [
            "Tipos de Manutenção",
            "Portal JDS",
            "Preventiva Nacional - Roda e Esteira",
            "Preventiva Importadas - Hidrostática", 
            "Live Link"
        ]
    },
    "Conjunto Motriz - JCB - 40h": {
        "classificação": "Mecânico I",
        "nível": "Técnico 160h",
        "status": [
            "Desmontagem and Montagem",
            "Sistemas de Rodagem",
            "Sistemas Eixos",
            "Sistemas Freios",
            "Sistemas Transmissão"
        ]
    },
    "Motores - JCB - 40h": {
        "classificação": "Mecânico I",
        "nível": "Técnico 160h",
        "status": [
            "Tipos - Conv. Eletrônico",
            "Principio Funcionamento", 
            "Desmontagem and Montagem",
            "Substituição de Sistemas"
        ]
    },
    "Sistemas Eletro - Hidráulicos THL e BHL - 40h": {
        "classificação": "Mecânico I",
        "nível": "Técnico 160h",
        "status": [
            "Conjuntos Motrizes",
            "Sistemas Operacionais",
            "Acessórios",
            "Substituição de Componentes"
        ]
    },
    "Sistemas Eletro - Hidráulicos WLS e EXC - 40h": {
        "classificação": "Mecânico I",
        "nível": "Técnico 160h", 
        "status": [
            "Conjuntos Motrizes",
            "Sistemas Operacionais",
            "Acessórios",
            "Substituição de Componentes"
        ]
    },
    "Diagnóstico Powetrain JCB - 40h": {
        "classificação": "Mecânico II",
        "nível": "Técnico Diagnóstico 120h",
        "status": [
            "Motores",
            "Conjuntos Motriz",
            "Service Master"
        ]
    },
    "Diagnóstico Sistemas Eletro-Hidráulicos Nacional - 40h": {
        "classificação": "Mecânico II",
        "nível": "Técnico Diagnóstico 120h",
        "status": [
            "Mant. Componentes",
            "Motores / Conj. Motriz",
            "Sistemas Operacionais",
            "Service Master"
        ]
    },
    "Diagnóstico Sistemas Eletro-Hidráulicos Importados - 40h": {
        "classificação": "Mecânico II",
        "nível": "Técnico Diagnóstico 120h",
        "status": [
            "Mant. Componentes",
            "Motores / Conj. Motriz",
            "Sistemas Operacionais", 
            "Service Master"
        ]
    },
    "JTC": {
        "classificação": "JTC",
        "nível": "Formação JTC",
        "status": [
            "Atualização Técnica",
            "Experiência Comprovada",
            "Competência Pessoais",
            "Multiplicador Interno"
        ]
    }
}

# Lista inicial de colaboradores (será gerenciada via session_state)
if 'BASE_COLABORADORES' not in st.session_state:
    st.session_state.BASE_COLABORADORES = [
        {"Colaborador": "Ivanildo Benvindo", "Classificação": "Mecânico I", "Nível": "Técnico 160h", "Revenda": "Recife",
         "Email": "ivanildo.benvindo@normaq.com.br", "Telefone": "+55 81 9119-9240"},
        {"Colaborador": "Luiz Guilherme", "Classificação": "Mecânico II", "Nível": "Técnico 160h", "Revenda": "Recife",
         "Email": "guilherme.santos@normaq.com.br", "Telefone": "+55 81 9786-0555"},
        {"Colaborador": "Jesse Pereira", "Classificação": "Mecânico II", "Nível": "Técnico 160h", "Revenda": "Recife",
         "Email": "jesse.pereira@normaq.com.br", "Telefone": "+55 81 9200-9598"},
        {"Colaborador": "Clemerson Jose", "Classificação": "Mecânico I", "Nível": "Técnico 160h", "Revenda": "Recife",
         "Email": "clemeson.jose@normaq.com.br", "Telefone": "+55 81 8942-1435"},
        {"Colaborador": "Leandro Tenorio", "Classificação": "Mecânico I", "Nível": "Técnico 160h", "Revenda": "Recife",
         "Email": "leandro.tenorio@normaq.com.br", "Telefone": "+55 81 9847-0771"},
        {"Colaborador": "Roberto Gomes", "Classificação": "Mecânico I", "Nível": "Técnico 160h", "Revenda": "Recife",
         "Email": "roberto.gomes@normaq.com.br", "Telefone": "+55 81 8621-6679"},
        {"Colaborador": "Rodolfo Monteiro", "Classificação": "Mecânico II", "Nível": "Técnico 160h", "Revenda": "Recife",
         "Email": "rodolfo.monteiro@normaq.com.br", "Telefone": "+55 81 7330-9016"},
        {"Colaborador": "Sergio Gomes", "Classificação": "JTC", "Nível": "Formação JTC", "Revenda": "Recife",
         "Email": "sergio.gomes@normaq.com.br", "Telefone": "+55 81 9247-3552"},
        {"Colaborador": "Icaro Cruz", "Classificação": "Mecânico I", "Nível": "Técnico 160h", "Revenda": "Natal",
         "Email": "icaro.cruz@normaq.com.br", "Telefone": "+55 84 9115-1029"},
        {"Colaborador": "Jeorge Rodrigues", "Classificação": "Mecânico I", "Nível": "Técnico 160h", "Revenda": "N Natal",
         "Email": "jeorge.rodrigues@normaq.com.br", "Telefone": "+55 84 9131-7495"},
        {"Colaborador": "Carlos Andre", "Classificação": "Mecânico I", "Nível": "Técnico 160h", "Revenda": "Fortaleza",
         "Email": "carlos.andre@normaq.com.br", "Telefone": "+55 85 9281-2340"},
        {"Colaborador": "Cleison Santos", "Classificação": "Mecânico I", "Nível": "Técnico 160h", "Revenda": "Fortaleza",
         "Email": "cleison.santos@normaq.com.br", "Telefone": "+55 85 9142-4501"},
        {"Colaborador": "Carlos Estevam", "Classificação": "Auxiliar de Mecânico", "Nível": "Auxiliar Técnico 40h", "Revenda": "Fortaleza",
         "Email": "carlos.estevam@normaq.com.br", "Telefone": "+55 85 9265-5102"},
        {"Colaborador": "Emerson Almeida", "Classificação": "Mecânico Champion", "Nível": "Técnico Master", "Revenda": "Fortaleza",
         "Email": "emerson.almeida@normaq.com.br", "Telefone": "+55 85 9119-9171"},
        {"Colaborador": "Daniel Leite", "Classificação": "JTC", "Nível": "Formação JTC", "Revenda": "Fortaleza",
         "Email": "daniel.leite@normaq.com.br", "Telefone": "+55 85 9117-6864"},
        {"Colaborador": "Willian Lucas", "Classificação": "Mecânico I", "Nível": "Técnico 160h", "Revenda": "Petrolina",
         "Email": "willian.lucas@normaq.com.br", "Telefone": "+55 87 8863-1640"},
        {"Colaborador": "Adriano Santos", "Classificação": "Mecânico I", "Nível": "Técnico 160h", "Revenda": "Petrolina",
         "Email": "adriano.santos@normaq.com.br", "Telefone": "+55 87 9146-3338"},
        {"Colaborador": "Francisco Neto", "Classificação": "Auxiliar de Mecânico", "Nível": "Auxiliar Técnico 40h", "Revenda": "Recife",
         "Email": "francisco.neto@normaq.com.br", "Telefone": ""},
        {"Colaborador": "Francisco Leonardo", "Classificação": "Auxiliar de Mecânico", "Nível": "Auxiliar Técnico 40h", "Revenda": "Fortaleza",
         "Email": "francisco.batista@normaq.com.br", "Telefone": ""},
        {"Colaborador": "Francisco Gabriel", "Classificação": "Auxiliar de Mecânico", "Nível": "Auxiliar Técnico 40h", "Revenda": "Fortaleza",
         "Email": "francisco.alves@normaq.com.br", "Telefone": ""}
    ]

# Funções auxiliares
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
    except:
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
    except:
        st.error("Erro ao salvar dados")
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
    except:
        st.error("Erro ao atualizar dados")
        return False

def delete_from_sheet(client, spreadsheet_name, sheet_name, row_index):
    try:
        spreadsheet = client.open(spreadsheet_name)
        worksheet = spreadsheet.worksheet(sheet_name)
        worksheet.delete_rows(row_index)
        return True
    except:
        st.error("Erro ao excluir dados")
        return False

# Função para adicionar técnico
def adicionar_tecnico(nome, telefone, email, classificacao, revenda):
    novo_tecnico = {
        "Colaborador": nome,
        "Telefone": telefone,
        "Email": email,
        "Classificação": classificacao,
        "Nível": CATEGORIA_NIVEIS.get(classificacao, ""),
        "Revenda": revenda
    }
    st.session_state.BASE_COLABORADORES.append(novo_tecnico)
    return True

# Função para atualizar técnico
def atualizar_tecnico(indice, nome, telefone, email, classificacao, revenda):
    st.session_state.BASE_COLABORADORES[indice] = {
        "Colaborador": nome,
        "Telefone": telefone,
        "Email": email,
        "Classificação": classificacao,
        "Nível": CATEGORIA_NIVEIS.get(classificacao, ""),
        "Revenda": revenda
    }
    return True

# Função para remover técnico
def remover_tecnico(indice):
    if 0 <= indice < len(st.session_state.BASE_COLABORADORES):
        st.session_state.BASE_COLABORADORES.pop(indice)
        return True
    return False

# Função principal
def main():
    st.title("📚 Sistema de Gestão de Treinamentos de Técnicos - NORMAQ")

    # Conexão
    try:
        creds = get_google_creds()
        if creds is None:
            st.error("❌ Credenciais não encontradas")
            return
        client = gspread.authorize(creds)
        SPREADSHEET_NAME = "Treinamentos"
        SHEET_NAME = "Página1"
        df_treinamentos = load_sheet_data(client, SPREADSHEET_NAME, SHEET_NAME)
        # Removida a mensagem de sucesso de conexão conforme solicitado
    except:
        st.error("❌ Erro de conexão")
        return

    # Abas - Agora temos 9 abas com as novas funcionalidades
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
        "📊 Consulta Técnicos", "🔍 Consulta Categoria", "📋 Consulta Tipo", 
        "➕ Cadastro Treinamento", "✏️ Atualização Treinamento", "🗑️ Exclusão Treinamento",
        "👨‍🔧 Cadastro Técnico", "⚙️ Ajuste Técnico", "🗑️ Exclusão Técnico"
    ])

    # Consulta por Técnicos
    with tab1:
        st.header("👨‍🔧 Consulta por Técnicos")
        tecnicos = [t["Colaborador"] for t in st.session_state.BASE_COLABORADORES]
        tecnico_selecionado = st.selectbox("Selecione o técnico:", tecnicos, key="consulta_tecnico")
        
        if tecnico_selecionado:
            tecnico_info = next((t for t in st.session_state.BASE_COLABORADORES if t["Colaborador"] == tecnico_selecionado), None)
            if tecnico_info:
                # Nome do técnico mais destacado
                st.markdown(f"<h2 style='color: #1f77b4;'>{tecnico_info['Colaborador']}</h2>", unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.info(f"**Classificação:** {tecnico_info['Classificação']}")
                with col2:
                    st.info(f"**Nível:** {tecnico_info['Nível']}")
                with col3:
                    st.info(f"**Revenda:** {tecnico_info['Revenda']}")
                
                col4, col5 = st.columns(2)
                with col4:
                    telefone = tecnico_info['Telefone']
                    if telefone:
                        telefone_limpo = re.sub(r'\D', '', telefone)
                        whatsapp_link = f"https://wa.me/{telefone_limpo}" if telefone_limpo else "#"
                        st.info(f"**Telefone:** [{telefone}]({whatsapp_link})")
                    else:
                        st.info("**Telefone:** Não informado")
                with col5:
                    st.info(f"**Email:** {tecnico_info['Email']}")

            if not df_treinamentos.empty:
                treinamentos_tecnico = df_treinamentos[df_treinamentos["Técnico"] == tecnico_selecionado]
                if not treinamentos_tecnico.empty:
                    treinamentos_ok = treinamentos_tecnico[treinamentos_tecnico["Situação"] == "OK"]
                    treinamentos_pendentes = treinamentos_tecnico[treinamentos_tecnico["Situação"] == "PENDENTE"]

                    if not treinamentos_ok.empty:
                        st.subheader("✅ Treinamentos Concluídos (OK)")
                        
                        # Ordem das colunas solicitada
                        colunas_ordenadas = [
                            "Tipo de Treinamento", "Classificação", "Treinamento",
                            "Classificação do Técnico", "Nível", "Revenda", "Categoria", "Situação",
                            "Modalidade", "Entrevista", "Status", "Técnico", "Data Cadastro", "Data Atualização"
                        ]
                        
                        # Filtrar apenas as colunas que existem no DataFrame
                        colunas_existentes = [col for col in colunas_ordenadas if col in treinamentos_ok.columns]
                        
                        st.dataframe(treinamentos_ok[colunas_existentes])
                        
                        # Botão para exportar
                        csv = treinamentos_ok[colunas_existentes].to_csv(index=False)
                        st.download_button(
                            label="📥 Exportar Treinamentos Concluídos",
                            data=csv,
                            file_name=f"treinamentos_concluidos_{tecnico_selecionado}.csv",
                            mime="text/csv"
                        )
                    
                    if not treinamentos_pendentes.empty:
                        st.subheader("⏳ Treinamentos Pendentes")
                        
                        # Filtrar apenas as colunas que existem no DataFrame
                        colunas_existentes = [col for col in colunas_ordenadas if col in treinamentos_pendentes.columns]
                        
                        st.dataframe(treinamentos_pendentes[colunas_existentes])
                        
                        # Botão para exportar
                        csv = treinamentos_pendentes[colunas_existentes].to_csv(index=False)
                        st.download_button(
                            label="📥 Exportar Treinamentos Pendentes",
                            data=csv,
                            file_name=f"treinamentos_pendentes_{tecnico_selecionado}.csv",
                            mime="text/csv"
                        )

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
                st.warning("Nenhum treinamento cadastrado no sistema.")

    # Consulta por Categoria
    with tab2:
        st.header("🔍 Consulta por Categoria")
        categorias = list(BASE_CATEGORIA.keys())
        categoria_selecionada = st.selectbox("Selecione a categoria:", categorias, key="consulta_categoria")
        
        if categoria_selecionada:
            # Mostrar nome da categoria
            nome_categoria = BASE_CATEGORIA.get(categoria_selecionada, "Nome não definido")
            st.info(f"**Categoria {categoria_selecionada}:** {nome_categoria}")
            
            if not df_treinamentos.empty:
                treinamentos_categoria = df_treinamentos[df_treinamentos["Categoria"] == categoria_selecionada]
                
                tecnicos_com_treinamento = treinamentos_categoria["Técnico"].unique().tolist()
                todos_tecnicos = [t["Colaborador"] for t in st.session_state.BASE_COLABORADORES]
                tecnicos_sem_treinamento = [t for t in todos_tecnicos if t not in tecnicos_com_treinamento]

                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("✅ Técnicos com Treinamento")
                    if tecnicos_com_treinamento:
                        for tecnico in tecnicos_com_treinamento:
                            # Encontrar a classificação do técnico
                            classif_tecnico = next((t["Classificação"] for t in st.session_state.BASE_COLABORADORES if t["Colaborador"] == tecnico), "N/A")
                            nivel_tecnico = next((t["Nível"] for t in st.session_state.BASE_COLABORADORES if t["Colaborador"] == tecnico), "N/A")
                            st.markdown(f"• **{tecnico}** ({classif_tecnico} - {nivel_tecnico})")
                    else:
                        st.write("Nenhum técnico com treinamento nesta categoria")
                
                with col2:
                    st.subheader("❌ Técnicos sem Treinamento")
                    if tecnicos_sem_treinamento:
                        for tecnico in tecnicos_sem_treinamento:
                            # Encontrar a classificação do técnico
                            classif_tecnico = next((t["Classificação"] for t in st.session_state.BASE_COLABORADORES if t["Colaborador"] == tecnico), "N/A")
                            nivel_tecnico = next((t["Nível"] for t in st.session_state.BASE_COLABORADORES if t["Colaborador"] == tecnico), "N/A")
                            st.markdown(f"• **{tecnico}** ({classif_tecnico} - {nivel_tecnico})")
                    else:
                        st.write("Todos os técnicos possuem treinamento nesta categoria")

    # Consulta por Tipo
    with tab3:
        st.header("📋 Consulta por Tipo de Treinamento")
        tipos_treinamento = list(MATRIZ_TREINAMENTOS.keys())
        tipo_selecionado = st.selectbox("Selecione o tipo de treinamento:", tipos_treinamento, key="consulta_tipo")
        
        if tipo_selecionado:
            info_tipo = MATRIZ_TREINAMENTOS.get(tipo_selecionado, {})
            status_list = info_tipo.get("status", [])
            
            if status_list:
                st.subheader("📝 Status do Treinamento")
                for status in status_list:
                    st.markdown(f"• {status}")
            
            # Mostrar técnicos que possuem este treinamento
            if not df_treinamentos.empty:
                tecnicos_com_treinamento = df_treinamentos[
                    (df_treinamentos["Tipo de Treinamento"] == tipo_selecionado) & 
                    (df_treinamentos["Situação"] == "OK")
                ]["Técnico"].unique().tolist()
                
                if tecnicos_com_treinamento:
                    st.subheader("👨‍🔧 Técnicos Qualificados")
                    for tecnico in tecnicos_com_treinamento:
                        st.markdown(f"• **{tecnico}**")
                else:
                    st.info("Nenhum técnico concluiu este treinamento ainda")

    # Cadastro de Treinamento
    with tab4:
        st.header("➕ Cadastro de Novo Treinamento")
        
        # Usar session_state para controlar o estado do formulário
        if 'form_submitted' not in st.session_state:
            st.session_state.form_submitted = False
            
        if st.session_state.form_submitted:
            st.success("🎉 Treinamento cadastrado com sucesso!")
            time.sleep(2)  # Pequeno delay para visualização
            st.session_state.form_submitted = False
            st.rerun()
        
        with st.form("form_cadastro", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                treinamento = st.selectbox("Treinamento*", BASE_TREINAMENTO)
                classificacao_tecnico = st.selectbox("Classificação do Técnico*", CLASSIFICACAO_TECNICO)
                nivel_tecnico = st.selectbox("Nível*", NIVEL_TREINAMENTO)
                situacao = st.selectbox("Situação*", BASE_SITUACAO)
                categoria = st.selectbox("Categoria*", list(BASE_CATEGORIA.keys()))
            with col2:
                tipo_treinamento = st.selectbox("Tipo de Treinamento*", BASE_TIPO_TREINAMENTO)
                modalidade = st.selectbox("Modalidade*", BASE_MODALIDADE)
                entrevista = st.selectbox("Entrevista*", BASE_ENTREVISTA)
                status = st.selectbox("Status*", BASE_STATUS)
                revenda = st.selectbox("Revenda*", BASE_REVENDA)
                tecnico = st.selectbox("Técnico*", [t["Colaborador"] for t in st.session_state.BASE_COLABORADORES])
            
            submitted = st.form_submit_button("✅ Cadastrar Treinamento")

            if submitted:
                novo_treinamento = {
                    "Treinamento": treinamento,
                    "Classificação do Técnico": classificacao_tecnico,
                    "Nível": nivel_tecnico,
                    "Situação": situacao,
                    "Categoria": categoria,
                    "Tipo de Treinamento": tipo_treinamento,
                    "Modalidade": modalidade,
                    "Entrevista": entrevista,
                    "Status": status,
                    "Revenda": revenda,
                    "Técnico": tecnico,
                    "Data Cadastro": get_brasilia_time().strftime("%d/%m/%Y %H:%M")
                }
                
                if save_to_sheet(client, SPREADSHEET_NAME, SHEET_NAME, novo_treinamento):
                    st.session_state.form_submitted = True
                else:
                    st.error("❌ Erro ao cadastrar treinamento.")

    # Atualização de Treinamento
    with tab5:
        st.header("✏️ Atualização de Treinamentos")
        if not df_treinamentos.empty:
            treinamentos_lista = df_treinamentos.apply(
                lambda x: f"{x['Técnico']} - {x['Tipo de Treinamento']} - {x['Situação']}", axis=1).tolist()
            treinamento_selecionado = st.selectbox("Selecione o treinamento para atualizar:", treinamentos_lista, key="atualiza_treinamento")
            if treinamento_selecionado:
                idx = treinamentos_lista.index(treinamento_selecionado)
                treinamento_data = df_treinamentos.iloc[idx]
                with st.form("form_atualizacao"):
                    col1, col2 = st.columns(2)
                    with col1:
                        nova_classificacao = st.selectbox("Classificação do Técnico*", CLASSIFICACAO_TECNICO,
                                                         index=CLASSIFICACAO_TECNICO.index(treinamento_data["Classificação do Técnico"]) if treinamento_data["Classificação do Técnico"] in CLASSIFICACAO_TECNICO else 0)
                        novo_nivel = st.selectbox("Nível*", NIVEL_TREINAMENTO,
                                                 index=NIVEL_TREINAMENTO.index(treinamento_data["Nível"]) if "Nível" in treinamento_data and treinamento_data["Nível"] in NIVEL_TREINAMENTO else 0)
                        nova_situacao = st.selectbox("Situação", BASE_SITUACAO,
                                                     index=BASE_SITUACAO.index(treinamento_data["Situação"]))
                        novo_status = st.selectbox("Status", BASE_STATUS,
                                                   index=BASE_STATUS.index(treinamento_data["Status"]))
                    with col2:
                        nova_entrevista = st.selectbox("Entrevista", BASE_ENTREVISTA,
                                                       index=BASE_ENTREVISTA.index(treinamento_data["Entrevista"]))
                        nova_modalidade = st.selectbox("Modalidade", BASE_MODALIDADE,
                                                       index=BASE_MODALIDADE.index(treinamento_data["Modalidade"]))
                        nova_revenda = st.selectbox("Revenda", BASE_REVENDA,
                                                    index=BASE_REVENDA.index(treinamento_data["Revenda"]))
                        nova_categoria = st.selectbox("Categoria*", list(BASE_CATEGORIA.keys()),
                                                     index=list(BASE_CATEGORIA.keys()).index(treinamento_data["Categoria"]) if treinamento_data["Categoria"] in BASE_CATEGORIA else 0)
                    submitted = st.form_submit_button("💾 Atualizar Treinamento")
                    if submitted:
                        dados_atualizados = {
                            "Classificação do Técnico": nova_classificacao,
                            "Nível": novo_nivel,
                            "Situação": nova_situacao,
                            "Status": novo_status,
                            "Entrevista": nova_entrevista,
                            "Modalidade": nova_modalidade,
                            "Revenda": nova_revenda,
                            "Categoria": nova_categoria,
                            "Data Atualização": get_brasilia_time().strftime("%d/%m/%Y %H:%M")
                        }
                        if update_sheet_data(client, SPREADSHEET_NAME, SHEET_NAME, idx + 2, dados_atualizados):
                            st.success("✅ Treinamento atualizado com sucesso!")
                            st.rerun()
                        else:
                            st.error("❌ Erro ao atualizar treinamento.")
        else:
            st.warning("Nenhum treinamento cadastrado.")

    # Exclusão de Treinamento
    with tab6:
        st.header("🗑️ Exclusão de Treinamentos")
        if not df_treinamentos.empty:
            senha = st.text_input("Digite a senha para acesso:", type="password", key="senha_exclusao_treinamento")
            if senha == "NMQ@2025":
                treinamentos_lista = df_treinamentos.apply(
                    lambda x: f"{x['Técnico']} - {x['Tipo de Treinamento']} - {x['Situação']}", axis=1).tolist()
                treinamento_selecionado = st.selectbox("Selecione o treinamento para excluir:", treinamentos_lista, key="exclui_treinamento")
                if treinamento_selecionado:
                    idx = treinamentos_lista.index(treinamento_selecionado)
                    treinamento_data = df_treinamentos.iloc[idx]
                    st.warning("📋 Treinamento selecionado para exclusão:")
                    st.json(treinamento_data.to_dict())
                    if st.button("🗑️ Confirmar Exclusão"):
                        if delete_from_sheet(client, SPREADSHEET_NAME, SHEET_NAME, idx + 2):
                            st.success("✅ Treinamento excluído com sucesso!")
                            st.rerun()
                        else:
                            st.error("❌ Erro ao excluir treinamento.")
            elif senha != "":
                st.error("❌ Senha incorreta!")
        else:
            st.warning("Nenhum treinamento cadastrado.")

    # Cadastro de Técnico
    with tab7:
        st.header("👨‍🔧 Cadastro de Novo Técnico")
        
        if 'tecnico_submitted' not in st.session_state:
            st.session_state.tecnico_submitted = False
            
        if st.session_state.tecnico_submitted:
            st.success("🎉 Técnico cadastrado com sucesso!")
            time.sleep(2)
            st.session_state.tecnico_submitted = False
            st.rerun()
        
        with st.form("form_cadastro_tecnico", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nome_tecnico = st.text_input("Nome do Técnico*")
                telefone_tecnico = st.text_input("Telefone")
                email_tecnico = st.text_input("Email*")
            with col2:
                classificacao_tecnico = st.selectbox("Classificação do Técnico*", CLASSIFICACAO_TECNICO)
                revenda_tecnico = st.selectbox("Revenda*", BASE_REVENDA)
            
            submitted = st.form_submit_button("✅ Cadastrar Técnico")

            if submitted:
                if not nome_tecnico or not email_tecnico:
                    st.error("❌ Nome e Email são obrigatórios!")
                else:
                    if adicionar_tecnico(nome_tecnico, telefone_tecnico, email_tecnico, classificacao_tecnico, revenda_tecnico):
                        st.session_state.tecnico_submitted = True
                    else:
                        st.error("❌ Erro ao cadastrar técnico.")

    # Ajuste de Técnico
    with tab8:
        st.header("⚙️ Ajuste de Cadastro do Técnico")
        
        tecnicos = [t["Colaborador"] for t in st.session_state.BASE_COLABORADORES]
        if tecnicos:
            tecnico_selecionado = st.selectbox("Selecione o técnico para ajustar:", tecnicos, key="ajuste_tecnico")
            
            if tecnico_selecionado:
                tecnico_info = next((t for t in st.session_state.BASE_COLABORADORES if t["Colaborador"] == tecnico_selecionado), None)
                if tecnico_info:
                    indice_tecnico = st.session_state.BASE_COLABORADORES.index(tecnico_info)
                    
                    with st.form("form_ajuste_tecnico"):
                        col1, col2 = st.columns(2)
                        with col1:
                            nome_tecnico = st.text_input("Nome do Técnico*", value=tecnico_info["Colaborador"])
                            telefone_tecnico = st.text_input("Telefone", value=tecnico_info["Telefone"])
                            email_tecnico = st.text_input("Email*", value=tecnico_info["Email"])
                        with col2:
                            classificacao_tecnico = st.selectbox("Classificação do Técnico*", CLASSIFICACAO_TECNICO, 
                                                                index=CLASSIFICACAO_TECNICO.index(tecnico_info["Classificação"]) if tecnico_info["Classificação"] in CLASSIFICACAO_TECNICO else 0)
                            revenda_tecnico = st.selectbox("Revenda*", BASE_REVENDA, 
                                                          index=BASE_REVENDA.index(tecnico_info["Revenda"]) if tecnico_info["Revenda"] in BASE_REVENDA else 0)
                        
                        submitted = st.form_submit_button("💾 Atualizar Técnico")
                        
                        if submitted:
                            if not nome_tecnico or not email_tecnico:
                                st.error("❌ Nome e Email são obrigatórios!")
                            else:
                                if atualizar_tecnico(indice_tecnico, nome_tecnico, telefone_tecnico, email_tecnico, classificacao_tecnico, revenda_tecnico):
                                    st.success("✅ Técnico atualizado com sucesso!")
                                    st.rerun()
                                else:
                                    st.error("❌ Erro ao atualizar técnico.")
        else:
            st.warning("Nenhum técnico cadastrado.")

    # Exclusão de Técnico
    with tab9:
        st.header("🗑️ Exclusão de Técnico")
        
        tecnicos = [t["Colaborador"] for t in st.session_state.BASE_COLABORADORES]
        if tecnicos:
            senha = st.text_input("Digite a senha para acesso:", type="password", key="senha_exclusao_tecnico")
            
            if senha == "NMQ@2025":
                tecnico_selecionado = st.selectbox("Selecione o técnico para excluir:", tecnicos, key="exclui_tecnico")
                
                if tecnico_selecionado:
                    tecnico_info = next((t for t in st.session_state.BASE_COLABORADORES if t["Colaborador"] == tecnico_selecionado), None)
                    if tecnico_info:
                        indice_tecnico = st.session_state.BASE_COLABORADORES.index(tecnico_info)
                        
                        st.warning("📋 Técnico selecionado para exclusão:")
                        st.json(tecnico_info)
                        
                        if st.button("🗑️ Confirmar Exclusão do Técnico"):
                            if remover_tecnico(indice_tecnico):
                                st.success("✅ Técnico excluído com sucesso!")
                                st.rerun()
                            else:
                                st.error("❌ Erro ao excluir técnico.")
            elif senha != "":
                st.error("❌ Senha incorreta!")
        else:
            st.warning("Nenhum técnico cadastrado.")

    # Rodapé
    st.markdown("---")
    st.markdown(
        f"<div style='text-align: center; font-size: 11px; color: #666;'>"
        f"© {datetime.now().year} NORMAQ - Sistema de Gestão de Treinamentos • Versão 1.0 • "
        f"Atualizado em {get_brasilia_time().strftime('%d/%m/%Y %H:%M')}</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
