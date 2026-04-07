import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  isTokenExpired,
  setTokens,
} from "@/lib/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

class ApiClient {
  private baseUrl: string;
  private isRefreshing = false;
  private refreshPromise: Promise<boolean> | null = null;

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
  }

  // --------------------------------------------------------------------------
  // Token helpers
  // --------------------------------------------------------------------------

  private getAuthHeaders(): Record<string, string> {
    const token = getAccessToken();
    if (!token) return {};
    return { Authorization: `Bearer ${token}` };
  }

  /**
   * Attempt to refresh the access token using the stored refresh token.
   * Returns true if successful, false otherwise.
   * De-duplicated so concurrent 401s don't fire multiple refresh calls.
   */
  private async refreshAccessToken(): Promise<boolean> {
    if (this.isRefreshing && this.refreshPromise) {
      return this.refreshPromise;
    }

    this.isRefreshing = true;
    this.refreshPromise = (async () => {
      try {
        const refreshToken = getRefreshToken();
        if (!refreshToken) return false;

        const res = await fetch(`${this.baseUrl}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });

        if (!res.ok) return false;

        const data = await res.json();
        setTokens(data.access_token, data.refresh_token);
        return true;
      } catch {
        return false;
      } finally {
        this.isRefreshing = false;
        this.refreshPromise = null;
      }
    })();

    return this.refreshPromise;
  }

  // --------------------------------------------------------------------------
  // Core request
  // --------------------------------------------------------------------------

  private async request<T>(
    path: string,
    options: RequestInit = {},
    retry = true
  ): Promise<T> {
    // If the token is about to expire, proactively refresh
    if (isTokenExpired() && getRefreshToken()) {
      await this.refreshAccessToken();
    }

    const url = `${this.baseUrl}${path}`;
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...this.getAuthHeaders(),
      ...(options.headers as Record<string, string>),
    };

    const res = await fetch(url, { ...options, headers });

    // Handle 401 — attempt one token refresh, then retry the original request
    if (res.status === 401 && retry) {
      const refreshed = await this.refreshAccessToken();
      if (refreshed) {
        return this.request<T>(path, options, false);
      }

      // Refresh failed — clear auth state and redirect to login
      clearTokens();
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
      throw new Error("Session expired. Please sign in again.");
    }

    if (!res.ok) {
      const error = await res
        .json()
        .catch(() => ({ detail: res.statusText }));
      throw new Error(error.detail || `API error: ${res.status}`);
    }

    return res.json();
  }

  // --------------------------------------------------------------------------
  // Videos
  // --------------------------------------------------------------------------

  async getVideos(params?: Record<string, string>) {
    const query = params ? "?" + new URLSearchParams(params).toString() : "";
    return this.request(`/videos${query}`);
  }

  async getVideo(id: string) {
    return this.request(`/videos/${id}`);
  }

  async createVideo(data: {
    topic: string;
    channel_id: string;
    format?: string;
  }) {
    return this.request("/videos", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async deleteVideo(id: string) {
    return this.request(`/videos/${id}`, { method: "DELETE" });
  }

  // --------------------------------------------------------------------------
  // Channels
  // --------------------------------------------------------------------------

  async getChannels() {
    return this.request("/channels");
  }

  async getChannel(id: string) {
    return this.request(`/channels/${id}`);
  }

  async createChannel(data: { name: string; profile_path?: string }) {
    return this.request("/channels", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  // --------------------------------------------------------------------------
  // Jobs
  // --------------------------------------------------------------------------

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

  // --------------------------------------------------------------------------
  // Generate
  // --------------------------------------------------------------------------

  async generateScript(data: { topic: string; channel_name: string }) {
    return this.request("/generate/script", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async generateVideo(data: {
    topic: string;
    channel_name: string;
    format?: string;
  }) {
    return this.request("/generate/video", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  // --------------------------------------------------------------------------
  // Analytics
  // --------------------------------------------------------------------------

  async getCosts(params?: Record<string, string>) {
    const query = params ? "?" + new URLSearchParams(params).toString() : "";
    return this.request(`/analytics/costs${query}`);
  }

  async getVideoAnalytics(videoId: string) {
    return this.request(`/analytics/video/${videoId}/cost`);
  }
}

export const api = new ApiClient();
