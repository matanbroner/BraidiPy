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

class Version(NamedTuple):
    """
    A Version is a collection of Patch objects in relation to parent Patches
    """
    key: str
    parents: list = []
    body: str = None
    patches: list = []

    def __str__(self):
        data = f"{self.name}/{self.version}\r\n"
        for resource in self.resources:
            data += str(resource) + "\r\n"
        return data

    def __repr__(self):
        return f"<Version {self}>"

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