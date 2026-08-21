# Build context is ./collector — the module is self-contained and the image has no
# reason to see the rest of the repository.
FROM golang:1.26-bookworm AS build

WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .

# Static, stripped, reproducible enough to compare between builds.
ENV CGO_ENABLED=0
RUN go build -trimpath -ldflags="-s -w" -o /out/collector .

# Distroless (architecture §8): no shell, no package manager, nothing to exec into.
# `nonroot` rather than root because nothing here needs privilege, and the OTLP ports are
# above 1024 precisely so it does not.
FROM gcr.io/distroless/static-debian12:nonroot

COPY --from=build /out/collector /collector

EXPOSE 4317 4318
USER nonroot:nonroot
ENTRYPOINT ["/collector"]
