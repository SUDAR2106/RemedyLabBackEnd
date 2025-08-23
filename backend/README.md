# TheRemedyLab-Personalized Treatment App

A FASTAPI -based backend application for document analysis using OCR, NLP, and PDF/Word processing tool , Autoallocation of doctors and to recvice AI Recomemendation 

---

## 📦 Features

- Extract text from PDFs (PyMuPDF, pdfplumber, PyPDF2)
- Read Word documents (`python-docx`)
- OCR from scanned images (`pytesseract`, `opencv-python`, `Pillow`)
- Named Entity Recognition with `spaCy`
- User login with password hashing (`bcrypt`)
- Integration with OpenAI for smart processing
- Postman / Swagger API to test the request the response

---

## 🚀 Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/SUDAR2106/RemedyLabBackEnd
cd personalized-treatment-app
``` 
### 2. Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On macOS/Linux
venv\Scripts\activate.bat  # On Windows
venv\Scripts>.\Activate.ps1 #On Windows - Powershell
``` 
### 3. Install Dependencies

```bash
pip install -r requirements.txt
```
### 4. Set Up Environment Variables
Create a `.env` file in the root directory with the following content:

```
OPENAI_API_KEY=your_openai_api_key
```
### 5. Run the Application

```bash
