from __future__ import annotations

from datetime import datetime
from typing import NamedTuple

from app.entities.git_object import GitObject, ObjectType


class Commit(NamedTuple):
    tree_id: str
    # First commit has no parent commit
    parent_commit_id: str | None
    date: datetime
    author_name: str
    author_email: str
    message: str

    def to_git_object(self) -> GitObject:
        timestamp = int(self.date.timestamp())
        utc_offset = self.date.strftime("%z")

        content = bytearray()
        content.extend(f"tree {self.tree_id}\n".encode("utf-8"))
        if self.parent_commit_id:
            content.extend(f"parent {self.parent_commit_id}\n".encode("utf-8"))
        commit_info = f"{self.author_name} <{self.author_email}> {timestamp} {utc_offset}"
        content.extend(f"author {commit_info}\n".encode("utf-8"))
        content.extend(f"committer {commit_info}\n".encode("utf-8"))
        content.extend(b"\n")
        content.extend(f"{self.message}\n".encode("utf-8"))

        return GitObject(ObjectType.COMMIT, content)

    @staticmethod
    def from_git_object(git_object: GitObject) -> Commit:
        assert git_object.object_type == ObjectType.COMMIT

        content = git_object.content.decode()
        tree_line, parent_line, author_line, committer_line, _, message = content.split("\n", maxsplit=5)

        assert tree_line.startswith("tree ")
        tree_id = tree_line[5:]

        assert parent_line.startswith("parent ")
        parent_commit_id = parent_line[7:]

        # TODO: implement deserialization of the author/committer line
        author_name = ""
        author_email = ""
        date = datetime.now().astimezone()

        return Commit(
            tree_id,
            parent_commit_id,
            date,
            author_name,
            author_email,
            message
        )
