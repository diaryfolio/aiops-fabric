.PHONY: bootstrap lint unit compose-up compose-test k8s-deploy k8s-test

bootstrap:
	./scripts/bootstrap-dev-pki.sh

lint:
	docker build --target test -t viewsense-test:dev .
	docker run --rm viewsense-test:dev ruff check --no-cache src tests

unit:
	docker build --target test -t viewsense-test:dev .
	docker run --rm viewsense-test:dev pytest -q -p no:cacheprovider

compose-up: bootstrap
	docker compose --env-file .env.viewsense up --build -d

compose-test: bootstrap
	docker compose --env-file .env.viewsense --profile test run --rm smoke

k8s-deploy:
	./scripts/k8s-deploy-dev.sh

k8s-test:
	./scripts/k8s-test.sh
