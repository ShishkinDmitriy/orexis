//! THE TREE, said once as a path with no `..` in it: the root every crate of the agent sits in.
fn main() {
    let kernel = std::path::PathBuf::from(std::env::var("CARGO_MANIFEST_DIR").expect("cargo says where the kernel is"));
    let tree = kernel.parent().expect("the kernel sits in the tree");
    println!("cargo:rustc-env=OREXIS_CRATES={}", tree.display());
    println!("cargo:rerun-if-changed=build.rs");
}
