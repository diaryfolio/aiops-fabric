# Identity Module

The identity module defines external enterprise federation and internal workload-token boundaries. The bundled RSA client-credentials issuer and development CA exist only for repeatable local tests.

- Runtime: `viewsense_identity`
- Contract: OAuth client credentials with exact audience and scopes
- Helm selection: `products.identity.product`
- Edge federation: `external-oidc` or `keycloak-oidc` validates issuer, JWKS, audience, scopes,
  subject, and a configured tenant claim before ViewSense creates an internal Trust Envelope.
- Workload identity: `static-development-pki` is executable for tests. SPIRE/mesh is planned;
  current Helm values record intent but do not mount or consume SVIDs.
- Production choice: enterprise OIDC plus renewable workload identity and external secrets.

Keycloak is an optional OIDC provider, not part of the ViewSense trust core. A future SPIRE
integration is a cluster-scoped managed dependency, not an application sidecar bundled into every pod. See
`deploy/integrations/keycloak.md` and `deploy/integrations/spire.md`.
