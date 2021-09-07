from typing import NamedTuple
from textwrap import dedent

def random_patch_string():
    patch = Patch("json", ".latest_change", "{\"body\": \"data here\"}")
    patches = [patch, patch]
    return generate_patch_stream_string(patches)

def generate_patch_stream_string(patches: list) -> str:
    """
    Generate a string of the patches in the order they were applied.

    Args:
        patches: List of Patch instances

    Returns: str
    """
    data = "Patches: {}\r\n".format(len(patches))
    for patch in patches:
        data += str(patch)
    return data


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