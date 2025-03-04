from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import os
import traceback
from utilities.helper import LLMHelper
import regex as re

import logging
logger = logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.WARNING)

def check_deployment():
    # Check if the deployment is working
    #\ 1. Check if the llm is working
    try:
        llm_helper = LLMHelper()
        llm_helper.get_completion("Generate a joke!")
        st.success("LLM is working!")
    except Exception as e:
        st.error(f"""LLM is not working.  
            Please check you have a deployment name {llm_helper.deployment_name} in your Azure OpenAI resource {llm_helper.api_base}.  
            If you are using an Instructions based deployment (text-davinci-003), please check you have an environment variable OPENAI_DEPLOYMENT_TYPE=Text or delete the environment variable OPENAI_DEPLOYMENT_TYPE.  
            If you are using a Chat based deployment (gpt-35-turbo or gpt-4-32k or gpt-4), please check you have an environment variable OPENAI_DEPLOYMENT_TYPE=Chat.  
            Then restart your application.
            """)
        st.error(traceback.format_exc())
    #\ 2. Check if the embedding is working
    try:
        llm_helper = LLMHelper()
        llm_helper.embeddings.embed_documents(texts=["This is a test"])
        st.success("Embedding is working!")
    except Exception as e:
        st.error(f"""Embedding model is not working.  
            Please check you have a deployment named "text-embedding-ada-002" for "text-embedding-ada-002" model in your Azure OpenAI resource {llm_helper.api_base}.  
            Then restart your application.
            """)
        st.error(traceback.format_exc())
    #\ 3. Check if the translation is working
    try:
        llm_helper = LLMHelper()
        llm_helper.translator.translate("This is a test", "it")
        st.success("Translation is working!")
    except Exception as e:
        st.error(f"""Translation model is not working.  
            Please check your Azure Translator key in the App Settings.  
            Then restart your application.  
            """)
        st.error(traceback.format_exc())
    #\ 4. Check if the Redis is working with previous version of data
    try:
        llm_helper = LLMHelper()
        if llm_helper.vector_store_type != "AzureSearch":
            if llm_helper.vector_store.check_existing_index("embeddings-index"):
                st.warning("""Seems like you're using a Redis with an old data structure.  
                If you want to use the new data structure, you can start using the app and go to "Add Document" -> "Add documents in Batch" and click on "Convert all files and add embeddings" to reprocess your documents.  
                To remove this working, please delete the index "embeddings-index" from your Redis.  
                If you prefer to use the old data structure, please change your Web App container image to point to the docker image: fruocco/oai-embeddings:2023-03-27_25. 
                """)
            else:
                st.success("Redis is working!")
        else:
            try:
                llm_helper.vector_store.index_exists()
                st.success("Azure Cognitive Search is working!")
            except Exception as e:
                st.error("""Azure Cognitive Search is not working.  
                    Please check your Azure Cognitive Search service name and service key in the App Settings.  
                    Then restart your application.  
                    """)
                st.error(traceback.format_exc())
    except Exception as e:
        st.error(f"""Redis is not working. 
            Please check your Redis connection string in the App Settings.  
            Then restart your application.
            """)
        st.error(traceback.format_exc())


def check_variables_in_prompt():
    # Check if "summaries" is present in the string custom_prompt
    if "{summaries}" not in st.session_state.custom_prompt:
        st.warning("""Your custom prompt doesn't contain the variable "{summaries}".  
        This variable is used to add the content of the documents retrieved from the VectorStore to the prompt.  
        Please add it to your custom prompt to use the app.  
        Reverting to default prompt.
        """)
        st.session_state.custom_prompt = ""
    if "{question}" not in st.session_state.custom_prompt:
        st.warning("""Your custom prompt doesn't contain the variable "{question}".  
        This variable is used to add the user's question to the prompt.  
        Please add it to your custom prompt to use the app.  
        Reverting to default prompt.  
        """)
        st.session_state.custom_prompt = ""
    

 # Callback to assign the follow-up question is selected by the user
def ask_followup_question(followup_question):
    st.session_state.askedquestion = followup_question
    st.session_state['input_message_key'] = st.session_state['input_message_key'] + 1

def questionAsked():
    st.session_state.askedquestion = st.session_state["input"+str(st.session_state ['input_message_key'])]

@st.cache_data()
def get_languages():
    return llm_helper.translator.get_available_languages()

