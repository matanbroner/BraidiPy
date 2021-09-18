"""
Braid Handler
Wraps Python application object to inject lifecyle methods
"""

import sys
import json
from flask import request, Response
from core import (
    Subscription,
    Version,
    is_true,
    subscriber_id,
    generate_patch_stream_string,
    parse_patches,
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
            setattr(request, "create_version", self.create_version)

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
                version = self.version_from_request()
                if version:
                    setattr(request, "version", version)
                # _patches allows user to control which patches are advertised
                # TODO: Maybe not needed/productive to the protocol being used correctly?
                setattr(
                    request, "advertise_version", lambda v: self.advertise_version(v)
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

    def advertise_version(self, version: list):
        """
        Advertise a resource update to all the subscribers of a resource
        """
        for subscription in self.subscriptions.values():
            if subscription.resource == request.path:
                self.create_version(
                    version,
                    subscription,
                )

    def version_from_request(self):
        """
        Extract version metadata and body from request
        """
        version = request.headers.get("Version")
        if version is None:
            return
        parents = request.headers.get("Parents")
        if parents:
            parents = parents.split(",")
        content_type = request.headers.get("Content-Type")
        merge_type = request.headers.get("Merge-Type")
        patches = parse_patches()
        body = request.data if patches is None else None
        new_version = Version(
            version=version,
            parents=parents,
            content_type=content_type,
            merge_type=merge_type,
            body=body,
            patches=patches,
        )
        return new_version

    def create_version(self, data, subscription: Subscription=None):
        """
        Create a new version of a resource and forward it depending on the request type
        returns: Flask.Response or None (write to stream)
        """
        if isinstance(data, Version):
            version = data
        elif isinstance(data, dict):
            if "patches" not in data and "body" not in data:
                raise ValueError("No 'patches' or 'body' provided in new version data")
            version = Version(**data)
        if subscription:
            # prepare for next version
            subscription.append(str(version))
        else:
            return Response(str(version), status=200)