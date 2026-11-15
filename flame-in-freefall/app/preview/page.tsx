import DetailPanel from "@/components/DetailPanel";
import { environments, investigations } from "@/lib/data";

export default function Preview() {
  const env = environments[0];
  const item = investigations.find((i) => i.id === "PSI-25") ?? investigations[0];

  return (
    <main className="mx-auto max-w-[420px] p-6">
      <DetailPanel item={item} env={env.id} envInfo={env} />
    </main>
  );
}
