import streamlit as st
import pandas as pd
from camelot.io import read_pdf  # Importa a função correta do Camelot
import io
import os
import re

# Configuração da página
st.set_page_config(
    page_title="Extrator de Tabelas de PDF",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.title("Extractor de Tabelas de PDF com Análise de Dados")

# Seção de Melhorias Implementadas
with st.expander("🚀 Principais Funções do Aplicativo", expanded=True):
    st.markdown("""
    - **Processamento Inteligente de Texto**  
      Remoção automática de quebras de linha (multinhas) e espaços extras em todas as colunas
    
    - **Validação Multicamadas**  
      Verificação de estrutura de tabelas e consistência de colunas
    
    - **Interface Aprimorada**  
      Barra de progresso em tempo real e múltiplos formatos de exportação
    
    - **Otimizações Técnicas**  
      Gerenciamento de memória eficiente e tratamento seguro de arquivos
    
    - **Análise Pós-Extração**  
      Resumo estatístico automático dos dados processados
    """)

# Upload do arquivo PDF
uploaded_file = st.file_uploader("📁 Selecione um arquivo PDF", type="pdf")

if uploaded_file:
    temp_pdf = "temp.pdf"
    try:
        # Salvar o arquivo temporariamente
        with open(temp_pdf, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Extração de tabelas utilizando o Camelot com os parâmetros para ajuste de células multilinhas
        with st.spinner("🔍 Extraindo tabelas..."):
            tables = read_pdf(
                temp_pdf,
                pages="all",
                flavor="lattice",
                split_text=True,   # Divide conteúdos multilinhas
                strip_text="\n",   # Remove quebras de linha
                line_scale=40      # Ajusta a sensibilidade da extração
            )
        
        st.success(f"✅ {len(tables)} tabelas detectadas")
        
        # Processamento das tabelas extraídas
        df_list = []
        progress_bar = st.progress(0)
        fixed_header = ["Nº TOMB.", "ESPECIFICAÇÃO", "CLASSIFICAÇÃO", "OBSERVAÇÃO", "RESPONSÁVEL", "LOCALIZAÇÃO"]
        
        for idx, table in enumerate(tables):
            df = table.df.copy()
            df.replace('', pd.NA, inplace=True)
            df.dropna(how='all', inplace=True)
            
            # Verifica se a tabela possui linhas e colunas suficientes para o processamento
            if len(df) < 2 or df.shape[1] < 6:
                continue
            
            # Considera a primeira linha como cabeçalho para eventuais ajustes (caso necessário)
            header = df.iloc[0].apply(lambda x: re.sub(r'\W+', ' ', str(x)).strip())
            data = df.iloc[1:].reset_index(drop=True)
            
            if data.shape[1] != 6:
                st.warning(f"⚠️ Tabela {idx + 1}: Estrutura inválida ({data.shape[1]} colunas)")
                continue
            
            # Define o cabeçalho fixo para manter a consistência
            data.columns = fixed_header
            data = data.applymap(lambda x: re.sub(r'\s+', ' ', str(x)).strip())
            
            # Filtra linhas onde a coluna "Nº TOMB." contém apenas dígitos
            data = data[data["Nº TOMB."].str.match(r'^\d+$', na=False)]
            
            if not data.empty:
                df_list.append(data)
            
            progress_bar.progress((idx + 1) / len(tables))
        
        # Combinação dos DataFrames processados
        if df_list:
            final_df = pd.concat(df_list, ignore_index=True)
            
            # Resumo estatístico dos dados extraídos
            st.subheader("📊 Resumo dos Dados Extraídos")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total de Registros", len(final_df))
                
            with col2:
                classificacoes = final_df["CLASSIFICAÇÃO"].nunique() if "CLASSIFICAÇÃO" in final_df.columns else "N/A"
                st.metric("Classificações Únicas", classificacoes)
                
            with col3:
                responsaveis = final_df["RESPONSÁVEL"].nunique() if "RESPONSÁVEL" in final_df.columns else 0
                st.metric("Responsáveis Únicos", responsaveis if responsaveis else "N/A")
                if responsaveis > 1:
                    st.caption(f"Principais: {', '.join(final_df['RESPONSÁVEL'].value_counts().index[:3])}")
            
            # Exibição detalhada dos dados extraídos
            with st.expander("🔍 Detalhamento Completo"):
                st.dataframe(final_df)
                
                if "CLASSIFICAÇÃO" in final_df.columns:
                    st.subheader("Classificações mais Frequentes")
                    st.table(final_df["CLASSIFICAÇÃO"].value_counts().head(10))
                
                if "LOCALIZAÇÃO" in final_df.columns:
                    st.subheader("Localizações mais Comuns")
                    st.table(final_df["LOCALIZAÇÃO"].value_counts().head(10))
            
            # Opções de exportação dos dados
            export_format = st.selectbox("💾 Formato de Exportação:", ["Excel", "CSV"])
            
            # Define o arquivo de saída e a extensão correta
            if export_format == "Excel":
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    final_df.to_excel(writer, index=False)
                output.seek(0)
                data = output.read()
                mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                file_extension = "xlsx"  # Define a extensão correta para Excel
            else:
                data = final_df.to_csv(index=False)
                mime_type = "text/csv"
                file_extension = "csv"
            
            st.download_button(
                label=f"📩 Download em {export_format}",
                data=data,
                file_name=f"dados_extraidos.{file_extension}",
                mime=mime_type
            )
        else:
            st.warning("⚠️ Nenhum dado válido encontrado após processamento")
    
    except Exception as e:
        st.error(f"❌ Erro inesperado: {str(e)}")
    
    finally:
        if os.path.exists(temp_pdf):
            os.remove(temp_pdf)