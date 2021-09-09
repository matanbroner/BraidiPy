"""
Braid Handler
Wraps Python application object to inject lifecyle methods
"""

import sys
from flask import request
from core import is_true

class Braid(object):
    
    def __init__(self, app):
        self.app = app
        self.setup_lifecycle_methods()

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
            return response
        self.app.after_request(after_request)
    
    def send_version(self, data):
        """
        Send version
        """
        url = request.url
        peer = request.peer
