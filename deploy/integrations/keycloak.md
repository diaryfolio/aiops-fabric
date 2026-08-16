# Keycloak and enterprise OIDC integration

The edge gateway accepts external OIDC tokens when issuer, JWKS URL, audience, tenant claim, and
scope claim are configured. It validates the external signature and audience, derives tenant at the
trust boundary, then uses the internal token broker for narrowed workload-to-workload tokens.
Public issuers use the container trust store. For an enterprise-private CA, mount a dedicated CA
bundle into the gateway and set `VS_EXTERNAL_OIDC_CA_FILE`; do not reuse the workload mTLS CA by
assumption. NetworkPolicy also requires the IdP/JWKS CIDR or an approved CNI FQDN policy.

For Keycloak, create a `viewsense` client/audience and protocol mappers for `tenant_id` and `scope`.
Operate Keycloak through its upstream Operator and database lifecycle; do not install it as a hidden
subchart. Validate key rotation, wrong issuer/audience, missing tenant, expired token, and cross-tenant
denial before enabling ingress.
