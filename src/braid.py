"""
Braid Handler
Wraps Python application object to inject lifecyle methods
"""

import sys
import json
from flask import request, Response
from core import (
    Subscription,
    is_true,
    subscriber_id,
    generate_patch_stream_string,
    parse_patches,
    advertise_patches,
    generate_articial_subscription_data,
)


class Braid(object):
    def __init__(self, app):
        self.app = app
        self.setup_lifecycle_methods()
        self.subscriptions = {}

    def setup_lifecycle_methods(self):
        """
        Setup lifecycle methods
        """
        self.setup_before_request()
        self.setup_after_request()

    def setup_before_request(self):
        """
        Setup before request function
        Assumes GET request
        """

        def before_request():
            """
            Setup before request function
            """
            url = request.url
            # Get Braid metadata from headers
            version = request.headers.get("version")
            parents = request.headers.get("parents")
            peer = request.headers.get("peer")
            # change to == "keep-alive" once braidify client doesn't auto set header to true
            subscribe = is_true(request.headers.get("subscribe", False))

            # Set variables as Request attributes
            setattr(request, "version", version)
            setattr(request, "parents", parents)
            setattr(request, "peer", peer)
            setattr(request, "subscribe", subscribe)
            setattr(request, "subscriptions", self.subscriptions)
            setattr(request, "resource", self.current_version)

            # TODO: add REST method handler functions
            if request.method == "GET":
                if request.subscribe:
                    # Store new subscription
                    s_id = subscriber_id(request)
                    if s_id in self.subscriptions:
                        # Kill existing subscription and replace with new one
                        # TODO: figure out if the protocol allows for a user
                        # to subscribe to the same resource multiple times concurrently
                        self.subscriptions[s_id].close()
                    subscription = Subscription(
                        request, s_id, lambda: self.subscriptions.pop(s_id)
                    )
                    self.subscriptions[s_id] = subscription
                    setattr(request, "subscription", subscription)
            elif request.method == "PUT":
                patches = parse_patches()
                setattr(request, "patches", patches)
                # _patches allows user to control which patches are advertised
                # TODO: Maybe not needed/productive to the protocol being used correctly?
                setattr(
                    request,
                    "advertise_patches",
                    lambda _patches: advertise_patches(
                        self.subscriptions.values(), request.path, _patches
                    ),
                )

        self.app.before_request(before_request)

    def setup_after_request(self):
        """
        Setup after request function
        Assumes GET request
        """

        def after_request(response):
            """
            Setup after request function
            """
            # Setup patching and JSON ranges headers
            response.headers["Range-Request-Allow-Methods"] = "PATCH, PUT"
            response.headers["Range-Request-Allow-Units"] = "json"
            response.headers["Patches"] = "OK"
            # for a new subscription only
            if request.subscribe and request.method == "GET":
                response.status_code = 209
            # TODO: figure out if Braid should automatically overwrite
            # a response when subscribe=True
            # How much abstraction is needed here?
            return response

        self.app.after_request(after_request)

    def current_version(self, data):
        """
        Returns an up to date version of a resource
        Will return either a typical Flask Response or a
        stream Response depending on the request's "subscribe" header
        Accepts:
            data: dict
                Keys:
                    version: str
                    parents: list[Patch]
                    peer: str
                    patches: list[Patch]
                    body: str
        Returns:
            Response: Flask Response
        """
        # Set up both options, depending on if request is a subscription
        stream_data = ""
        response = Response("", status=200)

        def set_header(header, value):
            nonlocal stream_data
            nonlocal response
            if request.subscribe:
                stream_data += "{}: {}\r\n".format(header, value)
            else:
                response.headers[header] = value

        def write_response(data):
            nonlocal stream_data
            nonlocal response
            if request.subscribe:
                stream_data += data
            else:
                response.data += str.encode(data)

        for header, value in data.items():
            if isinstance(value, list):
                value = ",".join(value)
            elif isinstance(value, dict):
                value = json.dumps(value)
            else:
                value = str(value)
            if header not in ["body", "patches"]:
                set_header(header, value)
            # for safety, rewrite in case we change the headers
            data[header] = value

        if data.get("patches", None):
            patches = generate_patch_stream_string(data["patches"])
            write_response(patches)
        elif data.get("body"):
            set_header("Content-Length", len(data["body"]))
            write_response("\r\n{}\r\n".format(data["body"]))
        else:
            raise RuntimeError("No 'body' or 'patches' found in version response")
        if request.subscribe:
            # prepare for next version
            write_response("\r\n")
            request.subscription.append(stream_data)
            return request.subscription.stream()
        else:
            return response
