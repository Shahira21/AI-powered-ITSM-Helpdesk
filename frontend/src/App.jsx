
import Provisioning from "./provisioning";

import { useEffect, useMemo, useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

const QUICK_QUESTIONS = [
  "My VPN is not connecting",
  "How do I reset my password?",
  "How do I request a new office chair?",
];

function App() {
  const [page, setPage] = useState("submit");

  // Issue submission
  const [description, setDescription] = useState("");
  const [analysis, setAnalysis] = useState(null);
  const [createdTicket, setCreatedTicket] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Dashboard
  const [tickets, setTickets] = useState([]);
  const [ticketsLoading, setTicketsLoading] = useState(false);
  const [ticketError, setTicketError] = useState("");

  // Knowledge base
  const [articles, setArticles] = useState([]);
  const [articlesLoading, setArticlesLoading] = useState(false);
  const [articlesError, setArticlesError] = useState("");
  const [articleSearch, setArticleSearch] = useState("");
  const [category, setCategory] = useState("All");
  const [selectedArticle, setSelectedArticle] = useState(null);

  // Chatbot
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      answer:
        "Hello! I'm your IT support assistant. Ask me about VPN access, passwords, software, or workplace IT services.",
      sources: [],
    },
  ]);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState("");

  async function readResponse(response, fallback) {
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.detail || data.error || fallback);
    }
    return data;
  }

  async function analyzeIssue(event) {
    event.preventDefault();
    if (!description.trim()) {
      setError("Please describe your IT issue.");
      return;
    }

    setLoading(true);
    setError("");
    setAnalysis(null);
    setCreatedTicket(null);

    try {
      const response = await fetch(`${API_URL}/api/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ description: description.trim() }),
      });
      const data = await readResponse(response, "Could not analyze your issue.");
      if (data.error) throw new Error(data.error);
      setAnalysis(data);
    } catch (err) {
      setError(err.message || "Could not connect to the backend.");
    } finally {
      setLoading(false);
    }
  }

  async function createTicket() {
    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${API_URL}/api/tickets`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ description: description.trim() }),
      });
      const data = await readResponse(response, "Could not create the ticket.");
      setCreatedTicket(data.ticket || data);
      await fetchTickets();
    } catch (err) {
      setError(err.message || "Could not create the ticket.");
    } finally {
      setLoading(false);
    }
  }

  async function fetchTickets() {
    setTicketsLoading(true);
    setTicketError("");

    try {
      const response = await fetch(`${API_URL}/api/tickets`);
      const data = await readResponse(response, "Could not load tickets.");
      setTickets(Array.isArray(data) ? data : data.tickets || []);
    } catch (err) {
      setTicketError(err.message || "Could not connect to the ticket service.");
    } finally {
      setTicketsLoading(false);
    }
  }

  
