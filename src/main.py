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
    "1": {"title": "Hello World", "body": "This is the first post"},
    "2": {"title": "Hello World 2", "body": "This is the second post"},
}

# Create heartbeat route
@app.route("/heartbeat", methods=["GET"])
def heartbeat():
    """
    Heartbeat route
    """
    return "OK"


@app.route("/post/<id>", methods=["GET"])
def get_post(id: str):
    """
    Tests Braid subscriptions on sample Posts resource
    """
    # Middleware will have set up a subscription for this request + user

    # Braid has no way of knowing how to fetch a resource.
    # TODO: implement an optional way for Braid to fetch resource
    if request.subscribe:
        return request.subscription.stream()
    else:
        version = request.create_version(
            {"version": posts[id]["version"], "body": posts[id]}
        )

        return version


@app.route("/post/<id>", methods=["PUT"])
def put_post(id: str):
    """
    Tests Braid patching (ie. PUT) on sample Posts resource
    """
    # For testing purposes, simply overwrite the current resource
    # with the content of each patch in the request
    # Later on, use op based CRDT to merge patches
    for patch in request.version.patches:
        json_patch = json.loads(patch.content)
        posts[id][json_patch["type"]] = json_patch["value"]
    # TODO: allow user to set field for auto-advertising of patches
    request.advertise_version(request.version)
    return Response(status=200)


# Run Flask app
if __name__ == "__main__":
    WSGIRequestHandler.protocol_version = "HTTP/1.1"
    app.run(host="0.0.0.0", port=8080, debug=True)
