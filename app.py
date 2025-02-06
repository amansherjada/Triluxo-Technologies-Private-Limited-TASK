from flask import Flask, request, jsonify, render_template
from langchain_community.document_loaders import UnstructuredURLLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os

load_dotenv()

# Step 1: Extract Data from the URL
urls = ["https://brainlox.com/courses/category/technical"]
loader = UnstructuredURLLoader(urls=urls)
documents = loader.load()

# Step 2: Create Embeddings and Store in a Local Database
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
persist_directory = "db"

# Initialize the Chroma vector store with persistence
vector_store = Chroma(persist_directory=persist_directory, embedding_function=embeddings)

# Check if the database is empty before adding new documents
existing_docs = vector_store.get()['documents']
if not existing_docs:
    print("Adding new documents to vector store...")
    vector_store.add_documents(documents)  # No need to call persist()
    print("Documents added successfully!")

# Step 3: Initialize Groq LLM
groq_llm = ChatGroq(model="gemma2-9b-it")

# Step 4: Create a Flask RESTful API to Handle Conversations
app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if request.method == 'GET':
        return render_template('chat.html')
    
    user_query = request.json.get('query')
    if not user_query:
        return jsonify({'error': 'No query provided'}), 400

    # Perform a similarity search in the vector store
    results = vector_store.similarity_search(user_query, k=5)

    # Combine the relevant content from the search results
    context = " ".join([result.page_content for result in results])

    # Generate a response using Groq LLM
    ai_response = groq_llm.invoke(f"Context: {context}\n\nUser: {user_query}\nBot: Provide the response in Markdown format.")

    if hasattr(ai_response, 'content'):
        return jsonify({'response': ai_response.content.strip()})
    else:
        return jsonify({'response': 'No valid response generated.'})


if __name__ == '__main__':
    app.run(debug=True)