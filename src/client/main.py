"""
BraidiPy Client Library
"""

import requests
import json
import threading


class BraidClient:
    def __init__(self, host: str = "localhost", port: int = 8080, config: dict = None):
        self.active_subscriptions = {}
        self.host = host
        self.port = port
        self.config = config or {}
        self._init_rest_methods()

    def __str__(self):
        return f"<BraidClient({self.host}, {self.port}, {self.config})>"

    def __repr__(self):
        return self.__str__()

    def _init_rest_methods(self):
        # TODO: is this the best way to do this?
        self.get = lambda **kwargs: self._rest_request("GET", **kwargs)
        self.post = lambda **kwargs: self._rest_request("POST", **kwargs)
        self.put = lambda **kwargs: self._rest_request("PUT", **kwargs)
        self.delete = lambda **kwargs: self._rest_request("DELETE", **kwargs)
        self.options = lambda **kwargs: self._rest_request("OPTIONS", **kwargs)

    def _rest_request(
        self,
        method: str,
        path: str,
        headers: dict = None,
        data: dict = None,
        config: dict = None,
    ):
        if headers is None:
            headers = {}
        if config is None:
            config = {}
        url = f"http://{self.host}:{self.port}{path}"
        print(f"{method} {url}")
        if headers.get("subscribe") or headers.get("Subscribe"):
            if method != "GET":
                raise ValueError("Subscription only supported for GET requests")
            if path in self.active_subscriptions:
                raise ValueError(f"Subscription for resource {path} already exists")
            # Can use this dict for configuring the subscription
            self.active_subscriptions[path] = {}
            # start either in blocking or non-blocking mode
            if config.get("async", False):
                t = threading.Thread(
                    target=self._subscription_stream, args=(path, headers, config)
                ).start()
            else:
                self._subscription_stream(path, headers, config)

    def _subscription_stream(self, path: str, headers: dict, config: dict):
        print(f"Subscribing to {path}")
        buffer = ""
        path = path if path[0] == "/" else f"/{path}"
        url = f"http://{self.host}:{self.port}{path}"
        try:
            with requests.get(url, headers=headers, stream=True) as r:
                print(f"Subscription stream started for {path}")
                if r.status_code < 200 or r.status_code >= 300:
                    raise ValueError(f"Subscription request for resource {path} failed with status code {r.status_code}")
                while self.active_subscriptions.get(path):
                    for line in r.iter_lines():
                        if line:
                            print(line)
                        else:
                            print("No data")
        except Exception as e:
            print(e)
        finally:
            self.active_subscriptions.pop(path)
                
    def cancel_subscription(self, path: str):
        if path in self.active_subscriptions:
            del self.active_subscriptions[path]
        else:
            raise ValueError(f"No active subscription for resource {path}")
