# Planned SPIRE integration

No executable SPIRE consumer ships in this repository. The target integration is to install the
upstream hardened SPIRE Helm charts in a dedicated security namespace, register each
ViewSense AI® Kubernetes service account with a distinct SPIFFE ID, mount the Workload API socket using
the SPIFFE CSI driver, and terminate workload mTLS through an SDS-capable Envoy/service-mesh proxy.
The application chart currently only records `trustDomain` and `socketPath`; future production overlays inject the proxy
and must remove static development PKI only after the SPIFFE mTLS negative tests pass.

ViewSense AI® does not vendor SPIRE manifests because SPIRE is cluster-scoped and its node attestation,
trust domain, federation, upgrade, and disaster-recovery settings belong to the cluster security
owner. Never enable a profile that merely mounts the socket while leaving traffic on static PKI.
