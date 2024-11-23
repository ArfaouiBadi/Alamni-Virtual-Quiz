from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import subprocess
import sys

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

if __name__ == '__main__':
    app.run(debug=True)