// Command collector receives OTLP trace exports and publishes them to Pub/Sub.
//
// It is the data plane, and its contract is narrow on purpose (architecture §2.1): it
// authenticates, rate limits, batches to a size budget, compresses and publishes. It
// does not parse span semantics, normalize attributes, or apply dialect logic — the
// bytes it receives are the bytes it publishes.
package main

import (
	"context"
	"errors"
	"log/slog"
	"net"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/arslan-kursad/plumbline/collector/internal/auth"
	"github.com/arslan-kursad/plumbline/collector/internal/config"
	"github.com/arslan-kursad/plumbline/collector/internal/ingest"
	"github.com/arslan-kursad/plumbline/collector/internal/publisher"
	"github.com/arslan-kursad/plumbline/collector/internal/ratelimit"
	"github.com/arslan-kursad/plumbline/collector/internal/receiver"
)

func main() {
	log := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{Level: slog.LevelInfo}))

	if err := run(log); err != nil {
		log.Error("collector stopped", "error", err)
		os.Exit(1)
	}
}

func run(log *slog.Logger) error {
	cfg, err := config.FromEnv()
	if err != nil {
		return err
	}

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	var registry auth.Registry
	if cfg.KeyFirestoreProject != "" {
		log.Info("key registry: firestore", "project", cfg.KeyFirestoreProject, "database", cfg.KeyFirestoreDatabase)
		registry, err = auth.LoadFirestoreRegistry(ctx, cfg.KeyFirestoreProject, cfg.KeyFirestoreDatabase)
	} else {
		log.Info("key registry: file", "path", cfg.KeyRegistryPath)
		registry, err = auth.LoadFileRegistry(cfg.KeyRegistryPath)
	}
	if err != nil {
		return err
	}

	pub, err := publisher.NewPubSub(ctx, cfg.ProjectID, cfg.Topic)
	if err != nil {
		return err
	}
	defer func() { _ = pub.Close() }()

	ingestor := &ingest.Ingestor{
		Registry:           registry,
		Limiter:            ratelimit.New(time.Now),
		Publisher:          pub,
		MaxCompressedBytes: cfg.MaxCompressedBytes,
	}

	httpServer := &http.Server{
		Addr:              cfg.HTTPAddr,
		Handler:           receiver.NewHTTP(ingestor, log),
		ReadHeaderTimeout: 10 * time.Second,
	}
	grpcServer := receiver.NewGRPC(ingestor, log)

	grpcListener, err := net.Listen("tcp", cfg.GRPCAddr)
	if err != nil {
		return err
	}

	errs := make(chan error, 2)

	go func() {
		log.Info("otlp/http listening", "addr", cfg.HTTPAddr, "topic", cfg.Topic)
		if err := httpServer.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			errs <- err
		}
	}()

	go func() {
		log.Info("otlp/grpc listening", "addr", cfg.GRPCAddr, "topic", cfg.Topic)
		if err := grpcServer.Serve(grpcListener); err != nil {
			errs <- err
		}
	}()

	select {
	case err := <-errs:
		return err
	case <-ctx.Done():
		log.Info("shutting down", "timeout", cfg.ShutdownTimeout)
	}

	// Graceful shutdown, in the order that avoids losing an accepted export: stop
	// taking new requests, let in-flight ones finish, and only then close the
	// publisher, whose Close flushes what is still buffered.
	shutdownCtx, cancel := context.WithTimeout(context.Background(), cfg.ShutdownTimeout)
	defer cancel()

	if err := httpServer.Shutdown(shutdownCtx); err != nil {
		log.Warn("http shutdown did not complete", "error", err)
	}

	stopped := make(chan struct{})
	go func() {
		grpcServer.GracefulStop()
		close(stopped)
	}()

	select {
	case <-stopped:
	case <-shutdownCtx.Done():
		log.Warn("grpc shutdown timed out; stopping now")
		grpcServer.Stop()
	}

	return nil
}
