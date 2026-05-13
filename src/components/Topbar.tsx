import { Search, Bell, HelpCircle } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "./ThemeToggle";

export function Topbar({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <header className="h-16 border-b bg-card/60 backdrop-blur sticky top-0 z-30">
      <div className="h-full px-6 flex items-center gap-4">
        <div className="min-w-0">
          <h1 className="text-base font-semibold tracking-tight truncate">{title}</h1>
          {subtitle && (
            <p className="text-xs text-muted-foreground truncate">{subtitle}</p>
          )}
        </div>
        <div className="ml-auto flex items-center gap-2">
          <div className="relative hidden md:block">
            <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search cases, patients…"
              className="pl-9 w-72 bg-background"
            />
          </div>
          <Button variant="ghost" size="icon" aria-label="Help">
            <HelpCircle className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon" aria-label="Notifications">
            <Bell className="h-4 w-4" />
          </Button>
          <ThemeToggle />
          <div className="h-9 w-9 rounded-full bg-gradient-hero text-white grid place-items-center text-xs font-semibold">
            DR
          </div>
        </div>
      </div>
    </header>
  );
}
