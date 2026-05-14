"""One-shot VAPID key generator for the Mindex Web Push backend.

Generates an ECDSA P-256 key pair and prints the base64url-encoded
public + private keys in the format Web Push services expect.

Run locally:

    pip install cryptography
    python scripts/generate_vapid.py

Pastes:

    VAPID_PUBLIC_KEY  = <base64url, ~87 chars>
    VAPID_PRIVATE_KEY = <base64url, ~43 chars>

Take both values into the Render dashboard:

    Render service → Environment → Add Environment Variable
    Add: VAPID_PUBLIC_KEY  = <public>
    Add: VAPID_PRIVATE_KEY = <private>
    Add: VAPID_CLAIM_SUB   = mailto:mindex.bh@gmail.com
    Save and trigger a deploy.

DO NOT commit the printed keys. The private key must never enter
the repo or any logs — it's the signing secret for every push
sent from the server. Loss is benign (just regenerate + update
both Render env vars + invalidate all client subscriptions); leak
means anyone can spoof Mindex notifications to subscribed devices.

Re-run the script any time keys need to be rotated. After rotation
the existing `push_subscriptions` rows still work for *receiving*
the new push messages (the keys identify the SENDER, not the
recipient endpoint), but it's safest to bump applicationServerKey
in the client + truncate the table so every subscriber re-grants
permission with the new public key on next visit.

Implementation note: we use the `cryptography` library directly
rather than py-vapid's generate_keys() because py-vapid 1.9.0
has a TypeError against modern cryptography releases
(it passes ec.SECP256R1 the class instead of ec.SECP256R1()).
The output format is identical and compatible with pywebpush.
"""
import base64
import sys


def b64url(raw_bytes):
    """RFC 4648 §5 base64url, no padding (per Web Push spec)."""
    return base64.urlsafe_b64encode(raw_bytes).rstrip(b"=").decode("ascii")


def main():
    try:
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.backends import default_backend
    except ImportError:
        sys.stderr.write(
            "[generate_vapid] cryptography not installed.\n"
            "Run: pip install cryptography\n")
        sys.exit(1)

    priv = ec.generate_private_key(ec.SECP256R1(), default_backend())
    pub = priv.public_key()

    # Public key: uncompressed point (0x04 || X || Y), 65 bytes total.
    # This is the format Web Push services + browsers expect.
    pub_bytes = pub.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )

    # Private key: 32-byte raw scalar (the integer 'd' in P-256).
    priv_int = priv.private_numbers().private_value
    priv_bytes = priv_int.to_bytes(32, byteorder="big")

    print("Generated VAPID key pair. Add to Render env vars:\n")
    print("VAPID_PUBLIC_KEY  = " + b64url(pub_bytes))
    print("VAPID_PRIVATE_KEY = " + b64url(priv_bytes))
    print("VAPID_CLAIM_SUB   = mailto:mindex.bh@gmail.com\n")
    print("Save in Render dashboard -> Environment, then redeploy.")
    print("DO NOT commit these values anywhere.")


if __name__ == "__main__":
    main()
