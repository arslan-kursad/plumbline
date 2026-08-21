terraform {
  # Partial backend configuration: the bucket is created by ./bootstrap and its
  # name depends on the project ID, which is not known at authoring time.
  #
  #   terraform init -backend-config=backend.hcl
  #
  # See backend.hcl.example.
  backend "gcs" {
    prefix = "f0"
  }
}
