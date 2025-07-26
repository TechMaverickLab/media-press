#!/bin/bash


APP_NAME="Media Press"
APP_PATH="dist/${APP_NAME}.app"
DMG_NAME="${APP_NAME}.dmg"
DMG_PATH="dist/${DMG_NAME}"
VOL_NAME="${APP_NAME} Installer"
ICON_PATH="icon.icns"
BG_IMAGE_PATH="" 


if [ ! -d "${APP_PATH}" ]; then
    echo "Error: ${APP_PATH} not found."
    echo "First run 'pyinstaller \"Media Press.spec\"'"
    exit 1
fi

echo "Creating a DMG image..."

rm -f "${DMG_PATH}"

hdiutil create -srcfolder "${APP_PATH}" -volname "${VOL_NAME}" -fs HFS+ -fsargs "-c c=64,a=16,e=16" -format UDRW -size 256m "dist/temp.dmg"

MOUNT_DIR=$(hdiutil attach -readwrite -noverify -noautoopen "dist/temp.dmg" | egrep '/Volumes/' | sed 's/.*\/Volumes\//\/Volumes\//')

echo "Adjusting the appearance of the image in '${MOUNT_DIR}'..."

if [ -f "${ICON_PATH}" ]; then
    cp "${ICON_PATH}" "${MOUNT_DIR}/.VolumeIcon.icns"
    SetFile -a C "${MOUNT_DIR}"
fi

ln -s /Applications "${MOUNT_DIR}/Applications"

hdiutil detach "${MOUNT_DIR}"

echo "Conversion to final R/O image..."

hdiutil convert "dist/temp.dmg" -format UDZO -imagekey zlib-level=9 -o "${DMG_PATH}"

rm -f "dist/temp.dmg"

echo "✅ Done! Your installer is here: ${DMG_PATH}"