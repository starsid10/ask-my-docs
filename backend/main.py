from fastapi import FastAPI, UploadFile, File, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions
import uuid
from pydantic import BaseModel
from fastapi.security import HTTPBearer

from extraction import extract_text
from chunking import chunk_text
from embeddings import create_embeddings
from vector_store import chroma_client, store_embeddings
from chunk_store import store_chunks
from retrieval import retrieve
from LLM import build_context, generate_answer



# ENVIRONMENT
# ===========

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")



# APP
# ===========
app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


security_scheme = HTTPBearer()


supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


# ==============
# MODELS
# ===============

class UserCreate(BaseModel):
    email: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


class AskRequest(BaseModel):
    query: str
    document_id: str
    conversation_id: str


# ==================
# HOME
# ===================

@app.get("/")
async def home():

    return {
        "Name": "sudhanshu",
        "server": "ON"
    }


# =========================================================
# UPLOAD DOCUMENT
# =========================================================

@app.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    credentials=Depends(security_scheme)
):

    token = credentials.credentials

    options = ClientOptions(
        headers={
            "Authorization": f"Bearer {token}"
        }
    )

    user_supabase = create_client(
        SUPABASE_URL,
        SUPABASE_KEY,
        options=options
    )

    # -----------------------------------------------------
    # Authenticate user
    # -----------------------------------------------------

    try:

        check_user = supabase.auth.get_user(token)

        user_id = check_user.user.id

    except Exception:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token."
        )

    # -----------------------------------------------------
    # Validate PDF
    # -----------------------------------------------------

    if file.content_type != "application/pdf":

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="UNSUPPORTED DOCUMENT TYPE"
        )

    document_id = uuid.uuid4()

    try:

        # -------------------------------------------------
        # Read file
        # -------------------------------------------------

        file_content = await file.read()

        storage_path = (
            f"DOC/{document_id}/{file.filename}"
        )

        # -------------------------------------------------
        # Create document record
        # -------------------------------------------------

        user_supabase.table("documents").insert({

            "document_id": str(document_id),

            "user_id": user_id,

            "filename": file.filename,

            "storage_path": storage_path,

            "processing_status": "processing",

            "processing_error": None

        }).execute()

        # -------------------------------------------------
        # Upload to Supabase Storage
        # -------------------------------------------------

        user_supabase.storage.from_("documents").upload(

            path=storage_path,

            file=file_content,

            file_options={
                "upsert": False
            }

        )

        # -------------------------------------------------
        # Extract PDF text
        # -------------------------------------------------

        extracted_text = extract_text(
            file_content
        )

        # -------------------------------------------------
        # Chunk document
        # -------------------------------------------------

        chunks = chunk_text(
            extracted_text,
            document_id
        )

        if not chunks:

            raise Exception(
                "No readable text was extracted from the PDF."
            )

        # -------------------------------------------------
        # Add metadata
        # -------------------------------------------------

        for chunk in chunks:

            chunk["filename"] = file.filename

            chunk["user_id"] = user_id

        # -------------------------------------------------
        # Store chunks in Supabase
        # -------------------------------------------------

        store_chunks(
            user_supabase,
            chunks
        )

        # -------------------------------------------------
        # Create embeddings
        # -------------------------------------------------

        embedded_chunks = create_embeddings(
            chunks
        )

        # -------------------------------------------------
        # Store vectors
        # -------------------------------------------------

        store_count = store_embeddings(
            chroma_client,
            "documents",
            embedded_chunks
        )

        # -------------------------------------------------
        # Determine page count
        # -------------------------------------------------

        pages = set()

        for chunk in chunks:

            if chunk.get("page") is not None:

                pages.add(
                    chunk.get("page")
                )

        total_pages = len(pages)

        # -------------------------------------------------
        # Mark completed
        # -------------------------------------------------

        user_supabase.table("documents").update({

            "processing_status": "completed",

            "processing_error": None

        }).eq(

            "document_id",
            str(document_id)

        ).eq(

            "user_id",
            user_id

        ).execute()

        print(
            f"Document processed: {file.filename}"
        )

        print(
            f"Chunks stored: {store_count}"
        )

        print(
            f"Pages: {total_pages}"
        )

    except Exception as e:

        print(
            "DOCUMENT PROCESSING ERROR:",
            str(e)
        )

        try:

            user_supabase.table("documents").update({

                "processing_status": "failed",

                "processing_error": str(e)

            }).eq(

                "document_id",
                str(document_id)

            ).eq(

                "user_id",
                user_id

            ).execute()

        except Exception:

            pass

        raise HTTPException(
            status_code=500,
            detail="Document processing failed."
        )

    return {

        "filename": file.filename,

        "content-type": file.content_type,

        "document_id": str(document_id),

        "processing_status": "completed",

        "total_pages": total_pages

    }


