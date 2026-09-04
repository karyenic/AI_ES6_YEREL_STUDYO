// static/js/workspace.js
import { API } from './api.js';
import { State } from './state.js';

export const Workspace = {
  async loadProjectList(renderCallback) {
    try {
      const d = await API.getProjects();
      const projects = d.projects || {};
      State.projectConvMap = {};
      Object.entries(projects).forEach(([pname, p]) => {
        if (p.conversationId) State.projectConvMap[p.conversationId] = pname;
      });

      const listEl = document.getElementById('projectList');
      if (!listEl) return;
      listEl.innerHTML = '';
      const names = Object.keys(projects);

      if (!names.length) {
        listEl.innerHTML = '<div style="color:var(--muted);font-size:.8rem;padding:4px 0;">Henüz proje yok</div>';
        return;
      }

      names.forEach(name => {
        const row = document.createElement('div');
        row.style.cssText = 'display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid var(--border);';
        
        const label = document.createElement('span');
        label.textContent = name;
        label.style.cssText = 'font-size:.85rem;cursor:pointer;flex:1;';
        label.onclick = () => this.activateProject(name, renderCallback);

        const delBtn = document.createElement('button');
        delBtn.textContent = '🗑️';
        delBtn.style.cssText = 'background:none;border:none;color:#ef4444;cursor:pointer;font-size:1rem;padding:0 4px;';
        delBtn.onclick = async (e) => {
          e.stopPropagation();
          if (!confirm(`"${name}" projesini silmek istediğinize emin misiniz?`)) return;
          const res = await API.deleteProject(name);
          if (res.status === 'success') {
            if (State.activeProjectName === name) {
              this.exitProject();
            }
            this.loadProjectList(renderCallback);
          } else {
            alert('Hata: ' + res.message);
          }
        };

        const btn = document.createElement('button');
        btn.textContent = '▶';
        btn.style.cssText = 'background:none;border:none;color:var(--accent);cursor:pointer;';
        btn.onclick = () => this.activateProject(name, renderCallback);

        row.appendChild(label);
        row.appendChild(delBtn);
        row.appendChild(btn);
        listEl.appendChild(row);
      });
    } catch (e) {
      console.error("Proje listesi yüklenemedi:", e);
    }
  },

  async activateProject(name, renderCallback) {
    try {
      const d = await API.activateProject(name);
      if (d.status !== 'success') {
        alert('Hata: ' + (d.message || 'Bilinmeyen hata'));
        return;
      }

      State.activeProjectName = d.project.name;
      State.activeProjectPath = d.project.path;
      State.activeProjectPackageContent = d.package_content;
      State.activeProjectIndexed = !!d.project.indexed;
      State.activeProjectChunkCount = d.project.chunk_count || 0;

      // ÇÖZÜM: Workspace aktifken manuel "Klasör Oku" butonu kilitlenir
      const folderBtn = document.getElementById('folderBtn');
      if (folderBtn) {
        folderBtn.disabled = true;
        folderBtn.style.opacity = '0.5';
        folderBtn.title = "Workspace aktifken manuel klasör okuma kilitlidir.";
      }

      const convId = d.project.conversationId;
      State.projectConvMap[convId] = name;
      // Proje YENIDEN aktive edildi (dizin yeniden tarandi, guncel icerik
      // geldi) - bir sonraki mesajda bu guncel icerigin bir kez daha
      // gonderilmesi icin bayragi sifirliyoruz.
      if (State.projectContextSentFor) State.projectContextSentFor[convId] = false;

      if (!State.conversations[convId]) {
        State.conversations[convId] = {
          id: convId,
          title: '📁 ' + name,
          messages: [],
          model: d.project.default_model,
          created: Date.now()
        };
      }

      State.currentId = convId;
      const modelSelect = document.getElementById('modelSelect');
      if (modelSelect) modelSelect.value = d.project.default_model;

      const activeBanner = document.getElementById('activeProjectBanner');
      const activeLabel = document.getElementById('activeProjectLabel');
      if (activeBanner) activeBanner.style.display = 'block';
      if (activeLabel) {
        const ragInfo = State.activeProjectIndexed
          ? `🟢 RAG aktif (${State.activeProjectChunkCount} parça) - her mesajda sadece alakalı içerik aranır`
          : `⚪ RAG indekslenmemiş - tüm dizin tek seferde gönderiliyor (büyük projelerde yavaş olabilir)`;
        activeLabel.innerHTML = `📁 ${name} (${d.file_count} dosya) — aktif<br><span style="font-size:.75rem;font-weight:400;">${ragInfo}</span>`;
      }
      this._renderIndexButton(name, renderCallback);

      State.saveToStorage();
      if (renderCallback) renderCallback();
    } catch (e) {
      alert('Sunucuya ulaşılamadı: ' + e.message);
    }
  },

  _renderIndexButton(name, renderCallback) {
    const banner = document.getElementById('activeProjectBanner');
    if (!banner) return;
    let btn = document.getElementById('indexProjectBtn');
    if (!btn) {
      btn = document.createElement('button');
      btn.id = 'indexProjectBtn';
      btn.style.cssText = 'margin-top:6px;width:100%;padding:5px;border-radius:4px;border:none;cursor:pointer;font-size:.8rem;background:#374151;color:#fff;';
      banner.appendChild(btn);
    }
    btn.textContent = State.activeProjectIndexed ? '🔄 Yeniden İndeksle (RAG)' : '⚡ İndeksle (RAG) - Büyük projelerde önerilir';
    btn.onclick = async () => {
      if (!confirm(`"${name}" projesi indekslenecek. Dosya sayısına göre bu birkaç dakika sürebilir (her parça için yerel bir embedding çağrısı yapılıyor). Devam edilsin mi?`)) return;
      btn.disabled = true;
      btn.textContent = '⏳ İndeksleniyor... (bekleyin, süre dizin boyutuna bağlı)';
      try {
        const res = await API.indexProject(name);
        if (res.status === 'success') {
          alert(`İndeksleme tamamlandı: ${res.file_count} dosya, ${res.chunk_count} parça.`);
          this.activateProject(name, renderCallback); // durumu tazele
        } else {
          alert('İndeksleme hatası: ' + res.message);
          btn.disabled = false;
          btn.textContent = '⚡ İndeksle (RAG)';
        }
      } catch (e) {
        alert('Sunucuya ulaşılamadı: ' + e.message);
        btn.disabled = false;
      }
    };
  },

  exitProject() {
    State.activeProjectName = null;
    State.activeProjectPath = null;
    State.activeProjectPackageContent = null;
    State.activeProjectIndexed = false;
    State.activeProjectChunkCount = 0;

    const activeBanner = document.getElementById('activeProjectBanner');
    if (activeBanner) activeBanner.style.display = 'none';

    const folderBtn = document.getElementById('folderBtn');
    if (folderBtn) {
      folderBtn.disabled = false;
      folderBtn.style.opacity = '1';
      folderBtn.title = "";
    }
  },

  initWorkspaceUI(renderCallback) {
    const newProjBtn = document.getElementById('newProjectBtn');
    const newProjForm = document.getElementById('newProjectForm');
    const confirmNewProjectBtn = document.getElementById('confirmNewProjectBtn');
    const exitProjectBtn = document.getElementById('exitProjectBtn');

    if (newProjBtn && newProjForm) {
      newProjBtn.onclick = () => {
        newProjForm.style.display = newProjForm.style.display === 'none' ? 'block' : 'none';
      };
    }

    if (confirmNewProjectBtn) {
      confirmNewProjectBtn.onclick = async () => {
        const nameEl = document.getElementById('newProjName');
        const pathEl = document.getElementById('newProjPath');
        const name = nameEl ? nameEl.value.trim() : '';
        const path = pathEl ? pathEl.value.trim() : '';
        const modelSelect = document.getElementById('modelSelect');

        if (!name || !path) {
          alert('Proje adı ve dizin yolu zorunludur.');
          return;
        }

        try {
          const res = await API.addProject({
            name,
            path,
            default_model: modelSelect ? modelSelect.value : 'auto'
          });

          if (res.status === 'success') {
            if (nameEl) nameEl.value = '';
            if (pathEl) pathEl.value = '';
            if (newProjForm) newProjForm.style.display = 'none';
            this.loadProjectList(renderCallback);
          } else {
            alert('Hata: ' + res.message);
          }
        } catch (e) {
          alert('Sunucu hatası: ' + e.message);
        }
      };
    }

    if (exitProjectBtn) {
      exitProjectBtn.onclick = () => {
        this.exitProject();
      };
    }

    this.loadProjectList(renderCallback);
  }
};