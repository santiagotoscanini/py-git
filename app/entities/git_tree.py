from __future__ import annotations

import enum
from pathlib import Path
from typing import NamedTuple, Iterable

from app.entities.git_object import GitObject, ObjectType, retrieve_object_by_id


class FileMode(enum.Enum):
    DIRECTORY = "40000"
    REGULAR_FILE = "100644"

    def __str__(self):
        return self.value


class TreeItem(NamedTuple):
    file_mode: FileMode
    file_name: str
    object_id: str


class Tree(NamedTuple):
    items: Iterable[TreeItem]

    @staticmethod
    def from_git_object(git_object: GitObject) -> Tree:
        assert git_object.object_type == ObjectType.TREE

        content = git_object.content
        items = list()

        while content:
            null_char = content.find(b"\0")

            # Hash 40 chars, encoded in hex, is 20 bytes
            object_sha1 = content[null_char + 1:null_char + 21].hex()
            file_mode, file_name = content[:null_char].decode("utf-8").split(" ")
            tree_item = TreeItem(FileMode(file_mode), file_name, object_sha1)

            items.append(tree_item)
            content = content[null_char + 21:]

        return Tree(tuple(items))

    def to_git_object(self) -> GitObject | None:
        if not self.items:
            return None

        content = bytearray()
        for tree_item in self.items:
            content.extend(f"{tree_item.file_mode} {tree_item.file_name}".encode("utf-8"))
            content.extend(b"\0")
            content.extend(bytes.fromhex(tree_item.object_id))

        return GitObject(ObjectType.TREE, content)

    def restore(self, dot_git: Path, work_dir: Path) -> None:
        for tree_item in self.items:
            file_path = work_dir / tree_item.file_name
            match tree_item.file_mode:
                case FileMode.DIRECTORY:
                    file_path.mkdir()

                    tree_git_obj = retrieve_object_by_id(dot_git, tree_item.object_id)
                    assert tree_git_obj.object_type == ObjectType.TREE

                    subtree = Tree.from_git_object(tree_git_obj)
                    subtree.restore(dot_git, file_path)
                case FileMode.REGULAR_FILE:
                    blob_object = retrieve_object_by_id(dot_git, tree_item.object_id)
                    assert blob_object.object_type == ObjectType.BLOB
                    file_path.write_bytes(blob_object.content)


def build_tree(dot_git: Path, current_dir: Path) -> str | None:
    tree_items = list()
    for child in sorted(current_dir.iterdir(), key=lambda file: file.name):
        # TODO: parse .gitignore file
        if child == dot_git or child == (dot_git.parent / ".idea"):
            continue

        if child.is_dir():
            object_id = build_tree(dot_git, child)
            mode = FileMode.DIRECTORY

            # Do not write empty directories
            if object_id is None:
                continue
        else:
            with child.open("rb") as f:
                file_content = f.read()
            git_object = GitObject(ObjectType.BLOB, file_content)
            git_object.store(dot_git)

            object_id = git_object.object_id
            mode = FileMode.REGULAR_FILE

        tree_items.append(TreeItem(mode, child.name, object_id))

    if not tree_items:
        return None

    tree = Tree(tree_items)
    git_object = tree.to_git_object()
    git_object.store(dot_git)

    return git_object.object_id
