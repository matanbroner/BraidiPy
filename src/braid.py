"""
Braid Handler
Wraps Python application object to inject lifecyle methods
"""

import sys
from flask import request, Response
from core import Subscription, is_true, subscriber_id, generate_patch_stream_string

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
        """
        def before_request():
            """
            Setup before request function
            """
            url = request.url
            # Get Braid metadata from headers
            version = request.headers.get('version')
            parents = request.headers.get('parents')
            peer = request.headers.get('peer')
            subscribe = is_true(request.headers.get('subscribe', False))

            # Set variables as Request attributes
            setattr(request, 'version', version)
            setattr(request, 'parents', parents)
            setattr(request, 'peer', peer)
            setattr(request, 'subscribe', subscribe)
            setattr(request, 'version_response', version_response)
            if request.subscribe:
                # Store new subscription
                subscription = Subscription(request)
                self.subscriptions[subscriber_id(request)] = subscription
        self.app.before_request(before_request)
    
    def setup_after_request(self):
        """
        Setup after request function
        """
        def after_request(response):
            """
            Setup after request function
            """
            # Setup patching and JSON ranges headers
            response.headers['Range-Request-Allow-Methods'] = 'PATCH, PUT'
            response.headers['Range-Request-Allow-Units'] = 'json'
            response.headers['Patches'] = 'OK'
            if(request.subscribe):
                # Store new subscription
                subscription = self.subscriptions[subscriber_id(request)]
                return subscription.patch_stream()
            else:
                # TODO: deal with non-subscribe requests
                # Send only one version
                return response
            
        self.app.after_request(after_request)
    
    def version_response(self, data):
        """
        Sends version
        Depending on if request is a subscription request, either
        static Response is sent or existing subscription will queue initial
        version to yield.
        """
        # Set up both options, depending on if request is a subscription
        stream_data = ""
        response = Response("", status=200)
        def set_header(header, value):
            if request.subscribe:
                stream_data += "{}: {}\r\n".format(header, value)
            else:
                response.headers[header] = value
        def write_response(data):
            if request.subscribe:
                stream_data += data
            else:
                response.data += data

        for header, value in data.items():
            if isinstance(value, list):
                value = ",".join(value)
            else:
                value = str(value)
            set_header(header, value)

        if data["patches"]:
            patches = generate_patch_stream_string(data["patches"])
            write_response(patches)
        elif data["body"]:
            set_header("Content-Length", len(data["body"]))
            write_response("\r\n{}\r\n".format(data["body"]))
        else:
            raise RuntimeError("No 'body' or 'patches' found in version response")
        if request.subscribe:
            subscription = self.subscriptions[subscriber_id(request)]
            subscription.push_to_stream(stream_data)
            # return nothing here due to stream
        else:
            return response
        

