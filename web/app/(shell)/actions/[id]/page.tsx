import { ActionPage } from "@/features/guard";

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ActionPage id={id} />;
}
