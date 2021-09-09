from flask import Response
from typing import NamedTuple
from textwrap import dedent

# Core data structures
class Patch(NamedTuple):
    """
    A Patch is a change to an HTTP resource
    """
    unit: str
    range: str
    content: str

    def __str__(self):
        # TODO: make this more readable and efficient
        data = "\r\nContent-Length: {}".format(len(self.content))
        data += f"\r\nContent-Range: {self.unit} {self.range}\r\n"
        data += f"\r\n{self.content}\r\n"
        return data

    def __repr__(self):
        return f"<Patch {self}>"

class Subscription:
    def __init__(self, request):
        self.path = request.path
        self.send_queue = []
        self.active = True
    
    def patch_stream(self):
        """
        Generator method to send patches
        """
        # Artificially add data to queue
        patch = Patch("json", ".latest_change", "{\"data\": 100}")
        patches = [patch for _ in range(10)]
        sample_data = generate_patch_stream_string(patches)
        self.push_to_stream(sample_data)
        def stream():
            try:
                # While client connected
                while self.active:
                    while len(self.send_queue) > 0:
                        data = self.send_queue.pop(0)
                        yield data
                # Exception thrown when client disconnects
            except GeneratorExit:
                print('stream_closed', file=sys.stdout)

        return Response(stream_with_context(gen()))
    
    def push_to_stream(self, data: str):
        """
        Queue string data to be streamed to the client
        """
        self.send_queue.append(queue_stream_data)
    
    def close(self):
        """
        Close the stream
        """
        self.active = False

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
    return hash(request.remote_addr)