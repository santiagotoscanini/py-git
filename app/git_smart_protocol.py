import struct
from http import HTTPStatus

from app.http_client import GetRequest, make_http_request, PostRequest

CAPABILITIES = [
    "command=fetch",
    "object-format=sha1",
    "no-progress",
    # This not sent, so we don't have to deal with OBJ_OFS_DELTA for now
    # "ofs-delta",
]


def _parse_pkt_line(pkt_line):
    # pkt-line format is "{4 bytes line size}{sha1 of ref} {ref name}"
    space = pkt_line.find(b" ")
    sha1 = pkt_line[4:space]
    ref = pkt_line[space + 1:]

    return sha1, ref


def get_main_ref(repo_url: str):
    """
    Info with
    GIT_TRACE_PACKET=1 git ls-remote https://github.com/rohitpaulk/minimal-git-repo
    """

    info_refs_request = GetRequest(
        base_url=repo_url + "/info/refs",
        url_params={
            "service": "git-upload-pack",
        },
        headers={
            "accept": "application/x-git-upload-pack-advertisement",
        },
    )
    response = make_http_request(info_refs_request)

    assert response.status_code == HTTPStatus.OK
    assert response.content_type() == "application/x-git-upload-pack-advertisement"

    response_body = response.body.split(b"\n")
    # First two lines are version and capabilities, the last one is 0000
    response_body = response_body[2:len(response_body) - 1]

    for pkt_line in response_body:
        sha1, ref = _parse_pkt_line(pkt_line)
        # TODO: currently we're only returning main/master, we should return all the refs in case we're cloning
        if ref.decode('utf-8') in ["refs/heads/main", "refs/heads/master"]:
            return sha1


def _create_want_command(wanted_content_sha1):
    # each line has the format "{4 bytes HEX for content length}want {sha1 of wanted content}\n"
    length = hex(4 + 4 + 1 + len(wanted_content_sha1) + 1)[2:].zfill(4)
    return f"{length}want {wanted_content_sha1}\n"


def download_pack_file(url, sha_1):
    capabilities = ''.join(CAPABILITIES)
    data = ''.join([
        _create_want_command(f'{sha_1} {capabilities}'),
        _create_want_command(sha_1),
        "00000009done\n"
    ]).encode()

    upload_pack_request = PostRequest(
        base_url=url + "/git-upload-pack",
        url_params={},
        headers={
            "accept": "application/x-git-upload-pack-result",
            "content-type": "application/x-git-upload-pack-request",
        },
        body=data,
    )

    response = make_http_request(upload_pack_request)
    assert response.status_code == HTTPStatus.OK
    assert response.content_type() == "application/x-git-upload-pack-result"

    # remove "0008NAK\n"
    response = response.body[8:]

    magic = response[:4]
    assert magic == b"PACK"
    version = struct.unpack('>I', response[4:8])[0]
    assert version == 2
    n_items = struct.unpack('>I', response[8:12])[0]
    assert n_items > 0

    # TODO: check checksum
    # Skip magic + version + n_items and last 20 bytes for checksum
    return response[12:-20], n_items
