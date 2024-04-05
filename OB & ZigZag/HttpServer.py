"""
Set FLASK_APP="HttpServer.py"
Set FLASK_DEBUG=0
python -m flask run --host=0.0.0.0
"""

from flask import Flask, request

app = Flask(__name__)

@app.route('/api', methods=['POST'])
def handle_request():
    data = request.json
    # Process data and perform actions as needed
    print("Received data:", data)
    return "Data received successfully"

if __name__ == "__main__":
    app.run()