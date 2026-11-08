"""Resolve OpenSSL configuration inside the bundle before importing hashlib/ssl.

Conda's libcrypto embeds an absolute build-prefix configuration path. Accessing
that path from a Finder app can block on macOS privacy checks and also makes the
application depend on a developer machine. Preserve deliberate user overrides.
"""

import os
import sys

os.environ.setdefault("OPENSSL_CONF", os.path.join(sys._MEIPASS, "openssl.cnf"))
