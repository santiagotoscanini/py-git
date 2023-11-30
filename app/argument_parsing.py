from argparse import ArgumentParser


def argument_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Git commands")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("init", help="Initialize a git repository")

    subparsers.add_parser("write-tree", help="Write a tree object")

    cat_file = subparsers.add_parser("cat-file", help="Provide info for repository objects")
    cat_file.add_argument("-p", help="Preview", action="store_true")
    cat_file.add_argument("sha1", help="SHA1 of a git object")

    hash_object = subparsers.add_parser("hash-object", help="Create a git object from a file")
    hash_object.add_argument("-w", help="write the object into the object database", action="store_true")
    hash_object.add_argument("file", help="File to hash")

    ls_tree = subparsers.add_parser("ls-tree", help="List the contents of a tree")
    ls_tree.add_argument("--name-only", help="Only print names", action="store_true")
    ls_tree.add_argument("sha1", help="sha1 of the tree for which to list the contents", type=str)

    commit_tree = subparsers.add_parser("commit-tree", help="Commit a tree object")
    commit_tree.add_argument("tree_sha", help="sha1 of the tree to commit", type=str)
    commit_tree.add_argument("-p", help="parent sha1 of the commit", type=str, required=True)
    commit_tree.add_argument("-m", help="commit message", type=str, required=True)

    clone = subparsers.add_parser("clone", help="Clone a repository")
    clone.add_argument("url", help="URL of the repository to clone")
    clone.add_argument("path", help="Relative path to clone the repository to")

    return parser
