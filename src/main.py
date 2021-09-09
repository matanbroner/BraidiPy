"""
Run Flask server
"""
import sys
import time
from flask import Flask, request, Response, stream_with_context
from werkzeug.serving import WSGIRequestHandler
from braid import Braid
from core import Patch, generate_patch_stream_string

# Create Flask app
app = Flask(__name__)
Braid(app)

posts = {
    '1': {
        'title': 'Hello World',
        'body': 'This is the first post',
    },
    '2': {
        'title': 'Hello World 2',
        'body': 'This is the second post',
    }
}

# Create heartbeat route
@app.route('/heartbeat', methods=['GET'])
def heartbeat():
    """
    Heartbeat route
    """
    return 'OK'

@app.route('/post/<id>', methods=['GET'])
def get_post(id: str):
    """
    Tests Braid subscriptions on sample Posts resource
    """
    # return current version of resouce, Braid has no
    # way of knowing how to fetch it. 
    # TODO: implement an optional way for Braid to fetch resource
    version = request.version_response({
        "version": len(posts.keys()),
        "body": posts[id]
    })
    # TODO: find a better way to do this
    # The user should not be tasked with returning a version
    if not request.subscribe:
        return version


# Run Flask app
if __name__ == '__main__':
    WSGIRequestHandler.protocol_version = "HTTP/1.1"
    app.run(host='0.0.0.0', port=8080, debug=True)

