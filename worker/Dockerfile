# Build context is the repository root: the worker embeds the mapping and redaction YAML
# from normalization/ and generates OTLP types from third_party/, so a context scoped to
# worker/ would build a binary with no mappings in it.
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build

WORKDIR /src
COPY worker/ worker/
COPY normalization/ normalization/
COPY third_party/ third_party/

RUN dotnet publish worker/Plumbline.Worker/Plumbline.Worker.csproj \
      --configuration Release \
      --output /out \
      /p:UseAppHost=false

# Chiseled: distroless for .NET — no shell, no package manager, runs as a non-root user
# by default (architecture §8).
FROM mcr.microsoft.com/dotnet/aspnet:8.0-jammy-chiseled

WORKDIR /app
COPY --from=build /out .

EXPOSE 8080
ENV ASPNETCORE_URLS=http://0.0.0.0:8080
ENTRYPOINT ["dotnet", "Plumbline.Worker.dll"]
