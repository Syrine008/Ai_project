import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export interface PatientMeta {
  id: string;
  age: string;
  sex: string;
  notes: string;
  /** If set, “Send analysis to patient” is offered after a successful run (requires API + SMTP). */
  email: string;
}

export function MetadataForm({
  value,
  onChange,
}: {
  value: PatientMeta;
  onChange: (v: PatientMeta) => void;
}) {
  const upd = (patch: Partial<PatientMeta>) => onChange({ ...value, ...patch });
  return (
    <div className="grid grid-cols-2 gap-4">
      <div className="space-y-1.5">
        <Label htmlFor="pid" className="text-xs">Patient ID</Label>
        <Input
          id="pid"
          placeholder="P-00000"
          value={value.id}
          onChange={(e) => upd({ id: e.target.value })}
        />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="age" className="text-xs">Age</Label>
        <Input
          id="age"
          type="number"
          placeholder="0"
          value={value.age}
          onChange={(e) => upd({ age: e.target.value })}
        />
      </div>
      <div className="space-y-1.5 col-span-2 sm:col-span-1">
        <Label className="text-xs">Sex</Label>
        <Select value={value.sex} onValueChange={(v) => upd({ sex: v })}>
          <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="F">Female</SelectItem>
            <SelectItem value="M">Male</SelectItem>
            <SelectItem value="Other">Other</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div className="space-y-1.5 col-span-2">
        <Label htmlFor="email" className="text-xs">Patient email (optional)</Label>
        <Input
          id="email"
          type="email"
          autoComplete="email"
          placeholder="patient@example.com — for sending a summary after analysis"
          value={value.email}
          onChange={(e) => upd({ email: e.target.value })}
        />
      </div>
      <div className="space-y-1.5 col-span-2">
        <Label htmlFor="notes" className="text-xs">Clinical notes (optional)</Label>
        <Textarea
          id="notes"
          rows={3}
          placeholder="Symptoms, onset, comorbidities…"
          value={value.notes}
          onChange={(e) => upd({ notes: e.target.value })}
        />
      </div>
    </div>
  );
}
