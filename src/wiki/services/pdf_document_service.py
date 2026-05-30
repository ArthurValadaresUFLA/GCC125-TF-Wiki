from html import escape
from pathlib import Path


class PdfDocumentService:
    def __init__(self, static_dir: Path):
        self.static_dir = Path(static_dir)

    def build_html(
        self,
        title: str,
        body: str,
    ) -> str:
        stylesheets = self._stylesheets()

        stylesheet_links = "\n".join(
            f'<link rel="stylesheet" href="file://{stylesheet}">'
            for stylesheet in stylesheets
            if stylesheet.exists()
        )

        return f"""<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="utf-8">
    <title>{escape(title)}</title>
    {stylesheet_links}
</head>
<body>
    <main class="content">
        <article class="markdown-body">
            {body}
        </article>
    </main>
</body>
</html>
"""

    def _stylesheets(self) -> list[Path]:
        return [
            (self.static_dir / "css/app.css").resolve(),
            (self.static_dir / "css/markdown.css").resolve(),
            (self.static_dir / "css/pygments.css").resolve(),
        ]
