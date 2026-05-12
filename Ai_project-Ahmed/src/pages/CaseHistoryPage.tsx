import { Layout } from "@/components/Layout";
import { RecentCasesTable } from "@/components/RecentCasesTable";
import { MOCK_CASES } from "@/lib/mockApi";
import { Input } from "@/components/ui/input";
import { Search } from "lucide-react";

export function CaseHistoryPage() {
  return (
    <Layout title="Case History" subtitle="All analyses across patients and axes.">
      <div className="relative max-w-md mb-5">
        <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
        <Input className="pl-9" placeholder="Search by case ID, patient or axis…" />
      </div>
      <RecentCasesTable cases={MOCK_CASES} />
    </Layout>
  );
}
