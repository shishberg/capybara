//! Puts `memory.x` where the linker finds it, and names the link scripts.

use std::path::PathBuf;
use std::{env, fs};

fn main() {
    let out = PathBuf::from(env::var_os("OUT_DIR").unwrap());
    fs::copy("memory.x", out.join("memory.x")).unwrap();
    println!("cargo:rustc-link-search={}", out.display());
    println!("cargo:rerun-if-changed=memory.x");

    // memory.x's regions don't start on a 64 KiB boundary.
    println!("cargo:rustc-link-arg=--nmagic");
    println!("cargo:rustc-link-arg=-Tlink.x");
    println!("cargo:rustc-link-arg=-Tlink-rp.x");
    println!("cargo:rustc-link-arg=-Tdefmt.x");
}
