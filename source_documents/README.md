# Source Documents

The source PDFs used by the current draft benchmark are included in:

```text
source_documents/raw/BaselFramework.pdf
source_documents/raw/Commercial Bank Examination.pdf
source_documents/raw/COMPS-260-Consumer-Credit-Protection-Act.pdf
```

## Documents Used

### Basel Framework

- Publisher: Bank for International Settlements / Basel Committee on Banking Supervision
- Official PDF URL: https://www.bis.org/baselframework/BaselFramework.pdf
- Repository path: `source_documents/raw/BaselFramework.pdf`
- SHA-256:
  `5b0f53b9462357796f0233152bb57676e0c154f767ae4ad0ba5eae95fc410cd6`

### Consumer Credit Protection Act

- Publisher: U.S. Government Publishing Office / GovInfo
- Official details page: https://www.govinfo.gov/app/details/COMPS-260/
- Official PDF URL: https://www.govinfo.gov/content/pkg/COMPS-260/pdf/COMPS-260.pdf
- Repository path: `source_documents/raw/COMPS-260-Consumer-Credit-Protection-Act.pdf`
- SHA-256:
  `8296d0e3d04ff48e43d72f8cbf0032da6f341ad6c86bcaf2d5c2a5ab49ba84b1`

### Federal Reserve Commercial Bank Examination Manual

- Publisher: Board of Governors of the Federal Reserve System
- Official manual page: https://www.federalreserve.gov/supervisionreg/supmanual.htm
- Official PDF URL: https://www.federalreserve.gov/publications/files/cbem.pdf
- Repository path: `source_documents/raw/Commercial Bank Examination.pdf`
- Download date recorded for this draft: 2026-05-06
- SHA-256:
  `a8d39072197561cc6014961b4e98569186c89fc292923592c9e2a024d2cd9d97`

## Verify Checksums

Run:

```bash
shasum -a 256 source_documents/raw/*.pdf
```

The hashes should match the values above. If a source publisher updates a PDF,
record the new download date and hash before regenerating the benchmark.
