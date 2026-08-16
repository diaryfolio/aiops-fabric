.PHONY: bootstrap lint unit catalog-check profile-check compose-up compose-test k8s-deploy k8s-test

bootstrap:
	./scripts/bootstrap-dev-pki.sh

lint:
	docker build --target test -t viewsense-test:dev .
	docker run --rm viewsense-test:dev ruff check --no-cache src tests

unit:
	docker build --target test -t viewsense-test:dev .
	docker run --rm viewsense-test:dev pytest -q -p no:cacheprovider

catalog-check:
	docker build --target test -t viewsense-test:dev .
	docker run --rm viewsense-test:dev pytest -q -p no:cacheprovider tests/unit/test_module_catalog.py

profile-check:
	helm lint fabric/charts/viewsense
	helm template viewsense fabric/charts/viewsense >/dev/null
	@for profile in fabric/charts/viewsense/profiles/*.yaml; do \
		echo "Validating $$profile"; \
		helm lint fabric/charts/viewsense -f "$$profile"; \
		helm template viewsense fabric/charts/viewsense -f "$$profile" >/dev/null; \
	done

compose-up: bootstrap
	docker compose --env-file .env.viewsense up --build -d

compose-test: bootstrap
	docker compose --env-file .env.viewsense --profile test run --rm smoke

k8s-deploy:
	./scripts/k8s-deploy-dev.sh

k8s-test:
	./scripts/k8s-test.sh
