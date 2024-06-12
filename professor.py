import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from datetime import datetime
from google.cloud import firestore
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import json

## CONFIG

if not firebase_admin._apps:
    key_dict = json.loads(st.secrets["textkey"])
    cred = credentials.Certificate(key_dict)
    app=firebase_admin.initialize_app(cred)

db = firestore.client()


prompt_template_tutor=ChatPromptTemplate.from_messages([
    ("system", "Age como um auxiliar de professores de programação proficiente na criação de exercícios."
            "Eu sou {name}, um(a) professor(a) do curso de Engenharia Informática e preciso da tua ajuda na criação de {amount} perguntas/exercícios"
            " do tipo {type} com dificuldade {level} em idioma {language}. Se o idioma for Português, usa Português de Portugal, de acordo com o Acordo Ortográfico da Língua Portuguesa."
            " Deves puxar pela tua criatividade e originalidade para inventar {amount} exercícios {level} diferentes e pedagógicos sobre o contexto que te for apresentado."),
    ("user", "{input}")
])

output_parser = StrOutputParser()

def load_llm():
    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=.5, openai_api_key = st.secrets["OPENAI_API_KEY"], streaming=True, callback_manager=CallbackManager([StreamingStdOutCallbackHandler()]))
    return llm

llm = load_llm()

chain = prompt_template_tutor | llm | output_parser

#APP PROFESSOR

st.set_page_config(page_title="App Professor", page_icon=":robot:", layout="wide")
st.title("App Professor")

## LOGIN
@st.experimental_dialog("Login")
def professor():
    name = st.text_input("Name")
    id = st.text_input("IST-id")
    if st.button("Submit"):
        st.session_state.professor.append({"Name": name, "IST-id": id})
        st.rerun()

if "professor" not in st.session_state:
    st.session_state.professor = []
    while st.session_state.professor == []:
        professor()

for s in st.session_state.professor:
        name = s["Name"]
        id = s["IST-id"]

if "messages" not in st.session_state:
        st.session_state.messages = []
        st.session_state.messages.append({"role":"assistant", "content": f"Olá! Seleciona nas caixas acima o tipo, quantidade, idioma e dificuldade dos exercícios que queres gerar. Depois diz-me sobre que temas queres que gere perguntas."})

if "setup" not in st.session_state:
    st.session_state.setup = []

col1, col2, col3, col4 = st.columns(4)
with col1:
    language=st.selectbox(
        'Idioma',
        ('Português', 'English')
    )

with col2:
    type=st.selectbox(
        'Tipo de Exercício',
        ('Escolha Múltipla', 'Resposta Aberta', 'Verdadeiro e Falso', 'Cloze')
    )

with col3:
    amount= st.selectbox(
        'Número de Exercícios',
        ('5', '10', '20', '50')
    )

with col4:
    level=st.selectbox(
        'Dificuldade',
        ('Fácil', 'Média', 'Difícil')
    )

st.session_state.setup.append({"language":language, "type": type, "amount": amount, "level":level})

with st.container(height=620):
    history = st.container(height=530)

    with history:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    if prompt := st.chat_input("Em que posso ajudar?"):
        with history:
            st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role":"user", "content":prompt})
    
        response = chain.stream({"name":name, "amount":amount, "type":type, "level":level, "language":language, "input":prompt})
        with history:
            with st.chat_message("ai"):
                ai_response = st.write_stream(response)
        st.session_state.messages.append({"role":"assistant", "content":ai_response})
        st.rerun()

##LOGS
if st.session_state.professor != []:
    doc_ref = db.collection("logs").document(f"logProfessor{id}")
    doc_ref.set({"professor": st.session_state.professor,
                "setup": st.session_state.setup,
                "messages": st.session_state.messages
                })