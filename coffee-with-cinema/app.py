import os
import json
import requests
import io
import re
from flask import Flask, render_template, request, jsonify, session, send_file
from concurrent.futures import ThreadPoolExecutor, as_completed

# PDF generation tools
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# Word document tools
from docx import Document
from xml.sax.saxutils import escape

app = Flask(__name__)
app.secret_key = 'super_secret_key_change_this'

# --- Configuration ---
OLLAMA_API = "http://localhost:11434/api/generate"
MODEL_NAME = "granite4:micro"

content_store = {}

# --- 1. The Cleaner Function (Updated) ---
def clean_ai_screenplay(text):
    """Aggressively removes leaked CSS/HTML code from the AI response."""
    if not text: return ""
    
    # 1. Remove the specific "color:..." junk seen in your screenshot
    # This regex looks for quotes starting with "color: and ending with >
    text = re.sub(r'"color:[^>]+>', '', text)
    
    # 2. Remove any remaining HTML tags like <br>, <span>
    text = re.sub(r'<[^>]+>', '', text)
    
    # 3. Clean up extra whitespace left behind
    text = text.replace('&nbsp;', ' ')
    
    return text.strip()

def generate_with_ollama(prompt, max_tokens=1500):
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "num_predict": max_tokens
        }
    }
    try:
        response = requests.post(OLLAMA_API, json=payload, timeout=120)
        response.raise_for_status()
        result = response.json()
        return result.get('response', '').strip()
    except Exception as e:
        print(f"Error calling Ollama: {str(e)}")
        return None

# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/set_username', methods=['POST'])
def set_username():
    data = request.json
    username = data.get('username', 'Guest')
    session['username'] = username
    return jsonify({'success': True, 'username': username})

@app.route('/generate_content', methods=['POST'])
def generate_content():
    data = request.json
    storyline = data.get('storyline', '')

    if not storyline:
        return jsonify({'error': 'No storyline provided'}), 400

    prompts = {
        "screenplay": f"""
            Act as an award-winning screenwriter.
            Write a 5-page screenplay based on this storyline: {storyline}.
            
            CRITICAL RULES:
            1. Output PLAIN TEXT only. 
            2. Do NOT write any code, HTML, CSS, or JSON.
            3. Do NOT use "color:" or "font-weight" strings.
            
            Formatting:
            - Sluglines in ALL CAPS (e.g., INT. HOUSE - DAY)
            - Character names in ALL CAPS centered
            - Dialogue under character names
        """,
        "characters": f"Create detailed character profiles for: {storyline}",
        "sound_design": f"Create a cinematic sound design plan for: {storyline}"
    }

    results = {}

    with ThreadPoolExecutor(max_workers=3) as executor:
        future_to_key = {executor.submit(generate_with_ollama, prompt): key for key, prompt in prompts.items()}
        
        for future in as_completed(future_to_key):
            key = future_to_key[future]
            try:
                content = future.result()
                if content:
                    # Apply the aggressive cleaning here
                    results[key] = clean_ai_screenplay(content)
            except Exception as e:
                print(f"Parallel Task Error ({key}): {e}")

    if "screenplay" not in results:
        return jsonify({'error': "AI generation failed. Please try again."}), 500
    
    user_key = session.get('username', 'Guest')
    content_store[user_key] = results
    
    return jsonify({'success': True, 'data': results})

@app.route('/download/<format_type>/<content_type>')
def download_file(format_type, content_type):
    user_key = session.get('username', 'Guest')
    user_data = content_store.get(user_key, {})
    text_content = user_data.get(content_type, "No content available.")

    if format_type == 'txt':
        return send_file(
            io.BytesIO(text_content.encode('utf-8')),
            mimetype='text/plain',
            as_attachment=True,
            download_name=f"{content_type}.txt"
        )
    elif format_type == 'pdf':
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []
        for line in text_content.split('\n'):
            if not line.strip():
                elements.append(Spacer(1, 12))
            else:
                clean_line = escape(line)
                elements.append(Paragraph(clean_line, styles['Normal']))
        doc.build(elements)
        buffer.seek(0)
        return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name=f"{content_type}.pdf")
    elif format_type == 'docx':
        doc = Document()
        doc.add_heading(content_type.replace('_', ' ').capitalize(), 0)
        for line in text_content.split('\n'):
            doc.add_paragraph(line)
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return send_file(buffer, mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document', as_attachment=True, download_name=f"{content_type}.docx")
    
    return "Invalid format", 400

if __name__ == '__main__':
    app.run(debug=True, port=5000, threaded=True)
