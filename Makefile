.PHONY: install run test lint docker-build docker-run

install:
	python -m pip install --upgrade pip
	pip install -r requirements.txt

run:
	streamlit run app.py

test:
	pytest -q

lint:
	ruff check agents connectors models simulator orchestration observability --ignore E501

docker-build:
	docker build -t worldcup-intelligence-center:latest .

docker-run:
	docker run --env-file .env -p 8501:8501 worldcup-intelligence-center:latest
