export const State = {
  conversations: {},
  currentId: null,
  nextId: 1,
  currentImages: [],
  currentFilePackage: null,
  activeProjectPackageContent: null,
  activeProjectName: null,
  activeProjectPath: null,
  projectConvMap: {},
  projectContextSentFor: {},
  themeMode: 0,
  sidebarOpen: true,

  loadFromStorage() {
    try {
      this.conversations = JSON.parse(localStorage.getItem('grk_convs') || '{}');
      this.currentId = localStorage.getItem('grk_current');
      this.nextId = parseInt(localStorage.getItem('grk_next') || '1');
      this.themeMode = parseInt(localStorage.getItem('grk_theme') || '0');
    } catch (e) {
      this.conversations = {};
    }
  },

  saveToStorage() {
    const cleanConvs = {};
    for (const [id, conv] of Object.entries(this.conversations)) {
      cleanConvs[id] = { ...conv };
      if (cleanConvs[id].messages) {
        cleanConvs[id].messages = conv.messages.filter(m => {
          if (m.role === 'system' && m.content && m.content.includes('[PROJE Ã‡ALIÅžMA ALANI DÄ°ZÄ°NÄ°]')) {
            return false;
          }
          return true;
        });
      }
    }
    localStorage.setItem('grk_convs', JSON.stringify(cleanConvs));
    localStorage.setItem('grk_current', this.currentId);
    localStorage.setItem('grk_next', this.nextId);
    localStorage.setItem('grk_theme', this.themeMode);
  },

  resetCurrentInput() {
    this.currentImages = [];
    this.currentFilePackage = null;
  }
};
