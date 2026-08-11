#!/data/data/com.termux/files/usr/bin/bash
# Install/update the pinned, unmodified Magia Exedra TW 1.1.2 XAPK from Termux.
# Android 11+ Wireless debugging must already be paired and connected.

set -euo pipefail

PACKAGE_NAME="tw.sonet.magiaexedra"
INSTALLER_PACKAGE="com.android.vending"
EXPECTED_VERSION_NAME="1.1.2"
EXPECTED_VERSION_CODE="26072717"

EXPECTED_XAPK_SIZE="769197299"
EXPECTED_XAPK_SHA256="664dfbc307c5f6b640d01b1fc661de02fa30fc382a68426530abc657dc9e2d14"

EXPECTED_BASE_SIZE="15521887"
EXPECTED_BASE_SHA256="ceafa5ba761b8d3996ce2718ff163b8b21707fdc1d304d6edc27b8582c93038e"
EXPECTED_ASSETS_SIZE="522274683"
EXPECTED_ASSETS_SHA256="0d21a05fd1007b31a1a6fa72561c6d6f2eeaa8353492913dd925465bc10d82ed"
EXPECTED_ARM64_SIZE="231099307"
EXPECTED_ARM64_SHA256="19466690a93ae7ea84485b86453901c5ed7745aea2b2d0cd4098bb13b02c69c5"

usage() {
    cat <<'EOF'
Usage:
  bash mobile/install_tw_termux.sh [--serial WIRELESS_ADB_SERIAL] /path/to/original.xapk

The script accepts only the pinned original TW 1.1.2 XAPK. It verifies the
whole XAPK and all three split APKs, installs with -r while attributing the
installer to com.android.vending, verifies the installed package, force-stops
it, and never launches the game.

Set TW_ADB_SERIAL instead of --serial when desired.
EOF
}

die() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

require_command() {
    command -v "$1" >/dev/null 2>&1 || die "missing command: $1"
}

sha256_file() {
    sha256sum "$1" | awk '{print tolower($1)}'
}

file_size() {
    stat -c '%s' "$1"
}

verify_file() {
    label="$1"
    path="$2"
    expected_size="$3"
    expected_sha="$4"
    actual_size="$(file_size "$path")"
    [ "$actual_size" = "$expected_size" ] || \
        die "$label size mismatch: $actual_size (expected $expected_size)"
    actual_sha="$(sha256_file "$path")"
    [ "$actual_sha" = "$expected_sha" ] || \
        die "$label SHA-256 mismatch: $actual_sha"
    printf '[OK] %s size=%s sha256=%s\n' "$label" "$actual_size" "$actual_sha"
}

is_wireless_serial() {
    case "$1" in
        *:*) return 0 ;;
        *_adb-tls-connect._tcp*) return 0 ;;
        *) return 1 ;;
    esac
}

choose_wireless_serial() {
    requested="$1"
    adb start-server >/dev/null
    mapfile -t ready_devices < <(adb devices | awk 'NR > 1 && $2 == "device" {print $1}')

    if [ -n "$requested" ]; then
        is_wireless_serial "$requested" || die "selected serial is not a Wireless debugging endpoint: $requested"
        for serial in "${ready_devices[@]}"; do
            [ "$serial" = "$requested" ] && { printf '%s\n' "$requested"; return 0; }
        done
        die "selected Wireless debugging endpoint is not ready: $requested"
    fi

    wireless=()
    loopback=()
    for serial in "${ready_devices[@]}"; do
        if is_wireless_serial "$serial"; then
            wireless+=("$serial")
            case "$serial" in
                127.0.0.1:*|localhost:*) loopback+=("$serial") ;;
            esac
        fi
    done

    if [ "${#loopback[@]}" -eq 1 ]; then
        printf '%s\n' "${loopback[0]}"
    elif [ "${#wireless[@]}" -eq 1 ]; then
        printf '%s\n' "${wireless[0]}"
    elif [ "${#wireless[@]}" -eq 0 ]; then
        die "no ready Wireless debugging endpoint; run adb pair HOST:PAIR_PORT and adb connect HOST:DEBUG_PORT first"
    else
        printf 'Ready wireless endpoints:\n' >&2
        printf '  %s\n' "${wireless[@]}" >&2
        die "more than one endpoint is ready; pass --serial or set TW_ADB_SERIAL"
    fi
}

serial_option="${TW_ADB_SERIAL:-}"
if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
    usage
    exit 0
fi
if [ "${1:-}" = "--serial" ]; then
    [ "$#" -ge 3 ] || { usage >&2; exit 2; }
    serial_option="$2"
    shift 2
fi
[ "$#" -eq 1 ] || { usage >&2; exit 2; }

for command_name in adb awk grep mapfile mktemp sha256sum sort stat tr unzip; do
    require_command "$command_name"
done

xapk_path="$1"
[ -f "$xapk_path" ] || die "XAPK not found: $xapk_path"

