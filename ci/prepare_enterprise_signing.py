"""Use the uploaded Enterprise profile's application ID in the CI checkout."""

import fnmatch
import os
import plistlib
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_BUNDLE_ID = "com.DefaultCompany.Boy003"


def choose_bundle_id(profile, override=None):
    if profile.get("ProvisionsAllDevices") is not True:
        raise ValueError("The uploaded profile must be an Enterprise (In House) profile.")
    if profile.get("Entitlements", {}).get("get-task-allow", False):
        raise ValueError("A distribution profile is required; debugging must be disabled.")
    expiry = profile["ExpirationDate"]
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    if expiry <= datetime.now(timezone.utc):
        raise ValueError("The uploaded Enterprise profile has expired.")

    app_id = profile["Entitlements"]["application-identifier"]
    prefix, separator, pattern = app_id.partition(".")
    if not separator or prefix not in profile.get("ApplicationIdentifierPrefix", []):
        raise ValueError("The profile has an invalid application identifier prefix.")
    if override:
        bundle_id = override
    elif "*" not in pattern:
        bundle_id = pattern
    elif fnmatch.fnmatchcase(DEFAULT_BUNDLE_ID, pattern):
        bundle_id = DEFAULT_BUNDLE_ID
    elif pattern.endswith(".*") and pattern.count("*") == 1:
        bundle_id = pattern[:-1] + "NroHan"
    else:
        raise ValueError("Set BUNDLE_ID in Codemagic to an ID covered by this profile.")
    if not re.fullmatch(r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+", bundle_id):
        raise ValueError("BUNDLE_ID must be a valid explicit reverse-DNS identifier.")
    if not fnmatch.fnmatchcase(bundle_id, pattern):
        raise ValueError("BUNDLE_ID does not match the uploaded Enterprise profile.")
    return bundle_id


def main():
    profile_path = os.environ.get("ENTERPRISE_PROFILE_PATH")
    if not profile_path or not Path(profile_path).is_file():
        raise SystemExit("Upload nrohan_enterprise_profile in Codemagic Code signing identities.")
    decoded = subprocess.run(
        ["security", "cms", "-D", "-i", profile_path],
        check=True, capture_output=True,
    )
    profile = plistlib.loads(decoded.stdout)
    bundle_id = choose_bundle_id(profile, os.environ.get("BUNDLE_ID"))
    project_path = Path(__file__).resolve().parents[1] / "Unity-iPhone.xcodeproj/project.pbxproj"
    project = project_path.read_text(encoding="utf-8")
    original = f"PRODUCT_BUNDLE_IDENTIFIER = {DEFAULT_BUNDLE_ID};"
    if original not in project:
        raise SystemExit("The app bundle ID has changed; update the signing preparation script.")
    project_path.write_text(
        project.replace(original, f"PRODUCT_BUNDLE_IDENTIFIER = {bundle_id};"),
        encoding="utf-8",
    )
    print(f"Enterprise app bundle ID: {bundle_id}")


if __name__ == "__main__":
    main()
