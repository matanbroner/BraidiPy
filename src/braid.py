"""
Braid Handler
Wraps Python application object to inject lifecyle methods
"""

import sys
from flask import request

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
            print("before_request", file=sys.stdout)
            print(request, file=sys.stdout)
        self.app.before_request(before_request)
    
    def setup_after_request(self):
        """
        Setup after request function
        """
        def after_request(response):
            """
            Setup after request function
            """
            print("after_request", file=sys.stdout)
            print(request, file=sys.stdout)
            return response
        self.app.after_request(after_request)
