# CC Git

This repository contains a small git implementation in Python. It's used as a way to learn about git internals.

### Supported operations

- [x] `git init`
- [x] `git cat-file -p {git_sha_1}`
- [x] `git hash-object -w {file}`
- [x] `git ls-tree --name-only {git_sha_1}`
- [x] `git write-tree`
- [x] `commit-tree {tree_sha_1} -p {parent_commit_sha_1} -m {message}`
- [x] `clone {git_repo_url} {directory}`