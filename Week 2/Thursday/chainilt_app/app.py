import os 
import openai

# used to create a query engine that can retrieve information from a document store using a retriever.
from llama_index.query_engine.retriever_query_engine import RetrieverQueryEngine
from llama_index.callbacks.base import CallbackManager

from llama_inde import (
    LLMPredictor,
    ServiceContext,
    load_index_from_storage
)

from llama_index.llms import OpenAI

import chainlit as cl

openai.api_key = os.environ["OPENAI_API_KEY"]

try:
    #rebuild storage context
    storage_context = StorageContext.from_defaults(persist_dir='./storage')
    #load index from storage
    index = load_index_from_storage(storage_context)
except:
    from llama_index import GPTVectorIndex, SimpleDirectoryReader 
    
    #load documents
    documents = SimpleDirectoryReader(input_files=["hitchhikers.pdf"]).load_data()
    #create an index from documents
    index = GPTVectorIndex.from_documents(documents)
    index.storage_context.persist()
    
@cl.on_chat_start
async def factory():
    llm_predictor = LLMPredictor(
        llm=OpenAI(
            temperature=0.1,
            model="ft:gpt-3.5-turbo-0613:personal::7ru6l1bi",
            streaming=True,
            context_window=2048
            ),
    service_context=ServiceContext.from_defaults(
        llm_predictor=llm_predictor,
        chunk_size=512,
        callback_manager=CallbackManager([cl.LlamaIndexCallbackHandler()])
        ),
    )
    
    query_engine = index.as_query_engine(
        service_context=service_context,
        streaming=True
    )
    
    cl.user_session.set("query_engine", query_engine)
    
@cl.on_message
async def main(message):
    query_engine = cl.user_session.get("query_engine") 
    response = await cl.make_async(query_engine.query(message))
    
    response_message = cl.Message(content="")
    
    for token in response.response_gen:
        await response_message.stream_token(token=token)
        
    if response.response_text:
        response_message.content = response.response_text
    
    await response_message.send()