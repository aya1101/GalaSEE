
import { ExplorerShell } from "@/components/explorer/ExplorerShell";

const DEFAULT_REGION = "can-gio";

function normalizeExplorerRegion(value: string | string[] | undefined) {
  const region = Array.isArray(value) ? value[0] : value;
  return region?.trim().toLowerCase() || DEFAULT_REGION;
}

export default async function ExplorerPage({
  searchParams,
}: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const params = await searchParams;
  return <ExplorerShell region={normalizeExplorerRegion(params.region)} />;
}
