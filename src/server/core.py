"""
Core data structures
"""

import sys
import json
import re
from flask import request, Response, stream_with_context
from typing import NamedTuple
from textwrap import dedent


class Patch(NamedTuple):
    """
    A Patch is an update to an HTTP resource
    """

    content: str
    content_type: str = None
    content_range: tuple = None

    @classmethod
    def list_from_buffer(cls, buffer: str) -> "Patch":
        """
        Creates a list of Patches from a request buffer
        """
        patches = []
        while len(buffer) > 0:
            # find end of first patch's headers
            dbl_newlines = list(re.finditer(r"(\r?\n)(\r?\n)", buffer))
            if not len(dbl_newlines):
                raise ValueError(
                    "Could not parse patches with no end of headers marker"
                )
            std_newline = "\r\n"
            headers_length = dbl_newlines[0].end()
            # now we can get the headers based on headers_length
            # remove all whitespaces (ie. not headers)
            headers = buffer[:headers_length].strip()
            # parse the headers
            headers = headers.split("\r\n")
            headers = [header.split(": ") for header in headers]
            headers = {header[0]: header[1] for header in headers}
            if "Content-Length" not in headers:
                raise ValueError("No 'Content-Length' header found in patch")
            content_length = int(headers.get("Content-Length"))
            if "Content-Range" in headers:
                content_range = tuple(headers["Content-Range"].split(" "))
            content_type = headers.get("Content-Type", None)
            if not content_type and not content_range:
                raise ValueError(
                    "No 'Content-Type' or 'Content-Range' header found in patch"
                )
            content = buffer[
                headers_length : headers_length + content_length + len(std_newline)
            ].strip()
            patches.append(cls(content, content_type, content_range))
            # cut off the parsed patch from the buffer
            buffer = buffer[headers_length + content_length + len(std_newline) :]

        return patches

    def __str__(self):
        p_str = "Content-Length: {}".format(len(self.content))
        if self.content_type:
            p_str += "\r\nContent-Type: {}".format(self.content_type)
        if self.content_range:
            p_str += "\r\nContent-Range: {} {}".format(
                self.content_range[0], self.content_range[1]
            )
        p_str += "\r\n\r\n{}".format(self.content)
        return p_str

    def __repr__(self):
        return "<Patch content_type={} content_range={}>".format(
            self.content_type, self.content_range
        )


class Version(NamedTuple):
    """
    A Version is a series of patches or a string body
    describing the state of an HTTP resource
    """

    version: str
    parents: list = None
    merge_type: str = None
    content_type: str = "application/json"
    patches: list = None
    body: str = ""

    def __str__(self):
        v_str = f"Version: {self.version}"
        if self.parents:
            v_str += "\r\nParents: {}".format(",".join(self.parents))
        if self.merge_type:
            v_str += "\r\nMerge-Type: {}".format(self.merge_type)
        if self.content_type:
            v_str += "\r\nContent-Type: {}".format(self.content_type)
        if self.patches:
            v_str += "\r\nPatches: {}".format(len(self.patches))
        content = "".join(str(patch) for patch in self.patches) if self.patches else self.body
        v_str += "\r\nContent-Length: {}".format(len(content))
        v_str += f"\r\n\r\n{content}"
        return v_str

    def __repr__(self):
        return f"<Version id={self.version}>"

    def is_valid_json(self):
        """
        Checks if the body or stringified patches is valid JSON
        Returns:
            bool
        """
        content = (
            self.body
            if self.patches is None
            else "".join(str(patch) for patch in self.patches)
        )
        try:
            json.loads(content)
            return True
        except ValueError:
            return False


class Subscription:
    """
    A subscription is a stream of data that is sent to a subscribed client
    When another client advertises a new version, the subscription is appended with
    the new version and all subscribers are notified.

    NOTE: currently a single subscription is allowed per request.path + request.remote_addr
    """

    def __init__(self, request, s_id, closed_cb):
        self.s_id = s_id
        # can change later, resource ID can be decided by the user
        self.resource = request.path
        self.send_queue = []
        self.active = True
        self.closed_cb = closed_cb

    def stream(self):
        """
        Generator method to send patches
        Stays alive as long as the stream can yield successfully
        """

        def _stream():
            try:
                # While client connected
                # TODO: is this the best way to keep a conn. alive? Two while loops?
                while self.active:
                    while len(self.send_queue) > 0:
                        data = self.send_queue.pop(0)
                        yield data
                # Exception thrown when client disconnects
                # NOTE: the generator will never terminate until
                # the client disconnects and a yield is invoked
                # TODO: is a heartbeat necessary to avoid zombie streams?
                # TODO: implement a way for subscriptions to have n minute lifetimes for renewals
            except GeneratorExit:
                self.close()

        return Response(stream_with_context(_stream()))

    def append(self, data: str):
        """
        Queue string data to be streamed to the client
        """
        self.send_queue.append(data)

    def close(self):
        """
        Close the stream
        """
        self.active = False
        self.closed_cb()


# Util functions
def generate_patch_stream_string(patches: list) -> str:
    """
    Generate a string of the patches in the order they were applied.

    Args:
        patches: List of Patch instances

    Returns: str
    """
    if not isinstance(patches, list):
        patches = [patches]
    data = "Patches: {}\r\n".format(len(patches))
    for patch in patches:
        data += str(patch)
    return data


def is_true(value: str) -> bool:
    """
    Returns True if the value is a string representation of a boolean True
    """
    if value == True or value == False:
        return value
    return value.lower() in ("true", "True", "t", "T" "1")


def subscriber_id(request) -> str:
    """
    Hashes Flask request object remote_address as a subscriber ID
    TODO: make this more robust to avoid collisions
    """
    return hash((request.remote_addr, request.path))


def parse_patches():
    """
    Parse patches from request
    Flask will read the patches as an incoming stream
    """
    num_patches = int(request.headers.get("patches", -1))
    if num_patches < 0:
        # if no patches are specified, ignore
        return
    buffer = ""
    patches = []
    if num_patches == 0:
        return patches
    while True:
        # Read a line from the stream
        chunk = request.stream.read()
        if not chunk:
            # end of stream
            break
        buffer += chunk.decode("utf-8")
        # buffer is sliced after each patch is parsed
        # read while buffer is not empty (ie. patches still exist)
    patches = Patch.list_from_buffer(buffer)
    if len(patches) != num_patches:
        raise RuntimeError(
            "Number of patches does not match number given in 'Patches' header"
        )
    return patches


"""
Temporary functions for testing
Should not be included in production code
"""
import threading, time


def generate_articial_subscription_data(subscription):
    """
    Generate artificial data to be streamed to the client
    """
    patch = Patch(json.dumps({"data": 100}), "json", ".latest_change")
    patches = [patch for _ in range(5)]
    version = Version(
        version="1",
        parents=[],
        merge_type="auto",
        content_type="application/json",
        patches=patches,
    )

    def gen_data():
        while subscription.active:
            time.sleep(1)
            subscription.append(str(version))

    thread = threading.Thread(target=gen_data)
    thread.start()