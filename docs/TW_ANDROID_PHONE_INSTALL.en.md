# Install the original TW XAPK entirely on one Android 11+ phone

This guide provides two computer-free routes that do not require a Taiwan-region
Google account. Both install the same unmodified, originally signed TW 1.1.2
three-split XAPK and set Android's installer package name to
`com.android.vending`.

- **Recommended GUI:** Shizuku plus the open-source Install with Options app.
- **Hash-enforcing script:** Termux, Wireless debugging, `android-tools`, and
  `mobile/install_tw_termux.sh`.

Android 11/API 30 or newer is required for the built-in on-device Wireless
debugging flow. On Android 10 and older, use computer-assisted ADB or the
Windows/MuMu wizard in this repository.

## Download and trust pins

Original XAPK:

<https://github.com/HiiragiNemu/MagiaExedraTWTools/releases/download/v1.1.2/tw.sonet.magiaexedra-1.1.2-26072717.xapk>

```text
Size: 769197299 bytes
SHA-256: 664dfbc307c5f6b640d01b1fc661de02fa30fc382a68426530abc657dc9e2d14
```

The three split pins are in
[`mobile/SHA256SUMS-tw-1.1.2.txt`](../mobile/SHA256SUMS-tw-1.1.2.txt).
A future client needs a newly verified XAPK and split set; never apply these
1.1.2 constants to another version.

Keep about 2.5 GiB free for the XAPK, extracted splits, and package-manager
staging. `-r` preserves app data during an update. The phone script does not
back up the previous APKs and is not an application-data backup tool.

## Route A: Shizuku + Install with Options (recommended GUI)

1. Install Shizuku from its [official download page](https://shizuku.rikka.app/download/).
2. Install the official Release of the open-source
   [zacharee/InstallWithOptions](https://github.com/zacharee/InstallWithOptions).
3. Enable Developer options and Wireless debugging. In Shizuku, choose the
   Wireless debugging start method and follow Android's pairing prompt. Shizuku
   normally needs to be started again after a phone reboot.
4. **Verify the XAPK first.** The GUI does not enforce this repository's hash.
   With Termux, run:

   ```text
   sha256sum ~/storage/downloads/tw.sonet.magiaexedra-1.1.2-26072717.xapk
   ```

   It must match the complete value above. A trusted local SHA-256 utility is
   another option.
5. Treat `.xapk` as a ZIP and extract it. Confirm that it contains exactly three
   APKs. Their hashes should match the three values in the repository manifest;
   archive filenames may differ from the manifest's normalized role names, so
   use hashes as the identity.
6. Open Install with Options, grant its Shizuku permission, select **all three
   APKs together**, and use split-APK installation.
7. Set **Installer package name** to:

   ```text
   com.android.vending
   ```

8. Leave unrelated options such as Disable Verification, Allow Downgrade, and
   Bypass Low Target SDK off. This client does not need signature verification
   disabled, and that option cannot make mismatched update signatures valid.
9. Install, but do not tap Open. Confirm from App info that the game remains
   stopped, then launch it manually.

Install with Options uses Shizuku shell permissions and supports split APKs.
Android 14+ restricts the shell from setting the originating package but still
allows the installer-package field; this workflow relies only on the latter.

## Route B: audited Termux installer

### 1. Prepare official Termux

Install Termux through an official channel linked by
[termux.dev](https://termux.dev/en/), not an unknown repack. Run:

```text
pkg update
pkg install android-tools coreutils unzip
termux-setup-storage
```

Grant shared-storage access, download and extract the latest tools Release from
this repository, and enter the tool root that contains `mobile/`.

### 2. Pair local Wireless ADB

Open Developer options → Wireless debugging → Pair device with pairing code.
The pairing and connection addresses use different temporary ports; use exactly
what Android displays:

```text
adb pair PHONE_IP:PAIR_PORT
adb connect PHONE_IP:DEBUG_PORT
adb devices
```

Enter the one-time pairing code. Split-screen Settings and Termux is convenient.
`adb devices` should show one local `HOST:PORT device`. With multiple endpoints,
the script requires an explicit selection rather than guessing.

### 3. Install

```text
bash mobile/install_tw_termux.sh ~/storage/downloads/tw.sonet.magiaexedra-1.1.2-26072717.xapk
```

The script:

1. enforces the complete 769197299-byte XAPK and SHA-256;
2. extracts exactly three APK entries and identifies base, assets, and arm64 by
   their independently pinned hashes;
3. auto-selects the sole connected local Wireless ADB endpoint;
4. requires Android 11/API 30 or newer;
5. runs `adb install-multiple -r -i com.android.vending` with all three splits;
6. verifies version `1.1.2 (26072717)`, installed paths, and installer package;
7. force-stops the package and never launches it.

When several wireless endpoints are ready:

```text
bash mobile/install_tw_termux.sh --serial PHONE_IP:DEBUG_PORT /path/to/original.xapk
```

`TW_ADB_SERIAL` is also supported.

## Troubleshooting

- **No Wireless debugging:** the OS is older than Android 11 or the vendor has
  removed it. Use computer-assisted ADB or the MuMu route.
- **Pairing succeeds but devices is empty:** the pairing port is not the
  connection port. Return to the Wireless debugging main page and run
  `adb connect` with its displayed IP address and port.
- **INSTALL_FAILED_USER_RESTRICTED:** some Android skins also require Install via
  USB or USB debugging (Security settings), and managed/guest profiles may block
  installs.
- **INSTALL_FAILED_UPDATE_INCOMPATIBLE:** the installed app has another
  signature. Do not uninstall valuable data merely to experiment; first verify
  that the previous client uses the same official signature.
- **Hash mismatch:** stop and redownload the complete Release XAPK. Never mix
  split APKs from different versions.
- **Network error after installation:** DNS, proxy, exit routing, server state,
  and account login are independent of installer attribution.

This workflow does not create a Play purchase record, patch or re-sign the APK,
modify game code, or intercept a license response.
