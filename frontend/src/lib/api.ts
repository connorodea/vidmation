const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

class ApiClient {
  private baseUrl: string;
  private apiKey: string;

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
    this.apiKey = typeof window !== "undefined"
      ? localStorage.getItem("vidmation_api_key") || ""
      : "";
  }

  private async request<T>(
    path: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(this.apiKey ? { "X-API-Key": this.apiKey } : {}),
      ...(options.headers as Record<string, string>),
    };

    const res = await fetch(url, { ...options, headers });

    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(error.detail || `API error: ${res.status}`);
    }

    return res.json();
  }

  // Videos
  async getVideos(params?: Record<string, string>) {
    const query = params ? "?" + new URLSearchParams(params).toString() : "";
    return this.request(`/videos${query}`);
  }

  async getVideo(id: string) {
    return this.request(`/videos/${id}`);
  }

  async createVideo(data: { topic: string; channel_id: string; format?: string }) {
    return this.request("/videos", { method: "POST", body: JSON.stringify(data) });
  }

  async deleteVideo(id: string) {
    return this.request(`/videos/${id}`, { method: "DELETE" });
  }

  // Channels
  async getChannels() {
    return this.request("/channels");
  }

  async getChannel(id: string) {
    return this.request(`/channels/${id}`);
  }

  async createChannel(data: { name: string; profile_path?: string }) {
    return this.request("/channels", { method: "POST", body: JSON.stringify(data) });
  }

  // Jobs
  async getJobs(params?: Record<string, string>) {
    const query = params ? "?" + new URLSearchParams(params).toString() : "";
    return this.request(`/jobs${query}`);
  }

  async getJob(id: string) {
    return this.request(`/jobs/${id}`);
  }

  async getJobProgress(id: string) {
    return this.request(`/jobs/${id}`);
  }

  async cancelJob(id: string) {
    return this.request(`/jobs/${id}/cancel`, { method: "POST" });
  }

  async retryJob(id: string) {
    return this.request(`/jobs/${id}/retry`, { method: "POST" });
  }

  // Generate
  async generateScript(data: { topic: string; channel_name: string }) {
    return this.request("/generate/script", { method: "POST", body: JSON.stringify(data) });
  }

  async generateVideo(data: { topic: string; channel_name: string; format?: string }) {
    return this.request("/generate/video", { method: "POST", body: JSON.stringify(data) });
  }

  // Analytics
  async getCosts(params?: Record<string, string>) {
    const query = params ? "?" + new URLSearchParams(params).toString() : "";
    return this.request(`/analytics/costs${query}`);
  }

  async getVideoAnalytics(videoId: string) {
    return this.request(`/analytics/video/${videoId}/cost`);
  }
}

export const api = new ApiClient();
