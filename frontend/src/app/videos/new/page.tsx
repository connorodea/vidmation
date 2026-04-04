import { CreateForm } from "@/components/videos/create-form";

export default function NewVideoPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[calc(100vh-8rem)]">
      <div className="w-full max-w-2xl">
        <div className="text-center mb-10">
          <h1 className="text-[32px] font-semibold text-[#ececec] mb-2">
            Create a video
          </h1>
          <p className="text-sm text-[#666]">
            Describe your topic and we will generate a complete video.
          </p>
        </div>

        <CreateForm />
      </div>
    </div>
  );
}
