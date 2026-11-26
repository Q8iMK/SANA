# SANA update to Hermes v0.23.4

Verified on November 26, 2026, on Windows.

The update integrates official Hermes v0.23.4, commit
`8fc0374447313e276f6b9a2764bfc750190c966a`, into the existing SANA source.
The starting SANA commit is `6fcc947e7acf0e72da0f393c4a8a68e5c9c77d22`,
preserved by branch `backup/sana-before-v0.23.4-20261126`.

The previous v0.23.3 integration was a single-parent commit. An ancestry-only
merge records its official baseline, `caafe5389ae585ef77387a962aee05b1bcf17029`,
without changing its tree. The subsequent update uses a normal three-way merge.

## Identity verification

- The product remains SANA, developed by Q8iDevAI.
- The default SOUL, default-persona implementation, central branding configuration,
  desktop artwork, installer configuration and license match the starting SANA tree.
- Stable desktop identifiers and data directories are preserved. The new upstream
  Store canary behavior uses `Q8iDevAI.SANACanary`, alongside stable `Q8iDevAI.SANA`.
- New approval, notification, startup and profile-backend messages use SANA.
  Technical identifiers and external service names retain their existing meanings.
- The existing prompt test now checks both SANA and Q8iDevAI in the generated
  context instead of expecting the upstream product name.

## Validation

- `python branding/scripts/apply_branding.py --check` passed.
- The project Python test runner passed 86 tests covering branding, prompt
  construction, SOUL profile isolation and the new plugin-settings CLI. It skipped
  11 platform-specific cases on Windows.
- Vitest passed 46 tests across product identity, profile-backend confirmations,
  launched profiles, composer placeholders, notification settings and i18n keys.
- After moving the connection-identity helper, all 76 existing gateway-boot tests
  passed, and the renderer TypeScript check passed again. Focused ESLint checks
  reported no errors and one existing statement-spacing warning in gateway boot.
- TypeScript renderer and Electron checks passed.
- All 565 changed Python files parsed successfully.
- Additional profile lifecycle tests passed 167 cases, failed 12 and skipped 5.
  The same 12 cases fail in an independently extracted official v0.23.4 checkout
  on this host. They cover Windows symlink privileges, POSIX permission/alias
  assumptions, an unescaped Windows path in a regex, and `..` path behavior.

The staged repository check passed 18 of 22 checks. It reported existing SANA
install-root lint, generated-shim metadata drift and two datetime lint findings.
It also reported a new file-size violation where upstream gateway changes joined
existing SANA boot fixes. The connection-identity helper was moved into
`use-gateway-boot/connection.ts`, with its callers and existing tests updated.
Its three existing tests moved alongside it. The final staged code-health
check passed with zero blocking findings and one upstream advisory.
The initial working-directory check additionally found local archives and,
when compared against upstream rather than the SANA starting point, existing
SANA ICNS assets over the blob-size limit.

The local pre-commit hook failed to parse its generated shell commands on Windows.
Validation was run separately. These findings are not a green release validation.

Raw comparison logs and the branding JSON report are under the ignored directory
`.cache/sana-v0.23.4-validation/`.

This verification covers source integration and focused tests. Installer creation,
installation, upgrade acceptance and live-model responses are pending.
