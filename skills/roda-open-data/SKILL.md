---
name: roda-open-data
description: >
  Search, filter, and inspect public datasets in the Registry of Open Data on AWS (RODA),
  including life-sciences, genomics, imaging, and health collections, and preview what is
  inside a public S3 bucket. Use when the user wants to find open or public data hosted on
  AWS, compare dataset licenses and access modes, or get the exact `aws s3` command to pull
  data. Triggers include "Registry of Open Data", "RODA", "AWS Open Data", "open data on AWS",
  "public dataset", "public S3 bucket", "registry.opendata.aws", "aws-pds", "requester pays",
  "no-sign-request", "STAC catalog", "1000 Genomes", "gnomAD on AWS", "Imaging Data Commons",
  "TCGA on AWS", "find a dataset", "dataset license"
usage: Invoke when the user needs to discover, vet, or access datasets from the Registry of Open Data on AWS.
version: 1.0.0
validated_against:
  date: 2026-11-10
  packages: {python: "3.9+", roda-index: "registry.opendata.aws/index.ndjson (1,497 datasets, 23 deprecated)"}
tags:
  - skill
  - category:pipeline
  - data-discovery
  - aws-open-data
  - hcls
---

# Registry of Open Data on AWS (RODA)

Searches the public RODA index with the bundled `scripts/roda.py` (stdlib only, no AWS credentials). Replicates the main features of the awslabs `roda-mcp-server`; if that MCP server is available, prefer it and use this skill as the fallback.

## When to Use

- The user asks what public/open data exists on AWS for a topic, publisher, tag, or license
- The user has a dataset name or slug and needs buckets, regions, access mode, or a CLI command
- The user wants to peek inside a public bucket or find similar datasets or STAC catalogs

Not for: querying data contents (use Athena/pandas after access is sorted), or non-AWS repositories (SRA, GEO, ClinicalTrials.gov directly).

## Setup

The index is ~14 MB NDJSON, about 1,500 datasets. Download it once; every command below reads the cached copy.

```bash
python scripts/roda.py download        # saves to ~/.cache/roda-open-data/index.ndjson (or $RODA_INDEX)
python scripts/roda.py stats           # sanity check: total_datasets should be > 1,000
```

If the sandbox has no outbound internet, download `https://registry.opendata.aws/index.ndjson` with the platform's download tool and point at it with `--index PATH` or `RODA_INDEX`. Do not hand-write bucket names or CLI commands from memory; always derive them from `details`.

## Command Selection

Global flags (`--index`, `--json`, `--include-deprecated`) go BEFORE the subcommand.

| User intent | Command |
|---|---|
| Free-text topic search | `search "single cell" --tags genomic --limit 10` |
| Browse by tag | `tags --min-count 8` then `list --tag "medical imaging"` |
| One dataset in depth | `--json details <slug>` (adds `access[]`: bucket, prefix, region, `cli`, `public`) |
| By publisher | `org NOAA` (substring on ManagedBy) |
| By license | `license "creative commons"` (only: creative commons, mit, apache, public domain) |
| Similar datasets | `related <slug> --limit 5` (ranked by shared tags) |
| Registry overview | `stats` |
| STAC APIs | `stac --query landsat` |
| Peek in a bucket | `preview <slug> [--prefix sub/dir/]` |

Useful HCLS tags (exact match): `life sciences`, `genomic`, `whole genome sequencing`, `vcf`, `fastq`, `single-cell transcriptomics`, `gene expression`, `medical imaging`, `histopathology`, `cancer`, `neuroimaging`, `structural biology`, `microbiome`, `covid-19`, `health`.

## Procedure

1. Confirm the index exists (`stats`). If not found, run `download`.
2. Classify the request:
   ```
   Has a dataset slug or exact name?
   ├─ Yes → details <slug>   (if the name is not a slug, search first, then details)
   └─ No → Has a publisher or license constraint only?
      ├─ Yes → org / license
      └─ No → search with --tags when the domain maps to a tag above
   ```
3. For `search`, pass 2-4 specific keywords. Stop words are stripped; a single broad word ("genomics") returns 100+ hits.
4. If `total_count` > 10, show the top 10 and ask ONE narrowing question (modality, organism, license, or region). Vary the question; do not repeat it.
5. For zero results: drop filters, then try a synonym, then run `tags` and suggest 3 close tags.
6. For each dataset you present, run `details` before giving access instructions.
7. Read `access[]` per resource and branch:
   - `public: true` → anonymous access works; give `cli` (`--no-sign-request`) and offer `preview`
   - `requester_pays: true` → caller needs AWS credentials and pays transfer/request costs; `cli` already has `--request-payer requester`
   - `controlled_access` set → data-use approval (e.g., dbGaP, NIH DAR) required first; do NOT preview; quote the access note
   - `account_required: true` → an AWS account (and sometimes registration) is needed; do NOT preview
