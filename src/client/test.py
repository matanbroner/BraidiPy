from main import BraidClient

braid = BraidClient()

# Test subscription stream
def test_get():
    global braid
    path = "/post/1"
    braid.get(path=path, headers={"Subscribe": "keep-alive"})


test_get()