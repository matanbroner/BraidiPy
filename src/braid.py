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
            subscribe = is_true(request.headers.get("subscribe", False))

            # Set variables as Request attributes
            setattr(request, "version", version)
            setattr(request, "parents", parents)
            setattr(request, "peer", peer)
            setattr(request, "subscribe", subscribe)
            setattr(request, "updated_version_response", self.updated_version_response)
            if request.subscribe:
                # Store new subscription
                s_id = subscriber_id(request)
                subscription = Subscription(
                    request, lambda: self.subscriptions.pop(s_id)
                )
                # TODO: delete this call, only for testing
                # generate_articial_subscription_data(subscription)
                if s_id in self.subscriptions:
                    # Kill existing subscription and replace with new one
                    print(
                        "Warning: Subscription already exists for {}".format(s_id),
                        file=sys.stderr,
                    )
                    self.subscriptions[s_id].close()
                else:
                    # Kill existing subscription and replace with new one
                    print("Subscription created for {}".format(s_id), file=sys.stderr)
                self.subscriptions[s_id] = subscription
                setattr(request, "subscription_stream", subscription.patch_stream)

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
            # TODO: figure out if Braid should automatically overwrite
            # a response when subscribe=True
            # How much abstraction is needed here?
            return response

        self.app.after_request(after_request)

    def updated_version_response(self, data):
        """
        Returns an updated version of resource
        Depending on if request is a subscription request, either
        static Response is returned or existing subscription will queue initial
        version to yield.
        Accepts:
            data: dict
                Keys:
                    version: str
                    parents: list[Patch]
                    peer: str
                    patches: list[Patch]
                    body: str
        Returns:
            Response (or None if subscription)
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
                response.data += data

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
            subscription = self.subscriptions[subscriber_id(request)]
            subscription.push_to_stream(stream_data)
            # return nothing here due to stream
            # TODO: should something relating to the stream be returned?
            return None
        else:
            return response
