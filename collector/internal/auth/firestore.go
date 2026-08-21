package auth

import (
	"context"
	"fmt"

	"cloud.google.com/go/firestore"
)

// FirestoreRegistry is the cloud key registry: the api_keys collection cmd/keyctl
// writes, read under the collector's own service account (architecture §6.3 — the
// collector holds no secret, only hashes reachable through its identity).
type FirestoreRegistry struct {
	keyset
}

// LoadFirestoreRegistry reads the whole collection once, at startup.
//
// Once, for the same reasons the file registry gives (LoadFileRegistry): the hot path
// must not depend on a per-request Firestore read, and key rotation is a redeploy,
// which with min_instances=0 costs no money and no downtime. The whole collection
// rather than a status query so that the two backends filter with the same code —
// buildKeyset skipping inactive entries — instead of one filtering in a query language
// the other never runs.
func LoadFirestoreRegistry(ctx context.Context, project, database string) (*FirestoreRegistry, error) {
	client, err := firestore.NewClientWithDatabase(ctx, project, database)
	if err != nil {
		return nil, fmt.Errorf("auth: connecting to Firestore: %w", err)
	}
	defer client.Close()

	documents, err := client.Collection(Collection).Documents(ctx).GetAll()
	if err != nil {
		return nil, fmt.Errorf("auth: reading Firestore %s/%s: %w", project, Collection, err)
	}

	entries := make([]storedKey, 0, len(documents))
	for _, document := range documents {
		var key storedKey
		if err := document.DataTo(&key); err != nil {
			// An unreadable document is an error, not a skip — the same rule
			// buildKeyset applies to a malformed hash, for the same reason: the
			// quietly dropped entry is somebody's refused traffic.
			return nil, fmt.Errorf("auth: document %s/%s does not parse as a key: %w",
				Collection, document.Ref.ID, err)
		}
		entries = append(entries, key)
	}

	set, err := buildKeyset(entries, fmt.Sprintf("Firestore %s/%s", project, Collection))
	if err != nil {
		return nil, err
	}

	return &FirestoreRegistry{keyset: set}, nil
}
