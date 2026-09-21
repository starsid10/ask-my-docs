Ask My Docs — AI Document Assistant

Ask My Docs is a full-stack AI document assistant that lets authenticated users upload PDF documents, ask questions about their content, and receive grounded answers with source citations.

The system uses Retrieval-Augmented Generation (RAG) with hybrid retrieval, Reciprocal Rank Fusion (RRF), cross-encoder reranking, Supabase persistence, and conversation history.

Features

User authentication and user-scoped access

PDF upload and document management

PDF text extraction and chunking

Processing status and error tracking

Embedding generation and Chroma vector storage

BM25 keyword retrieval

Semantic vector retrieval

Hybrid retrieval with RRF

Cross-encoder reranking

LLM-based grounded answers

Page-level source citations

Conversation and message history

Document/conversation ownership checks

Abstention when required information is unavailable

Automated tests and RAG evaluation

GitHub Actions CI

Architecture

React Frontend
      |
      v
FastAPI Backend
      |
      +-------------------+-------------------+
      |                   |                   |
      v                   v                   v
  Supabase             Chroma               LLM
 PostgreSQL             Vectors           Generation
 Storage
      ^
      |
      +-- Documents / Chunks / Conversations / Messages / Citations

Question
   |
   +--> BM25 Search --------+
   |                        |
   +--> Vector Search ------+--> RRF Fusion --> Cross-Encoder
                                                    |
                                                    v
                                             Relevant Context
                                                    |
                                                    v
                                                   LLM
                                                    |
                                                    v
                                             Answer + Citation

RAG Pipeline

PDF Upload
   -> Text Extraction
   -> Chunking
   -> Embeddings
   -> Supabase + Chroma

User Question
   -> BM25 Search
   -> Semantic Vector Search
   -> RRF Hybrid Fusion
   -> Cross-Encoder Reranking
   -> Relevant Context
   -> LLM
   -> Grounded Answer + Citation

Technology Stack

Frontend

React

JavaScript

React Markdown

Backend

Python

FastAPI

Sentence-transformer embeddings

BM25

ChromaDB

Reciprocal Rank Fusion

Cross-encoder reranking

LLM integration

Database / Storage

Supabase

PostgreSQL

Supabase Storage

Testing / CI

Pytest

Retrieval evaluation

RAG quality gate

GitHub Actions

Document Processing

When a PDF is uploaded:

Validate the document.

Store the PDF.

Extract text.

Split the text into chunks.

Store chunks with page/document metadata.

Generate embeddings.

Store vectors in Chroma.

Update processing status.

Make the document available for question answering.

Failed processing is tracked rather than silently treated as successful.

Hybrid Retrieval

BM25

Keyword retrieval helps with exact terms, names, technologies, and phrases.

Vector Search

The question is embedded and compared with document embeddings for semantic similarity.

RRF Fusion

BM25 and vector rankings are combined using Reciprocal Rank Fusion.

Cross-Encoder Reranking

The hybrid candidates are reranked before being supplied as context to the answer-generation stage.

Citations and Reliability

Answers are generated from retrieved document context.

Citations preserve source information such as:

Source document

Page number

Relevant chunk

When the required information cannot be found in the document, the system can abstain rather than confidently invent an answer.

Conversations

The backend maintains the relationship:

User
  -> Conversation
      -> Messages
          -> Citations
              -> Document

Conversation ownership is explicitly checked before a user can access or modify a conversation.

Evaluation

The project includes live evaluation and a CI regression quality gate.

Latest project evaluation:

Metric

Result

API success rate

100%

Answer correctness

100%

Citation accuracy

100%

Hallucinations

0

Retrieval evaluation

100%

Automated tests

15 passed

GitHub Actions CI

Passing

These are results from the project's small evaluation dataset and are not intended as a claim of universal model accuracy.

Running Locally

1. Clone

git clone https://github.com/starsid10/ask-my-docs.git
cd ask-my-docs

2. Create virtual environment

Windows PowerShell:

python -m venv venv
.\venv\Scripts\Activate.ps1

Linux/macOS:

python3 -m venv venv
source venv/bin/activate

3. Install Python dependencies

pip install -r requirements.txt

4. Configure environment variables

Create a local .env file with the credentials required by the application.

Example:

SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
LLM_API_KEY=your_llm_api_key

Never commit real credentials.

5. Start backend

cd backend
uvicorn main:app --reload

6. Start frontend

In another terminal:

cd frontend
npm install
npm run dev

Open the local URL shown by the frontend development server.

Testing

From the project root:

pytest -q

The repository includes automated API tests and a deterministic RAG retrieval quality gate.

GitHub Actions CI

GitHub Actions runs automatically on pushes and pull requests.

The CI workflow:

Checks out the repository.

Sets up Python.

Installs dependencies.

Runs automated tests.

Runs the RAG quality gate.

A failed quality check causes the CI workflow to fail.

Project Structure

ask-my-docs/
├── backend/
│   ├── main.py
│   ├── retrieval.py
│   ├── vector_store.py
│   ├── chunk_store.py
│   ├── reranker.py
│   ├── embeddings.py
│   └── ...
├── frontend/
│   ├── src/
│   ├── package.json
│   └── ...
├── evaluation/
│   ├── eval_dataset.json
│   ├── evaluate.py
│   ├── evaluate_retrieval.py
│   └── test_quality_gate.py
├── tests/
│   └── test_api.py
├── .github/
│   └── workflows/
│       └── ci.yml
├── .gitignore
├── requirements.txt
└── README.md

Security

The repository excludes sensitive/local-only files such as:

.env
.env.*
backend/chroma_db/
venv/
__pycache__/
.pytest_cache/

Never commit API keys, database credentials, JWT secrets, or other private configuration.

Future Improvements

Additional document formats such as DOCX and TXT

Improved chunking strategies

Larger evaluation datasets

More detailed retrieval metrics

Streaming LLM responses

Multi-document question answering

Background processing for very large documents

More extensive integration testing

Project Status

The current implementation includes authentication, document processing, chunk storage, embeddings, BM25 retrieval, semantic retrieval, RRF fusion, cross-encoder reranking, LLM answer generation, citations, conversations, evaluation, automated tests, and GitHub Actions CI.