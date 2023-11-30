import logging
import tempfile
from functools import wraps
from http import HTTPStatus, HTTPMethod
from typing import NamedTuple, Iterable, Callable
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request as HTTPRequest, urlopen

_logger = logging.getLogger(__name__)


class GetRequest(NamedTuple):
    base_url: str
    url_params: dict | None
    headers: dict | None


class PostRequest(NamedTuple):
    base_url: str
    url_params: dict | None
    headers: dict | None
    body: bytes


class Response:
    def __init__(self, status_code: HTTPStatus, headers: Iterable[tuple[str, str]], body: bytes):
        self.status_code = status_code
        self.headers = {key.lower(): value for key, value in headers}
        self.body = body

    def content_type(self):
        return self.headers["content-type"]


# Custom decorator to log requests and responses
def log_request(http_request: Callable[[GetRequest | PostRequest], Response]):
    @wraps(http_request)
    def decorated(request: GetRequest | PostRequest) -> Response:
        match request:
            case GetRequest():
                method = HTTPMethod.GET
                body = None
            case PostRequest():
                method = HTTPMethod.POST
                body = _body_as_str(request.body)

        # Request
        _logger.debug("Making request:")
        _logger.debug(f" method:  {method}")
        _logger.debug(f" url:     {request.base_url}")
        _logger.debug(f" headers: {request.headers}")
        _logger.debug(f" params:  {request.url_params}")
        if body:
            _logger.debug(f" body:    {body}")

        response = http_request(request)

        # Response
        _logger.debug("Received:")
        _logger.debug(" status_code: %s", response.status_code)
        _logger.debug(" headers:     %s", response.headers)
        _logger.debug(" body_len:    %s", len(response.body))
        _logger.debug(" body:        %s", _body_as_str(response.body))
        return response

    return decorated


def _body_as_str(body: bytes) -> str:
    try:
        body_str = body.decode("utf-8")
        body_str = body_str.replace("\n", "\\n")
        body_str = body_str.replace("\0", "\\0")
        return body_str
    except UnicodeDecodeError:
        if _logger.isEnabledFor(logging.DEBUG):
            filename = tempfile.mktemp()
            with open(filename, "wb") as f:
                f.write(body)
            return f"Warning - problem decoding unicode, see: {filename} >"
        else:
            return "Warning - problem decoding unicode"


@log_request
def make_http_request(request: GetRequest | PostRequest) -> Response:
    params = urlencode(request.url_params)
    req = HTTPRequest(f"{request.base_url}?{params}")
    for key, value in request.headers.items():
        req.add_header(key, value)

    match request:
        case GetRequest():
            req.method = HTTPMethod.GET
        case PostRequest():
            req.method = HTTPMethod.POST
            req.data = request.body

    try:
        with urlopen(req, timeout=5) as res:
            status_code = HTTPStatus(res.status)
            return Response(status_code, res.getheaders(), res.read())
    except HTTPError as e:
        return Response(HTTPStatus(e.code), e.headers.items(), bytes())
