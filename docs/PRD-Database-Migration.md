# PRD – Safe Database Migration for Phase Console

## 1. Objective

Enable **safe, repeatable, and auditable** PostgreSQL database migrations for the `phase-console` Helm chart so that upgrades do not risk data loss and are easy to operate in production.

## 2. Problem Statement

Current / previous migration approach in PR #36 was not production-safe:
- No end-to-end verification of migrated data.
- Used `pg_dump | psql` piping with weak error handling.
- Credentials and DB access patterns not hardened for Kubernetes best practices.
- No clear user-facing migration paths (fresh install, migrate, external DB).
- No documented rollback or troubleshooting process.

## 3. Goals

- Provide a **single, robust migration job** that:
  - Validates connectivity to old and new DBs.
  - Migrates data using a safe mechanism.
  - Verifies schema and basic data integrity after migration.
- Expose **clear Helm values** so users can:
  - Choose between migration, fresh install, or external DB.
- Ensure **security best practices** for credentials, permissions, and pod security.
- Deliver **operator-grade docs**: runbooks, rollback, and troubleshooting.

## 4. Non‑Goals

- Implement application-level data transformations or versioned schema migrations.
- Support non-PostgreSQL backends.
- Build a generic migration framework for arbitrary apps.

## 5. User Personas

- **SRE / DevOps Engineer**: Maintains clusters, runs upgrades, cares about safety, rollback, and observability.
- **Platform Engineer**: Maintains Helm charts, ensures security posture and consistency.
- **Phase OSS User**: Uses `phase-console` Helm chart in non-trivial environments and needs clear docs.

## 6. Functional Requirements

1. **Migration Job**
   - A Kubernetes `Job` runs the migration when `migration.enabled=true`.
   - The job must:
     - Retry DB connectivity for both old and new DB (configurable attempts).
     - Create a binary dump of the old DB.
     - Restore into the new DB.
     - Optionally verify table counts, schemas, and indexes.

2. **Configuration via values.yaml**
   - `migration.enabled` – toggles data migration.
   - `migration.freshInstall` – explicitly indicates no migration needed.
   - Old DB coordinates: host, port, secret name, secret key.
   - Migration timeout and verification toggle.

3. **Safety Gate**
   - Chart upgrade must **fail fast** (template validation) when neither:
     - `migration.enabled=true`, nor
     - `migration.freshInstall=true`, nor
     - `database.external=true`
     is set, to prevent accidental silent behavior.

4. **PostgreSQL Target**
   - New DB is provided by the Bitnami PostgreSQL subchart and wired to app.
   - Backend deployment updates to point at the new DB when migration is enabled.

5. **Documentation**
   - Runbooks for:
     - Upgrade with migration.
     - Fresh install.
     - Using an external DB.
     - Migrating from old external DB to new DB.
   - Rollback instructions (Helm rollback + restore from backup).

## 7. Non‑Functional Requirements

- **Reliability**:
  - Migration must detect failures and exit with non-zero status.
  - Post-migration verification must catch mismatches in table counts and basic schema fingerprints.

- **Security**:
  - No secrets or passwords printed in logs.
  - Credentials consumed via Kubernetes `Secret` references.
  - Pod runs as non-root, read-only filesystem, minimal RBAC.

- **Performance**:
  - Handle DB sizes from small (<100 MB) to large (10–100+ GB) with tunable timeout and resources.

- **Operability**:
  - Logs must clearly show phases and outcomes of migration.
  - Helm values must be self-documented with comments and examples.

***

# User Acceptance Criteria (UAC)

### UAC 1 – Safe Enablement

1. When a user runs `helm upgrade` **without** setting any of:
   - `migration.enabled=true`
   - `migration.freshInstall=true`
   - `database.external=true`
   the Helm render/upgrade must **fail with a clear, actionable error message** explaining what to set.

2. When a user sets **exactly one** of the three flags, the chart must render successfully.

### UAC 2 – Data Migration Path

When `migration.enabled=true` is set and old + new DBs are reachable:

1. A `Job` named with the release prefix and `-migration` is created.
2. The job logs must show steps:
   - Connection validation for old and new DB.
   - Pre-migration stats (table count and DB size).
   - Dump and restore progress.
   - Post-migration verification (table count and schema checks).
3. On success, the job must complete with status `Succeeded` and exit code 0.
4. After job completion, the application backend must point to the **new** PostgreSQL service and operate normally.

### UAC 3 – Fresh Install Path

When `migration.freshInstall=true` is set:

1. No migration job should be created.
2. The new PostgreSQL subchart should deploy and be wired to the backend.
3. `helm install` or `helm upgrade` must complete successfully and the application must function with an empty DB.

### UAC 4 – External DB Path

When `database.external=true` and `postgresql.enabled=false` are set with valid external DB values:

1. No internal PostgreSQL StatefulSet is created.
2. No migration job is created by default.
3. Backend pods must use the external DB endpoint and start successfully.

### UAC 5 – Security Constraints

1. Migration pod runs as a **non-root user**, with `runAsNonRoot=true` and `runAsUser` set to a non-zero UID.
2. `readOnlyRootFilesystem=true` is set on the migration container.
3. Credentials for old and new DBs are only referenced via `secretKeyRef` and never appear as plain text in rendered manifests or logs.
4. The Role/RoleBinding for the migration job is limited to `get` on specific secrets only.

### UAC 6 – Observability & Error Handling

1. If old DB is not reachable, the migration job must:
   - Retry according to configured logic.
   - Log each attempt clearly.
   - Eventually fail with a clear error if still unreachable.

2. If the restore to new DB fails, the job must:
   - Exit with non-zero status.
   - Log reason for failure (timeout, invalid dump, etc.).

3. If post-migration verification detects mismatches:
   - The job must exit non-zero.
   - Logs must clearly show mismatch (e.g., table counts).

### UAC 7 – Rollback Instructions

1. Documentation must include a clear rollback procedure using `helm rollback` and restoring from backup.
2. Following those documented steps must successfully restore the environment to a pre-migration, working state in a test environment.
