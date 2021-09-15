"""
Run Flask server
"""
import sys
import time
import json
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
        'version': 1
    },
    '2': {
        'title': 'Hello World 2',
        'body': 'This is the second post',
        'version': 1
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
    # Middleware will have set up a subscription for this request + user

    # return current version of resouce either as a standard 200 Response or stream Response.
    # Braid has no way of knowing how to fetch it. 
    # TODO: implement an optional way for Braid to fetch resource
    version_or_stream = request.resource({
        "version": len(posts.keys()),
        "body": posts[id]
    })
    
    return version_or_stream

@app.route('/post/<id>', methods=['PUT'])
def put_post(id: str):
    """
    Tests Braid patching (ie. PUT) on sample Posts resource
    """
    # For testing purposes, simply overwrite the current resource 
    # with the content of each patch in the request
    # Later on, use op based CRDT to merge patches
    for patch in request.patches:
        json_patch = json.loads(patch.content)
        posts[id][json_patch["type"]] = json_patch["value"]
        posts[id]["version"] += 1
    # TODO: allow user to set field for auto-advertising of patches
    request.advertise_patches(request.patches)
    return Response(status=200)


# Run Flask app
if __name__ == '__main__':
    WSGIRequestHandler.protocol_version = "HTTP/1.1"
    app.run(host='0.0.0.0', port=8080, debug=True)

