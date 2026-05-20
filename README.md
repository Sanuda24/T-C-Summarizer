# Legal Lens — Terms & Conditions Summarizer with AI

A full-stack web application that uses a fine-tuned BART transformer model 
to convert complex legal Terms & Conditions documents into plain-English summaries.

## Results
| Metric | Baseline | Legal Lens | Target |
|--------|----------|------------|--------|
| ROUGE-L | 0.492 | **0.646** | 0.600 |
| Readability (FK Grade) | 13.2 | **9.9** | 11.0 |
| Processing Time | 8.1s | 10.4s | <12.0s |

## Stack
Python · Flask · MongoDB Atlas · PyTorch · Hugging Face Transformers · 
Tesseract OCR · HTML/CSS/JavaScript · LoRA (PEFT)
