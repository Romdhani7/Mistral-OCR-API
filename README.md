# 🧾 Optical Character Recognition (OCR) & Mistral OCR

## 📖 Introduction to OCR  
Optical Character Recognition (OCR) is a technology that extracts text from images, scanned documents, and printed or handwritten text. Modern OCR solutions go beyond simple character recognition by integrating **machine learning (ML) and natural language processing (NLP)** to improve accuracy and context understanding.

### 🌟 Evolution of OCR  
Traditional OCR methods, such as **Tesseract**, relied on rule-based algorithms to detect and recognize text. However, modern OCR solutions use **deep learning models**, significantly improving accuracy on handwritten and noisy text.

### 🚀 Mistral OCR – A Hybrid Approach  
Mistral OCR is an advanced OCR system that enhances traditional text extraction methods with **language understanding**. It combines:  
- **Deep Learning OCR**: Extracts text from images with high precision.  
- **Large Language Models (LLMs)**: Understands and structures extracted text for better usability.  
- **Automated Data Validation**: Ensures extracted data follows a meaningful structure.
 
![Mistral OCR Image](https://i.gzn.jp/img/2025/03/07/mistral-ocr/02.png)

Optical Character Recognition (OCR) is a technology that extracts text from images, scanned documents, and printed or handwritten text. Modern OCR solutions go beyond simple character recognition by integrating **machine learning (ML) and natural language processing (NLP)** to improve accuracy and context understanding.


---

## 🏗 Mistral OCR Architecture  

Mistral OCR is divided into two main parts:

### 1️⃣ **Text Extraction Pipeline (Computer Vision-based OCR)**  
This stage processes the image and extracts raw text. It consists of:  
- **Preprocessing:** Uses OpenCV to enhance contrast and remove noise.  
- **OCR Engine:** Utilizes **EasyOCR** for recognizing characters and words.  
- **Bounding Box Detection:** Identifies text regions within the document.  


## 🚀 Mistral OCR API – My Project

### 🎯 Purpose & Implementation
🔹 Purpose
The goal of this project is to automate financial document processing by combining OCR and language models to extract, validate, and format structured data. This is useful for:

Expense tracking
Invoice processing
Financial auditing

### 📦 Installation Guide

🔹 Prerequisites
Python 3.10+
Git
🔹 Clone & Setup

git clone https://github.com/yourusername/mistral-ocr-api.git
cd mistral-ocr-api

🔹 Environment Setup

python -m venv .venv
source .venv/bin/activate  # On Windows, use: .venv\Scripts\activate
pip install -r requirements.txt

🔹 Initialize Components

python -m spacy download en_core_web_sm
python scripts/download_models.py

🚦 API Usage
🔹 Single File Processing

curl -X POST "http://localhost:8000/ocr" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@receipt.jpg"
🔹 Batch Processing

import requests

url = "http://localhost:8000/batch"
files = [('files', open(f'receipt_{i}.jpg', 'rb')) for i in range(5)]
response = requests.post(url, files=files, headers={"Authorization": "Bearer YOUR_TOKEN"})

🎬 Demo Video
[![Demo Video](demo.gif)




👤 Author
Romdhani Amina


