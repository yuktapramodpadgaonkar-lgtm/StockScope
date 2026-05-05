"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

function ChatBubbleIcon({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={1.75}
      stroke="currentColor"
      className={className}
      aria-hidden
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337L5.454 21l1.395-3.72C5.452 15.909 5 13.973 5 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z"
      />
    </svg>
  );
}

/** Global entry to `/chatbot`. Hidden on the chatbot route to avoid a duplicate control. */
export function FloatingChatButton() {
  const pathname = usePathname();
  if (pathname === "/chatbot" || pathname.startsWith("/chatbot/")) {
    return null;
  }

  return (
    <Link
      href="/chatbot"
      aria-label="Open chatbot"
      title="Open chatbot"
      className="fixed bottom-6 left-6 z-50 flex h-14 w-14 cursor-pointer items-center justify-center rounded-full bg-teal-700 text-white shadow-lg transition duration-200 ease-out hover:scale-105 hover:bg-teal-800 focus-visible:outline focus-visible:ring-2 focus-visible:ring-teal-400 focus-visible:ring-offset-2 dark:bg-teal-600 dark:text-white dark:hover:bg-teal-500 dark:focus-visible:ring-teal-300"
    >
      <ChatBubbleIcon className="h-7 w-7 shrink-0" />
    </Link>
  );
}
