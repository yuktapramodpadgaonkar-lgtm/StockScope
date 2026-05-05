import type { ReactNode } from "react";

import { Card } from "@/components/ui/Card";

type SectionCardProps = {
  title: string;
  subtitle?: string;
  children: ReactNode;
  className?: string;
};

export function SectionCard({ title, subtitle, children, className = "" }: SectionCardProps) {
  return (
    <Card className={className}>
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-slate-900">{title}</h3>
        {subtitle ? <p className="mt-1 text-sm text-slate-600">{subtitle}</p> : null}
      </div>
      {children}
    </Card>
  );
}
