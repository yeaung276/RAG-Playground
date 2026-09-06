from nanoid import generate


def new_id() -> str:
    """Primary-key generator: a 21-char URL-safe nanoid."""
    return generate()