try:

    default_prompt = "" 
    default_question = "" 
    default_answer = ""

    if 'question' not in st.session_state:
        st.session_state['question'] = default_question
    if 'response' not in st.session_state:
        st.session_state['response'] = default_answer
    if 'context' not in st.session_state:
        st.session_state['context'] = ""
    if 'custom_prompt' not in st.session_state:
        st.session_state['custom_prompt'] = ""
    if 'custom_temperature' not in st.session_state:
        st.session_state['custom_temperature'] = float(os.getenv("OPENAI_TEMPERATURE", 0.7))

    if 'sources' not in st.session_state:
        st.session_state['sources'] = ""
    if 'followup_questions' not in st.session_state:
        st.session_state['followup_questions'] = []
    if 'input_message_key' not in st.session_state:
        st.session_state ['input_message_key'] = 1
    if 'askedquestion' not in st.session_state:
        st.session_state.askedquestion = default_question

    # Set page layout to wide screen and menu item
    menu_items = {
	'Get help': None,
	'Report a bug': None,
	'About': '''
	 ## Embeddings App
	 Embedding testing application.
	'''
    }
    st.set_page_config(layout="wide", menu_items=menu_items)

    llm_helper = LLMHelper(custom_prompt=st.session_state.custom_prompt, temperature=st.session_state.custom_temperature)

    # Get available languages for translation
    available_languages = get_languages()

    # Custom prompt variables
    custom_prompt_placeholder = """{summaries}  
    Please reply to the question using only the text above.  
    Question: {question}  
    Answer:"""
    custom_prompt_help = """You can configure a custom prompt by adding the variables {summaries} and {question} to the prompt.  
    {summaries} will be replaced with the content of the documents retrieved from the VectorStore.  
    {question} will be replaced with the user's question.
        """

    col1, col2, col3 = st.columns([1,2,1])
    with col1:
        st.image(os.path.join('images','edutecno.png'))

    col1, col2, col3 = st.columns([2,2,2])
    with col1:
        st.button("Check deployment", on_click=check_deployment)
    with col3:
        with st.expander("Settings"):
            # model = st.selectbox(
            #     "OpenAI GPT-3 Model",
            #     [os.environ['OPENAI_ENGINE']]
            # )
            # st.tokens_response = st.slider("Tokens response length", 100, 500, 400)
            st.slider("Temperature", min_value=0.0, max_value=1.0, step=0.1, key='custom_temperature')
            st.text_area("Custom Prompt", key='custom_prompt', on_change=check_variables_in_prompt, placeholder= custom_prompt_placeholder,help=custom_prompt_help, height=150)
            st.selectbox("Language", [None] + list(available_languages.keys()), key='translation_language')


    question = st.text_input("Azure OpenAI Semantic Answer", value=st.session_state['askedquestion'], key="input"+str(st.session_state ['input_message_key']), on_change=questionAsked)

    # Answer the question if any
    if st.session_state.askedquestion != '':
        st.session_state['question'] = st.session_state.askedquestion
        st.session_state.askedquestion = ""
        st.session_state['question'], \
        st.session_state['response'], \
        st.session_state['context'], \
        st.session_state['sources'] = llm_helper.get_semantic_answer_lang_chain(st.session_state['question'], [])
        st.session_state['response'], followup_questions_list = llm_helper.extract_followupquestions(st.session_state['response'])
        st.session_state['followup_questions'] = followup_questions_list

    sourceList = []

    # Display the sources and context - even if the page is reloaded
    if st.session_state['sources'] or st.session_state['context']:
        st.session_state['response'], sourceList, matchedSourcesList, linkList, filenameList = llm_helper.get_links_filenames(st.session_state['response'], st.session_state['sources'])
        st.write("<br>", unsafe_allow_html=True)
        st.markdown("Answer: " + st.session_state['response'])
 
    # Display proposed follow-up questions which can be clicked on to ask that question automatically
    if len(st.session_state['followup_questions']) > 0:
        st.write("<br>", unsafe_allow_html=True)
        st.markdown('**Proposed follow-up questions:**')
    with st.container():
        for questionId, followup_question in enumerate(st.session_state['followup_questions']):
            if followup_question:
                str_followup_question = re.sub(r"(^|[^\\\\])'", r"\1\\'", followup_question)
                st.button(str_followup_question, key=1000+questionId, on_click=ask_followup_question, args=(followup_question, ))

    if st.session_state['sources'] or st.session_state['context']:
        # Buttons to display the context used to answer
        st.write("<br>", unsafe_allow_html=True)
        st.markdown('**Document sources:**')
        for id in range(len(sourceList)):
            st.markdown(f"[{id+1}] {sourceList[id]}")

        # Details on the question and answer context
        st.write("<br><br>", unsafe_allow_html=True)
        with st.expander("Question and Answer Context"):
            if not st.session_state['context'] is None and st.session_state['context'] != []:
                for content_source in st.session_state['context'].keys():
                    st.markdown(f"#### {content_source}")
                    for context_text in st.session_state['context'][content_source]:
                        st.markdown(f"{context_text}")

            st.markdown(f"SOURCES: {st.session_state['sources']}") 

    for questionId, followup_question in enumerate(st.session_state['followup_questions']):
        if followup_question:
            str_followup_question = re.sub(r"(^|[^\\\\])'", r"\1\\'", followup_question)

    if st.session_state['translation_language'] and st.session_state['translation_language'] != '':
        st.write(f"Translation to other languages, 翻译成其他语言, النص باللغة العربية")
        st.write(f"{llm_helper.translator.translate(st.session_state['response'], available_languages[st.session_state['translation_language']])}")		
		
except Exception:
    st.error(traceback.format_exc())
