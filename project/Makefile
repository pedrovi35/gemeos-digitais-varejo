# Gêmeo Digital de Varejo — developer targets

.PHONY: install run bootstrap bootstrap-full validate test lint clean reset deploy-check

install:
	pip install -r requirements.txt

run:
	streamlit run app.py

bootstrap:
	python scripts/bootstrap.py --force

bootstrap-full:
	python scripts/bootstrap.py --force --full

bootstrap-train:
	python scripts/bootstrap.py --force --full --train

validate:
	python scripts/validate.py

test:
	pytest -q

lint:
	ruff check .

clean:
	rm -rf .pytest_cache .ruff_cache __pycache__ */__pycache__ */*/__pycache__

reset:
	rm -f data/warehouse.duckdb data/warehouse.duckdb.wal
	find data/bronze data/silver data/gold -type f ! -name '.gitkeep' -delete 2>/dev/null || true

deploy-check: validate test
	@echo "Deploy check passed."