# =========================================================
# GET DOCUMENTS
# =========================================================

@app.get("/documents")
def get_documents(
    credentials=Depends(security_scheme)
):

    token = credentials.credentials

    # -----------------------------------------------------
    # Authenticate
    # -----------------------------------------------------

    try:

        check_user = supabase.auth.get_user(token)

        user_id = check_user.user.id

    except Exception:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token."
        )

    # -----------------------------------------------------
    # User scoped client
    # -----------------------------------------------------

    options = ClientOptions(
        headers={
            "Authorization": f"Bearer {token}"
        }
    )

    user_supabase = create_client(
        SUPABASE_URL,
        SUPABASE_KEY,
        options=options
    )

    # -----------------------------------------------------
    # Get documents
    # -----------------------------------------------------

    response = user_supabase.table(
        "documents"
    ).select(
        """
        document_id,
        filename,
        storage_path,
        processing_status,
        processing_error
        """
    ).eq(
        "user_id",
        user_id
    ).order(
        "filename"
    ).execute()

    documents = []

    # -----------------------------------------------------
    # Verify actual processed chunks
    # -----------------------------------------------------

    for document in response.data:

        document_id = document["document_id"]

        chunks_response = user_supabase.table(
            "document_chunks"
        ).select(
            "page"
        ).eq(
            "document_id",
            document_id
        ).execute()

        chunks = chunks_response.data or []

        pages = sorted(
            set(
                chunk.get("page")
                for chunk in chunks
                if chunk.get("page") is not None
            )
        )

        total_pages = len(pages)

        # -------------------------------------------------
        # IMPORTANT:
        #
        # If chunks exist, processing has actually
        # completed even if an old status says processing.
        # -------------------------------------------------

        if len(chunks) > 0:

            actual_status = "completed"

        else:

            actual_status = (
                document.get(
                    "processing_status"
                )
                or "processing"
            )

        documents.append({

            "document_id": document_id,

            "filename": document["filename"],

            "storage_path": document.get(
                "storage_path"
            ),

            "processing_status": actual_status,

            "processing_error": document.get(
                "processing_error"
            ),

            "total_pages": total_pages,

            "chunk_count": len(chunks)

        })

    return {
        "documents": documents
    }


# =========================================================
# CREATE CONVERSATION
# =========================================================

@app.post("/conversations")
def create_conversation(
    credentials=Depends(security_scheme)
):

    token = credentials.credentials

    try:

        check_user = supabase.auth.get_user(token)

        user_id = check_user.user.id

    except Exception:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token."
        )

    options = ClientOptions(
        headers={
            "Authorization": f"Bearer {token}"
        }
    )

    user_supabase = create_client(
        SUPABASE_URL,
        SUPABASE_KEY,
        options=options
    )

    response = user_supabase.table(
        "conversations"
    ).insert({

        "user_id": user_id,

        "title": "New Conversation"

    }).execute()

    return {

        "message":
            "Conversation created successfully.",

        "conversation":
            response.data[0]

    }


# =========================================================
# GET CONVERSATIONS
# =========================================================

@app.get("/conversations")
def get_conversations(
    credentials=Depends(security_scheme)
):

    token = credentials.credentials

    try:

        check_user = supabase.auth.get_user(token)

        user_id = check_user.user.id

    except Exception:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token."
        )

    options = ClientOptions(
        headers={
            "Authorization": f"Bearer {token}"
        }
    )

    user_supabase = create_client(
        SUPABASE_URL,
        SUPABASE_KEY,
        options=options
    )

    response = user_supabase.table(
        "conversations"
    ).select(
        "conversation_id, title, created_at"
    ).eq(
        "user_id",
        user_id
    ).order(
        "created_at",
        desc=True
    ).execute()

    return {
        "conversations": response.data
    }


# =========================================================
# GET CONVERSATION MESSAGES
# =========================================================

