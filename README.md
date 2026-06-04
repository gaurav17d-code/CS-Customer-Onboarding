# Customer Onboarding & Verification Automation System

## Overview
A **Streamlit-based prototype** for automating customer onboarding and document verification in the oil & gas / energy sector. This system handles multi-product onboarding (Bitumen, Sulphur, HSD, SEZ) with automated document classification, OCR-based field extraction, product-specific checklist validation, and CMR (Customer Master Record) generation.

## Key Features

### Evidence-First Review Design
- **Human-in-the-Loop**: Side-by-side document preview (image/PDF) and extracted fields for manual verification
- **Editable Extracted Data**: Operators can correct OCR errors inline
- **Approval/Rejection Workflow**: Each document can be approved, rejected, or flagged for re-upload

### Automated Processing Pipeline
1. **OCR**: Tesseract-based text extraction from scanned PDFs, JPG, PNG
2. **Classification**: Keyword-based document type detection (GST Certificate, PAN, Bank Proof, etc.)
3. **Field Extraction**: Regex-based structured data extraction (GSTIN, PAN, Account Number, etc.)
4. **Checklist Validation**: Product-specific mandatory document checklist
5. **Cross-Verification**: Detect conflicts (e.g., GSTIN mismatch across documents)
6. **CMR Generation**: Populate Excel template using `openpyxl`
7. **Exception Report**: PDF report highlighting missing/rejected documents

### Multi-Page Streamlit Interface
- **Create Case**: Register new customer with product type selection
- **Upload Documents**: Bulk file upload with auto-classification
- **Review Workspace**: Evidence panel + field editing + approval workflow
- **CMR Generator**: Export final CMR Excel and exception report
- **Admin Dashboard**: Audit logs, case statistics, database diagnostics

### Audit & Compliance
- **Full Audit Trail**: Every action (case creation, upload, review, approval) logged to SQLite
- **Configurable Rules**: Business logic externalized to JSON files (no hardcoding)

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| **UI** | Streamlit |
| **OCR** | Tesseract (pytesseract) |
| **Image Processing** | OpenCV, Pillow, pdf2image |
| **Database** | SQLite |
| **Excel Generation** | openpyxl |
| **PDF Reports** | ReportLab |
| **Backend** | Python 3.9+ |

---

## Project Structure

```
CS-Customer-Onboarding/
├── app.py                    # Main Streamlit entry point
├── database.py               # SQLite schema and CRUD functions
├── ocr_engine.py             # OCR extraction logic (Tesseract)
├── classifier.py             # Document type classification
├── extractor.py              # Regex-based field extraction
├── rules_engine.py           # Checklist validation logic
├── cross_verifier.py         # Cross-document conflict detection
├── cmr_mapper.py             # CMR Excel template population
├── report_generator.py       # Exception report (PDF)
├── requirements.txt          # Python dependencies
├── config/
│   ├── checklist_rules.json  # Product-specific doc requirements
│   ├── cmr_mapping.json      # Field mapping for CMR Excel
│   └── extraction_patterns.json # Regex patterns for field extraction
├── pages/
│   ├── 01_create_case.py
│   ├── 02_upload_documents.py
│   ├── 03_review_workspace.py
│   ├── 04_cmr_generator.py
│   └── 05_admin.py
└── README.md
```

---

## Installation & Setup