printf 'Verifying pinned original TW XAPK...\n'
verify_file "XAPK" "$xapk_path" "$EXPECTED_XAPK_SIZE" "$EXPECTED_XAPK_SHA256"

tmp_root="${TMPDIR:-${PREFIX:-/data/data/com.termux/files/usr}/tmp}"
mkdir -p "$tmp_root"
work_dir="$(mktemp -d "$tmp_root/magia-exedra-tw.XXXXXX")"
trap 'rm -rf -- "$work_dir"' EXIT HUP INT TERM

mapfile -t apk_entries < <(unzip -Z1 "$xapk_path" | awk 'tolower($0) ~ /\.apk$/ {print}')
[ "${#apk_entries[@]}" -eq 3 ] || die "XAPK must contain exactly three APK entries"

for entry in "${apk_entries[@]}"; do
    case "$entry" in
        /*|*../*|../*|*\\*) die "unsafe APK entry name: $entry" ;;
    esac
done

index=0
for entry in "${apk_entries[@]}"; do
    index=$((index + 1))
    candidate="$work_dir/candidate-$index.apk"
    unzip -p "$xapk_path" "$entry" > "$candidate" || die "failed to extract APK entry: $entry"
    digest="$(sha256_file "$candidate")"
    case "$digest" in
        "$EXPECTED_BASE_SHA256")
            destination="$work_dir/base.apk"
            expected_size="$EXPECTED_BASE_SIZE"
            label="base.apk"
            ;;
        "$EXPECTED_ASSETS_SHA256")
            destination="$work_dir/split_base_assets.apk"
            expected_size="$EXPECTED_ASSETS_SIZE"
            label="split_base_assets.apk"
            ;;
        "$EXPECTED_ARM64_SHA256")
            destination="$work_dir/split_config.arm64_v8a.apk"
            expected_size="$EXPECTED_ARM64_SIZE"
            label="split_config.arm64_v8a.apk"
            ;;
        *) die "unrecognized split SHA-256 for entry: $entry" ;;
    esac
    [ ! -e "$destination" ] || die "duplicate split in XAPK: $label"
    mv "$candidate" "$destination"
    verify_file "$label" "$destination" "$expected_size" "$digest"
done

for split_path in \
    "$work_dir/base.apk" \
    "$work_dir/split_base_assets.apk" \
    "$work_dir/split_config.arm64_v8a.apk"; do
    [ -f "$split_path" ] || die "required split was not recovered: $split_path"
done

serial="$(choose_wireless_serial "$serial_option")"
printf 'Wireless ADB endpoint: %s\n' "$serial"
[ "$(adb -s "$serial" get-state | tr -d '\r')" = "device" ] || die "ADB endpoint is not ready"

sdk="$(adb -s "$serial" shell getprop ro.build.version.sdk | tr -d '\r[:space:]')"
case "$sdk" in
    ''|*[!0-9]*) die "could not read Android SDK level" ;;
esac
[ "$sdk" -ge 30 ] || die "Android 11/API 30 or newer is required; device reports API $sdk"

printf 'Installing original split set on Android API %s...\n' "$sdk"
if ! install_output="$(adb -s "$serial" install-multiple -r -i "$INSTALLER_PACKAGE" \
    "$work_dir/base.apk" \
    "$work_dir/split_base_assets.apk" \
    "$work_dir/split_config.arm64_v8a.apk" 2>&1)"; then
    printf '%s\n' "$install_output" >&2
    die "adb install-multiple failed"
fi
printf '%s\n' "$install_output"
printf '%s\n' "$install_output" | grep -qi 'success' || die "package installer did not report Success"

# Installation must finish with the game stopped. The script deliberately has
# no launch invocation; the user remains in control of the first start.
adb -s "$serial" shell am force-stop "$PACKAGE_NAME"

package_paths="$(adb -s "$serial" shell pm path "$PACKAGE_NAME" | tr -d '\r')"
for expected_leaf in base.apk split_base_assets.apk split_config.arm64_v8a.apk; do
    printf '%s\n' "$package_paths" | grep -q "/$expected_leaf$" || \
        die "installed split verification failed: $expected_leaf"
done

package_dump="$(adb -s "$serial" shell dumpsys package "$PACKAGE_NAME" | tr -d '\r')"
printf '%s\n' "$package_dump" | grep -q "versionName=$EXPECTED_VERSION_NAME" || \
    die "installed versionName verification failed"
printf '%s\n' "$package_dump" | grep -q "versionCode=$EXPECTED_VERSION_CODE" || \
    die "installed versionCode verification failed"
printf '%s\n' "$package_dump" | grep -q "installerPackageName=$INSTALLER_PACKAGE" || \
    die "installerPackageName verification failed"

printf '\nSUCCESS: original TW %s (%s) is installed and remains stopped.\n' \
    "$EXPECTED_VERSION_NAME" "$EXPECTED_VERSION_CODE"
printf 'Launch it manually only after this script exits.\n'
