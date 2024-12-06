from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import subprocess
import sys
import fitz  # PyMuPDF
import os
import csv
import google.generativeai as genai
import re

os.environ["GEMINI_API_KEY"] ="AIzaSyCTWZJJqxRI0c7wWn4si2lOcb_D37EYWPQ"
app = Flask(__name__)
CORS(app)

def get_leaderboard():
    try:
        with open('leaderboard.json', 'r') as f:
            leaderboard = json.load(f)
    except FileNotFoundError:
        leaderboard = []
    return leaderboard

@app.route('/leaderboard', methods=['GET'])
def leaderboard():
    return jsonify(get_leaderboard())

@app.route('/start-quiz', methods=['POST'])
def start_quiz():
    data = request.get_json()
    username = data.get('username', 'User')
    python_executable = sys.executable
    script_path = 'main.py'
    subprocess.Popen([python_executable, script_path, username])
    return jsonify({'status': 'Quiz started', 'username': username})

@app.route('/upload-pdf', methods=['POST'])
def upload_pdf():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and file.filename.endswith('.pdf'):
        upload_folder = 'uploads'
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
        file_path = os.path.join(upload_folder, file.filename)
        file.save(file_path)
        questions = generate_questions_from_pdf(file_path)
        return jsonify({'questions': questions})
    return jsonify({'error': 'Invalid file format'}), 400

@app.route('/generate-quiz', methods=['POST'])
def generate_quiz():
    data = request.get_json()
    course_name = data.get('course_name', '')
    if not course_name:
        return jsonify({'error': 'Course name is required'}), 400
    questions = generate_quiz_from_course(course_name)
    write_questions_to_csv(questions)  # Write the generated questions to CSV
    start_quiz()  # Start the quiz
    return jsonify({'questions': questions})

def generate_quiz_with_gemini(text):
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    generation_config = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
        "response_mime_type": "text/plain",
    }
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config=generation_config,
    )
    chat_session = model.start_chat(history=[])
    response = chat_session.send_message(text)
    generated_questions = []
    try:
        generated_questions = parse_quiz_text(response.text)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    return generated_questions
def generate_questions_from_pdf(file_path):
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text()
    chunks = [text[i:i + 1000] for i in range(0, len(text), 1000)]
    questions_list = []
    for chunk in chunks:
        questions = generate_quiz_with_gemini(chunk)
        questions_list.extend(questions)

    with open('generated_questions.csv', 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Question', 'Choice1', 'Choice2', 'Choice3', 'Choice4', 'Answer']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for question in questions_list:
            writer.writerow(question)
        print("Questions written to generated_questions.csv")

    return questions_list

def generate_quiz_from_course(course_name):
    prompt = f"""
    Create 10 beginner-level questions with 4 multiple-choices each for the course "{course_name}".
    The structure of the output should be:
    **Question <number>**
    <Question text>
    Choice1: <Choice1 text>
    Choice2: <Choice2 text>
    Choice3: <Choice3 text>
    Choice4: <Choice4 text>
    Answer: <Choice number>
    """
    response = generate_quiz_with_gemini(prompt)
    return response
def write_questions_to_csv(questions, filename='generated_questions.csv'):
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Question', 'Choice1', 'Choice2', 'Choice3', 'Choice4', 'Answer']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for question in questions:
            writer.writerow(question)
        print(f"Questions written to {filename}")

# Example usage:
questions = generate_quiz_from_course("Advanced Java Programming")
write_questions_to_csv(questions)
def parse_quiz_text(text):
    pattern = re.compile(r'\*\*Question \d+\*\*\n(.*?)\nChoice1:\s(.*?)\nChoice2:\s(.*?)\nChoice3:\s(.*?)\nChoice4:\s(.*?)\nAnswer:\s(\d)', re.DOTALL)
    matches = pattern.findall(text)
    questions = []
    for match in matches:
        question_text = match[0].strip()
        choice1 = match[1].strip()
        choice2 = match[2].strip()
        choice3 = match[3].strip()
        choice4 = match[4].strip()
        answer = match[5].strip()
        question_data = {
            'Question': question_text,
            'Choice1': choice1,
            'Choice2': choice2,
            'Choice3': choice3,
            'Choice4': choice4,
            'Answer': answer
        }
        questions.append(question_data)
    return questions

def generate_quiz_with_gemini(text):
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    generation_config = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
        "response_mime_type": "text/plain",
    }
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config=generation_config,
    )
    chat_session = model.start_chat(history=[])
    response = chat_session.send_message(text)
    generated_questions = []
    try:
        generated_questions = parse_quiz_text(response.text)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    return generated_questions

if __name__ == '__main__':
    app.run(debug=True)