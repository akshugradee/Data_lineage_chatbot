import os
import pyodbc
import streamlit as st
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI

# Load environment variables
load_dotenv('.env')

# Initialize Azure OpenAI model
azure_model = AzureChatOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_deployment=os.getenv("AZURE_GPT_MODEL"),
    temperature=0
)

# Function to create a database connection
def create_db_connection():
    server = os.environ.get("SERVER")
    database = os.environ.get("DATABASE")
    username = os.environ.get("ACC_USERNAME")
    driver = os.environ.get("DRIVER")
    
    try:
        conn = pyodbc.connect(
            f'DRIVER={driver};SERVER=tcp:{server};PORT=1433;DATABASE={database};UID={username};Authentication=ActiveDirectoryInteractive;Encrypt=yes;'
        )
        st.success("Connection successful")
        return conn
    except pyodbc.Error as e:
        st.error(f"Error: {e}")
        st.error("Please re-authenticate.")
        return None

# Function to execute SQL query
def execute_sql_query(conn, sql_query):
    try:
        cur = conn.cursor()
        cur.execute(sql_query)
        rows = cur.fetchall()
        columns = [column[0] for column in cur.description]
        cur.close()
        return rows, columns
    except Exception as e:
        st.error(f"An error occurred while executing SQL query: {e}")
        return None, None

# Function to get stored procedure definition
def get_stored_procedure_definition(conn, schema_name, proc_name):
    sql_query = f"""
    SELECT 
        s.name AS SchemaName,
        o.name AS ProcedureName,
        m.definition AS ProcedureDefinition
    FROM 
        sys.sql_modules m
    JOIN 
        sys.objects o ON m.object_id = o.object_id
    JOIN 
        sys.schemas s ON o.schema_id = s.schema_id
    WHERE 
        o.type = 'P' AND
        s.name = '{schema_name}' AND
        o.name = '{proc_name}';
    """
    rows, columns = execute_sql_query(conn, sql_query)
    
    if rows and rows[0][2] is not None:
        return rows[0][2]
    else:
        st.error("Stored procedure not found.")
        return None

# Function to save stored procedure to a file
def save_stored_procedure_to_file(proc_definition, proc_name):
    file_path = rf"C:\Users\ak185560\OneDrive - NCR ATLEOS\Desktop\CodeMerge_backtrack_chatbot\{proc_name}.sql"
    with open(file_path, 'w') as file:
        file.write(proc_definition)
    st.success(f"Stored procedure saved to {file_path}")

# Function to analyze stored procedure using LLM
def analyze_stored_procedure(proc_definition, user_query):
    prompt = f"""
    You are an expert T-SQL code reviewer specializing in tracking column derivations, their source tables, and understanding complex T-SQL logic. Please analyze the following SQL stored procedure and provide detailed insights based on the user's query.

    User Query: '{user_query}'

    Instructions:
    1. Identify the source table and column names involved in the derivation of the specified column.
    2. Explain any derivation or logic used to create the specified column.
    3. Summarise the 
    3. Verify the column names provided in the query. If any column name is incorrect, please highlight the error.
    

    ### Stored Procedure:
    {proc_definition}
    """

    
    response = azure_model.invoke(prompt)
    return response.content

# Streamlit UI
st.title("Data Lineage ChatBot")

# Initialize session state
if 'requests' not in st.session_state:
    st.session_state.requests = []

# Get user inputs
schema_name = st.text_input("Schema Name")
proc_name = st.text_input("Procedure Name")
user_query = st.text_input("Enter your query about a specific column ")

if st.button("Analyze"):
    conn = create_db_connection()
    if conn:
        proc_definition = get_stored_procedure_definition(conn, schema_name, proc_name)
        if proc_definition:
            save_stored_procedure_to_file(proc_definition, proc_name)
            
            result = analyze_stored_procedure(proc_definition, user_query)
            
            st.session_state.requests.append({
                'schema_name': schema_name,
                'proc_name': proc_name,
                'user_query': user_query,
                'result': result
            })

# Display current response
if st.session_state.requests:
    st.subheader("Current Response")
    current_request = st.session_state.requests[-1]
    st.write(f"**Schema Name:** {current_request['schema_name']}")
    st.write(f"**Procedure Name:** {current_request['proc_name']}")
    st.write(f"**User Query:** {current_request['user_query']}")
    st.write(f"**Result:** {current_request['result']}")
    st.write("---")

# Display previous requests
if len(st.session_state.requests) > 1:
    st.subheader("Previous Requests")
    for req in st.session_state.requests[:-1]:
        st.write(f"**Schema Name:** {req['schema_name']}")
        st.write(f"**Procedure Name:** {req['proc_name']}")
        st.write(f"**User Query:** {req['user_query']}")
        st.write(f"**Result:** {req['result']}")
        st.write("---")
