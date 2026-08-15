# Identity Module

The identity module defines external enterprise federation and internal workload-token boundaries. The bundled RSA client-credentials issuer and development CA exist only for repeatable local tests.

- Runtime: `viewsense_identity`
- Contract: OAuth client credentials with exact audience and scopes
- Helm selection: `products.identity.product`
- Production choice: enterprise OIDC plus renewable workload identity and external secrets