async function updateTicketStatus(ticketReference, newStatus) {
  try {
    const response = await fetch(
      `${API_URL}/api/tickets/${ticketReference}/status`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: newStatus }),
      }
    );

    const data = await readResponse(
      response,
      "Could not update ticket status."
    );

    await fetchTickets();
    return data;
  } catch (err) {
    setTicketError(err.message || "Could not update ticket status.");
    throw err;
  }
}



  async function fetchArticles() {
    setArticlesLoading(true);
    setArticlesError("");

    try {
      // Change this path if your backend uses a different article endpoint.
      const response = await fetch(`${API_URL}/api/knowledge-base`);
      const data = await readResponse(
        response,
        "Could not load knowledge-base articles."
      );
      const items = Array.isArray(data)
        ? data
        : data.articles || data.items || [];
      setArticles(items);
    } catch (err) {
      setArticles([]);
      setArticlesError(
        `${err.message} Check that GET /api/knowledge-base exists in FastAPI.`
      );
    } finally {
      setArticlesLoading(false);
    }
  }

  useEffect(() => {
    if (page === "dashboard") fetchTickets();
    if (page === "knowledge") fetchArticles();
  }, [page]);

  async function sendQuestion(text = question) {
    const prompt = text.trim();
    if (!prompt || chatLoading) return;

    setQuestion("");
    setChatError("");
    setMessages((previous) => [
      ...previous,
      { role: "user", question: prompt },
    ]);
    setChatLoading(true);

    try {
      const response = await fetch(`${API_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: prompt }),
      });
      const data = await readResponse(response, "Could not get a chatbot answer.");

      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          answer: data.answer || "No answer was returned.",
          sources: Array.isArray(data.sources) ? data.sources : [],
          escalation_recommended: Boolean(data.escalation_recommended),
        },
      ]);
    } catch (err) {
      setChatError(
        `${err.message} Make sure FastAPI is running on port 8000.`
      );
    } finally {
      setChatLoading(false);
    }
  }

  function startNewIssue(prefill = "") {
    setDescription(prefill);
    setAnalysis(null);
    setCreatedTicket(null);
    setError("");
    setPage("submit");
  }

  function escalateQuestion(text) {
    startNewIssue(text);
  }

  function getField(item, ...keys) {
    for (const key of keys) {
      if (item?.[key] !== undefined && item[key] !== null) return item[key];
    }
    return "—";
  }

  const categories = useMemo(
    () => [
      "All",
      ...new Set(
        articles.map((article) => article.category).filter(Boolean)
      ),
    ],
    [articles]
  );

  const filteredArticles = useMemo(() => {
    const term = articleSearch.toLowerCase().trim();
    return articles.filter((article) => {
      const matchesCategory =
        category === "All" || article.category === category;
      const text = [
        article.title,
        article.category,
        article.summary,
        article.content,
        article.body,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return matchesCategory && (!term || text.includes(term));
    });
  }, [articles, articleSearch, category]);

  const openCount = tickets.filter((ticket) =>
    ["open", "new", "in progress", "pending"].includes(
      String(ticket.status || "").toLowerCase()
    )
  ).length;

  const resolvedCount = tickets.filter((ticket) =>
    ["resolved", "closed", "completed"].includes(
      String(ticket.status || "").toLowerCase()
    )
  ).length;

  const highPriorityCount = tickets.filter((ticket) =>
    ["p1", "p2", "high", "critical"].includes(
      String(ticket.priority || "").toLowerCase()
    )
  ).length;

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-icon">AI</div>
          <div>
            <h1>ITSM Helpdesk</h1>
            <p>AI-Powered IT Support Platform</p>
          </div>
        </div>

        <nav className="navigation">
          <button
            className={page === "submit" ? "nav-button active" : "nav-button"}
            onClick={() => setPage("submit")}
          >
            Submit an Issue
          </button>
          <button
            className={page === "dashboard" ? "nav-button active" : "nav-button"}
            onClick={() => setPage("dashboard")}
          >
            ITSM Dashboard
          </button>
          <button
            className={page === "knowledge" ? "nav-button active" : "nav-button"}
            onClick={() => setPage("knowledge")}
          >
            Knowledge & Chat
          </button>
          <button
            className={page === "provisioning" ? "nav-button active" : "nav-button"}
            onClick={() => setPage("provisioning")}
          >
            Software Provisioning
          </button>
        </nav>
      </header>

      <main className="main-content">
        {page === "submit" && (
          <>
            <section className="page-heading">
              <span className="eyebrow">EMPLOYEE SELF-SERVICE</span>
              <h2>How can we help you today?</h2>
              <p>
                Describe your IT problem. Analyze it and create a support ticket.
              </p>
            </section>

            <section className="panel issue-panel">
              <h3>Submit a Support Request</h3>
              <form onSubmit={analyzeIssue}>
                <label htmlFor="description">Describe your issue</label>
                <textarea
                  id="description"
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                  placeholder="Example: I cannot connect to the company VPN..."
                  rows={5}
                  required
                />
                <button className="primary-button" type="submit" disabled={loading}>
                  {loading ? "Analyzing..." : "Analyze My Issue"}
                </button>
              </form>

              {error && <p className="error-message">{error}</p>}

              {analysis && !createdTicket && (
                <div className="analysis-result">
                  <h3>Issue Analysis</h3>
                  <div className="details-grid">
                    <Detail label="Intent" value={analysis.intent} />
                    <Detail label="Category" value={analysis.category} />
                    <Detail label="Priority" value={analysis.priority} />
                    <Detail
                      label="Assignment Group"
                      value={analysis.assignment_group || analysis.assignmentGroup}
                    />
                  </div>
                  <div className="resolution-box">
                    <strong>Suggested resolution</strong>
                    <p>
                      {analysis.suggested_resolution ||
                        analysis.resolution ||
                        "Please contact IT support."}
                    </p>
                  </div>
                  <button
                    className="primary-button"
                    onClick={createTicket}
                    disabled={loading}
                  >
                    {loading ? "Creating Ticket..." : "Create Support Ticket"}
                  </button>
                </div>
              )}

              {createdTicket && (
                <div className="success-message">
                  <h3>Ticket Created Successfully!</h3>
                  <p>Your support request has been saved.</p>
                  <div className="ticket-reference">
                    {getField(
                      createdTicket,
                      "ticket_ref",
                      "reference",
                      "ticket_reference",
                      "ticket_id"
                    )}
                  </div>
                  <p>Status: <strong>{createdTicket.status || "Open"}</strong></p>
                  <div className="button-row">
                    <button className="primary-button" onClick={() => setPage("dashboard")}>
                      View Dashboard
                    </button>
                    <button className="secondary-button" onClick={() => startNewIssue()}>
                      Submit Another Issue
                    </button>
                  </div>
                </div>
              )}
            </section>

            <section className="feature-grid">
              <Feature title="AI Ticket Analysis" description="Classify issues and suggest priorities." />
              <Feature title="Knowledge Assistance" description="Search articles and ask the IT chatbot." />
              <Feature title="Ticket Management" description="Store and track support requests through MongoDB." />
            </section>
          </>
        )}

        {page === "dashboard" && (
          <>
            <section className="page-heading dashboard-heading">
              <span className="eyebrow">IT OPERATIONS</span>
              <h2>ITSM Dashboard</h2>
              <p>Monitor support requests saved in your ticket database.</p>
              <button
                className="secondary-button refresh-button"
                onClick={fetchTickets}
                disabled={ticketsLoading}
              >
                {ticketsLoading ? "Refreshing..." : "↻ Refresh Tickets"}
              </button>
            </section>

            <section className="stats-grid">
              <StatCard label="Total Tickets" value={tickets.length} description="All recorded requests" />
              <StatCard label="Open / Active" value={openCount} description="Requests needing attention" />
              <StatCard label="High Priority" value={highPriorityCount} description="P1 and P2 tickets" />
              <StatCard label="Resolved" value={resolvedCount} description="Resolved or closed tickets" />
            </section>

            <section className="panel ticket-table-panel">
              <div className="table-heading">
                <div>
                  <h3>Support Tickets</h3>
                  <p>Latest tickets retrieved from MongoDB</p>
                </div>
                <span className="ticket-count">{tickets.length} tickets</span>
              </div>

              {ticketError && <p className="error-message">{ticketError}</p>}
              {ticketsLoading ? (
                <p className="empty-state">Loading tickets...</p>
              ) : tickets.length === 0 ? (
                <div className="empty-state">
                  <h3>No tickets found</h3>
                  <p>Submit an issue to create your first ticket.</p>
                  <button className="primary-button" onClick={() => startNewIssue()}>
                    Submit an Issue
                  </button>
                </div>
              ) : (
                <div className="table-wrapper">
                  <table className="tickets-table">
                    <thead>
                      <tr>
                        <th>Ticket Reference</th>
                        <th>Issue</th>
                        <th>Category</th>
                        <th>Priority</th>
                        <th>Status</th>
                        <th>Assignment Group</th>
                      </tr>
                    </thead>
                    <tbody>
                      {tickets.map((ticket, index) => (
                        <tr key={ticket._id || ticket.ticket_reference || index}>
                          <td className="reference-cell">
                            {getField(ticket, "ticket_ref", "reference", "ticket_reference", "ticket_id")}
                          </td>
                          <td className="issue-cell">{getField(ticket, "description", "title")}</td>
                          <td>{getField(ticket, "category")}</td>
                          <td>
                            <span
                              className={`priority-badge ${String(
                                ticket.priority || ""
                              ).toLowerCase()}`}
                            >
                              {getField(ticket, "priority")}
                            </span>
                          </td>
                          <td>
                            <select
                              className="text-input"
                              value={ticket.status || "Open"}
                              onChange={(event) => {
                                updateTicketStatus(
                                  ticket.ticket_reference,
                                  event.target.value
                                ).catch(() => {});
                              }}
                              aria-label={`Update status for ${ticket.ticket_reference}`}
                            >
                              <option value="Open">Open</option>
                              <option value="In Progress">In Progress</option>
                              <option value="Resolved">Resolved</option>
                            </select>
                          </td>
                          <td>
                            {getField(
                              ticket,
                              "assignment_group",
                              "assignmentGroup"
                            )}
                          </td>

                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          </>
        )}

        {page === "knowledge" && (
          <>
            <section className="page-heading">
              <span className="eyebrow">EMPLOYEE KNOWLEDGE CENTER</span>
              <h2>Knowledge Base & AI Assistant</h2>
              <p>Search support guidance or ask a question in your own words.</p>
            </section>

            <section className="knowledge-layout">
              <div className="panel knowledge-panel">
                <div className="knowledge-title-row">
                  <div>
                    <h3>Knowledge articles</h3>
                    <p>Browse available IT support guidance.</p>
                  </div>
                  <button
                    className="secondary-button"
                    onClick={fetchArticles}
                    disabled={articlesLoading}
                  >
                    {articlesLoading ? "Loading..." : "Refresh"}
                  </button>
                </div>

                <label htmlFor="article-search">Search articles</label>
                <input
                  id="article-search"
                  className="text-input"
                  value={articleSearch}
                  onChange={(event) => setArticleSearch(event.target.value)}
                  placeholder="Search VPN, passwords, software..."
                />

                <div className="category-filters">
                  {categories.map((item) => (
                    <button
                      key={item}
                      className={category === item ? "filter-chip selected" : "filter-chip"}
                      onClick={() => setCategory(item)}
                    >
                      {item}
                    </button>
                  ))}
                </div>

                {articlesError && <p className="error-message">{articlesError}</p>}
                {articlesLoading ? (
                  <p className="empty-state">Loading articles...</p>
                ) : filteredArticles.length === 0 ? (
                  <div className="empty-state">
                    <h3>No articles to display</h3>
                    <p>
                      {articles.length
                        ? "Try another search or category."
                        : "Add articles to your backend knowledge base, then refresh."}
                    </p>
                  </div>
                ) : (
                  <div className="article-list">
                    {filteredArticles.map((article, index) => (
                      <article className="article-card" key={article._id || article.id || article.title || index}>
                        <span className="article-category">
                          {article.category || "General IT"}
                        </span>
                        <h4>{article.title || "Untitled article"}</h4>
                        <p>
                          {article.summary ||
                            article.content?.slice(0, 150) ||
                            article.body?.slice(0, 150) ||
                            "Open this article to read more."}
                        </p>
                        <button
                          className="text-button"
                          onClick={() => setSelectedArticle(article)}
                        >
                          Read article →
                        </button>
                      </article>
                    ))}
                  </div>
                )}
              </div>

              <div className="panel chat-panel">
                <div className="chat-header">
                  <div className="chat-avatar">AI</div>
                  <div>
                    <h3>IT Support Assistant</h3>
                    <p><span className="online-dot" /> Knowledge-powered help</p>
                  </div>
                </div>

                <div className="quick-questions">
                  {QUICK_QUESTIONS.map((item) => (
                    <button
                      key={item}
                      className="quick-question"
                      disabled={chatLoading}
                      onClick={() => sendQuestion(item)}
                    >
                      {item}
                    </button>
                  ))}
                </div>

                <div className="chat-messages" aria-live="polite">
                  {messages.map((message, index) => (
                    <div
                      key={`${message.role}-${index}`}
                      className={`chat-message ${message.role === "user" ? "user-message" : "assistant-message"}`}
                    >
                      <span className="message-role">
                        {message.role === "user" ? "You" : "IT Assistant"}
                      </span>
                      <p>{message.role === "user" ? message.question : message.answer}</p>

                      {message.sources?.length > 0 && (
                        <div className="source-list">
                          <strong>Sources</strong>
                          {message.sources.map((source, sourceIndex) => (
                            <div className="source-item" key={source.title || sourceIndex}>
                              <span>▤</span>
                              <div>
                                <strong>{source.title || source.name || "Knowledge article"}</strong>
                                {source.category && <small>{source.category}</small>}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}

                      {message.role === "assistant" && message.escalation_recommended && (
                        <div className="escalation-note">
                          <p>This question may need assistance from the IT team.</p>
                          <button
                            className="secondary-button"
                            onClick={() => escalateQuestion(messages[index - 1]?.question || "")}
                          >
                            Create a support ticket
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                  {chatLoading && (
                    <div className="chat-message assistant-message">
                      <span className="message-role">IT Assistant</span>
                      <p className="typing-indicator">Searching knowledge articles…</p>
                    </div>
                  )}
                </div>

                {chatError && <p className="error-message">{chatError}</p>}

                <form
                  className="chat-composer"
                  onSubmit={(event) => {
                    event.preventDefault();
                    sendQuestion();
                  }}
                >
                  <input
                    className="text-input"
                    value={question}
                    onChange={(event) => setQuestion(event.target.value)}
                    placeholder="Ask an IT question..."
                    aria-label="Ask an IT question"
                    disabled={chatLoading}
                  />
                  <button
                    className="primary-button"
                    type="submit"
                    disabled={chatLoading || !question.trim()}
                  >
                    {chatLoading ? "..." : "Send"}
                  </button>
                </form>
                <p className="chat-disclaimer">
                  Answers depend on available knowledge articles. Follow your
                  company's approved IT procedures.
                </p>
              </div>
            </section>
          </>
        )}
        
          {page === "provisioning" && <Provisioning />}

      </main>

      <footer className="app-footer">
        AI-Powered ITSM Helpdesk · React · FastAPI · MongoDB
      </footer>

      {selectedArticle && (
        <div
          className="modal-backdrop"
          role="presentation"
          onClick={(event) => {
            if (event.target === event.currentTarget) setSelectedArticle(null);
          }}
        >
          <section
            className="article-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="article-modal-title"
          >
            <button
              className="modal-close"
              aria-label="Close article"
              onClick={() => setSelectedArticle(null)}
            >
              ×
            </button>
            <span className="article-category">
              {selectedArticle.category || "General IT"}
            </span>
            <h2 id="article-modal-title">{selectedArticle.title || "Knowledge article"}</h2>
            <div className="article-body">
              {selectedArticle.content || selectedArticle.body || selectedArticle.summary || "No article content is available."}
            </div>
            <button
              className="primary-button"
              onClick={() => {
                const title = selectedArticle.title || "Knowledge base question";
                setSelectedArticle(null);
                setQuestion(`I need more help with: ${title}`);
                setPage("knowledge");
              }}
            >
              Ask the chatbot about this
            </button>
          </section>
        </div>
      )}
    </div>
  );
}

function Detail({ label, value }) {
  return (
    <div className="detail-item">
      <span>{label}</span>
      <strong>{value || "Not available"}</strong>
    </div>
  );
}

function StatCard({ label, value, description }) {
  return (
    <div className="stat-card">
      <p>{label}</p>
      <div className="stat-value">{value}</div>
      <span>{description}</span>
    </div>
  );
}

function Feature({ title, description }) {
  return (
    <div className="feature-card">
      <div className="feature-dot">✓</div>
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  );
}

export default App;
