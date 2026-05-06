import { LoginCard } from "@/components/LoginCard";

export default function LoginPage() {
  return (
    <div className="min-h-screen bg-gray-50 px-4 py-10 dark:bg-gray-950 sm:px-6 sm:py-16">
      <div className="mx-auto flex min-h-[calc(100vh-5rem)] w-full max-w-md flex-col items-center justify-center sm:min-h-[calc(100vh-8rem)]">
        <LoginCard />
      </div>
    </div>
  );
}
