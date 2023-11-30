import logging
from datetime import datetime
from pathlib import Path

from app.argument_parsing import argument_parser
from app.entities.git_commit import Commit
from app.entities.git_object import retrieve_object_by_id, GitObject, ObjectType
from app.entities.git_pack_file import unpack_objects
from app.entities.git_ref import Ref
from app.entities.git_tree import Tree, build_tree
from app.git_smart_protocol import download_pack_file, get_main_ref


def is_debug():
    codecrafters_yml = (Path(__file__).parent.parent / "codecrafters.yml").read_text()
    return "debug: true" in codecrafters_yml


def create_git_dirs(target_dir: Path) -> None:
    # Check that the target directory exists
    assert target_dir.is_dir()
    assert target_dir.exists()

    # Check that the target directory does not have a .git folder
    dot_git = target_dir / ".git"
    assert not dot_git.exists()
    dot_git.mkdir()

    # Create the required folders
    (dot_git / "objects").mkdir()
    (dot_git / "refs").mkdir()
    (dot_git / "refs" / "heads").mkdir()

    # Create the HEAD file
    Ref("HEAD", "ref: refs/heads/master").store(dot_git)


def main():
    args = argument_parser().parse_args()
    logging.basicConfig(level=logging.DEBUG if is_debug() else logging.INFO)

    if args.command == "init":
        create_git_dirs(Path())
        print("Initialized git directory")
    elif args.command == "cat-file":
        if args.p:
            dot_git = Path() / ".git"
            git_object = retrieve_object_by_id(dot_git, args.sha1)
            print(git_object.content.decode("utf-8"), end='')
    elif args.command == "hash-object":
        if args.w:
            dot_git = Path() / ".git"
            with open(args.file, 'rb') as f:
                content = f.read()
            git_object = GitObject(ObjectType.BLOB, content)
            git_object.store(dot_git)
            print(git_object.object_id)
    elif args.command == "ls-tree":
        if args.name_only:
            dot_git = Path() / ".git"
            git_object = retrieve_object_by_id(dot_git, args.sha1)
            tree = Tree.from_git_object(git_object)
            file_names = [entry.file_name for entry in tree.items]
            print(*file_names, sep='\n')
    elif args.command == "write-tree":
        dot_git = Path() / ".git"
        object_id = build_tree(dot_git, Path())
        print(object_id)
    elif args.command == "commit-tree":
        dot_git = Path() / ".git"
        author_name = "Santiago Toscanini"
        author_email = "pulp@fiction.com"
        date = datetime.now().astimezone()

        commit = Commit(args.tree_sha, args.p, date, author_name, author_email, args.m)
        commit_object = commit.to_git_object()
        commit_object.store(dot_git)
        print(commit_object.object_id)
    elif args.command == "clone":
        # Create the directory for the clone
        clone_path = Path() / args.path
        clone_path.mkdir()
        create_git_dirs(clone_path)

        # Fetch pack-file
        master_sha1 = get_main_ref(args.url).decode('utf-8')
        pack_file, n_items = download_pack_file(args.url, master_sha1)

        # Unpack objects
        git_objects = list(unpack_objects(pack_file))

        # Create objects inside .git folder
        dot_git = clone_path / ".git"
        for git_object in git_objects:
            git_object.store(dot_git)

        # Build the tree
        master_commit = Commit.from_git_object(retrieve_object_by_id(dot_git, master_sha1))
        root_tree = Tree.from_git_object(retrieve_object_by_id(dot_git, master_commit.tree_id))
        root_tree.restore(dot_git, clone_path)
    else:
        raise RuntimeError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
