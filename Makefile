.PHONY: all test lint format release

all:

test:
	pytest -v

lint:
	flake8 servicorn tests

format:
	black servicorn tests
	isort servicorn tests

release:
ifndef version
	$(error Please supply a version)
endif
	@echo Releasing version $(version)
ifeq (,$(findstring $(version),$(shell git log --oneline -1)))
	$(error Last commit does not match version)
endif
	git tag $(version)
	git push
	git push --tags
