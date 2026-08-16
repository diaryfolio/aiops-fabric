.PHONY: bootstrap lint unit catalog-check profile-check docs-build compose-up compose-test k8s-deploy k8s-test openai-enable openai-enable-fresh openai-model-update openai-disable ports ports-start ports-stop ports-status

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

docs-build:
	bash scripts/build-docs.sh

compose-up: bootstrap
	docker compose --env-file .env.viewsense up --build -d

compose-test: bootstrap
	docker compose --env-file .env.viewsense --profile test run --rm smoke

k8s-deploy:
	./scripts/k8s-deploy-dev.sh

k8s-test:
	./scripts/k8s-test.sh

openai-enable:
	./scripts/configure-openai-dev.sh

openai-enable-fresh: k8s-deploy
	./scripts/configure-openai-dev.sh

openai-model-update:
	./scripts/update-openai-model-dev.sh

openai-disable:
	./scripts/disable-openai-dev.sh

ports:
	./scripts/port-forward-dev.sh foreground

ports-start:
	./scripts/port-forward-dev.sh start

ports-stop:
	./scripts/port-forward-dev.sh stop

ports-status:
	./scripts/port-forward-dev.sh status
