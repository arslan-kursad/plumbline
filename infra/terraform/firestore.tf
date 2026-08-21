# Firestore — the metadata store (architecture §4.2, §6.3).
#
# It holds the hashed API key registry the collector reads under its own identity,
# which is what lets the collector be secret-free by construction (F2 D3). Keys are
# written by tools/keyctl and never by Terraform: state would otherwise hold
# material derived from a show-once workflow (D5).
resource "google_firestore_database" "plumbline" {
  project = var.project_id

  # The default database. A named one would need every client to say so, for no
  # benefit at this size.
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"

  # Firestore holds the key registry. A destroy that took it would revoke every
  # issued key at once, and the plaintext to reissue them does not exist anywhere
  # (D5) — the operator would have to reissue and redistribute to every agent.
  delete_protection_state = "DELETE_PROTECTION_ENABLED"
  deletion_policy         = "ABANDON"

  depends_on = [google_project_service.required]
}
