import logging

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    level=logging.INFO,
)


class _MetadataAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        prefix = " ".join(f"[{k}={v}]" for k, v in (self.extra or {}).items())
        return f"{prefix} {msg}" if prefix else msg, kwargs


def get_logger(name: str):
    return logging.getLogger(name)


def with_metadata(logger, **metadata):
    return _MetadataAdapter(logger, metadata)
