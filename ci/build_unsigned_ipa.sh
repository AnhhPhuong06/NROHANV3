#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$PWD"
BUILD_DIR="$ROOT/build"
ARCHIVE_PATH="$BUILD_DIR/NroHan.xcarchive"
IPA_PATH="$BUILD_DIR/NroHan-unsigned.ipa"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This script requires macOS and Xcode (run the ios-unsigned workflow on Codemagic)." >&2
  exit 1
fi

# Fail early if a checkout still contains Git LFS pointers instead of libraries.
python3 - <<'PY'
from pathlib import Path

for name in ("libiPhone-lib.a", "libil2cpp.a", "baselib.a"):
    library = Path("Libraries") / name
    with library.open("rb") as stream:
        header = stream.read(64)
    if header.startswith(b"version https://git-lfs.github.com/spec/v1"):
        raise SystemExit(f"{library} is a Git LFS pointer. Run git lfs pull first.")
    if not header:
        raise SystemExit(f"{library} is empty.")
PY

mkdir -p "$BUILD_DIR/logs"
# Xcode requires a new result bundle path for every invocation.
RESULT_PATH="$BUILD_DIR/Build-$(date +%Y%m%d-%H%M%S)-$$.xcresult"
xcodebuild archive \
  -project "$ROOT/Unity-iPhone.xcodeproj" \
  -scheme Unity-iPhone \
  -configuration Release \
  -sdk iphoneos \
  -destination 'generic/platform=iOS' \
  -archivePath "$ARCHIVE_PATH" \
  -derivedDataPath "$BUILD_DIR/DerivedData" \
  -resultBundlePath "$RESULT_PATH" \
  ARCHS=arm64 \
  ONLY_ACTIVE_ARCH=NO \
  CODE_SIGNING_ALLOWED=NO \
  CODE_SIGNING_REQUIRED=NO \
  CODE_SIGN_IDENTITY= \
  DEVELOPMENT_TEAM= \
  ENABLE_BITCODE=NO \
  COMPILER_INDEX_STORE_ENABLE=NO \
  2>&1 | tee "$BUILD_DIR/logs/xcodebuild.log"

shopt -s nullglob
APPS=("$ARCHIVE_PATH/Products/Applications/"*.app)
if [[ ${#APPS[@]} -ne 1 ]]; then
  echo "Expected exactly one archived app; found ${#APPS[@]}." >&2
  exit 1
fi
APP_PATH="${APPS[0]}"
APP_NAME="$(basename "$APP_PATH")"
EXECUTABLE="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleExecutable' "$APP_PATH/Info.plist")"
xcrun lipo "$APP_PATH/$EXECUTABLE" -verify_arch arm64
test -f "$APP_PATH/Frameworks/UnityFramework.framework/UnityFramework"

# Use a fresh staging directory so a repeated build cannot mix app versions.
STAGING_DIR="$(mktemp -d "$BUILD_DIR/ipa.XXXXXX")"
trap 'rm -rf "$STAGING_DIR"' EXIT
mkdir -p "$STAGING_DIR/Payload"
ditto "$APP_PATH" "$STAGING_DIR/Payload/$APP_NAME"

# Archive the Payload directly; unsigned builds do not need an export profile.
rm -f "$IPA_PATH"
ditto -c -k --keepParent --norsrc "$STAGING_DIR/Payload" "$IPA_PATH"
unzip -tq "$IPA_PATH"
echo "Unsigned IPA: $IPA_PATH"
