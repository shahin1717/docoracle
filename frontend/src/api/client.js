const API_URL = "http://localhost:8000";

// Helper to add auth token to requests
function getHeaders(includeAuth = true) {
  const headers = { "Content-Type": "application/json" };
  if (includeAuth) {
    const token = localStorage.getItem("token");
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
  }
  return headers;
}

// ==================== AUTH ====================
export async function loginUser(email, password) {
  const res = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Login failed");
  }

  const data = await res.json();
  return data; // { access_token: "...", token_type: "bearer" }
}

export async function registerUser(name, email, password) {
  const res = await fetch(`${API_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, email, password }),
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Registration failed");
  }

  return res.json();
}

export async function logoutUser() {
  const res = await fetch(`${API_URL}/auth/logout`, {
    method: "POST",
    headers: getHeaders(),
  });

  if (!res.ok) {
    console.warn("Logout request failed, clearing local token anyway");
  }

  return res.ok;
}

// ==================== DOCUMENTS ====================
export async function getDocuments() {
  const res = await fetch(`${API_URL}/documents`, {
    method: "GET",
    headers: getHeaders(),
  });

  if (!res.ok) {
    throw new Error("Failed to fetch documents");
  }

  return res.json(); // [ { id, name, pages, uploaded_at, ... } ]
}

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append("file", file);

  const token = localStorage.getItem("token");
  const headers = {};
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const res = await fetch(`${API_URL}/documents/upload`, {
    method: "POST",
    headers,
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Upload failed");
  }

  return res.json(); // { id, name, pages, ... }
}

export async function deleteDocument(docId) {
  const res = await fetch(`${API_URL}/documents/${docId}`, {
    method: "DELETE",
    headers: getHeaders(),
  });

  if (!res.ok) {
    throw new Error("Failed to delete document");
  }

  return res.ok;
}

// ==================== CHAT / QUERY ====================
export async function queryDocuments(query, docIds = null) {
  const payload = {
    query,
    doc_ids: docIds, // optional: filter by specific documents
  };

  const res = await fetch(`${API_URL}/chat/query`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error("Query failed");
  }

  return res;
}

// Stream helper for chat responses (Server-Sent Events)
export async function streamQuery(query, docIds = null, onChunk, onError) {
  try {
    const payload = {
      query,
      doc_ids: docIds,
    };

    const token = localStorage.getItem("token");
    const headers = { "Content-Type": "application/json" };
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    const res = await fetch(`${API_URL}/chat/query`, {
      method: "POST",
      headers,
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      throw new Error("Query failed");
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();

      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");

      // Process complete lines
      for (let i = 0; i < lines.length - 1; i++) {
        const line = lines[i];
        if (line.startsWith("data: ")) {
          try {
            const data = JSON.parse(line.slice(6));
            onChunk(data);
          } catch (e) {
            console.error("Parse error:", e);
          }
        }
      }

      // Keep incomplete line in buffer
      buffer = lines[lines.length - 1];
    }

    // Process final line if any
    if (buffer.startsWith("data: ")) {
      try {
        const data = JSON.parse(buffer.slice(6));
        onChunk(data);
      } catch (e) {
        console.error("Parse error:", e);
      }
    }
  } catch (error) {
    onError?.(error);
  }
}

// ==================== KNOWLEDGE GRAPH ====================
export async function getDocumentGraph(docId) {
  const res = await fetch(`${API_URL}/graph/${docId}`, {
    method: "GET",
    headers: getHeaders(),
  });

  if (!res.ok) {
    throw new Error("Failed to fetch graph");
  }

  return res.json(); // { nodes: [...], links: [...] }
}

// ==================== HEALTH ====================
export async function checkHealth() {
  const res = await fetch(`${API_URL}/health`);
  return res.ok;
}