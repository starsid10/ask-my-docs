import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";

import {
  Sparkles,
  Mail,
  Lock,
  ArrowRight,
  Eye,
  EyeOff,
  Upload,
  FileText,
  MessageSquare,
  LogOut,
  CheckCircle2,
  Loader2,
  Plus,
} from "lucide-react";

import {
  login,
  signup,
  getDocuments,
  uploadDocument,
  createConversation,
  getConversations,
  getMessages,
  askQuestion,
} from "./api";

import "./App.css";


function getInitials(email) {
  const localPart = (email || "").split("@")[0].trim();

  if (!localPart) {
    return "U";
  }

  const parts = localPart.split(/[._\-\s]+/).filter(Boolean);

  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }

  const cleaned = localPart.replace(/[^A-Za-z0-9]/g, "");
  return cleaned.slice(0, 2).toUpperCase();
}

function App() {
  /* =====================================================
     AUTHENTICATION STATE
  ===================================================== */

  const [token, setToken] = useState(
    localStorage.getItem("access_token")
  );

  const [mode, setMode] = useState("login");

  const [email, setEmail] = useState(() => localStorage.getItem("user_email") || "");
  const [password, setPassword] = useState("");

  const [showPassword, setShowPassword] = useState(false);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");


  /* =====================================================
     DASHBOARD STATE
  ===================================================== */

  const [documents, setDocuments] = useState([]);

  const [documentsLoading, setDocumentsLoading] = useState(false);

  const [selectedDocument, setSelectedDocument] = useState(null);

  const [uploading, setUploading] = useState(false);

  const [searchTerm, setSearchTerm] = useState("");

  const [conversations, setConversations] = useState([]);
  const [conversationsLoading, setConversationsLoading] = useState(false);

  // Human-readable metadata derived from each conversation's messages.
  const [conversationMeta, setConversationMeta] = useState({});


  /* =====================================================
     CHAT STATE
  ===================================================== */

  const [question, setQuestion] = useState("");

  const [asking, setAsking] = useState(false);

  const [conversationId, setConversationId] = useState(null);

  const [messages, setMessages] = useState([]);


  /* =====================================================
     DOCUMENT HELPERS
  ===================================================== */

  function getDocumentId(document) {
    if (!document) {
      return null;
    }

    return (
      document.document_id ||
      document.id ||
      document.documentId ||
      null
    );
  }


  function getDocumentName(document) {
    if (!document) {
      return "Document";
    }

    return (
      document.filename ||
      document.name ||
      document.file_name ||
      "Untitled document"
    );
  }


  function getDocumentStatus(document) {
    if (!document) {
      return "unknown";
    }

    /*
      Backend uses:
      processing_status

      We also support alternative names so the
      frontend remains safe.
    */

    const rawStatus =
      document.processing_status ??
      document.status ??
      document.processingState ??
      "";

    const status = String(rawStatus)
      .trim()
      .toLowerCase();

    /*
      Completed states
    */

    if (
      status === "completed" ||
      status === "complete" ||
      status === "processed" ||
      status === "ready" ||
      status === "success"
    ) {
      return "completed";
    }

    /*
      Failed states
    */

    if (
      status === "failed" ||
      status === "error"
    ) {
      return "failed";
    }

    /*
      Processing states
    */

    if (
      status === "processing" ||
      status === "pending" ||
      status === "queued" ||
      status === "in_progress"
    ) {
      return "processing";
    }

    return status || "unknown";
  }


  function getDocumentPages(document) {
    if (!document) {
      return 0;
    }

    return (
      document.total_pages ??
      document.pages ??
      document.page_count ??
      document.totalPages ??
      0
    );
  }


  function normalizeDocument(document) {
    return {
      ...document,

      document_id: getDocumentId(document),

      filename: getDocumentName(document),

      processing_status: getDocumentStatus(document),

      total_pages: getDocumentPages(document),
    };
  }


  /* =====================================================
     LOAD DOCUMENTS AFTER LOGIN
  ===================================================== */

  useEffect(() => {
    if (!token) {
      return;
    }

    loadDocuments();
    loadConversationList();
  }, [token]);


  /* =====================================================
     LOAD PREVIOUS CONVERSATIONS
  ===================================================== */

  async function loadConversationList() {
    try {
      setConversationsLoading(true);

      const result = await getConversations(token);

      const list = Array.isArray(result)
        ? result
        : Array.isArray(result?.conversations)
          ? result.conversations
          : Array.isArray(result?.data)
            ? result.data
            : [];

      setConversations(list);

      /*
        The backend currently returns generic names such as
        "New Conversation". We derive a useful title from the
        first question instead of changing the working backend.
      */

      const metadataEntries = await Promise.all(
        list.map(async (conversation) => {
          const id =
            conversation?.conversation_id ||
            conversation?.id;

          if (!id) {
            return null;
          }

          try {
            const messageResult = await getMessages(token, id);

            const messageList = Array.isArray(messageResult)
              ? messageResult
              : Array.isArray(messageResult?.messages)
                ? messageResult.messages
                : Array.isArray(messageResult?.data)
                  ? messageResult.data
                  : [];

            const firstUserMessage = messageList.find(
              (message) =>
                String(message?.role || "").toLowerCase() === "user"
            );

            const firstAssistantMessage = messageList.find(
              (message) =>
                String(message?.role || "").toLowerCase() === "assistant"
            );

            const questionText =
              firstUserMessage?.content ||
              firstUserMessage?.message ||
              "";

            let documentName =
              firstUserMessage?.filename ||
              firstUserMessage?.document_name ||
              firstUserMessage?.document_filename ||
              conversation?.filename ||
              conversation?.document_name ||
              "";

            if (
              !documentName &&
              Array.isArray(firstAssistantMessage?.citations) &&
              firstAssistantMessage.citations.length > 0
            ) {
              documentName =
                firstAssistantMessage.citations[0]?.filename ||
                firstAssistantMessage.citations[0]?.document_name ||
                "";
            }

            let title = questionText.trim();

            if (title.length > 48) {
              title = `${title.slice(0, 48).trim()}...`;
            }

            if (!title) {
              title = "New conversation";
            }

            return [
              String(id),
              {
                title,
                documentName,
              },
            ];

          } catch (error) {
            console.warn(
              `Could not load messages for conversation ${id}:`,
              error
            );

            return [
              String(id),
              {
                title: "Previous conversation",
                documentName: "",
              },
            ];
          }
        })
      );

      const metadata = {};

      metadataEntries.forEach((entry) => {
        if (entry) {
          metadata[entry[0]] = entry[1];
        }
      });

      setConversationMeta(metadata);

    } catch (error) {
      console.error("Failed to load conversations:", error);

      const message = error.message?.toLowerCase() || "";

      if (
        message.includes("token") ||
        message.includes("authentication") ||
        message.includes("unauthorized") ||
        message.includes("401")
      ) {
        logout();
      }

    } finally {
      setConversationsLoading(false);
    }
  }


  /* =====================================================
     SELECT PREVIOUS CONVERSATION
  ===================================================== */

  async function handleSelectConversation(conversation) {
    const id =
      conversation?.conversation_id ||
      conversation?.id;

    if (!id) {
      return;
    }

    try {
      setError("");
      setConversationId(id);

      const result = await getMessages(token, id);

      const messageList = Array.isArray(result)
        ? result
        : Array.isArray(result?.messages)
          ? result.messages
          : Array.isArray(result?.data)
            ? result.data
            : [];

      const formattedMessages = messageList.map((message) => ({
        role: message.role,
        content: message.content || "",
        citations: Array.isArray(message.citations)
          ? message.citations
          : [],
      }));

      setMessages(formattedMessages);

      // Restore the document associated with the conversation.
      const documentId =
        messageList.find((message) => message.document_id)?.document_id;

      if (documentId) {
        const matchingDocument = documents.find(
          (document) =>
            String(getDocumentId(document)) === String(documentId)
        );

        if (matchingDocument) {
          setSelectedDocument(matchingDocument);
        }
      }

      setQuestion("");

    } catch (error) {
      console.error("Failed to load conversation:", error);

      setError(
        error.message ||
        "Failed to load this conversation."
      );
    }
  }


  /* =====================================================
     IMPORTANT:
     KEEP CHECKING PROCESSING DOCUMENTS
  ===================================================== */

  useEffect(() => {
    if (!token || !selectedDocument) {
      return;
    }

    const status = getDocumentStatus(selectedDocument);

    /*
      Only poll while the selected document
      is actually processing.
    */

    if (status !== "processing") {
      return;
    }

    const interval = setInterval(() => {
      loadDocuments();
    }, 2000);

    return () => {
      clearInterval(interval);
    };
  }, [
    token,
    selectedDocument?.document_id,
    getDocumentStatus(selectedDocument),
  ]);


  async function loadDocuments() {
    try {
      setDocumentsLoading(true);

      const result = await getDocuments(token);

      console.log(
        "Documents API response:",
        result
      );

      /*
        Backend returns:

        {
          documents: [...]
        }
      */

      let documentList = [];

      if (Array.isArray(result)) {
        documentList = result;
      } else if (Array.isArray(result?.documents)) {
        documentList = result.documents;
      } else if (Array.isArray(result?.data)) {
        documentList = result.data;
      }

      /*
        Normalize all documents.
      */

      const normalizedDocuments =
        documentList.map(normalizeDocument);

      console.log(
        "Normalized documents:",
        normalizedDocuments
      );

      setDocuments(normalizedDocuments);


      /*
        Keep the currently selected document
        if it still exists.
      */

      if (normalizedDocuments.length > 0) {
        setSelectedDocument((previous) => {
          if (!previous) {
            return normalizedDocuments[0];
          }

          const previousId =
            getDocumentId(previous);

          const matchingDocument =
            normalizedDocuments.find(
              (document) =>
                getDocumentId(document) ===
                previousId
            );

          return (
            matchingDocument ||
            normalizedDocuments[0]
          );
        });
      } else {
        setSelectedDocument(null);
      }

    } catch (error) {

      console.error(
        "Failed to load documents:",
        error
      );

      const message =
        error.message?.toLowerCase() || "";

      if (
        message.includes("token") ||
        message.includes("authentication") ||
        message.includes("unauthorized") ||
        message.includes("401")
      ) {
        logout();
      }

    } finally {
      setDocumentsLoading(false);
    }
  }


  /* =====================================================
     LOGIN / SIGNUP
  ===================================================== */

  async function handleSubmit(event) {
    event.preventDefault();

    setError("");
    setLoading(true);

    try {

      /* ================= LOGIN ================= */

      if (mode === "login") {

        const data = await login(
          email,
          password
        );

        console.log(
          "Login successful:",
          data
        );


        if (!data?.access_token) {
          throw new Error(
            "Login succeeded but no access token was returned."
          );
        }


        /*
          Save authentication information.
        */

        localStorage.setItem(
          "access_token",
          data.access_token
        );


        if (data.UUID) {
          localStorage.setItem(
            "user_id",
            data.UUID
          );
        }

  localStorage.setItem("user_email", email);


        /*
          Update React state.

          This switches Login → Dashboard.
        */

        setToken(data.access_token);

        setEmail(email);
        setPassword("");

      }


      /* ================= SIGNUP ================= */

      else {

        await signup(
          email,
          password
        );

        setMode("login");

        setPassword("");

        setError("");

        alert(
          "Signup successful. Please log in."
        );
      }

    } catch (error) {

      console.error(
        "Authentication error:",
        error
      );

      setError(
        error.message ||
        "Something went wrong."
      );

    } finally {

      setLoading(false);
    }
  }


  /* =====================================================
     LOGOUT
  ===================================================== */

  function logout() {

    localStorage.removeItem(
      "access_token"
    );

    localStorage.removeItem(
      "user_id"
    );

  localStorage.removeItem("user_email");

    setToken(null);

    setDocuments([]);

    setSelectedDocument(null);

    setEmail("");

    setPassword("");

    setError("");

    setQuestion("");

    setMessages([]);

    setConversationId(null);

    setSearchTerm("");

    setConversations([]);
  }


  /* =====================================================
     UPLOAD DOCUMENT
  ===================================================== */

  async function handleUpload(event) {

    const file =
      event.target.files?.[0];

    if (!file) {
      return;
    }


    /*
      Only PDF files are accepted.
    */

    if (
      file.type !== "application/pdf" &&
      !file.name
        .toLowerCase()
        .endsWith(".pdf")
    ) {

      alert(
        "Please upload a PDF document."
      );

      event.target.value = "";

      return;
    }


    try {

      setUploading(true);

      setError("");


      /*
        Upload document.

        Backend returns:

        {
          filename,
          document_id,
          processing_status
        }
      */

      const uploadResult =
        await uploadDocument(
          token,
          file
        );


      console.log(
        "Upload response:",
        uploadResult
      );


      /*
        Refresh document list.
      */

      await loadDocuments();


      /*
        If backend returned a document ID,
        immediately select that document.
      */

      if (uploadResult?.document_id) {

        const uploadedDocumentId =
          String(uploadResult.document_id);


        /*
          Find the uploaded document
          from the refreshed list.
        */

        const matchingDocument =
          documents.find(
            (document) =>
              String(
                getDocumentId(document)
              ) === uploadedDocumentId
          );


        if (matchingDocument) {

          setSelectedDocument(
            matchingDocument
          );

        } else {

          /*
            If React has not yet updated the
            documents state, create a temporary
            representation from the upload response.
          */

          setSelectedDocument(
            normalizeDocument({
              document_id:
                uploadResult.document_id,

              filename:
                uploadResult.filename ||
                file.name,

              processing_status:
                uploadResult.processing_status ||
                "processing",

              total_pages: 0,
            })
          );
        }

      }


      /*
        Reset chat for the new document.
      */

      setConversationId(null);

      setMessages([]);

      setQuestion("");


      alert(
        "Document uploaded successfully."
      );

    } catch (error) {

      console.error(
        "Upload error:",
        error
      );

      setError(
        error.message ||
        "Document upload failed."
      );

      alert(
        error.message ||
        "Document upload failed."
      );

    } finally {

      setUploading(false);

      /*
        Allow selecting the same file again.
      */

      event.target.value = "";
    }
  }


  /* =====================================================
     SELECT DOCUMENT
  ===================================================== */

  function handleSelectDocument(document) {

    const normalizedDocument =
      normalizeDocument(document);

    setSelectedDocument(
      normalizedDocument
    );

    /*
      Different document = fresh conversation
      in the current UI.
    */

    setConversationId(null);

    setMessages([]);

    setQuestion("");

    setError("");
  }


  /* =====================================================
     CREATE / GET CONVERSATION ID
  ===================================================== */

  async function getConversationId() {

    /*
      Reuse existing conversation.
    */

    if (conversationId) {
      return conversationId;
    }


    /*
      Create a new conversation.
    */

    const result =
      await createConversation(token);

    console.log(
      "Conversation API response:",
      result
    );


    /*
      Support several possible response shapes.
    */

    const newConversationId =
      result?.conversation?.conversation_id ||
      result?.conversation?.id ||
      result?.conversation_id ||
      result?.id ||
      result?.data?.conversation_id ||
      result?.data?.id;


    if (!newConversationId) {
      throw new Error(
        "Conversation was created but no conversation ID was returned."
      );
    }


    setConversationId(
      newConversationId
    );

    return newConversationId;
  }


  /* =====================================================
     ASK QUESTION
  ===================================================== */

  async function handleAsk(event) {

    if (event) {
      event.preventDefault();
    }


    /*
      Basic validation.
    */

    if (
      !question.trim() ||
      !selectedDocument ||
      asking
    ) {
      return;
    }


    /*
      Check document processing status.
    */

    const documentStatus =
      getDocumentStatus(
        selectedDocument
      );


    if (documentStatus === "processing") {

      setError(
        "Please wait until the document has finished processing."
      );

      return;
    }


    if (documentStatus === "failed") {

      setError(
        "This document could not be processed. Please upload it again."
      );

      return;
    }


    if (documentStatus !== "completed") {

      setError(
        "The document is not ready yet."
      );

      return;
    }


    try {

      setAsking(true);

      setError("");


      /*
        Get/create conversation.
      */

      const currentConversationId =
        await getConversationId();


      const userQuestion =
        question.trim();


      /*
        Immediately display user's question.
      */

      setMessages((previous) => [
        ...previous,

        {
          role: "user",
          content: userQuestion,
        },
      ]);


      /*
        Clear input.
      */

      setQuestion("");


      /*
        Get document ID.
      */

      const documentId =
        getDocumentId(
          selectedDocument
        );


      if (!documentId) {
        throw new Error(
          "Selected document does not have a valid document ID."
        );
      }


      console.log(
        "Asking question:",
        {
          question: userQuestion,
          documentId,
          conversationId:
            currentConversationId,
        }
      );


      /*
        Call FastAPI /ask.
      */

      const result =
        await askQuestion(
          token,
          userQuestion,
          documentId,
          currentConversationId
        );


      console.log(
        "Ask API response:",
        result
      );


      /*
        Display AI answer.
      */

      setMessages((previous) => [
        ...previous,

        {
          role: "assistant",

          content:
            result?.answer ||
            "I couldn't generate an answer.",

          citations:
            Array.isArray(
              result?.citations
            )
              ? result.citations
              : [],
        },
      ]);

      await loadConversationList();

    } catch (error) {

      console.error(
        "Ask error:",
        error
      );


      setError(
        error.message ||
        "Failed to get an answer."
      );

    } finally {

      setAsking(false);
    }
  }


  /* =====================================================
     LOGIN SCREEN
  ===================================================== */

  if (!token) {

    return (

      <div className="auth-page">

        <div className="auth-background-glow glow-one"></div>

        <div className="auth-background-glow glow-two"></div>


        <div className="auth-card">

          {/* ================= BRAND ================= */}

          <div className="auth-brand">

            <div className="auth-logo">

              <Sparkles size={32} />

            </div>


            <h1>
              Ask My Docs
            </h1>


            <p>
              AI-powered document assistant
            </p>

          </div>


          {/* ================= HEADING ================= */}

          <div className="auth-heading">

            <h2>

              {mode === "login"
                ? "Welcome back"
                : "Create your account"}

            </h2>


            <p>

              {mode === "login"
                ? "Sign in to continue to your documents."
                : "Create an account to start asking your documents questions."}

            </p>

          </div>


          {/* ================= FORM ================= */}

          <form
            onSubmit={handleSubmit}
          >

            {/* EMAIL */}

            <div className="input-group">

              <label htmlFor="email">
                Email
              </label>


              <div className="input-wrapper">

                <Mail size={20} />


                <input
                  id="email"
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(event) =>
                    setEmail(
                      event.target.value
                    )
                  }
                  required
                />

              </div>

            </div>


            {/* PASSWORD */}

            <div className="input-group">

              <label htmlFor="password">
                Password
              </label>


              <div className="input-wrapper">

                <Lock size={20} />


                <input
                  id="password"
                  type={
                    showPassword
                      ? "text"
                      : "password"
                  }
                  placeholder="Enter your password"
                  value={password}
                  onChange={(event) =>
                    setPassword(
                      event.target.value
                    )
                  }
                  required
                />


                <button
                  type="button"
                  className="password-toggle"
                  onClick={() =>
                    setShowPassword(
                      !showPassword
                    )
                  }
                >

                  {showPassword ? (
                    <EyeOff size={20} />
                  ) : (
                    <Eye size={20} />
                  )}

                </button>

              </div>

            </div>


            {/* ERROR */}

            {error && (

              <div className="auth-error">
                {error}
              </div>

            )}


            {/* SUBMIT */}

            <button
              type="submit"
              className="auth-submit"
              disabled={loading}
            >

              <span>

                {loading
                  ? "Please wait..."
                  : mode === "login"
                    ? "Login"
                    : "Create account"}

              </span>


              {!loading && (
                <ArrowRight size={20} />
              )}

            </button>

          </form>


          {/* ================= SWITCH ================= */}

          <div className="auth-switch">

            <div className="switch-line"></div>


            <div className="switch-content">

              <span>

                {mode === "login"
                  ? "Don't have an account?"
                  : "Already have an account?"}

              </span>


              <button
                type="button"
                onClick={() => {

                  setMode(
                    mode === "login"
                      ? "signup"
                      : "login"
                  );

                  setError("");

                  setPassword("");

                }}
              >

                {mode === "login"
                  ? "Sign up"
                  : "Login"}

              </button>

            </div>


            <div className="switch-line"></div>

          </div>

        </div>

      </div>

    );
  }


  /* =====================================================
     DASHBOARD
  ===================================================== */

  const filteredDocuments = documents.filter((document) =>
    getDocumentName(document)
      .toLowerCase()
      .includes(searchTerm.trim().toLowerCase())
  );

  return (

    <div className="app">


      {/* =================================================
          SIDEBAR
      ================================================= */}

      <aside className="sidebar">


        {/* ================= BRAND ================= */}

        <div className="brand">

          <div className="brand-icon">

            <Sparkles size={27} />

          </div>


          <div>

            <h1>
              Ask My Docs
            </h1>

            <span>
              AI Document Assistant
            </span>

          </div>

        </div>


        {/* ================= UPLOAD ================= */}

        <label
          className="upload-button"
          style={{
            opacity:
              uploading
                ? 0.65
                : 1,

            pointerEvents:
              uploading
                ? "none"
                : "auto",
          }}
        >

          {uploading ? (

            <Loader2
              size={21}
              className="processing-icon"
            />

          ) : (

            <Upload size={21} />

          )}


          <span>

            {uploading
              ? "Uploading..."
              : "Upload document"}

          </span>


          <input
            type="file"
            accept=".pdf,application/pdf"
            onChange={handleUpload}
            hidden
            disabled={uploading}
          />

        </label>


        {/* =================================================
            DOCUMENTS
        ================================================= */}

        <div className="sidebar-section">

          <div className="section-header">

            <div className="section-title">

              <FileText size={17} />

              <span>
                Documents
              </span>

            </div>

            <Plus size={19} />

          </div>


          <div className="document-list">


            {/* LOADING */}

            {documentsLoading && documents.length === 0 ? (

              <div className="document-item">

                <Loader2
                  size={20}
                  className="processing-icon"
                />


                <div className="document-info">

                  <strong>
                    Loading documents...
                  </strong>

                </div>

              </div>


            ) : documents.length === 0 ? (

              /* NO DOCUMENTS */

              <div className="document-item">

                <FileText size={20} />


                <div className="document-info">

                  <strong>
                    No documents yet
                  </strong>

                  <span>
                    Upload a PDF to begin
                  </span>

                </div>

              </div>


            ) : (

              /* DOCUMENT LIST */

              filteredDocuments.map(
                (document) => {

                  const documentId =
                    getDocumentId(
                      document
                    );


                  const isSelected =
                    getDocumentId(
                      selectedDocument
                    ) === documentId;


                  const status =
                    getDocumentStatus(
                      document
                    );


                  return (

                    <button
                      key={documentId}
                      className={
                        `document-item ${
                          isSelected
                            ? "selected"
                            : ""
                        }`
                      }
                      onClick={() =>
                        handleSelectDocument(
                          document
                        )
                      }
                    >

                      <FileText size={21} />


                      <div className="document-info">

                        <strong>

                          {getDocumentName(
                            document
                          )}

                        </strong>


                        <span>

                          {getDocumentPages(
                            document
                          )}

                          {" pages · "}


                          {status ===
                          "completed"
                            ? "Ready"
                            : status ===
                              "failed"
                              ? "Failed"
                              : status ===
                                "processing"
                                ? "Processing"
                                : "Unknown"}

                        </span>

                      </div>


                      {status ===
                      "completed" ? (

                        <CheckCircle2
                          size={18}
                          className="success-icon"
                        />

                      ) : status ===
                        "failed" ? (

                        <span
                          className="processing-icon"
                          style={{
                            fontSize:
                              "11px",
                          }}
                        >
                          !
                        </span>

                      ) : (

                        <Loader2
                          size={18}
                          className="processing-icon"
                        />

                      )}

                    </button>

                  );

                }

              )

            )}

          </div>

        </div>


        {/* =================================================
            CONVERSATIONS
        ================================================= */}

        <div className="sidebar-section conversations">

          <div className="section-header">

            <div className="section-title">

              <MessageSquare size={17} />

              <span>
                Conversations
              </span>

            </div>

            <Plus size={19} />

          </div>


          <div
            className="conversation-item"
            onClick={() => {

              setConversationId(null);

              setMessages([]);

              setQuestion("");

              setError("");

            }}
          >

            <MessageSquare size={20} />

            <div>

              <strong>
                New conversation
              </strong>

              <span>
                Ask questions about a document
              </span>

            </div>

          </div>

          {conversationsLoading ? (

            <div className="conversation-item">

              <Loader2
                size={19}
                className="processing-icon"
              />

              <div>

                <strong>
                  Loading conversations...
                </strong>

              </div>

            </div>

          ) : conversations.length > 0 ? (

            conversations.map((conversation) => {

              const id =
                conversation?.conversation_id ||
                conversation?.id;

              const isActive =
                String(id) === String(conversationId);

              const metadata =
                conversationMeta[String(id)] || {};

              const title =
                metadata.title ||
                conversation?.title ||
                "Previous conversation";

              const documentName =
                metadata.documentName ||
                conversation?.filename ||
                conversation?.document_name ||
                "";

              let dateText = "";

              if (conversation?.created_at) {
                try {
                  dateText = new Date(
                    conversation.created_at
                  ).toLocaleDateString();
                } catch {
                  dateText = "";
                }
              }

              const subtitle =
                documentName
                  ? documentName
                  : dateText || "Previous conversation";

              return (

                <div
                  key={id}
                  className={`conversation-item ${
                    isActive ? "selected" : ""
                  }`}
                  onClick={() =>
                    handleSelectConversation(
                      conversation
                    )
                  }
                >

                  <MessageSquare size={20} />

                  <div>

                    <strong>
                      {title}
                    </strong>

                    <span>
                      {subtitle}
                    </span>

                  </div>

                </div>

              );

            })

          ) : null}

        </div>


        {/* =================================================
            LOGOUT
        ================================================= */}

        <div className="sidebar-bottom">

          <button
            className="bottom-button"
            onClick={logout}
          >

            <LogOut size={20} />

            <span>
              Logout
            </span>

          </button>

        </div>

      </aside>


      {/* =================================================
          MAIN WORKSPACE
      ================================================= */}

      <main className="workspace">


        {/* ================= TOP BAR ================= */}

        <header className="topbar">

          <div>

            <div className="eyebrow">
              DOCUMENT WORKSPACE
            </div>


            <h2>

              {selectedDocument
                ? getDocumentName(
                    selectedDocument
                  )
                : "Select a document"}

            </h2>

          </div>


          <div className="topbar-actions">

            <div className="search-box">

              <input
                placeholder="Search documents..."
                value={searchTerm}
                onChange={(event) =>
                  setSearchTerm(event.target.value)
                }
              />

            </div>


            <div className="avatar">
              {getInitials(email)}
            </div>

          </div>

        </header>


        {/* =================================================
            CHAT AREA
        ================================================= */}

        <section className="chat-area">


          {selectedDocument ? (

            <>


              {/* ================= DOCUMENT HEADER ================= */}

              <div className="selected-document">

                <div className="document-large-icon">

                  <FileText size={27} />

                </div>


                <div>

                  <strong>

                    {getDocumentName(
                      selectedDocument
                    )}

                  </strong>


                  <span>

                    {getDocumentPages(
                      selectedDocument
                    )}

                    {" pages · "}


                    {getDocumentStatus(
                      selectedDocument
                    ) === "completed"
                      ? "Ready to answer questions"
                      : getDocumentStatus(
                          selectedDocument
                        ) === "failed"
                        ? "Processing failed"
                        : "Processing"}

                  </span>

                </div>


                {getDocumentStatus(
                  selectedDocument
                ) === "completed" ? (

                  <div className="ready-badge">

                    <CheckCircle2 size={16} />

                    Ready

                  </div>

                ) : getDocumentStatus(
                    selectedDocument
                  ) === "failed" ? (

                  <div className="ready-badge">

                    !

                    Failed

                  </div>

                ) : (

                  <div className="ready-badge">

                    <Loader2
                      size={16}
                      className="processing-icon"
                    />

                    Processing

                  </div>

                )}

              </div>


              {/* ================= MESSAGES ================= */}

              <div className="messages">

                {messages.length === 0 ? (

                  <div className="question-hint">

                    <Sparkles size={20} />

                    <span>

                      {getDocumentStatus(
                        selectedDocument
                      ) === "completed"

                        ? (
                          <>
                            Ask anything about{" "}
                            {getDocumentName(
                              selectedDocument
                            )}
                          </>
                        )

                        : getDocumentStatus(
                            selectedDocument
                          ) === "failed"

                          ? (
                            <>
                              This document could not be
                              processed.
                            </>
                          )

                          : (
                            <>
                              Your document is being
                              processed. You can ask
                              questions once it is ready.
                            </>
                          )}

                    </span>

                  </div>

                ) : (

                  messages.map(
                    (message, index) => (

                      <div
                        key={index}
                        className={
                          `message ${
                            message.role ===
                            "user"
                              ? "user-message"
                              : "assistant-message"
                          }`
                        }
                      >

                        <div className="message-content">

                          {message.role === "assistant" ? (
                            <ReactMarkdown>
                              {message.content || ""}
                            </ReactMarkdown>
                          ) : (
                            message.content || ""
                          )}

                        </div>


                        {/* ================= CITATIONS ================= */}

                        {message.role ===
                          "assistant" &&
                          message.citations?.length >
                            0 && (

                          <div className="citations">

                            <strong>
                              Sources
                            </strong>


                            {message.citations.map(
                              (
                                citation,
                                citationIndex
                              ) => (

                                <div
                                  key={
                                    citationIndex
                                  }
                                  className="citation-card"
                                >

                                  <FileText
                                    size={16}
                                  />


                                  <span>

                                    {citation.filename}

                                    {" — Page "}

                                    {citation.page}

                                  </span>

                                </div>

                              )
                            )}

                          </div>

                        )}

                      </div>

                    )
                  )

                )}


                {/* ================= ASKING INDICATOR ================= */}

                {asking && (

                  <div className="message assistant-message">

                    <div className="message-content">

                      <Loader2
                        size={18}
                        className="processing-icon"
                      />

                      {" Generating answer..."}

                    </div>

                  </div>

                )}

              </div>


              {/* ================= ERROR ================= */}

              {error && (

                <div className="auth-error">
                  {error}
                </div>

              )}


              {/* ================= COMPOSER ================= */}

              <div className="composer">

                <textarea

                  placeholder={
                    getDocumentStatus(
                      selectedDocument
                    ) === "completed"

                      ? "Ask a question about this document..."

                      : getDocumentStatus(
                          selectedDocument
                        ) === "failed"

                        ? "Document processing failed..."

                        : "Document is still processing..."
                  }


                  value={question}


                  onChange={(event) =>
                    setQuestion(
                      event.target.value
                    )
                  }


                  onKeyDown={(event) => {

                    if (
                      event.key ===
                        "Enter" &&
                      !event.shiftKey
                    ) {

                      event.preventDefault();

                      handleAsk(event);

                    }

                  }}


                  disabled={
                    getDocumentStatus(
                      selectedDocument
                    ) !== "completed" ||
                    asking
                  }

                />


                <button
                  className="send-button"
                  onClick={handleAsk}

                  disabled={
                    !question.trim() ||
                    getDocumentStatus(
                      selectedDocument
                    ) !== "completed" ||
                    asking
                  }
                >

                  {asking ? (

                    <Loader2
                      size={23}
                      className="processing-icon"
                    />

                  ) : (

                    <ArrowRight size={23} />

                  )}

                </button>


                <div className="composer-footer">

                  <span>
                    Answers are generated
                    from your documents
                  </span>


                  <span>
                    Enter to send ·
                    Shift + Enter for new line
                  </span>

                </div>

              </div>

            </>


          ) : (


            /* =================================================
               NO DOCUMENT SELECTED
            ================================================= */

            <div className="empty-state">

              <div className="empty-icon">

                <Sparkles size={45} />

              </div>


              <h3>
                Start asking your documents
              </h3>


              <p>
                Upload and select a processed
                document, then ask questions
                about its content.
              </p>


              <div className="empty-features">

                <div>

                  <Upload size={19} />

                  Upload documents

                </div>


                <div>

                  <FileText size={19} />

                  Search relevant content

                </div>


                <div>

                  <MessageSquare size={19} />

                  Ask questions with citations

                </div>

              </div>

            </div>

          )}

        </section>

      </main>

    </div>

  );
}


export default App;

