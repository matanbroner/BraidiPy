"""
Run Flask server
"""
from flask import Flask, request
from werkzeug.serving import WSGIRequestHandler
from braid import Braid

# Create Flask app
app = Flask(__name__)
Braid(app)

# Create heartbeat route
@app.route('/heartbeat', methods=['GET'])
def heartbeat():
    """
    Heartbeat route
    """
    return 'OK'

# Run Flask app
if __name__ == '__main__':
    WSGIRequestHandler.protocol_version = "HTTP/1.1"
    app.run(host='0.0.0.0', port=8080, debug=True)

