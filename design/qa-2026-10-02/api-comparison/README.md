# API reference cache metadata

Raw external research downloads were relocated on 2026-10-03 to the local cache `/private/tmp/polymarket-api-reference-cache-2026-10-03`. Their contents were preserved unchanged and SHA-256 checked. The temporary cache is local and may be cleared by the operating system.

The [original download index](download-index.json) remains unchanged. The [relocation manifest](cache-relocation-manifest.json) records paths, source URLs, sizes, hashes, and preservation evidence. [Schema source metadata](schema-source-metadata.json) records the canonical OpenAPI locations discovered from official documentation indexes; those two schemas had no entry in the original download index, so their original download provenance is explicitly marked incomplete.

For fresh official sources, use [Polymarket documentation](https://docs.polymarket.com/) and [Limitless documentation](https://docs.limitless.exchange/). Re-fetch references from the recorded source URLs into a local cache rather than committing complete third-party articles.

This relocation repairs repository link-check scope. It does not complete the separate API compatibility investigation or establish that cached schemas are current.
