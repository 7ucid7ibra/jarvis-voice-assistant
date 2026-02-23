#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_NAME="Jarvis Assistant"
SPEC_FILE="${PROJECT_ROOT}/Jarvis Assistant.spec"
PYTHON_BIN="${PYTHON_BIN:-${PROJECT_ROOT}/.venv/bin/python}"

VERSION_TAG="${1:-vNEXT}"
TARGET_ARCH="${2:-universal2}" # universal2 | x86_64 | arm64

DIST_DIR="${PROJECT_ROOT}/dist"
BUILD_DIR="${PROJECT_ROOT}/build"
DMG_STAGE_DIR="${BUILD_DIR}/dmg_stage"
APP_BUNDLE_PATH="${DIST_DIR}/${APP_NAME}.app"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Python executable not found at ${PYTHON_BIN}"
  echo "Set PYTHON_BIN or create .venv first."
  exit 1
fi

if [[ ! -f "${SPEC_FILE}" ]]; then
  echo "Spec file missing: ${SPEC_FILE}"
  exit 1
fi

NATIVE_ARCH="$(uname -m)"
if [[ "${NATIVE_ARCH}" != "x86_64" && "${NATIVE_ARCH}" != "arm64" ]]; then
  echo "Unsupported native architecture: ${NATIVE_ARCH}"
  exit 1
fi

EFFECTIVE_ARCH="${TARGET_ARCH}"
echo "Building ${APP_NAME}.app (target_arch=${TARGET_ARCH})..."
if ! JARVIS_TARGET_ARCH="${TARGET_ARCH}" "${PYTHON_BIN}" -m PyInstaller -y "${SPEC_FILE}"; then
  if [[ "${TARGET_ARCH}" == "universal2" ]]; then
    echo "Universal2 build failed in this environment. Falling back to native arch: ${NATIVE_ARCH}"
    EFFECTIVE_ARCH="${NATIVE_ARCH}"
    JARVIS_TARGET_ARCH="${EFFECTIVE_ARCH}" "${PYTHON_BIN}" -m PyInstaller -y "${SPEC_FILE}"
  else
    exit 1
  fi
fi

if [[ ! -d "${APP_BUNDLE_PATH}" ]]; then
  echo "Build failed: app bundle not found at ${APP_BUNDLE_PATH}"
  exit 1
fi

APP_EXECUTABLE="${APP_BUNDLE_PATH}/Contents/MacOS/${APP_NAME}"
if [[ -f "${APP_EXECUTABLE}" ]]; then
  APP_FILE_DESC="$(file "${APP_EXECUTABLE}" || true)"
  if [[ "${APP_FILE_DESC}" == *"arm64"* && "${APP_FILE_DESC}" == *"x86_64"* ]]; then
    EFFECTIVE_ARCH="universal2"
  elif [[ "${APP_FILE_DESC}" == *"arm64"* ]]; then
    EFFECTIVE_ARCH="arm64"
  elif [[ "${APP_FILE_DESC}" == *"x86_64"* ]]; then
    EFFECTIVE_ARCH="x86_64"
  fi
fi

rm -rf "${DMG_STAGE_DIR}"
mkdir -p "${DMG_STAGE_DIR}"
cp -R "${APP_BUNDLE_PATH}" "${DMG_STAGE_DIR}/${APP_NAME}.app"
ln -s /Applications "${DMG_STAGE_DIR}/Applications"

DMG_BASENAME="Jarvis-Assistant-${VERSION_TAG}"
if [[ "${EFFECTIVE_ARCH}" != "universal2" ]]; then
  DMG_BASENAME="${DMG_BASENAME}-${EFFECTIVE_ARCH}"
fi
DMG_OUTPUT="${DIST_DIR}/${DMG_BASENAME}.dmg"
rm -f "${DMG_OUTPUT}"

echo "Creating DMG: ${DMG_OUTPUT}"
hdiutil create \
  -volname "${APP_NAME}" \
  -srcfolder "${DMG_STAGE_DIR}" \
  -ov \
  -format UDZO \
  "${DMG_OUTPUT}"

echo "Done: ${DMG_OUTPUT}"
echo
if [[ "${EFFECTIVE_ARCH}" != "universal2" ]]; then
  echo "Built native-arch artifact (${EFFECTIVE_ARCH})."
  echo "To publish both fallback artifacts, also build on the other native host:"
  if [[ "${EFFECTIVE_ARCH}" == "x86_64" ]]; then
    echo "  ${0} ${VERSION_TAG} arm64"
  else
    echo "  ${0} ${VERSION_TAG} x86_64"
  fi
fi
