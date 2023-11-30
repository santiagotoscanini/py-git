import enum
import hashlib
from pathlib import Path

import zlib


class ObjectType(str, enum.Enum):
    TREE = "tree"
    BLOB = "blob"
    COMMIT = "commit"
    TAG = "tag"

    def __str__(self):
        return self.value


class GitObject:
    def __init__(self, object_type: ObjectType, content: bytes):
        self.object_header = GitObject._object_header(object_type, content)
        self.object_id = hashlib.sha1(self.object_header).hexdigest()
        self.object_type = object_type
        self.content = content

    @staticmethod
    def _object_header(object_type: ObjectType, content: bytes) -> bytes:
        # Git objects are stored in the following format:
        # objectType contentSize\0content
        header = f'{object_type} {len(content)}\x00'.encode() + content

        return header

    def store(self, dot_git: Path):
        path = get_object_path(dot_git, self.object_id)

        # Create the directory with the first 2 characters of the object_id
        path.parent.mkdir(exist_ok=True)

        path.write_bytes(zlib.compress(self.object_header))


def get_object_path(dot_git: Path, object_id: str) -> Path:
    return dot_git / "objects" / object_id[:2] / object_id[2:]


def retrieve_object_by_id(dot_git: Path, object_id: str) -> GitObject:
    obj_path = get_object_path(dot_git, object_id)
    stream = zlib.decompress(obj_path.read_bytes())

    # blob 12\x00* text=auto\n
    # Split the stream into the header and the content, check how we write the header to understand this
    header, content = stream.split(b"\0", maxsplit=1)
    object_type_str, length_str = header.decode().split(" ", maxsplit=1)
    assert len(content) == int(length_str)

    return GitObject(ObjectType(object_type_str), content)
