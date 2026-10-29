VERSION ?= $(shell cat VERSION)
DIST_DIR = dist
RELEASE_DIR = release

.PHONY: help
help:
	@echo "TypoLima Makefile (v$(VERSION))"
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  build-pip        Build Python wheel distribution"
	@echo "  build-bin        Build standalone binary (using PyInstaller)"
	@echo "  prepare-release  Bump VERSION, update CHANGELOG, prepare release notes"
	@echo "  release          Full release using GoReleaser (usage: make release VERSION=X.Y.Z)"
	@echo "  snapshot         Local release test using GoReleaser"
	@echo "  test             Run all tests"
	@echo "  clean            Remove build artifacts"
	@echo "  help             Show this help message"

VENV = venv
PYTHON = $(VENV)/bin/python3

.PHONY: test
test:
	@$(PYTHON) tests/test_typolima.py

.PHONY: build-pip
build-pip: clean
	@echo "Building pip package..."
	@mkdir -p $(DIST_DIR)
	@$(PYTHON) -m build --outdir $(DIST_DIR)

.PHONY: build-bin
build-bin:
	@echo "Building standalone binary (v$(VERSION))..."
	@mkdir -p $(RELEASE_DIR)
	@$(PYTHON) -m pip install pyinstaller
	@$(PYTHON) -m PyInstaller --onefile --name typolima \
		--add-data "typolima/rules/*.yaml:typolima/rules" \
		--add-data "VERSION:." \
		--runtime-hook pyinstaller_hooks/pyi_rth_disable_mp.py \
		--hidden-import array \
		--hidden-import multiprocessing \
		--hidden-import _multiprocessing \
		--hidden-import threading \
		--hidden-import _hashlib \
		--hidden-import hashlib \
		--hidden-import _sha256 \
		--hidden-import _sha512 \
		--hidden-import _sha1 \
		--hidden-import _md5 \
		--collect-submodules hashlib \
		typolima/__main__.py
	@mv dist/typolima $(RELEASE_DIR)/typolima-$(VERSION)-macos
	@echo "Binary created in $(RELEASE_DIR)/"

.PHONY: snapshot
snapshot: clean
	@echo "Creating snapshot release with GoReleaser..."
	@goreleaser release --snapshot --clean

.PHONY: prepare-release
prepare-release:
	@echo "Preparing release v$(VERSION)..."
	@if git rev-parse -q --verify "refs/tags/v$(VERSION)" >/dev/null; then \
		echo "Error: tag v$(VERSION) already exists, so this version was already released. Pick a new VERSION."; \
		exit 1; \
	fi
	@if [ -n "$$(git status --porcelain)" ]; then \
		echo "Error: working tree is not clean - commit or stash your changes before releasing:"; \
		git status --short; \
		exit 1; \
	fi
	@BRANCH=$$(git rev-parse --abbrev-ref HEAD); \
	if git rev-parse -q --verify "$$BRANCH@{u}" >/dev/null; then \
		if [ "$$(git rev-parse HEAD)" != "$$(git rev-parse "$$BRANCH@{u}")" ]; then \
			echo "Error: $$BRANCH is not in sync with its upstream - push or pull first."; \
			exit 1; \
		fi; \
	fi
	@if grep -q "^## \[$(VERSION)\]" CHANGELOG.md; then \
		if [ "$$(cat VERSION)" != "$(VERSION)" ]; then \
			echo "Error: CHANGELOG.md already has a [$(VERSION)] entry but VERSION contains $$(cat VERSION)."; \
			exit 1; \
		fi; \
		echo "VERSION and CHANGELOG.md are already bumped to $(VERSION) - skipping the bump commit."; \
	elif [ "$$(cat VERSION)" = "$(VERSION)" ]; then \
		echo "Error: VERSION is already $(VERSION) but CHANGELOG.md has no [$(VERSION)] entry. Add entries under [Unreleased] first."; \
		exit 1; \
	else \
		if ! awk '/^## \[Unreleased\]/{f=1; next} /^## \[/{if(f) exit} f{if ($$0 !~ /^[[:space:]]*$$/) found=1} END{exit !found}' CHANGELOG.md; then \
			echo "Error: CHANGELOG.md's [Unreleased] section is empty (or missing). Nothing to release - add changelog entries first."; \
			exit 1; \
		fi; \
		echo "$(VERSION)" > VERSION; \
		DATE=$$(date +%Y-%m-%d); \
		awk -v ver="$(VERSION)" -v date="$$DATE" '{ \
			if ($$0 ~ /^## \[Unreleased\]/) { \
				print "## [Unreleased]"; \
				print ""; \
				print "## [" ver "] - " date; \
			} else { \
				print; \
			} \
		}' CHANGELOG.md > CHANGELOG.md.tmp && mv CHANGELOG.md.tmp CHANGELOG.md; \
		git add VERSION CHANGELOG.md; \
		git commit -m "Release v$(VERSION)"; \
		git push origin HEAD; \
	fi
	@awk '/^## \[$(VERSION)\]/{found=1; next} /^## \[/{if(found) exit} found{print}' CHANGELOG.md > release-notes.md
	@echo "Release notes written to release-notes.md"

.PHONY: release
release: clean prepare-release
	@echo "Syncing with version $(VERSION)..."
	@if [ -z "$$(git tag -l v$(VERSION))" ]; then \
		echo "Creating new tag v$(VERSION)..."; \
		git tag -a v$(VERSION) -m "Release v$(VERSION)"; \
		git push origin v$(VERSION); \
	else \
		echo "Tag v$(VERSION) already exists."; \
	fi
	@echo "Starting full release with GoReleaser..."
	@goreleaser release --clean --release-notes=release-notes.md

.PHONY: clean
clean:
	rm -rf $(DIST_DIR) $(RELEASE_DIR) build/ typolima.spec
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
