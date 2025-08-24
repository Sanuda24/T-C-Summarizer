from transformers import pipeline
from PyPDF2 import PdfReader
from docx import Document
import torch
import logging
from PIL import Image
import pytesseract
import cv2
import numpy as np
from transformers import BartTokenizer, BartForConditionalGeneration, pipeline
from peft import PeftModel


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import torch
from transformers import pipeline

use_cuda = torch.cuda.is_available()
device_index = 0 if use_cuda else -1

if use_cuda:
    logger.info(f"🚀 Using GPU: {torch.cuda.get_device_name(0)}")
else:
    logger.warning("⚠️ Using CPU (No GPU detected)")

base_model_name = "facebook/bart-base"
model = BartForConditionalGeneration.from_pretrained(base_model_name).to("cuda" if use_cuda else "cpu")
model = PeftModel.from_pretrained(model, "./legal-summarizer-lora")
tokenizer = BartTokenizer.from_pretrained("./legal-summarizer-lora")

#Summarizer pipeline

summarizer = pipeline(
    "summarization",
    model=model,
    tokenizer=tokenizer,
    device=device_index
)

def extract_text_from_image(image_path):
    """Extract text from images using OCR"""
    try:
       
        img = cv2.imread(image_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        processed_img = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        
        text = pytesseract.image_to_string(processed_img)
        return text.strip()
    except Exception as e:
        logger.error(f"Image processing failed: {str(e)}")
        raise

def extract_text_from_file(filepath):
    try:
        if filepath.endswith('.pdf'):
            reader = PdfReader(filepath)
            return ''.join([page.extract_text() for page in reader.pages])
        elif filepath.endswith('.docx'):
            doc = Document(filepath)
            return '\n'.join([p.text for p in doc.paragraphs])
        elif filepath.endswith('.txt'):
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        elif filepath.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
            return extract_text_from_image(filepath)
        return ''
    except Exception as e:
        logger.error(f"File extraction failed: {str(e)}")
        raise

def generate_summary(text):
    try:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        chunk_size = 768 if torch.cuda.is_available() else 512
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        
        return [
            s['summary_text'] 
            for s in summarizer(
                chunks,
                max_new_tokens=256,
                min_length=40,
                do_sample=False
            )
        ]
    finally:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

def simplify_jargon(text):
    dictionary = {
        "hereinafter": "from now on",
        "pursuant to": "under",
        "notwithstanding": "despite",
        "therein": "in there",
        "hereby": "by this",
        "whereas": "while",
        "forthwith": "immediately",
        "witnesseth": "certifies that"
    }
    return {term: meaning for term, meaning in dictionary.items() if term in text.lower()}

