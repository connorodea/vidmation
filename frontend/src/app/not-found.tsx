import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-[#0d0d0d] px-6">
      <div className="text-center">
        <p className="text-sm font-medium text-[#666]">404</p>
        <h1 className="mt-3 text-2xl font-semibold text-[#ececec]">
          Page not found
        </h1>
        <p className="mt-2 text-sm text-[#999]">
          The page you are looking for does not exist or has been moved.
        </p>
        <Link
          href="/"
          className="mt-6 inline-flex items-center justify-center rounded-xl bg-[#10a37f] px-4 py-2.5 text-sm font-medium text-white transition-colors duration-150 hover:bg-[#1a7f64] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#10a37f] focus-visible:ring-offset-2 focus-visible:ring-offset-[#0d0d0d]"
        >
          Back to Dashboard
        </Link>
      </div>
    </div>
  );
}
