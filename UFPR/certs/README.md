# Public intermediate certificate for the UFPR source

The UFPR HTTPS server currently presents its `*.ufpr.br` leaf certificate without
its intermediate. The leaf's Authority Information Access points to:

https://secure.globalsign.com/cacert/rnpicpedugr46ovtlsca2025.crt

The bundled PEM is the DER certificate from that official CA endpoint, converted
with `openssl x509 -inform DER -outform PEM`. SHA-256 fingerprint:

`E1:07:47:D4:DA:7B:AB:09:CB:A9:95:2F:01:9D:35:34:CB:9F:BA:07:0B:F1:3D:87:91:B1:69:9C:D2:FF:59:DD`

Subject: RNP ICPEdu GR46 OV TLS CA 2025. Issuer: GlobalSign Root R46.
Valid from November 19, 2025 until November 19, 2030.

The collector first verifies this intermediate against the operating system's
trusted roots, then includes it in the UFPR-specific certificate store. Peer,
hostname and expiry verification stay enabled. No global CA settings are changed;
Firebase keeps its existing HTTPS trust configuration. This is a public CA
certificate, not a private key or application credential.
