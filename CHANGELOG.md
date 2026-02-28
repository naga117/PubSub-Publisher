# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog and this project follows Semantic Versioning.

## [1.0.1] - 2026-02-28

### Added
- Visible app version in Settings and Help -> About dialog.
- Native macOS menu bar sections for File, Edit, View, Window, and Help.

### Changed
- Reused Pub/Sub publisher clients to reduce per-message overhead.
- Improved bulk publish throughput by batching in-flight publish futures.
- Debounced project change handling to reduce repeated sync calls and config writes.

### Fixed
- Fixed bundled macOS app startup failure caused by relative import resolution.

