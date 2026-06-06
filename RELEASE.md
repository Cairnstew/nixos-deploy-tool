# Release Process

## Versioning

This project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Version is read from `src/uv2nix_template/__init__.py` by hatchling.

## Release steps

1. Update `CHANGELOG.md` with the new version
2. Update version in `src/uv2nix_template/__init__.py`
3. Commit with message `release: v<version>`
4. Tag with `v<version>`
5. Push the tag

```bash
git tag -a v0.1.0 -m "v0.1.0"
git push origin v0.1.0
```

## Automation

Pushing a `v*` tag triggers `.github/workflows/release.yml`:

1. **Build** — `nix build .#default`
2. **PyPI publish** — OIDC trusted publishing (no token needed). Requires
   PyPI trusted publisher configured for the `uv2nix-template` project.
3. **GitHub release** — auto-generated release notes from commits.