@app.get(
    "/conversations/{conversation_id}/messages"
)
def get_conversation_messages(
    conversation_id: str,
    credentials=Depends(security_scheme)
):

    token = credentials.credentials

    try:

        check_user = supabase.auth.get_user(token)

        user_id = check_user.user.id

    except Exception:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token."
        )

    options = ClientOptions(
        headers={
            "Authorization": f"Bearer {token}"
        }
    )

    user_supabase = create_client(
        SUPABASE_URL,
        SUPABASE_KEY,
        options=options
    )

    conversation_check = user_supabase.table(
        "conversations"
    ).select(
        "conversation_id"
    ).eq(
        "conversation_id",
        conversation_id
    ).eq(
        "user_id",
        user_id
    ).execute()

    if not conversation_check.data:

        raise HTTPException(
            status_code=404,
            detail="Conversation not found."
        )

    response = user_supabase.table(
        "messages"
    ).select(
        """
        message_id,
        conversation_id,
        document_id,
        role,
        content,
        created_at
        """
    ).eq(
        "conversation_id",
        conversation_id
    ).eq(
        "user_id",
        user_id
    ).order(
        "created_at",
        desc=False
    ).execute()

    return {

        "conversation_id":
            conversation_id,

        "messages":
            response.data

    }


# =========================================================
# SIGNUP
# =========================================================

@app.post("/signup")
def add_user(
    user: UserCreate
):

    credentials = {

        "email":
            user.email,

        "password":
            user.password

    }

    try:

        signup_result = (
            supabase
            .auth
            .sign_up(credentials)
        )

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    user_id = (
        signup_result.user.id
        if signup_result.user
        else None
    )

    return {

        "message":
            "Signup successful",

        "user_id":
            user_id

    }


# =========================================================
# LOGIN
# =========================================================

@app.post("/login")
def login_user(
    user: UserLogin
):

    credentials = {

        "email":
            user.email,

        "password":
            user.password

    }

    try:

        login_result = (
            supabase
            .auth
            .sign_in_with_password(
                credentials
            )
        )

    except Exception:

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password."
        )

    login_user_id = (
        login_result.user.id
    )

    session_token = (
        login_result
        .session
        .access_token
    )

    return {

        "UUID":
            login_user_id,

        "access_token":
            session_token

    }


# =========================================================
# DELETE DOCUMENT
# =========================================================

@app.delete(
    "/documents/{document_id}"
)
def delete_document(
    document_id: str,
    credentials=Depends(security_scheme)
):

    token = credentials.credentials

    try:

        check_user = (
            supabase
            .auth
            .get_user(token)
        )

        user_id = check_user.user.id

    except Exception:

        raise HTTPException(
            status_code=401,
            detail="Invalid or expired authentication token."
        )

    options = ClientOptions(
        headers={
            "Authorization":
                f"Bearer {token}"
        }
    )

    user_supabase = create_client(
        SUPABASE_URL,
        SUPABASE_KEY,
        options=options
    )

    document_response = (
        user_supabase
        .table("documents")
        .select(
            "document_id, storage_path"
        )
        .eq(
            "document_id",
            document_id
        )
        .eq(
            "user_id",
            user_id
        )
        .execute()
    )

    if not document_response.data:

        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    document = document_response.data[0]

    storage_path = document[
        "storage_path"
    ]

    # Delete chunks
    user_supabase.table(
        "document_chunks"
    ).delete().eq(
        "document_id",
        document_id
    ).execute()

    # Delete storage file
    user_supabase.storage.from_(
        "documents"
    ).remove([
        storage_path
    ])

    # Delete DB document
    user_supabase.table(
        "documents"
    ).delete().eq(
        "document_id",
        document_id
    ).eq(
        "user_id",
        user_id
    ).execute()

    # Delete Chroma vectors
    collection = (
        chroma_client
        .get_collection(
            name="documents"
        )
    )

    chroma_data = collection.get(

        where={

            "$and": [

                {
                    "document_id":
                        document_id
                },

                {
                    "user_id":
                        str(user_id)
                }

            ]

        }

    )

    if chroma_data["ids"]:

        collection.delete(
            ids=chroma_data["ids"]
        )

    return {

        "message":
            "Document deleted successfully."

    }


# =========================================================
# ASK QUESTION
# =========================================================

