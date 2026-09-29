# MemPoisonGuard

MemPoisonGuard is a provenance-aware framework for detecting and mitigating long-term memory poisoning in AI agents.

## Key features

- Captures memory provenance and SHA-256 integrity hashes
- Screens candidate memories for prompt injection and sensitive authorization claims
- Uses contradiction analysis and trust-risk scoring
- Classifies memory as verified, provisional, or quarantined
- Restricts semantic retrieval to verified memory

## Technology stack

- Python 3.12
- FastAPI
- Streamlit
- SQLite
- ChromaDB
- Sentence Transformers
- Ollama (`qwen2.5:3b`)
- Pandas, scikit-learn, and Plotly

## Controlled evaluation

The prototype was evaluated using 12 controlled memory candidates:

- 5 benign candidates
- 7 malicious candidates
- Baseline: 7 malicious candidates available to retrieval
- MemPoisonGuard: 0 malicious candidates entered verified retrieval

These results apply only to the controlled evaluation set and do not establish universal robustness.

## Setup

```bash
git clone [https://github.com/YOUR_USERNAME/MemPoisonGuard.git](https://github.com/YOUR_USERNAME/MemPoisonGuard.git)
cd MemPoisonGuard
python -m venv .venv
```

Activate the virtual environment:

```bash
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the backend:

```bash
uvicorn app.main:app --reload
```

Run the dashboard:

```bash
streamlit run dashboard/app.py
```

## Security notice

Do not store API keys, credentials, personal data, real user memory, local databases, or model files in this repository. The included scenarios are sanitized controlled examples intended only for security testing.

## Project status

Academic M.Tech Data Science project under development.