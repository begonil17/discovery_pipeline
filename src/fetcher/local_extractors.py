from dataclasses import dataclass
import html
from io import BytesIO
import re
from urllib.parse import (
    parse_qsl,
    urldefrag,
    urlencode,
    urljoin,
    urlparse,
    urlunparse,
    unquote,
)

import requests

from src.config.settings import (
    LOCAL_FETCH_MAX_BYTES,
    LOCAL_FETCH_TIMEOUT,
    USER_AGENT,
)


ASSET_EXTENSIONS = {
    ".css",
    ".gif",
    ".ico",
    ".jpeg",
    ".jpg",
    ".js",
    ".png",
    ".svg",
    ".webp",
    ".xml",
    ".zip",
}


@dataclass
class DownloadedContent:

    url: str

    content_type: str

    body: bytes

    encoding: str | None


@dataclass
class ExtractedContent:

    url: str

    title: str

    text: str


@dataclass
class LinkCandidate:

    url: str

    title: str

    score: int


class LocalExtractionError(Exception):

    pass


class LocalExtractor:

    def __init__(self):

        self.session = requests.Session()

        self.headers = {
            "User-Agent": USER_AGENT,
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/pdf;q=0.9,*/*;q=0.8"
            ),
        }

    def is_pdf_url(self, url: str) -> bool:

        parsed = urlparse(url)

        text = f"{parsed.path} {parsed.query}".casefold()

        return ".pdf" in text

    def is_pdf_content(
        self,
        content_type: str,
        body: bytes,
    ) -> bool:

        return (
            "pdf" in content_type.casefold()
            or body.lstrip().startswith(b"%PDF")
        )

    def is_likely_search_page(
        self,
        url: str,
    ) -> bool:

        parsed = urlparse(url)

        path = parsed.path.casefold()
        query = parsed.query.casefold()

        document_path_markers = (
            "detail",
            "details",
            "download",
            "downloadfile",
            "document",
            "viewer",
        )

        if any(
            marker in path
            for marker in document_path_markers
        ):
            return False

        path_markers = (
            "search",
            "arama",
            "catalog",
            "catalogue",
            "katalog",
        )

        query_markers = (
            "query=",
            "q=",
            "keyword=",
            "subject=",
        )

        if any(marker in path for marker in path_markers):
            return True

        return any(marker in query for marker in query_markers)

    def download(
        self,
        url: str,
    ) -> DownloadedContent:

        response = self.session.get(
            url,
            headers=self.headers,
            timeout=LOCAL_FETCH_TIMEOUT,
            allow_redirects=True,
            stream=True,
        )

        response.raise_for_status()

        chunks = []
        total_size = 0

        for chunk in response.iter_content(
            chunk_size=64 * 1024,
        ):

            if not chunk:
                continue

            total_size += len(chunk)

            if total_size > LOCAL_FETCH_MAX_BYTES:
                raise LocalExtractionError(
                    "Local fetch exceeded "
                    f"{LOCAL_FETCH_MAX_BYTES} bytes."
                )

            chunks.append(chunk)

        content_type = response.headers.get(
            "Content-Type",
            "",
        )

        body = b"".join(chunks)
        encoding = response.encoding

        if "charset=" not in content_type.casefold():
            encoding = self.detect_encoding(body) or encoding

        return DownloadedContent(
            url=response.url,
            content_type=content_type,
            body=body,
            encoding=encoding,
        )

    def detect_encoding(
        self,
        body: bytes,
    ) -> str | None:

        if not body:
            return None

        try:
            from charset_normalizer import from_bytes

            best_match = from_bytes(body).best()

            if best_match and best_match.encoding:
                return best_match.encoding

        except Exception:
            pass

        return None

    def extract(
        self,
        url: str,
    ) -> ExtractedContent:

        downloaded = self.download(url)

        if self.is_pdf_content(
            downloaded.content_type,
            downloaded.body,
        ):
            return self.extract_pdf(downloaded)

        return self.extract_html(downloaded)

    def extract_pdf(
        self,
        downloaded: DownloadedContent,
    ) -> ExtractedContent:

        try:
            from pypdf import PdfReader

        except ImportError as exc:
            raise LocalExtractionError(
                "PDF fallback requires pypdf. "
                "Install project requirements first."
            ) from exc

        try:
            reader = PdfReader(
                BytesIO(downloaded.body),
                strict=True,
            )

        except Exception as exc:
            raise LocalExtractionError(
                "Could not parse PDF locally."
            ) from exc

        title = self.title_from_pdf(
            reader,
            downloaded.url,
        )

        pages = []

        for page_number, page in enumerate(
            reader.pages,
            start=1,
        ):

            try:
                text = page.extract_text() or ""

            except Exception:
                continue

            text = text.strip()

            if text:
                pages.append(
                    f"# Page {page_number}\n\n{text}"
                )

        full_text = "\n\n".join(pages).strip()

        if not full_text:
            raise LocalExtractionError(
                "PDF contained no extractable text."
            )

        return ExtractedContent(
            url=downloaded.url,
            title=title,
            text=full_text,
        )

    def extract_html(
        self,
        downloaded: DownloadedContent,
    ) -> ExtractedContent:

        html = downloaded.body.decode(
            downloaded.encoding or "utf-8",
            errors="replace",
        )

        title = self.title_from_html(
            html,
            downloaded.url,
        )

        text = self.extract_html_text(
            html,
            downloaded.url,
        )

        if not text:
            raise LocalExtractionError(
                "HTML page contained no extractable text."
            )

        return ExtractedContent(
            url=downloaded.url,
            title=title,
            text=text,
        )

    def extract_html_text(
        self,
        html: str,
        url: str,
    ) -> str:

        try:
            import trafilatura

            extracted = trafilatura.extract(
                html,
                url=url,
                output_format="markdown",
                include_comments=False,
                include_tables=True,
            )

            if extracted and extracted.strip():
                return extracted.strip()

        except Exception:
            pass

        return self.extract_html_text_with_bs4(html)

    def extract_html_text_with_bs4(
        self,
        html: str,
    ) -> str:

        try:
            from bs4 import BeautifulSoup

        except ImportError:
            return self.strip_html_with_regex(html)

        soup = BeautifulSoup(
            html,
            "html.parser",
        )

        for tag in soup(
            [
                "script",
                "style",
                "noscript",
                "svg",
                "form",
            ]
        ):
            tag.decompose()

        root = (
            soup.find("main")
            or soup.find("article")
            or soup.body
            or soup
        )

        return self.normalize_text(
            root.get_text("\n")
        )

    def strip_html_with_regex(
        self,
        html: str,
    ) -> str:

        text = re.sub(
            r"(?is)<(script|style|noscript).*?</\1>",
            " ",
            html,
        )
        text = re.sub(r"(?s)<[^>]+>", "\n", text)

        return self.normalize_text(text)

    def discover_document_links(
        self,
        url: str,
        limit: int,
    ) -> list[LinkCandidate]:

        downloaded = self.download(url)

        if self.is_pdf_content(
            downloaded.content_type,
            downloaded.body,
        ):
            return []

        html = downloaded.body.decode(
            downloaded.encoding or "utf-8",
            errors="replace",
        )

        candidates = []

        for href, title in self.extract_links(html):

            candidate_url = self.normalize_link(
                downloaded.url,
                href,
            )

            if candidate_url is None:
                continue

            score = self.score_link(
                downloaded.url,
                candidate_url,
                title,
            )

            if score <= 0:
                continue

            candidates.append(
                LinkCandidate(
                    url=candidate_url,
                    title=title.strip() or candidate_url,
                    score=score,
                )
            )

        deduped = {}

        for candidate in candidates:

            current = deduped.get(candidate.url)

            if current is None or candidate.score > current.score:
                deduped[candidate.url] = candidate

        return sorted(
            deduped.values(),
            key=lambda item: item.score,
            reverse=True,
        )[:limit]

    def extract_links(
        self,
        html: str,
    ) -> list[tuple[str, str]]:

        try:
            from bs4 import BeautifulSoup

        except ImportError:
            return [
                (match.group(1), "")
                for match in re.finditer(
                    r"""(?is)<a[^>]+href=["']([^"']+)["']""",
                    html,
                )
            ]

        soup = BeautifulSoup(
            html,
            "html.parser",
        )

        links = []

        for anchor in soup.find_all(
            "a",
            href=True,
        ):
            links.append(
                (
                    anchor["href"],
                    self.normalize_text(
                        anchor.get_text(" ")
                    ),
                )
            )

        return links

    def normalize_link(
        self,
        base_url: str,
        href: str,
    ) -> str | None:

        href = href.strip()

        if not href:
            return None

        lowered = href.casefold()

        if lowered.startswith(
            (
                "javascript:",
                "mailto:",
                "tel:",
            )
        ):
            return None

        href = html.unescape(href)

        joined = urljoin(
            base_url,
            href,
        )
        joined, _fragment = urldefrag(joined)

        parsed = urlparse(joined)

        if parsed.scheme not in {
            "http",
            "https",
        }:
            return None

        if self.has_asset_extension(parsed.path):
            return None

        return self.canonicalize_url(joined)

    def canonicalize_url(
        self,
        url: str,
    ) -> str:

        parsed = urlparse(url)
        query_items = []

        ignored_query_params = {
            "detailtype",
            "modal",
            "utm_campaign",
            "utm_content",
            "utm_medium",
            "utm_source",
            "utm_term",
        }

        for key, value in parse_qsl(
            parsed.query,
            keep_blank_values=True,
        ):

            if key.casefold() in ignored_query_params:
                continue

            query_items.append((key, value))

        return urlunparse(
            parsed._replace(
                query=urlencode(query_items),
            )
        )

    def score_link(
        self,
        base_url: str,
        candidate_url: str,
        title: str,
    ) -> int:

        base = urlparse(base_url)
        candidate = urlparse(candidate_url)

        if candidate_url == base_url:
            return 0

        if not candidate.path.strip("/"):
            return 0

        score = 0

        if candidate.netloc == base.netloc:
            score += 10
        else:
            score += 2

        text = f"{candidate.path} {candidate.query} {title}"
        text = text.casefold()

        strong_markers = (
            ".pdf",
            "download",
            "downloadfile",
            "document",
            "dokuman",
            "dosya",
            "detail",
            "details",
            "detay",
            "record",
            "eser",
            "kitap",
            "yayin",
            "publication",
            "fulltext",
            "viewer",
        )

        for marker in strong_markers:
            if self.has_marker(text, marker):
                score += 5

        weak_markers = (
            "title",
            "author",
            "subject",
            "catalog",
            "catalogue",
            "katalog",
            "library",
            "kutuphane",
            "k%C3%BCt%C3%BCphane".casefold(),
        )

        for marker in weak_markers:
            if self.has_marker(text, marker):
                score += 2

        if self.is_likely_search_page(candidate_url):
            score -= 8

        if self.has_navigation_marker(text):
            return 0

        if len(title.split()) >= 2:
            score += 1

        return score

    def has_marker(
        self,
        text: str,
        marker: str,
    ) -> bool:

        if marker.startswith(".") or "%" in marker:
            return marker in text

        return re.search(
            rf"(?<![a-z0-9]){re.escape(marker)}(?![a-z0-9])",
            text,
        ) is not None

    def has_asset_extension(
        self,
        path: str,
    ) -> bool:

        lowered = path.casefold()

        return any(
            lowered.endswith(extension)
            for extension in ASSET_EXTENSIONS
        )

    def has_navigation_marker(
        self,
        text: str,
    ) -> bool:

        navigation_markers = (
            "login",
            "signin",
            "register",
            "profile",
            "account",
            "member",
            "user",
            "reservation",
            "itemreservation",
            "cart",
            "donators",
            "request",
            "fines",
            "uye",
            "uyelik",
            "üyelik",
            "iletisim",
            "contact",
            "about",
            "hakkimizda",
            "privacy",
            "gizlilik",
            "facebook",
            "twitter",
            "instagram",
            "youtube",
        )

        return any(
            self.has_marker(text, marker)
            for marker in navigation_markers
        )

    def title_from_pdf(
        self,
        reader,
        url: str,
    ) -> str:

        metadata = getattr(
            reader,
            "metadata",
            None,
        )

        title = getattr(
            metadata,
            "title",
            None,
        )

        if title:
            return str(title).strip()

        return self.title_from_url(url)

    def title_from_html(
        self,
        html: str,
        url: str,
    ) -> str:

        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(
                html,
                "html.parser",
            )

            if soup.title and soup.title.string:
                title = soup.title.string.strip()

                if title:
                    return title

            heading = soup.find("h1")

            if heading:
                title = self.normalize_text(
                    heading.get_text(" ")
                )

                if title:
                    return title

        except Exception:
            pass

        match = re.search(
            r"(?is)<title[^>]*>(.*?)</title>",
            html,
        )

        if match:
            title = self.normalize_text(match.group(1))

            if title:
                return title

        return self.title_from_url(url)

    def title_from_url(
        self,
        url: str,
    ) -> str:

        parsed = urlparse(url)
        path = unquote(parsed.path).rstrip("/")
        filename = path.rsplit("/", 1)[-1]
        filename = re.sub(
            r"\.[A-Za-z0-9]{1,8}$",
            "",
            filename,
        )
        title = re.sub(
            r"[_-]+",
            " ",
            filename,
        ).strip()

        return title or parsed.netloc or url

    def normalize_text(
        self,
        text: str,
    ) -> str:

        lines = [
            line.strip()
            for line in text.splitlines()
        ]

        normalized = []
        previous_blank = False

        for line in lines:

            if not line:

                if not previous_blank:
                    normalized.append("")

                previous_blank = True
                continue

            normalized.append(line)
            previous_blank = False

        return "\n".join(normalized).strip()