@app.post("/ask")
def ask_question(
    request: AskRequest,
    credentials=Depends(security_scheme)
):

    token = credentials.credentials

    try:

        check_user = (
            supabase
            .auth
            .get_user(token)
        )

        user_id = check_user.user.id

    except Exception:

        raise HTTPException(
            status_code=401,
            detail="Invalid or expired authentication token."
        )

    options = ClientOptions(
        headers={
            "Authorization":
                f"Bearer {token}"
        }
    )

    user_supabase = create_client(
        SUPABASE_URL,
        SUPABASE_KEY,
        options=options
    )

    # -----------------------------------------------------
    # Check document
    # -----------------------------------------------------

    document_check = (
        user_supabase
        .table("documents")
        .select(
            "document_id, processing_status"
        )
        .eq(
            "document_id",
            request.document_id
        )
        .eq(
            "user_id",
            user_id
        )
        .execute()
    )

    if not document_check.data:

        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    # -----------------------------------------------------
    # Verify actual chunks
    # -----------------------------------------------------

    chunk_check = (
        user_supabase
        .table("document_chunks")
        .select(
            "page"
        )
        .eq(
            "document_id",
            request.document_id
        )
        .execute()
    )

    if not chunk_check.data:

        raise HTTPException(
            status_code=400,
            detail="Document is still processing or contains no readable text."
        )

    # -----------------------------------------------------
    # Check conversation
    # -----------------------------------------------------

    conversation_check = (
        supabase
        .table("conversations")
        .select(
            "conversation_id, user_id"
        )
        .eq(
            "conversation_id",
            request.conversation_id
        )
        .execute()
    )

    if not conversation_check.data:

        raise HTTPException(
            status_code=404,
            detail="Conversation not found."
        )

    conversation = conversation_check.data[0]

    if str(conversation["user_id"]) != str(user_id):

        raise HTTPException(
            status_code=403,
            detail="You do not have access to this conversation."
        ) 

    # -----------------------------------------------------
    # Retrieval
    # -----------------------------------------------------

    retrieved_chunks = retrieve(

        request.query,

        user_id,

        request.document_id

    )

    if not retrieved_chunks:

        answer = (
            "I don't have enough information "
            "in the provided documents."
        )

        return {

            "answer":
                answer,

            "citations":
                []

        }

    # -----------------------------------------------------
    # Build context
    # -----------------------------------------------------

    context = build_context(
        retrieved_chunks
    )

    # -----------------------------------------------------
    # Generate answer
    # -----------------------------------------------------

    answer = generate_answer(

        request.query,

        context

    )

    # -----------------------------------------------------
    # Detect abstention
    # -----------------------------------------------------

    normalized_answer = (
        answer
        .lower()
        .strip()
    )

    abstention_phrases = [

        "i don't have enough information",

        "i do not have enough information",

        "not enough information",

        "information is not available"

    ]

    is_abstention = any(

        phrase in normalized_answer

        for phrase in abstention_phrases

    )

    # -----------------------------------------------------
    # Save user message
    # -----------------------------------------------------

    user_supabase.table(
        "messages"
    ).insert({

        "conversation_id":
            request.conversation_id,

        "user_id":
            user_id,

        "document_id":
            request.document_id,

        "role":
            "user",

        "content":
            request.query

    }).execute()

    # -----------------------------------------------------
    # Save assistant message
    # -----------------------------------------------------

    assistant_message = (
        user_supabase
        .table("messages")
        .insert({

            "conversation_id":
                request.conversation_id,

            "user_id":
                user_id,

            "document_id":
                request.document_id,

            "role":
                "assistant",

            "content":
                answer

        })
        .execute()
    )

    # -----------------------------------------------------
    # Citations
    # -----------------------------------------------------

    citations = []

    seen = set()

    assistant_message_id = (
        assistant_message
        .data[0]
        ["message_id"]
    )

    if not is_abstention:

        for chunk in retrieved_chunks:

            metadata = (
                chunk["metadata"]
            )

            filename = (
                metadata.get(
                    "filename"
                )
            )

            page = (
                metadata.get(
                    "page"
                )
            )

            citation_key = (
                filename,
                page
            )

            if citation_key in seen:
                continue

            citation = {

                "message_id":
                    assistant_message_id,

                "document_id":
                    request.document_id,

                "filename":
                    filename,

                "page":
                    page

            }

            user_supabase.table(
                "citations"
            ).insert(
                citation
            ).execute()

            citations.append({

                "filename":
                    filename,

                "page":
                    page

            })

            seen.add(
                citation_key
            )

    return {

        "answer":
            answer,

        "citations":
            citations

    }