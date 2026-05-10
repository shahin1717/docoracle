# DocOracle: Local Intelligence Workspace

DocOracle is a privacy-focused artificial intelligence platform designed to transform local document repositories into interactive knowledge bases. Utilizing local Large Language Models (LLMs) via Ollama, the platform integrates high-performance Hybrid Search (RAG) with dynamic Knowledge Graph visualization to provide deep analytical insights while ensuring data remains entirely on the user's local infrastructure.

---

## Core Features

### Multi-modal Document Ingestion
Native support for PDF, DOCX, PPTX, and Markdown formats. The system automatically processes document layouts, tables, and speaker notes to ensure high-fidelity data extraction.

### Hybrid RAG Engine
Advanced retrieval system combining Semantic Vector Search (FAISS) and Keyword Search (BM25). The platform utilizes Reciprocal Rank Fusion (RRF) and re-ranking algorithms to deliver high-precision context for LLM generation.

### Dynamic Knowledge Graph
Automated extraction of entities and relationships from processed documents. The system constructs a visual Knowledge Map, enabling users to explore semantic connections and discover non-obvious insights within their data.

### Real-time Workspace
Professional chat interface featuring Server-Sent Events (SSE) for streaming responses, interactive source citations, and automated chat session management.

### Model Management Console
Integrated interface to pull, delete, and monitor Ollama models. Supports a wide range of Large Language Models and Embedding models.

### Privacy and Security
All processing is performed locally. The platform requires no external API keys, data sharing, or telemetry, ensuring complete data sovereignty.

---

## Technical Stack

### Backend and AI Core
- Framework: FastAPI (Python 3.11+)
- Database: SQLAlchemy with SQLite
- Vector Engine: FAISS (Meta AI)
- Graph Library: NetworkX
- Local Inference: Ollama
- Document Parsing: PyMuPDF, python-docx, python-pptx

### Frontend Architecture
- Framework: React 19 with Vite
- Styling: Tailwind CSS
- Visualization: Lucide React, react-force-graph
- Communication: SSE (Server-Sent Events)

---

## Installation and Setup

### 1. Prerequisites
- Node.js: Required for frontend execution.
- Python Environment: Python 3.11+ (Miniconda or Anaconda recommended).

### 2. Initial Configuration
Execute the universal setup script to install system dependencies, configure the Python environment, and initialize Ollama:

```bash
bash setup_all.sh
```
The script will prompt for a Conda environment name (defaults to `docoracle`) and install Ollama.

### 3. Execution
Launch the backend and frontend services simultaneously using the provided startup script:

```bash
bash run.sh
```
Once initialized, the services will be available at:
- Frontend Interface: http://localhost:5173
- Backend API: http://localhost:8000

---

## Usage Instructions

1. Account Creation: Register a local account to manage private chat sessions and document sets.
2. Data Upload: Utilize the sidebar to upload documents into the workspace.
3. Model Selection: Choose the desired LLM from the available models in the dropdown menu.
4. Interaction: Submit queries to the AI. Reference citations are provided to verify the source material used for each response.
5. Visualization: Access the Knowledge Map to view a graphical representation of entities and relations extracted from your documents.

---

## Project Structure

```text
├── ai/                # Core AI logic (Retrieval, Embedding, Chunker)
├── backend/           # FastAPI application & API routes
├── frontend/          # React + Vite frontend
├── knowledge_graph/   # Entity/Relation extraction & Graph building
└── data/              # Local storage (Databases, Index, Uploads)
```

---

## License
This project is licensed under the MIT License.