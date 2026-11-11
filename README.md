# Eloquence Rust host

A 32-bit Rust host for an independently supplied Eloquence ECI engine. It
replaces a 32-bit Python host process; it contains no engine DLL, voice data,
or dictionaries. The host runs inside Windows' 32-bit Rundll32 process so that
a 64-bit NVDA add-on can use a 32-bit ECI.DLL. Derived from Eloquence64RS commit
`b1132129fb50c2957b5396b881f9b8dccec6eb0e`; GPL-2.0-only.

The binary protocol differs from the Python host's pickle protocol and the
in-process OpenEVV ECI ABI. Eloquence64 needs a client adapter for this backend.
OpenEVV and Reloq-C remain separate backends.

## Build and launch

Install Rust's `i686-pc-windows-msvc` target and run on Windows:

```powershell
$env:RUSTFLAGS = '-C target-feature=+crt-static'
cargo build --release --target i686-pc-windows-msvc
```

The result is `target/i686-pc-windows-msvc/release/eloquence_native_host.dll`.
Run 32-bit Rundll32 with an absolute DLL path and the **base** entry point
`EloquenceHost` (Windows resolves `EloquenceHostW`):

```text
<32-bit system rundll32.exe> <absolute DLL path>,EloquenceHost --auth-key <32 hex digits>
```

Redirect stdin and stdout to separate pipes. Generate a fresh random 16-byte
key for each process. The first frame must be Hello with that key.
`python/launcher.py` demonstrates the launch and authentication. Run it off the
UI thread with a timeout; own the process and arrange for it to be killed if
NVDA exits unexpectedly. EOF on stdin ends the host.

## Python client interface

`python/eloquence_native.py` supplies `NativeHostConnection`, an adapter for
Eloquence64's command/response/event shape. The launcher returns `(process,
connection)`. A dedicated receiver thread must continuously call
`connection.recv()`: responses carry the request `id`; audio, index,
completion and error events arrive asynchronously. Use unique nonzero IDs.

Send `{"type": "command", "id": id, "command": name, "payload": {...}}`
with `connection.send(...)`. Available commands and payloads:

| Command | Payload |
| --- | --- |
| `initialize` | `eciPath`, `dataDirectory`, `language`, `languageId`; optional `dictionaryDirectory`, `enableAbbreviationDict`, `enablePhrasePrediction`, `voiceVariant`, `sampleRate` (11025 or 16000) |
| `addText` | `text`: ECI-encoded bytes |
| `insertIndex` | `value`: unsigned index |
| `synthesize`, `stop`, `delete` | empty |
| `setParam`, `setVoiceParam` | `paramId`, `value` |
| `copyVoice` | `variant` |
| `setDictionaryDirectory` | `directory`, `reload` |

Before a new utterance call `prepare_generation()`, enqueue text and indexes,
then synthesize. The adapter suppresses events from cancelled generations.
Audio events contain `payload.data` as mono signed 16-bit little-endian PCM;
index and final events have empty data and `index` or `final` fields. Apply
audio contours in the caller. Responses can include parameter and voice
parameter maps, or an `error`. Send `delete`, wait for its response and process
exit, then close the connection. Consult the adapter for the exact encoding.

The adapter and launcher are integration building blocks, not a drop-in
replacement for Eloquence64's existing host client: integrate its receiver,
timeouts, lifecycle, and job-object handling with the add-on.

## Tests

`cargo test --target i686-pc-windows-msvc` runs host tests. The real-engine
test is skipped unless `ELOQUENCE_ECI_PATH` points to an independently supplied
32-bit ECI.DLL and its accompanying files. To test DLL launch, also set
`ELOQUENCE_HOST_DLL` to the absolute path of a built DLL, then run
`cargo test --target i686-pc-windows-msvc --test host_process`. It exercises
authentication, initialization, PCM synthesis, indexes and shutdown.
Do not commit proprietary engine files.
