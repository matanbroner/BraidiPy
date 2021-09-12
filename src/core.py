import sys
import re
from flask import request, Response, stream_with_context
from typing import NamedTuple
from textwrap import dedent

# Core data structures
class Patch(NamedTuple):
    """
    A Patch is a change to an HTTP resource
    """
    version: str
    unit: str
    range: str
    content: str
    parents: list
    merge_type: str = "sync9"
    content_type: str = "application/json"

    def __str__(self):
        # TODO: make this more readable and efficient
        data = "\r\nContent-Length: {}".format(len(self.content))
        data += f"\r\nContent-Range: {self.unit} {self.range}\r\n"
        data += f"\r\n{self.content}\r\n"
        return data

    def __repr__(self):
        return f"<Patch {self}>"

class Subscription:
    def __init__(self, request, closed_cb):
        self.path = request.path
        self.send_queue = []
        self.active = True
        self.closed_cb = closed_cb
    
    def patch_stream(self):
        """
        Generator method to send patches
        Stays alive as long as the stream can yield successfully
        """
        def stream():
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
            except GeneratorExit:
                self.close()
        return Response(stream_with_context(stream()))
    
    def push_to_stream(self, data: str):
        """
        Queue string data to be streamed to the client
        """
        self.send_queue.append(data)
    
    def close(self):
        """
        Close the stream
        """
        print('stream_closed', file=sys.stdout)
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

        TODO: allow patch types other than JSON ranges
        """
        num_patches = int(request.headers.get("patches", None))
        if num_patches is None:
            raise RuntimeError("No 'patches' header found in request")
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
            buffer += chunk.decode('utf-8')
            # buffer is sliced after each patch is parsed
            # read while buffer is not empty (ie. patches still exist)
            while len(buffer) > 0:
                # parse a potentially complete patch
                # first figure out if we have all the patch's headers
                dbl_newlines = list(re.finditer(r"(\r?\n)(\r?\n)", buffer))
                # len(dbl_newlines) should be 1 == end of headers
                if not len(dbl_newlines):
                    # headers not complete
                    continue
                # TODO: figure out if this assumption is valid
                # Braidify JS checks the length of incoming newlines
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
                    raise RuntimeError("No 'Content-Length' header found in patch")
                content_length = int(headers["Content-Length"])
                if len(buffer) < headers_length + content_length + len(std_newline):
                    # patch not complete, get next chunk and retry
                    continue
                unit, range = headers["Content-Range"].split(" ")
                content = buffer[headers_length:headers_length + content_length + len(std_newline)].strip()
                patch = Patch(unit, range, content)
                patches.append(patch)
                # cut off the parsed patch from the buffer
                buffer = buffer[headers_length + content_length + len(std_newline):]
        if len(patches) != num_patches:
            raise RuntimeError("Number of patches does not match number given in 'Patches' header")
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
    patch = Patch("json", ".latest_change", "{\"data\": 100}")
    patches = [patch for _ in range(1)]
    sample_data = generate_patch_stream_string(patches)
    def gen_data():
        while subscription.active:
            time.sleep(1)
            subscription.push_to_stream(sample_data)
    thread = threading.Thread(target=gen_data)
    thread.start()