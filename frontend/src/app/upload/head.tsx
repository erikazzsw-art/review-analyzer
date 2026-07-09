import type { ReactElement } from "react";

export default function Head(): ReactElement {
  return (
    <>
      <title>Upload Reviews</title>
      <meta
        name="description"
        content="Upload review batches, create analysis jobs, and continue into the workspace."
      />
      <meta name="robots" content="noindex, nofollow" />
      <meta property="og:title" content="Upload Reviews" />
      <meta
        property="og:description"
        content="Upload review batches, create analysis jobs, and continue into the workspace."
      />
      <meta property="og:type" content="website" />
    </>
  );
}
