# Releasing

- There is no changelog file. GitHub generates the release notes from the titles of the merged pull requests. Never create or edit a `CHANGELOG.md`
- Pull request titles are Conventional Commits (`type(scope): description`), written as a line of the release notes
- Only `make prepare-release` changes the version in `pyproject.toml`. Feature pull requests never do
- Never create tags or GitHub releases by hand. Merging the pull request labelled `release` creates them
- The full process is under Releasing in `README.md`
