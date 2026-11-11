//! Rundll32 entry point for the existing authenticated stdio server.

use crate::protocol::AUTH_KEY_LEN;
use std::ffi::c_void;
use std::panic::{catch_unwind, AssertUnwindSafe};

#[no_mangle]
pub unsafe extern "system" fn EloquenceHostW(
    _window: *mut c_void,
    _instance: *mut c_void,
    command_line: *const u16,
    _show: i32,
) {
    let _ = catch_unwind(AssertUnwindSafe(|| {
        if command_line.is_null() {
            return;
        }
        let mut length = 0;
        while *command_line.add(length) != 0 && length < 1024 {
            length += 1;
        }
        if length == 1024 {
            return;
        }
        let line = String::from_utf16_lossy(std::slice::from_raw_parts(command_line, length));
        let mut arguments = line.split_whitespace();
        if arguments.next() != Some("--auth-key") {
            return;
        }
        let Some(encoded) = arguments.next() else {
            return;
        };
        if encoded.len() != AUTH_KEY_LEN * 2 || arguments.next().is_some() || !encoded.is_ascii() {
            return;
        }
        let mut key = [0; AUTH_KEY_LEN];
        for (index, byte) in key.iter_mut().enumerate() {
            let Ok(value) = u8::from_str_radix(&encoded[index * 2..index * 2 + 2], 16) else {
                return;
            };
            *byte = value;
        }
        let _ = crate::server::run(key, std::io::stdin(), std::io::stdout());
    }));
}
