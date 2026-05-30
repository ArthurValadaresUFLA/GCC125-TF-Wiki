from collections.abc import Mapping
from typing import Any

import markdown


class MarkdownService:
    DEFAULT_EXTENSIONS = [
        "extra",
        "codehilite",
        "toc",
        "wikilinks",
    ]

    DEFAULT_EXTENSION_CONFIGS = {
        "wikilinks": {
            "base_url": "/",
            "end_url": "",
        },
        "codehilite": {
            "guess_lang": False,
            "use_pygments": True,
        },
        "toc": {
            "permalink": True,
        },
    }

    def __init__(
        self,
        extensions: list[str] | None = None,
        extension_configs: Mapping[str, Mapping[str, Any]] | None = None,
    ):
        self.extensions = extensions or self.DEFAULT_EXTENSIONS
        self.extension_configs = extension_configs or self.DEFAULT_EXTENSION_CONFIGS

    def render(self, text: str) -> str:
        return markdown.markdown(
            text or "",
            extensions=self.extensions,
            extension_configs=self.extension_configs,
            output_format="html5",
        )
