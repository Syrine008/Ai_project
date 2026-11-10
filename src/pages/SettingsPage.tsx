import { Layout } from "@/components/Layout";
import { Card } from "@/components/ui/card";
import { ThemeToggle } from "@/components/ThemeToggle";
export function SettingsPage() {
  return (
    <Layout title="Workspace settings" subtitle="Display preferences and data handling.">
      <div className="max-w-3xl space-y-5">
        <Card className="p-6 flex justify-between items-center">
          <div>
            <h2 className="font-semibold">Appearance</h2>
            <p className="text-sm text-muted-foreground mt-1">
              Switch between light and dark display.
            </p>
          </div>
          <ThemeToggle />
        </Card>
        <Card className="p-6 space-y-3">
          <h2 className="font-semibold">Saved reports</h2>
          <p className="text-sm text-muted-foreground">
            Reports you save are stored in this browser. They are not synchronized across devices.
            Export a report before clearing browser data. Removing a browser report does not delete
            a server record.
          </p>
          <p className="text-sm text-muted-foreground">
            Use de-identified case references. This research workspace is not an electronic medical
            record system.
          </p>
        </Card>
        <Card className="p-6 space-y-3">
          <h2 className="font-semibold">Analysis service</h2>
          <p className="text-sm text-muted-foreground">
            The analysis service and model files are managed by your workspace administrator.
            Missing services produce an error; the interface never substitutes generated findings.
          </p>
        </Card>
      </div>
    </Layout>
  );
}
