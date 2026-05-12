import { Layout } from "@/components/Layout";
import { Card } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/ThemeToggle";
import { AXES } from "@/lib/axes";

export function SettingsPage() {
  return (
    <Layout title="Settings" subtitle="Workspace, models and preferences.">
      <div className="grid lg:grid-cols-3 gap-6">
        <Card className="p-6 lg:col-span-2 space-y-5">
          <div>
            <h3 className="font-semibold">Workspace</h3>
            <p className="text-xs text-muted-foreground">Identity used on exported reports.</p>
          </div>
          <div className="grid sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label className="text-xs">Clinician name</Label>
              <Input defaultValue="Dr. Reza" />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Institution</Label>
              <Input defaultValue="Neurology Research Lab" />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Email</Label>
              <Input defaultValue="reza@brain.lab" />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Default report language</Label>
              <Input defaultValue="English" />
            </div>
          </div>
          <Button className="w-fit">Save changes</Button>
        </Card>

        <Card className="p-6 space-y-5">
          <div>
            <h3 className="font-semibold">Preferences</h3>
            <p className="text-xs text-muted-foreground">Visual and demo settings.</p>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium">Theme</div>
              <div className="text-xs text-muted-foreground">Light or dark mode</div>
            </div>
            <ThemeToggle />
          </div>
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium">Demo mode</div>
              <div className="text-xs text-muted-foreground">Use mock results</div>
            </div>
            <Switch defaultChecked />
          </div>
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium">Verbose explainability</div>
              <div className="text-xs text-muted-foreground">Show all region contributions</div>
            </div>
            <Switch />
          </div>
        </Card>

        <Card className="p-6 lg:col-span-3">
          <h3 className="font-semibold">API endpoints (Django backend)</h3>
          <p className="text-xs text-muted-foreground">
            These are placeholders — colleagues working on each axis can wire them in their own Django app.
          </p>
          <div className="mt-4 grid md:grid-cols-2 gap-2.5">
            {AXES.map((a) => (
              <div key={a.id} className="flex items-center gap-3 rounded-lg border bg-card p-3">
                <a.icon className="h-4 w-4 text-bluegray" />
                <div className="min-w-0">
                  <div className="text-sm font-medium truncate">{a.title}</div>
                  <div className="text-[11px] font-mono text-muted-foreground truncate">
                    POST {a.endpoint}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </Layout>
  );
}
