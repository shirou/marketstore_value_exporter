build:
	docker build -t marketstore_value_exporter .

lock:
	venv/bin/pip3 freeze > requirements.lock
