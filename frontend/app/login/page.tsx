import { LoginCard } from "@/components/LoginCard";

export default function LoginPage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-950 to-slate-900">
      <div className="mx-auto max-w-lg px-4 py-8 sm:px-6 lg:px-8">
        <h1 className="text-2xl font-semibold tracking-tight text-gray-900">Login</h1>
        <p className="mt-1 text-sm text-gray-500">
          Mock sign-in for StockScope — OAuth and real sessions come later.
        </p>
        <div className="mt-8">
          <LoginCard />
        </div>
      </div>
    </div>
  );
}