8. For `preview`, only public resources are listed (max 10 keys, alphabetical, not by date). If a dataset has several public buckets, ask which one (`--resource-index N`).
9. A 403 on preview means the bucket is not anonymously listable. Fall back to the `cli` command and the dataset's Documentation link.
10. Check `UpdateFrequency` and `Deprecated`. Deprecated datasets are hidden by default; use `--include-deprecated` only when asked, and flag the `DeprecatedNotice`.
11. For human-subject data (`controlled_access`, or tags such as `health`, `cancer`, `genomic` with an NIH/GDS license), state that use may be restricted by a data-use agreement even when the bucket is readable.
12. Present results using the Response Format below.

## Response Format

Respond with a numbered list. Each item has, in this order:

1. Name linked to `https://registry.opendata.aws/<slug>/`, with the slug in backticks
2. One-line description (shorten; do not paste the whole abstract)
3. Managed by
4. License, **copied exactly as written** (never paraphrase or normalize)
5. Access: public / requester-pays / controlled / account-required, with region
6. For `details` requests: bucket(s), the `cli` command, Documentation link, and tutorials from `DataAtWork`

When `total_count` exceeds the number shown, write "Showing N of M." The decision logic in Procedure is for internal reasoning only; do not narrate it. Present the findings and any single follow-up question.

## Worked Example

Request: "Find open whole-genome sequencing data on AWS that I can use without credentials."

```bash
python scripts/roda.py search "whole genome" --tags "whole genome sequencing" --limit 5
python scripts/roda.py --json details 1000-genomes
python scripts/roda.py preview 1000-genomes
```

Expected output shape: `1000-genomes` is managed by National Institutes of Health, update frequency "Not updated", bucket `1000genomes` in `us-east-1`, public, with
`aws s3 ls s3://1000genomes/ --no-sign-request --region us-east-1`. The preview shows a top-level prefix such as `1000G_2504_high_coverage/`. Contrast with NIH Genomic Data Sharing datasets (e.g., `nciccr-dlbcl`), which carry a data-access policy in the License field; flag that to the user.

## Common Mistakes

- **Wrong:** Putting `--json` after the subcommand (`details x --json`). **Right:** `--json details x`; global flags precede the subcommand.
- **Wrong:** Summarizing a license as "open" or "CC-BY". **Right:** Quote the License string verbatim; many HCLS entries say "NIH Genomic Data Sharing Policy" or link to terms, and the text format varies.
- **Wrong:** Assuming a readable bucket means unrestricted use. **Right:** Check License and `controlled_access`; readable does not mean permitted.
- **Wrong:** Giving `aws s3 ls` without `--no-sign-request` for a public bucket (fails with no credentials). **Right:** Use the generated `cli`.
- **Wrong:** Dropping `--request-payer requester` for requester-pays resources. **Right:** Use the `cli` field; warn the user they pay for transfer.
- **Wrong:** Previewing controlled-access or account-required resources. **Right:** Skip `preview`; give access notes.
- **Wrong:** Treating the preview as the newest data. **Right:** S3 lists keys alphabetically; use `last_modified` and `UpdateFrequency`.
- **Wrong:** Treating `ManagedBy` as plain text when filtering. **Right:** It is a markdown link in the raw index; `org` does substring matching, and `summary` extracts the name.
- **Wrong:** `license "cc-by"`, `"gpl"`, or `search ... --license-type cc0`. **Right:** Only `creative commons`, `mit`, `apache`, `public domain` are supported (both `license` and `search --license-type` reject others with a hint); for others, `search` without the filter and read the License field.
- **Wrong:** Searching one broad word and listing 100 results. **Right:** Add tags/keywords, or ask one narrowing question.
- **Wrong:** Passing a dataset title to `details`. **Right:** It needs the slug; `search` first.
- **Wrong:** Fetching the index inside a no-internet sandbox with `requests`. **Right:** Use the platform's download tool, then `--index`.
- **Wrong:** Reusing a stale index across long sessions. **Right:** Re-run `download` if the file is weeks old; the registry changes daily.

## Reference

- Registry: https://registry.opendata.aws/ ; index: https://registry.opendata.aws/index.ndjson
- Index fields: `Name`, `Slug`, `Description`, `Documentation`, `ManagedBy`, `UpdateFrequency`, `Tags`, `License`, `Resources[]` (`Type`, `ARN`, `Region`, `RequesterPays`, `ControlledAccess`, `AccountRequired`, `Explore`), `DataAtWork`, `Citation`, `Deprecated`
- Source of dataset docs: https://github.com/awslabs/open-data-docs