### Prerequisites
- Python 3.9 or higher
- Tesseract OCR installed on your system:
  - **Ubuntu/Debian**: `sudo apt-get install tesseract-ocr`
  - **macOS**: `brew install tesseract`
  - **Windows**: Download installer from [https://github.com/tesseract-ocr/tesseract](https://github.com/tesseract-ocr/tesseract)

### Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/gaurav17d-code/CS-Customer-Onboarding.git
   cd CS-Customer-Onboarding
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize database**
   ```bash
   python database.py
   ```
   This creates `onboarding.db` with required tables.

5. **Run the application**
   ```bash
   streamlit run app.py
   ```
   The app will open at `http://localhost:8501`

---

## Usage Workflow

### Step 1: Create a Case
- Navigate to **"Create Case"** page
- Enter customer details (Name, GSTIN, PAN, etc.)
- Select **Product Type** (Bitumen / Sulphur / HSD / SEZ)
- Click **"Create Case"**

### Step 2: Upload Documents
- Go to **"Upload Documents"**
- Select the case created in Step 1
- Upload scanned documents (PDF/JPG/PNG)
- Choose **"Auto-detect"** or manually specify document type
- Click **"Process & Save Documents"**

### Step 3: Review & Approve
- Open **"Review Workspace"**
- View **checklist status** (missing documents highlighted)
- Select a document to review:
  - **Left Panel**: Document preview + OCR text
  - **Right Panel**: Extracted fields (editable)
- Correct any extraction errors
- Mark document as **Approved** or **Rejected**
- Click **"Save Changes"**
- Repeat for all documents
- Once all approved and checklist satisfied, click **"Mark Case as Complete"**

### Step 4: Generate CMR & Reports
- Navigate to **"CMR Generator"**
- Click **"Generate CMR Excel"** → Download populated template
- Click **"Generate Exception Report"** → Download PDF with exceptions

### Step 5: Monitor (Admin)
- Visit **"Admin Dashboard"**
- View case statistics, audit logs, and database diagnostics

---

## Configuration Files

### `config/checklist_rules.json`
Defines mandatory documents for each product type:
```json
{
  "Bitumen": [
    "GST Registration Certificate",
    "PAN Card",
    "Bank Account Proof"
  ],
  "SEZ": [
    "SEZ Approval Letter",
    "Export License"
  ]
}
```

### `config/extraction_patterns.json`
Regex patterns for field extraction:
```json
{
  "gstin": "\\b\\d{2}[A-Z]{5}\\d{4}[A-Z]{1}[A-Z\\d]{1}[Z]{1}[A-Z\\d]{1}\\b",
  "pan": "\\b[A-Z]{5}\\d{4}[A-Z]{1}\\b"
}
```

### `config/cmr_mapping.json`
Maps extracted fields to CMR Excel columns:
```json
{
  "customer_name": "B2",
  "gstin": "B5",
  "pan": "B6"
}
```

---

## Deployment Notes

### Deploy on Render.com (Recommended)

Render.com offers free hosting for Streamlit applications with better stability than Streamlit Community Cloud.

1. **Sign up** at [render.com](https://render.com) (no credit card required)
2. Click **New +** → **Web Service**
3. Connect your GitHub account and select this repository
4. Configure the service:
   - **Name**: Choose a unique name (e.g., `cs-customer-onboarding`)
   - **Environment**: `Python 3`
   - **Region**: Choose closest to you
   - **Branch**: `main`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `streamlit run app.py --server.port=$PORT --server.address=0.0.0.0`
   - **Instance Type**: Select **Free**
5. Click **Create Web Service**
6. Wait 3-5 minutes for deployment to complete
7. Access your app at the generated URL (e.g., `https://cs-customer-onboarding.onrender.com`)

### Deploy on Streamlit Community Cloud (Alternative)

1. **Fork** this repository to your GitHub account
2. Sign in to [share.streamlit.io](https://share.streamlit.io)
3. Click **New app** and select:
   - Repository: `your-username/CS-Customer-Onboarding`
   - Branch: `main`  
   - Main file path: `app.py`
4. Click **Deploy**
5. Your app will be live at `https://share.streamlit.io/your-username/cs-customer-onboarding`

**Note**: Streamlit Community Cloud may experience caching issues. If you encounter import errors after deployment, try the Render.com option above.

### Performance
- **Target**: 2-5 minutes processing time for a typical case (5-10 documents)
- **Hardware**: Commodity server (4 CPU cores, 8GB RAM)
- **Scaling**: For production, replace SQLite with PostgreSQL and add async processing

### Security
- Uploaded documents stored in `uploads/` directory (ensure proper access controls)
- Audit logs track all user actions for compliance
- Sensitive data (GSTIN, PAN, account numbers) should be encrypted at rest (not implemented in prototype)

### Limitations (Prototype)
- No user authentication (add Streamlit-Auth or OAuth for production)
- No concurrency safeguards (SQLite may lock under heavy load)
- OCR accuracy depends on scan quality
- PDF preview requires `pdf2image` and `poppler-utils`

---

## Future Enhancements

- [ ] **ML-based Classification**: Replace keyword matching with trained classifier
- [ ] **Layout Analysis**: Use LayoutLM or similar for better field extraction
- [ ] **Workflow Engine**: Implement configurable approval workflows
- [ ] **Integration**: Connect to SAP/ERP for automatic CMR upload
- [ ] **Notifications**: Email/SMS alerts for case status changes
- [ ] **Analytics**: Dashboard with processing time metrics

---

## License
MIT License

## Contact
For questions: gaurav17d.code@github.com

## Acknowledgments
Built as a prototype for customer onboarding automation in the oil & gas sector.
