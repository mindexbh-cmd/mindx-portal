"""One-shot VAPID key generator for the Mindex Web Push backend.

Run locally on any machine that has `py-vapid` installed:

    pip install py-vapid==1.9.0
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
recipient endpoint), but it's safest to bump
applicationServerKey in the client + truncate the table so every
subscriber re-grants permission with the new public key on next
visit.
"""
import sys


def main():
    try:
        from py_vapid import Vapid01
    except ImportError:
        sys.stderr.write(
            "[generate_vapid] py-vapid not installed.\n"
            "Run: pip install py-vapid==1.9.0\n")
        sys.exit(1)

    v = Vapid01()
    v.generate_keys()

    # py-vapid exposes the keys via internal helpers; the public
    # key in the format push services want is the uncompressed
    # x963 point serialised as base64url. The private key is the
    # 32-byte ECDSA scalar, also base64url.
    pub_b64 = v.public_key_to_b64()
    priv_b64 = v.private_key_to_b64()

    print("Generated VAPID key pair. Add to Render env vars:\n")
    print("VAPID_PUBLIC_KEY  = " + pub_b64)
    print("VAPID_PRIVATE_KEY = " + priv_b64)
    print("VAPID_CLAIM_SUB   = mailto:mindex.bh@gmail.com\n")
    print("Save in Render dashboard → Environment, then redeploy.")


if __name__ == "__main__":
    main()
