# SPIRE integration

Install the upstream hardened SPIRE Helm charts in a dedicated security namespace. Register each
ViewSense Kubernetes service account with a distinct SPIFFE ID, mount the Workload API socket using
the SPIFFE CSI driver, and terminate workload mTLS through an SDS-capable Envoy/service-mesh proxy.
The application chart records `trustDomain` and `socketPath`; production overlays inject the proxy
and must remove static development PKI only after the SPIFFE mTLS negative tests pass.

ViewSense does not vendor SPIRE manifests because SPIRE is cluster-scoped and its node attestation,
trust domain, federation, upgrade, and disaster-recovery settings belong to the cluster security
owner. Never enable a profile that merely mounts the socket while leaving traffic on static PKI.
