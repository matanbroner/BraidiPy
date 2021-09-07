"""
Run Flask server
"""
import sys
import time
from flask import Flask, request, Response, stream_with_context
from werkzeug.serving import WSGIRequestHandler
from braid import Braid
from core import Patch, random_patch_string

# Create Flask app
app = Flask(__name__)
# Braid(app)

# Create heartbeat route
@app.route('/heartbeat', methods=['GET'])
def heartbeat():
    """
    Heartbeat route
    """
    return 'OK'

@app.route('/stream', methods=['GET'])
def stream():
    """
    Stream route
    """
    data = random_patch_string()
    def gen():
        try:
            while True:
                print(data)
                yield data
                time.sleep(1)
        except GeneratorExit:
            print('closed', file=sys.stdout)

    return Response(stream_with_context(gen()))


# Run Flask app
if __name__ == '__main__':
    WSGIRequestHandler.protocol_version = "HTTP/1.1"
    app.run(host='0.0.0.0', port=8080, debug=True)

