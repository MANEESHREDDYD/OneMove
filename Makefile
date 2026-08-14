.PHONY: public-export publish-check schema-drift

schema-drift:
	@echo "Checking for schema drift between local filesystem migrations and Supabase remote..."
	npx supabase db diff

public-export:
	@echo "Running public export sequence (stripping PII/HMAC)..."
	python services/etl/public_export.py

publish-check:
	@echo "Validating public export for release..."
	python services/etl/publish_check.py
