install:
	pip install -r requirements.txt

tests:
	pytest

coverage:
	coverage html
	coverage report

pretty:
	black .
