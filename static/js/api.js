export const API = {
  async getModels() {
    const res = await fetch('/models');
    return await res.json();
  },
  async getStatus() {
    const res = await fetch('/status');
    return await res.json();
  },
  async getGpuStatus() {
    const res = await fetch('/gpu-status', { cache: 'no-store' });
    return await res.json();
  },
  async getProjects() {
    const res = await fetch('/api/projects/list');
    return await res.json();
  },
  async addProject(data) {
    const res = await fetch('/api/projects/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return await res.json();
  },
  async deleteProject(name) {
    const res = await fetch('/api/projects/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name })
    });
    return await res.json();
  },
  async activateProject(name) {
    const res = await fetch('/api/projects/activate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name })
    });
    return await res.json();
  },
  async deleteConversation(id) {
    const res = await fetch('/api/conversations/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id })
    });
    return await res.json();
  },
  async loadConversations() {
    const res = await fetch('/load-conversations');
    return await res.json();
  },
  async saveConversations(data) {
    const res = await fetch('/save-conversations', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return await res.json();
  },
  async markdownToExcel(markdown_text, project_name) {
    return await fetch('/markdown-to-excel', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ markdown_text, project_name })
    });
  },
  async imageToExcel(image, use_cloud, project_name) {
    return await fetch('/image-to-excel', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image, use_cloud, project_name })
    });
  },
  async uploadPdf(formData) {
    const res = await fetch('/upload-pdf', {
      method: 'POST',
      body: formData
    });
    return await res.json();
  },
  async shutdown() {
    return await fetch('/shutdown', { method: 'POST' });
  },
  async chat(payload, signal) {
    const hasImg = payload.images && payload.images.length > 0;
    const endpoint = hasImg ? '/chat-multi-image' : '/chat';
    return await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal
    });
  }
};