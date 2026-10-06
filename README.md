# Lightweight Resume Screener

A transparent, explainable, and deterministic resume screening application designed for talent acquisition teams and technical portfolio demonstrations. Built with Python, Streamlit, PyMuPDF, and Pandas.

---

## 1. Project Overview

Recruiters frequently receive hundreds of resumes for technical job requisitions. Traditional Applicant Tracking Systems (ATS) often operate as opaque black boxes, while complex LLM-based pipelines can be slow, expensive, nondeterministic, and prone to hallucinations.

The **Lightweight Resume Screener** solves this problem by providing a fast, transparent, and auditable screening tool. It extracts candidate metadata directly from PDF resumes, evaluates them against a customizable job profile using a 100-point scoring system, ranks candidates with deterministic tie-breaking, and provides plain-English score explanations for every candidate.

---

## 2. Key Features

- **Multi-PDF Parsing**: Batch uploads 3–5 resumes simultaneously using PyMuPDF (`fitz`), handling malformed or zero-text documents gracefully with descriptive warnings.
- **Robust Skill Extraction**: Employs word-boundary regular expressions and an alias dictionary (`SKILL_ALIASES`) to recognize naming variations (e.g., `PowerBI` → `Power BI`, `MS Excel` → `Excel`) while preventing false positive substring matches (e.g., `excel` inside `excellent`).
- **Heuristic Information Extraction**:
  - **Candidate Name**: Scans header lines for high-confidence proper names; falls back safely to sanitized filenames without hallucinating.
  - **Years of Experience**: Detects explicit numerical phrases (e.g., *"3+ years of experience"*) and employment date spans (*"2021 - 2024"*).
  - **Education Credentialing**: Identifies degree levels (B.Tech, B.Sc, M.Sc, Master's, Ph.D.) and aligns them with relevant quantitative and analytical fields.
- **Transparent 100-Point Scoring Model**: Component-based scoring (60 Required / 20 Preferred / 15 Experience / 5 Education) bounded strictly within `[0, 100]`.
- **Explainability**: Plain-English rationale for each candidate explaining exactly why points were awarded or deducted.
- **Dynamic Streamlit UI**: Interactive job requirement editing, instant re-ranking, candidate inspection cards, and 1-click CSV export.
- **Built-in Demo Mode**: Includes 5 pre-packaged synthetic test resumes for instant 5-minute live demonstrations.

---

## 3. Architecture

```text
 ┌───────────────────────────┐
 │     PDF Resume Upload     │  (Streamlit UI / 3-5 Resumes)
 └─────────────┬─────────────┘
               │
               ▼
 ┌───────────────────────────┐
 │      Text Extraction      │  (PyMuPDF / Error Handling & Fallbacks)
 └─────────────┬─────────────┘
               │
               ▼
 ┌───────────────────────────┐
 │   Information Extraction  │  (Name, Skills, Experience, Education)
 └─────────────┬─────────────┘
               │
               ▼
 ┌───────────────────────────┐
 │   Job Profile Matching    │  (Alias Dict & Word-Boundary Regex)
 └─────────────┬─────────────┘
               │
               ▼
 ┌───────────────────────────┐
 │     100-Point Scoring     │  (60 Req / 20 Pref / 15 Exp / 5 Edu)
 └─────────────┬─────────────┘
               │
               ▼
 ┌───────────────────────────┐
 │   Deterministic Ranking   │  (Score Descending + Tie-Breaking)
 └─────────────┬─────────────┘
               │
               ▼
 ┌───────────────────────────┐
 │ Results Table / CSV Export│  (Streamlit Dashboard & Downloadable CSV)
 └───────────────────────────┘
```

---

## 4. How to Run

### Prerequisites
- Python 3.9+ (tested up to Python 3.14)

### Quickstart

1. **Clone or navigate into the project directory**:
   ```bash
   cd resume-screener
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **(Optional) Generate sample resumes**:
   ```bash
   python3 generate_samples.py
   ```

5. **Run the unit tests**:
   ```bash
   python3 -m unittest discover -s tests -p "test_*.py" -v
   ```

6. **Launch the Streamlit web application**:
   ```bash
   streamlit run app.py
   ```
   Open your browser to `http://localhost:8501`.

---

## 5. Scoring Methodology

The screener calculates a deterministic score out of **100 points**:

| Component | Maximum Points | Calculation & Logic |
| :--- | :---: | :--- |
| **Required Skills** | **60 pts** | $\frac{\text{matched\_required}}{\text{total\_required}} \times 60$. Core prerequisite skills. |
| **Preferred Skills** | **20 pts** | $\frac{\text{matched\_preferred}}{\text{total\_preferred}} \times 20$. Desirable bonus skills. |
| **Experience** | **15 pts** | For entry-level (0–1 yrs): $\ge 1$ yr = 15 pts; entry-level/internship = 11–13 pts; unstated experience = 7 pts (partial credit rather than auto-rejection). For higher minimum requirements: scaled proportionally. |
| **Education** | **5 pts** | Relevant Bachelor's/Master's/Ph.D. in STEM or analytical field = 5 pts; general degree in adjacent field = 3 pts; none detected = 0 pts. |
| **Total** | **100 pts** | $\min(100.0, \max(0.0, \text{Req} + \text{Pref} + \text{Exp} + \text{Edu}))$. |

### Deterministic Tie-Breaking
When two candidates share identical total scores:
1. Candidate with higher **Required Skills Score** ranks higher.
2. Candidate with higher **Preferred Skills Score** ranks higher.
3. Alphabetical ordering by Candidate Name.

---

## 6. Assumptions

1. **Selectable PDF Text**: Input PDFs contain machine-readable text layers rather than scanned bitmaps.
2. **Rule-Based Matching**: Skill evaluation relies on standard industry terms and defined synonyms.
3. **Conservative Heuristics**: Experience and candidate name extraction favor precision over speculation; the screener never invents or guesses a candidate name.
4. **Recruiter Tooling**: The system acts strictly as an auditable decision-support aid, not an autonomous hiring authority.

---

## 7. Limitations

- **Scanned Images**: PDFs without a selectable text layer require Optical Character Recognition (OCR).
- **Keyword Variation**: Highly idiosyncratic skill descriptions outside the alias map may not match without embeddings or semantic NLP.
- **Experience Ambiguity**: Complex overlapping job dates and career gaps can challenge simple regex parsers.
- **Claim Verification**: The software parses self-reported statements without validating employer records.

---

## 8. Future Improvements

- **OCR Integration**: Incorporate `pytesseract` or `pdf2image` for scanned resumes.
- **Embedding-Based Semantic Matching**: Use lightweight sentence embeddings (e.g., `sentence-transformers`) to match semantic equivalents (e.g., "ETL pipeline authoring" $\approx$ "Data Engineering").
- **LLM-Assisted Section Analysis**: Optional local LLM (e.g., Ollama / Llama 3) for deep narrative synthesis.
- **Bias & Fairness Auditing**: Tooling to redact personally identifiable information (names, emails, graduation years) before scoring to promote blind screening.
- **ATS Webhooks**: Export screened cohorts directly into Greenhouse, Lever, or Workday.

---

## 9. 5-Minute Live Interview Demo Script

| Time | Action | What to Say / Demonstrate |
| :---: | :--- | :--- |
| **0:00 - 1:00** | **Introduction & Problem** | *"In technical recruiting, automated screening often suffers from two extremes: keyword-stuffed ATS filters that reject good talent, or expensive black-box LLMs that hallucinate and can't be audited. I built this lightweight screener to demonstrate an explainable, deterministic 100-point scoring engine."* |
| **1:00 - 2:00** | **Load & Screen Resumes** | 1. Click **'📁 Load 5 Built-in Demo Resumes'**.<br>2. Highlight the 5 distinct candidate archetypes.<br>3. Click **'🚀 Screen Resumes'**.<br>*"Within 200 milliseconds, PyMuPDF parses all documents, extracts skills and experience, and ranks the candidates."* |
| **2:00 - 3:15** | **Explainability & Breakdown** | 1. Show Leaderboard: `#1 Alex Morgan (100)`, `#2 Priya Patel (85)`, down to `#5 Taylor Brooks (32)`.<br>2. Select candidate `#2 Priya Patel`: Show 60/60 required skills, 5/20 preferred, 15/15 experience, and 5/5 education.<br>3. Point to the explanation sentence: *"Every score has a plain-English explanation so a recruiter or hiring manager knows exactly why points were awarded."* |
| **3:15 - 4:15** | **Live Requirement Change** | 1. In the sidebar, add `Tableau` to **Required Skills** (making it 6 required skills).<br>2. Click **'🚀 Screen Resumes'**.<br>3. Show how candidate ranks adjust dynamically in response to business needs.<br>*"Because the logic is deterministic, requirements changes propagate immediately and predictably."* |
| **4:15 - 5:00** | **CSV Export & Wrap-up** | 1. Click **'⬇️ Download Results CSV'**.<br>2. Briefly show the clean exported format.<br>3. Conclude: *"This architecture is transparent, inexpensive to run, completely reproducible, and ready to be extended with semantic embeddings or OCR."* |

---

## 10. Interview Questions & Model Answers

### Q1: Why did you choose a rule-based approach instead of an LLM or vector embeddings?
> *"I chose deterministic rule-based scoring for the initial version because transparency, auditability, speed, and cost efficiency are paramount in hiring compliance. A recruiter needs to explain to candidates and stakeholders why a profile was ranked where it was. Rule-based scoring provides 100% reproducible results with zero API costs, zero hallucination risk, and sub-second execution. Embeddings and LLMs can be added modularly as an enhancement layer for semantic matching without replacing the audit trail."*

### Q2: How do you prevent false positives in skill matching (e.g., 'Excel' matching 'Excellent')?
> *"I used token-level regular expressions with word boundary assertions (`\b(?:excel|ms excel)\b`) combined with case-insensitive matching. This guarantees that substrings appearing inside larger words—such as 'excellent' or the letter 'C' inside 'communication'—are never counted as technical skills."*

### Q3: How does the application handle corrupted or image-only PDFs?
> *"The PyMuPDF wrapper encapsulates text extraction within defensive `try/except` blocks checking page count, byte size, and character output. If a corrupted file or an image-only PDF is uploaded, the parser logs a user-visible warning in the UI advising that OCR is required, while allowing the remaining valid resumes in the batch to process without crashing the application."*

### Q4: How does the system avoid penalizing entry-level candidates who don't list explicit years of experience?
> *"In the scoring engine, if the job profile specifies an entry-level requirement ($\le 1$ year), a candidate without explicitly stated years of experience receives partial credit (7 points out of 15) rather than zero points or an automatic disqualification. This ensures recent graduates and boot camp alumni are evaluated fairly on their verified skills and projects."*

### Q5: How would you scale this to handle 50,000 resumes a day?
> *"First, I would decouple parsing and scoring from the UI by placing incoming documents into an asynchronous queue (such as Celery with Redis or AWS SQS). PyMuPDF text extraction is highly optimized C code, capable of parsing hundreds of pages per second per core. Parsed resume entities would be stored in PostgreSQL with indexed skill tags, while a vector database (such as pgvector or Milvus) could cache embeddings for semantic search."*
