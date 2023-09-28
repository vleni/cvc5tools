
test:
	pipenv run python -m cvc5tools.tabulate
	pipenv run python -m cvc5tools.trace

.PHONY: test
