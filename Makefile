VERSION ?= $(shell cat VERSION)
DIST_DIR = dist
RELEASE_DIR = release

.PHONY: help
help:
	@echo "TypoLima Makefile (v$(VERSION))"
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  build-pip      Build Python source and wheel distribution"
	@echo "  build-bin      Build standalone binary (using PyInstaller)"
	@echo "  release        Full release using GoReleaser (requires tag)"
	@echo "  snapshot       Local release test using GoReleaser"
	@echo "  test           Run all tests"
	@echo "  clean          Remove build artifacts"
	@echo "  help           Show this help message"

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
	@$(PYTHON) -m PyInstaller --onefile --name typolima --add-data "typolima/rules/*.yaml:typolima/rules" --add-data "VERSION:." typolima/__main__.py
	@mv dist/typolima $(RELEASE_DIR)/typolima-$(VERSION)-macos
	@echo "Binary created in $(RELEASE_DIR)/"

.PHONY: snapshot
snapshot: clean
	@echo "Creating snapshot release with GoReleaser..."
	@goreleaser release --snapshot --clean

.PHONY: release
release: clean
	@echo "Syncing with version $(VERSION)..."
	@if [ -z "$$(git tag -l v$(VERSION))" ]; then \
		echo "Creating new tag v$(VERSION)..."; \
		git tag -a v$(VERSION) -m "Release v$(VERSION)"; \
		git push origin v$(VERSION); \
	else \
		echo "Tag v$(VERSION) already exists."; \
	fi
	@echo "Starting full release with GoReleaser..."
	@goreleaser release --clean

.PHONY: clean
clean:
	rm -rf $(DIST_DIR) $(RELEASE_DIR) build/ typolima.spec
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
