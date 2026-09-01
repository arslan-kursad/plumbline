# Development entry points. Every target here is also runnable in CI, because a command
# that only works on a laptop is a command whose failure nobody sees until a laptop
# changes.

.DEFAULT_GOAL := help
.PHONY: help gates test test-go test-dotnet fixtures e2e e2e-up e2e-down e2e-cloud e2e-cloud-drill

help: ## List the targets
	@grep -hE '^[a-z0-9-]+:.*?## ' $(MAKEFILE_LIST) | awk -F':.*?## ' '{printf "  %-12s %s\n", $$1, $$2}'

gates: ## Run the invariant gates and prove each one can fail
	./scripts/ci/invariant-gates.sh
	./scripts/ci/prove-gates.sh

test: test-go test-dotnet ## Run every unit and golden test

test-go: ## Collector tests, with the race detector
	cd collector && go vet ./... && go test -race ./...

test-dotnet: ## Normalization, worker and golden-file tests
	dotnet test worker/Plumbline.Worker.sln --nologo

fixtures: ## Regenerate the binary fixtures from their OTLP/JSON twins
	dotnet run --project worker/Plumbline.Fixtures

e2e: ## Full local pipeline: fixtures in, views out, poison in the DLQ
	./scripts/e2e/run.sh

e2e-up: ## Bring the local stack up and leave it running
	E2E_KEEP_UP=1 ./scripts/e2e/run.sh

e2e-down: ## Tear the local stack down
	docker compose --profile tools down --volumes --remove-orphans

# The first cloud run of this harness is the DoD 7b exam and it is taken once. Both
# targets refuse without PLUMBLINE_E2E_TARGET=cloud and E2E_RUN_ID (directive Decision 10).
e2e-cloud: ## Cloud happy path — armed, run-scoped; the DoD 7b exam on its first cloud run
	./scripts/e2e/run-cloud.sh

e2e-cloud-drill: ## Cloud failure path — poison to the DLQ, DoD 4; needs a drained queue
	./scripts/e2e/run-cloud.sh --drill
