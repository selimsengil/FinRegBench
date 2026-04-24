# Source Documents

The source PDFs are not committed to this repository by default.

Create this local folder before rebuilding the benchmark:

```bash
mkdir -p source_documents/raw
```

Then download the source PDFs into:

```text
source_documents/raw/BaselFramework.pdf
source_documents/raw/COMPS-260-Consumer-Credit-Protection-Act.pdf
```

## Documents Used

### Basel Framework

- Publisher: Bank for International Settlements / Basel Committee on Banking Supervision
- Official PDF URL: https://www.bis.org/baselframework/BaselFramework.pdf
- Expected local path: `source_documents/raw/BaselFramework.pdf`
- SHA-256 observed in local draft build:
  `5b0f53b9462357796f0233152bb57676e0c154f767ae4ad0ba5eae95fc410cd6`

### Consumer Credit Protection Act

- Publisher: U.S. Government Publishing Office / GovInfo
- Official details page: https://www.govinfo.gov/app/details/COMPS-260/
- Official PDF URL: https://www.govinfo.gov/content/pkg/COMPS-260/pdf/COMPS-260.pdf
- Expected local path: `source_documents/raw/COMPS-260-Consumer-Credit-Protection-Act.pdf`
- SHA-256 observed in local draft build:
  `8296d0e3d04ff48e43d72f8cbf0032da6f341ad6c86bcaf2d5c2a5ab49ba84b1`

## Why PDFs Are Not Committed

Keeping source PDFs out of Git makes the benchmark repository smaller and avoids
redistributing documents whose publication terms may differ from the generated
benchmark files.

The benchmark rows preserve source metadata so experiments can be reproduced
after downloading the official documents.
