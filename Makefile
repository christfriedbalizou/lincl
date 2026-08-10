.PHONY: build check-dist clean lint sync test upgrade-reqs

sync:
	pip-sync requirements.txt requirements-dev.txt
	python -m pip install -e .

lint:
	pre-commit run --all-files

test:
	python -m pytest

build: clean
	python -m build

check-dist: build
	python -m twine check --strict dist/*
	python -m pip install --force-reinstall --no-deps dist/*.whl
	cd /tmp && python "$(CURDIR)/scripts/verify_installation.py"
	python -m pip install --force-reinstall --no-deps dist/*.tar.gz
	cd /tmp && python "$(CURDIR)/scripts/verify_installation.py"

upgrade-reqs:
	pip-compile --allow-unsafe --generate-hashes --no-emit-index-url requirements.in
	pip-compile --allow-unsafe --generate-hashes --no-emit-index-url requirements-dev.in

clean:
	rm -rf build dist
