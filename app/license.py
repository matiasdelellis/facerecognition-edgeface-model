"""Non-commercial acknowledgement required by the model weights.

The weights are not part of the repository and are licensed for non-commercial
use only. Nothing here can verify how the service is used: the variable only
records that the operator confirmed the terms, and the service refuses to start
until it is set. The upstream licenses remain in force.
"""
import os

VARIABLE = "LICENSE_ACCEPTED"
VALUE = "non-commercial"

MESSAGE = f"""\
This service uses model weights that are licensed for non-commercial use only:
  EdgeFace-Base  CC BY-NC-SA 4.0 (Idiap Research Institute)
  SCRFD          non-commercial research use only (InsightFace)

Set {VARIABLE}={VALUE} to confirm that this deployment is not primarily
intended for or directed towards commercial advantage or monetary
compensation. See NOTICE.md.

This acknowledgement is not a license: the weights remain under their own
terms, and commercial use requires a license from their authors.
"""


def accepted():
    return os.getenv(VARIABLE, "").strip().lower() == VALUE


def require():
    if not accepted():
        raise SystemExit(MESSAGE)
