.PHONY: load ratios test report dashboard api clean

load:
	python src/etl/loader.py

ratios:
	python src/analytics/ratios.py

test:
	pytest tests/

report:
	python src/reports/portfolio_report.py

dashboard:
	streamlit run src/dashboard/app.py

api:
	uvicorn src.api.main:app --port 8000

clean:
	python -c "import pathlib; [p.unlink() for p in pathlib.Path('.').rglob('*.pyc')]; print('Cleanup complete')"