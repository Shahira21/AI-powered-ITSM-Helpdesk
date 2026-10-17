
import { useEffect, useState } from "react";

const API = "http://127.0.0.1:8000";

export default function Provisioning() {
  const [software, setSoftware] = useState("Visual Studio Code");
  const [employee, setEmployee] = useState("Employee 001");
  const [requests, setRequests] = useState([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function loadRequests() {
    try {
      const response = await fetch(`${API}/api/provisioning`);
      if (!response.ok) throw new Error("Could not load requests");

      const data = await response.json();
      setRequests(data.requests || []);
    } catch {
      setMessage("Unable to load requests. Check that the backend is running.");
    }
  }

  useEffect(() => {
    loadRequests();
  }, []);

  async function submitRequest(event) {
    event.preventDefault();
    setLoading(true);
    setMessage("");

    try {
      const response = await fetch(`${API}/api/provisioning`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          software_name: software,
          employee,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Request failed");
      }

      setMessage(
        `Request ${data.request.request_number} created successfully!`
      );

      await loadRequests();
    } catch (error) {
      setMessage(error.message || "Could not create request.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ maxWidth: 900, margin: "30px auto", padding: 20 }}>
      <h1>Software Provisioning</h1>
      <p>Request approved software through the IT helpdesk.</p>

      <form
        onSubmit={submitRequest}
        style={{
          display: "grid",
          gap: 14,
          maxWidth: 450,
          padding: 20,
          border: "1px solid #ddd",
          borderRadius: 12,
        }}
      >
        <label>
          Employee
          <input
            value={employee}
            onChange={(e) => setEmployee(e.target.value)}
            required
            style={{ display: "block", width: "100%", padding: 10 }}
          />
        </label>

        <label>
          Software
          <select
            value={software}
            onChange={(e) => setSoftware(e.target.value)}
            style={{ display: "block", width: "100%", padding: 10 }}
          >
            <option>Visual Studio Code</option>
            <option>Python</option>
            <option>Google Chrome</option>
            <option>Microsoft Office</option>
          </select>
        </label>

        <button type="submit" disabled={loading} style={{ padding: 12 }}>
          {loading ? "Submitting..." : "Request Software"}
        </button>

        {message && <p role="status">{message}</p>}
      </form>

      <h2>Request History</h2>

      <button onClick={loadRequests} style={{ padding: 8 }}>
        Refresh Requests
      </button>

      {requests.length === 0 ? (
        <p>No requests found yet.</p>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table
            style={{
              width: "100%",
              marginTop: 16,
              borderCollapse: "collapse",
            }}
          >
            <thead>
              <tr>
                <th style={{ textAlign: "left", padding: 10 }}>Request ID</th>
                <th style={{ textAlign: "left", padding: 10 }}>Software</th>
                <th style={{ textAlign: "left", padding: 10 }}>Employee</th>
                <th style={{ textAlign: "left", padding: 10 }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {requests.map((request) => (
                <tr key={request._id || request.request_number}>
                  <td style={{ padding: 10 }}>
                    {request.request_number}
                  </td>
                  <td style={{ padding: 10 }}>
                    {request.software_name}
                  </td>
                  <td style={{ padding: 10 }}>{request.employee}</td>
                  <td style={{ padding: 10 }}>{request.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p style={{ color: "#777", marginTop: 20 }}>
        Demo mode: requests are recorded, but software is not actually installed.
      </p>
    </main>
  );
}
