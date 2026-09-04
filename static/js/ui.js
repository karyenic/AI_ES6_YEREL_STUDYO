// static/js/ui.js
import { API } from './api.js';
import { State } from './state.js';
import { Workspace } from './workspace.js';

export const UI = {
  chatBox: null,
  promptEl: null,
  sendBtn: null,
  stopBtn: null,
  modelSelect: null,
  roleSelect: null,
  historyList: null,
  statusBar: null,
  gpuIndicator: null,
  badgeEl: null,
  imagePreview: null,
  packagePreview: null,
  sidebar: null,
  recognition: null,
  isListening: false,

  init() {
    this.chatBox = document.getElementById('chatBox');
    this.promptEl = document.getElementById('prompt');
    this.sendBtn = document.getElementById('sendBtn');
    this.stopBtn = document.getElementById('stopBtn');
    this.modelSelect = document.getElementById('modelSelect');
    this.roleSelect = document.getElementById('roleSelect');
    this.historyList = document.getElementById('history-list');
    this.statusBar = document.getElementById('statusBar');
    this.gpuIndicator = document.getElementById('gpu-indicator');
    this.badgeEl = document.getElementById('currentModelBadge');
    this.imagePreview = document.getElementById('imagePreview');
    this.packagePreview = document.getElementById('packagePreview');
    this.sidebar = document.getElementById('sidebar');

    State.loadFromStorage();
    this.applyTheme();
    this.initEvents();
    this.initSpeech();

    API.getModels().then(d => this.populateModels(d)).catch(() => this.populateModels({}));
    this.updateStatus();
    setInterval(() => this.updateStatus(), 10000);
    this.updateGpuStatus();
    setInterval(() => this.updateGpuStatus(), 4000);

    Workspace.initWorkspaceUI(() => this.renderHistory());

    if (!State.currentId || !State.conversations[State.currentId]) {
      this.createNewChat();
    } else {
      this.renderHistory();
      this.renderChat();
      this.updateTopBadge(State.conversations[State.currentId]);
    }
  },

  applyTheme() {
    document.body.classList.remove('light-theme', 'dim-theme');
    if (State.themeMode === 1) document.body.classList.add('light-theme');
    if (State.themeMode === 2) document.body.classList.add('dim-theme');
  },

  kind(m) {
    if (!m) return 'yerel';
    const lm = (m + '').toLowerCase();
    if (lm.includes('vision') || lm.includes('vl') || lm.includes('moondream') || lm.includes('granite')) return 'vision';
    if (lm.includes('coder') || lm.includes('r1') || lm.includes('deepseek')) return 'skill';
    if (lm.includes('gemini')) return 'bulut';
    return 'yerel';
  },

  tagCls(k) {
    if (k === 'bulut') return 'tag-bulut';
    if (k === 'vision') return 'tag-vision';
    if (k === 'skill') return 'tag-skill';
    return 'tag-yerel';
  },

  badgeCls(k) {
    if (k === 'bulut') return 'badge-bulut';
    if (k === 'vision') return 'badge-vision';
    if (k === 'skill') return 'badge-skill';
    return 'badge-yerel';
  },

  shortModel(m, route) {
    if (!m) return 'Auto';
    let base = (m === 'auto') ? 'Auto' : (m.startsWith('skill:') ? m.slice(6) : m);
    if (route) { return `${base} [${route}]`; }
    return base;
  },

  getFormattedTimestamp(ts) {
    if (!ts) return '';
    const d = new Date(ts);
    return d.toLocaleDateString('tr-TR') + ' ' + d.toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  },

  updateTopBadge(conv) {
    if (!conv) {
      this.badgeEl.textContent = 'Auto · Orkestratör';
      this.badgeEl.className = 'badge';
      return;
    }
    const activeModel = conv.lastUsedModel || conv.model;
    const routeTag = conv.lastRoute || '';
    if (!activeModel || activeModel === 'auto') {
      this.badgeEl.textContent = 'Auto (Akıllı Router)';
      this.badgeEl.className = 'badge badge-bulut';
    } else {
      this.badgeEl.textContent = this.shortModel(activeModel, routeTag);
      this.badgeEl.className = 'badge ' + this.badgeCls(this.kind(activeModel));
    }
  },

  async updateStatus() {
    try {
      const d = await API.getStatus();
      const gpuRes = await API.getGpuStatus();
      this.statusBar.innerHTML = '';

      const sOllama = document.createElement('span');
      sOllama.className = 'pill ' + (d.ollama ? 'ok' : 'down');
      sOllama.textContent = 'Ollama';
      this.statusBar.appendChild(sOllama);

      const sCloud = document.createElement('span');
      sCloud.className = 'pill ' + (d.gemini ? 'ok' : 'down');
      sCloud.textContent = 'Bulut';
      this.statusBar.appendChild(sCloud);

      const sGpu = document.createElement('span');
      sGpu.className = 'pill ' + (d.gpu ? 'ok' : 'down');
      sGpu.textContent = d.gpu ? 'GPU: Aktif' : 'GPU: Pasif';
      this.statusBar.appendChild(sGpu);

      if (this.gpuIndicator) {
        this.gpuIndicator.textContent = gpuRes.info || 'CPU/RAM okunamadı';
      }
    } catch {
      this.statusBar.innerHTML = '<span class="pill down">Bağlantı yok</span>';
    }
  },

  async updateGpuStatus() {
    if (!this.gpuIndicator) return;
    try {
      const data = await API.getGpuStatus();
      this.gpuIndicator.textContent = data.info || 'GPU okunamadı';
    } catch {
      this.gpuIndicator.textContent = 'GPU durumu alınamadı';
    }
  },

  populateModels(d) {
    this.modelSelect.innerHTML = '<option value="auto" style="font-weight:bold;color:var(--accent)">🤖 Otomatik Yönlendirme (Auto Router)</option>';
    const add = (lab, arr, icon) => {
      if (!arr || !arr.length) return;
      const g = document.createElement('optgroup');
      g.label = icon + ' ' + lab;
      arr.forEach(m => {
        const o = document.createElement('option');
        o.value = m;
        o.textContent = m;
        g.appendChild(o);
      });
      this.modelSelect.appendChild(g);
    };
    add('Yerel', d.local || [], '🖥️');
    add('Kod (Coder)', d.coder || [], '💻');
    add('Akıl Yürütme (Reasoning)', d.reasoning || [], '🧠');
    add('Görsel / Vision', d.vision || [], '👁️');
    add('Bulut', d.cloud || [], '☁️');
  },

  confirmLeaveProjectIfNeeded(targetIsProjectConv) {
    if (State.activeProjectName && !targetIsProjectConv) {
      if (!confirm(`"${State.activeProjectName}" projesinden çıkılıyor. Emin misiniz?`)) return false;
      Workspace.exitProject();
    }
    return true;
  },

  createNewChat() {
    if (!this.confirmLeaveProjectIfNeeded(false)) return;
    if (State.currentId && State.conversations[State.currentId]) {
      const cur = State.conversations[State.currentId];
      if (!(cur.messages || []).some(m => m.role === 'user')) {
        cur.model = this.modelSelect.value || 'auto';
        this.updateTopBadge(cur);
        this.renderChat();
        return;
      }
    }
    const id = String(State.nextId++);
    State.conversations[id] = { title: 'Yeni Sohbet', model: this.modelSelect.value || 'auto', created: Date.now(), messages: [{ role: 'system', content: 'WELCOME' }], pending: false };
    State.currentId = id;
    State.saveToStorage();
    this.renderHistory();
    this.renderChat();
    this.updateTopBadge(State.conversations[id]);
  },

  async deleteChat(id) {
    if (!confirm('Silinsin mi?')) return;
    if (State.conversations[id]?.abortCtrl) {
      try { State.conversations[id].abortCtrl.abort(); } catch {}
    }
    if (State.conversations[id]) State.conversations[id].pending = false;
    delete State.conversations[id];
    if (State.projectConvMap[id]) delete State.projectConvMap[id];
    if (State.currentId === id) {
      const ids = Object.keys(State.conversations);
      State.currentId = ids[0] || null;
    }
    State.saveToStorage();
    try { await API.deleteConversation(id); } catch {}
    if (!State.currentId) this.createNewChat();
    else {
      this.renderHistory();
      this.renderChat();
      this.updateTopBadge(State.conversations[State.currentId]);
    }
  },

  renderHistory() {
    this.historyList.innerHTML = '';
    const validIds = Object.keys(State.conversations).filter(id => {
      const c = State.conversations[id];
      return (c.messages || []).some(m => m.role === 'user') || id === State.currentId;
    });
    validIds.sort((a, b) => {
      const ca = State.conversations[a], cb = State.conversations[b];
      return (cb.created || 0) - (ca.created || 0);
    });

    validIds.forEach(id => {
      const c = State.conversations[id];
      const div = document.createElement('div');
      div.className = 'hist-item' + (id === State.currentId ? ' active' : '');
      const t = document.createElement('span');
      t.className = 'title';
      t.innerHTML = (c.pending ? '<span class="hourglass">⏳</span>' : '') + (c.title || c.model);

      const tag = document.createElement('span');
      const activeModelToDisplay = c.lastUsedModel || c.model;
      tag.className = 'tag ' + this.tagCls(this.kind(activeModelToDisplay));
      tag.textContent = this.shortModel(activeModelToDisplay, c.lastRoute);

      const del = document.createElement('button');
      del.className = 'del';
      del.textContent = 'Sil';
      del.onclick = e => { e.stopPropagation(); this.deleteChat(id); };

      div.appendChild(t);
      div.appendChild(tag);
      div.appendChild(del);

      div.onclick = () => {
        const isProjectConv = !!State.projectConvMap[id];
        if (!this.confirmLeaveProjectIfNeeded(isProjectConv)) return;
        State.currentId = id;
        State.saveToStorage();
        this.renderHistory();
        this.renderChat();
        this.updateTopBadge(State.conversations[id]);
        this.stopBtn.style.display = State.conversations[id]?.pending ? 'inline-block' : 'none';
        if (isProjectConv) Workspace.activateProject(State.projectConvMap[id], () => this.renderHistory());
      };
      this.historyList.appendChild(div);
    });
  },

  attachMini(wrap, text) {
    const row = document.createElement('div');
    row.className = 'msg-actions';
    const c = document.createElement('button');
    c.className = 'msg-action-btn';
    c.textContent = 'Kopyala';
    c.onclick = () => navigator.clipboard.writeText(text);

    const d = document.createElement('button');
    d.className = 'msg-action-btn';
    d.textContent = 'İndir';
    d.onclick = () => {
      const a = document.createElement('a');
      a.href = URL.createObjectURL(new Blob([text], { type: 'text/plain' }));
      a.download = 'yanit.txt';
      a.click();
    };
    row.appendChild(c);
    row.appendChild(d);

    if (text && text.includes('|') && text.split('\n').filter(l => l.includes('|')).length >= 2) {
      const ex = document.createElement('button');
      ex.className = 'msg-action-btn excel-btn';
      ex.textContent = '📊 Excel İndir';
      ex.onclick = async () => {
        ex.textContent = '⏳ Hazırlanıyor...';
        ex.disabled = true;
        try {
          const res = await API.markdownToExcel(text, State.activeProjectName || '');
          if (!res.ok) throw new Error('Excel oluşturulamadı');
          const blob = await res.blob();
          const a = document.createElement('a');
          a.href = URL.createObjectURL(blob);
          a.download = 'studyo_tablo.xlsx';
          a.click();
        } catch (e) {
          alert('Excel Hatası: ' + e.message);
        } finally {
          ex.textContent = '📊 Excel İndir';
          ex.disabled = false;
        }
      };
      row.appendChild(ex);
    }
    wrap.appendChild(row);
  },

  renderChat() {
    const conv = State.conversations[State.currentId];
    if (!conv) return;
    this.chatBox.innerHTML = '';
    document.getElementById('chatTitle').textContent = conv.title || 'Sohbet';
    this.updateTopBadge(conv);

    (conv.messages || []).forEach((m, index) => {
      if (m.role === "system" && m.content !== 'WELCOME') return;
      const wrap = document.createElement('div');
      wrap.className = 'msg-wrapper ' + (m.role || 'assistant');

      if (m.role === 'assistant') {
        const b = document.createElement('div');
        let label = m.model;
        if (!label || label === 'auto') label = conv.lastUsedModel || conv.model;
        b.className = 'badge ' + this.badgeCls(this.kind(label)) + (conv.pending && index === conv.messages.length - 1 ? ' pulse' : '');
        b.textContent = this.shortModel(label, m.route);
        wrap.appendChild(b);
      }

      const msg = document.createElement('div');
      msg.className = 'msg';
      if (m.role === 'system' && m.content === 'WELCOME') {
        msg.innerHTML = '<strong>Hoş geldin, Güven</strong>. Sistem Sürüm GK+GPT v2.9 ES6 aktif.';
      } else if (m.role === 'assistant' || m.role === 'user') {
        try { msg.innerHTML = marked.parse(m.content || ''); } catch { msg.textContent = m.content || ''; }
      } else {
        msg.textContent = m.content;
      }
      wrap.appendChild(msg);

      if (m.needsWebApproval) {
        const agentBox = document.createElement('div');
        agentBox.className = 'web-agent-box';
        agentBox.innerHTML = `<span>🌐 Bu sorgu internet üzerinden güncel veri taraması gerektiriyor. Web Ajanı çalıştırılsın mı?</span>
                              <div class="web-agent-btns">
                                <button class="web-agent-btn-ok">Onayla</button>
                                <button class="web-agent-btn-cancel">İptal</button>
                              </div>`;
        const approvalBtn = agentBox.querySelector('.web-agent-btn-ok');
        const cancelBtn = agentBox.querySelector('.web-agent-btn-cancel');
        approvalBtn.onclick = () => {
          approvalBtn.disabled = true; approvalBtn.textContent = 'İşleniyor...'; cancelBtn.disabled = true;
          setTimeout(() => { agentBox.remove(); }, 150);
          this.executeSend(m.originalPrompt, true);
        };
        cancelBtn.onclick = () => { agentBox.remove(); this.executeSend(m.originalPrompt, false); };
        wrap.appendChild(agentBox);
      }

      if (m.role === 'assistant' && m.content) this.attachMini(wrap, m.content);

      const ts = document.createElement('div');
      ts.className = 'msg-timestamp';
      ts.textContent = this.getFormattedTimestamp(m.created || conv.created || Date.now());
      wrap.appendChild(ts);
      this.chatBox.appendChild(wrap);
    });

    this.chatBox.scrollTop = this.chatBox.scrollHeight;
    if (this.stopBtn) this.stopBtn.style.display = conv.pending ? 'inline-block' : 'none';
  },

  toBase64(file) {
    return new Promise((res, rej) => {
      const r = new FileReader();
      r.onload = () => res(r.result.split(',')[1]);
      r.onerror = rej;
      r.readAsDataURL(file);
    });
  },

  setFilePackage(label, textContent) {
    State.currentFilePackage = textContent;
    this.packagePreview.innerHTML = `<span>📁 <strong>${label}</strong> yüklendi ve pakete alındı.</span><button class="remove-pkg" id="removePkgBtn">Kaldır</button>`;
    this.packagePreview.style.display = 'flex';
    document.getElementById('removePkgBtn').onclick = () => {
      State.currentFilePackage = null;
      this.packagePreview.innerHTML = '';
      this.packagePreview.style.display = 'none';
    };
  },

  initSpeech() {
    const micBtn = document.getElementById('micBtn');
    if (!micBtn) return;
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      this.recognition = new SpeechRecognition();
      this.recognition.lang = 'tr-TR';
      this.recognition.onresult = (event) => {
        this.promptEl.value = (this.promptEl.value ? this.promptEl.value + ' ' : '') + event.results[0][0].transcript;
        this.isListening = false;
        micBtn.style.background = '#0284c7';
        micBtn.textContent = '🎤 Ses';
      };
      this.recognition.onerror = () => {
        this.isListening = false;
        micBtn.style.background = '#0284c7';
        micBtn.textContent = '🎤 Ses';
      };
      this.recognition.onend = () => {
        this.isListening = false;
        micBtn.style.background = '#0284c7';
        micBtn.textContent = '🎤 Ses';
      };
    }
    micBtn.onclick = () => {
      if (!this.recognition) { alert('Ses tanıma desteklenmiyor.'); return; }
      if (this.isListening) {
        this.recognition.stop();
        this.isListening = false;
        micBtn.style.background = '#0284c7';
        micBtn.textContent = '🎤 Ses';
        return;
      }
      try {
        this.recognition.start();
        this.isListening = true;
        micBtn.style.background = '#dc2626';
        micBtn.textContent = '🔴 Dinleniyor...';
      } catch { this.isListening = false; }
    };
  },

  initEvents() {
    document.getElementById('newChatBtn').onclick = () => this.createNewChat();
    this.modelSelect.onchange = () => {
      if (State.conversations[State.currentId]) {
        State.conversations[State.currentId].model = this.modelSelect.value;
        State.saveToStorage();
        this.updateTopBadge(State.conversations[State.currentId]);
      }
    };

    document.getElementById('themeToggle').onclick = () => {
      State.themeMode = (State.themeMode + 1) % 3;
      this.applyTheme();
      State.saveToStorage();
    };

    document.getElementById('sidebarToggle').onclick = () => {
      State.sidebarOpen = !State.sidebarOpen;
      this.sidebar.classList.toggle('collapsed', !State.sidebarOpen);
    };

    this.stopBtn.onclick = () => {
      const conv = State.conversations[State.currentId];
      if (conv && conv.abortCtrl) conv.abortCtrl.abort();
    };

    document.getElementById('shutdownBtn').onclick = async () => {
      if (!confirm('GK AI Stüdyo kapatılsın mi?')) return;
      document.body.innerHTML = '<div style="display:flex;justify-content:center;align-items:center;height:100vh;background:#0b0b0f;color:#fff;font-family:sans-serif;font-size:1.2rem;flex-direction:column;gap:10px;"><div>Sistem güvenli bir şekilde kapatıldı.</div><div style="font-size:0.9rem;color:#9a9aa8;">Bu sekmeyi kapatabilirsiniz.</div></div>';
      try { await API.shutdown(); } catch {}
      setTimeout(() => { try { window.close(); } catch {} }, 300);
    };

    // Görsel Ekleme
    document.getElementById('selectImageBtn').onclick = () => document.getElementById('imageInput').click();
    document.getElementById('imageInput').onchange = async e => {
      for (const f of Array.from(e.target.files || [])) {
        const b64 = await this.toBase64(f);
        State.currentImages.push(b64);
        const div = document.createElement('div');
        div.className = 'preview-item';
        const img = document.createElement('img');
        img.src = URL.createObjectURL(f);
        const rm = document.createElement('span');
        rm.className = 'remove-img';
        rm.textContent = 'x';
        rm.onclick = () => {
          const i = State.currentImages.indexOf(b64);
          if (i >= 0) State.currentImages.splice(i, 1);
          div.remove();
          if (!State.currentImages.length) this.imagePreview.style.display = 'none';
        };
        div.appendChild(img);
        div.appendChild(rm);
        this.imagePreview.appendChild(div);
      }
      this.imagePreview.style.display = State.currentImages.length ? 'flex' : 'none';
      e.target.value = '';
    };

    // Excel Çözme
    document.getElementById('excelBtn').onclick = async () => {
      if (!State.currentImages.length) { alert('Önce görsel eklemelisiniz!'); return; }
      const excelBtn = document.getElementById('excelBtn');
      const originalText = excelBtn.textContent;
      const useCloud = document.getElementById('cloudVisionCheck')?.checked || false;
      excelBtn.textContent = useCloud ? '⚡ Bulut Çözülüyor...' : '⏳ Tablo Çözülüyor...';
      excelBtn.disabled = true;
      try {
        const res = await API.imageToExcel(State.currentImages[0], useCloud, State.activeProjectName || '');
        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.error || 'Tablo çözme hatası');
        }
        const blob = await res.blob();
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = 'tablo_analiz.xlsx';
        a.click();
      } catch (e) {
        alert('Excel Hatası: ' + e.message);
      } finally {
        excelBtn.textContent = originalText;
        excelBtn.disabled = false;
      }
    };

    // PDF Yükleme
    document.getElementById('pdfBtn').onclick = () => document.getElementById('pdfInput').click();
    document.getElementById('pdfInput').onchange = async e => {
      const f = e.target.files[0];
      if (!f) return;
      try {
        const fd = new FormData();
        fd.append('file', f);
        const d = await API.uploadPdf(fd);
        if (d.error) throw new Error(d.error);
        if (d.text) this.setFilePackage(`PDF: ${f.name} (${d.pages} sayfa)`, d.text);
      } catch (err) { alert(err.message); }
      e.target.value = '';
    };

    // Klasör Oku
    document.getElementById('folderBtn').onclick = () => document.getElementById('folderInput').click();
    document.getElementById('folderInput').onchange = async e => {
      const files = Array.from(e.target.files || []);
      if (!files.length) return;
      const folderBtn = document.getElementById('folderBtn');
      folderBtn.textContent = '⏳ Taranıyor...';
      let packageText = "[PROJE KLASÖRÜ / KOD PAKETİ]\n";
      let count = 0;
      for (const f of files) {
        const path = f.webkitRelativePath || f.name;
        const lower = path.toLowerCase();
        if (lower.includes('/.git/') || lower.includes('/venv/') || lower.includes('/__pycache__/') || lower.includes('/node_modules/') || lower.endsWith('.png') || lower.endsWith('.exe')) continue;
        try {
          const content = await new Promise((resolve) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.readAsText(f, 'UTF-8');
          });
          packageText += `\n--- DOSYA: ${path} ---\n${content}\n`;
          count++;
        } catch {}
      }
      folderBtn.textContent = '📂 Klasör Oku';
      if (count > 0) this.setFilePackage(`Klasör (${count} dosya)`, packageText);
      else alert('Uygun metin dosyası bulunamadı.');
      e.target.value = '';
    };

    // TXT Gönder
    document.getElementById('txtBtn').onclick = () => document.getElementById('txtInput').click();
    document.getElementById('txtInput').onchange = async e => {
      const f = e.target.files[0];
      if (!f) return;
      try {
        const content = await new Promise((res, rej) => {
          const reader = new FileReader();
          reader.onload = () => res(reader.result);
          reader.onerror = rej;
          reader.readAsText(f, 'UTF-8');
        });
        this.setFilePackage(`TXT: ${f.name}`, content);
      } catch (err) { alert('TXT okuma hatası: ' + err.message); }
      e.target.value = '';
    };

    // Kod Gönder
    document.getElementById('codeBtn').onclick = () => document.getElementById('codeInput').click();
    document.getElementById('codeInput').onchange = async e => {
      const files = Array.from(e.target.files || []);
      if (!files.length) return;
      let codePackage = "[KOD DOSYALARI PAKETİ]\n";
      for (const f of files) {
        try {
          const content = await new Promise((res, rej) => {
            const reader = new FileReader();
            reader.onload = () => res(reader.result);
            reader.onerror = rej;
            reader.readAsText(f, 'UTF-8');
          });
          codePackage += `\n--- KOD DOSYASI: ${f.name} ---\n${content}\n`;
        } catch {}
      }
      this.setFilePackage(`Kod Paketi (${files.length} dosya)`, codePackage);
      e.target.value = '';
    };

    // Sürükle Bırak ve Yapıştırma
    const inputAreaEl = document.getElementById('inputArea');
    inputAreaEl.addEventListener('dragover', (e) => { e.preventDefault(); inputAreaEl.style.borderColor = 'var(--accent)'; });
    inputAreaEl.addEventListener('dragleave', (e) => { e.preventDefault(); inputAreaEl.style.borderColor = 'var(--border)'; });
    inputAreaEl.addEventListener('drop', async (e) => {
      e.preventDefault();
      inputAreaEl.style.borderColor = 'var(--border)';
      const files = Array.from(e.dataTransfer.files || []);
      if (!files.length) return;

      let combinedContent = "[SÜRÜKLENEN DOSYA PAKETİ]\n";
      let droppedCount = 0;

      for (const f of files) {
        const lower = f.name.toLowerCase();
        if (lower.endsWith(('.png', '.jpg', '.jpeg', '.webp'))) {
          const b64 = await this.toBase64(f);
          State.currentImages.push(b64);
          const div = document.createElement('div');
          div.className = 'preview-item';
          const img = document.createElement('img');
          img.src = URL.createObjectURL(f);
          const rm = document.createElement('span');
          rm.className = 'remove-img';
          rm.textContent = 'x';
          rm.onclick = () => {
            const i = State.currentImages.indexOf(b64);
            if (i >= 0) State.currentImages.splice(i, 1);
            div.remove();
            if (!State.currentImages.length) this.imagePreview.style.display = 'none';
          };
          div.appendChild(img);
          div.appendChild(rm);
          this.imagePreview.appendChild(div);
          this.imagePreview.style.display = 'flex';
        } else {
          try {
            const content = await new Promise((res) => {
              const reader = new FileReader();
              reader.onload = () => res(reader.result);
              reader.readAsText(f, 'UTF-8');
            });
            combinedContent += `\n--- DOSYA: ${f.name} ---\n${content}\n`;
            droppedCount++;
          } catch {}
        }
      }
      if (droppedCount > 0) {
        this.setFilePackage(`Sürüklenen Dosyalar (${droppedCount} adet)`, combinedContent);
      }
    });

    this.promptEl.addEventListener('paste', async (e) => {
      const items = (e.clipboardData || e.originalEvent.clipboardData).items;
      for (const item of items) {
        if (item.type.indexOf('image') === 0) {
          const blob = item.getAsFile();
          const b64 = await this.toBase64(blob);
          State.currentImages.push(b64);
          const div = document.createElement('div');
          div.className = 'preview-item';
          const img = document.createElement('img');
          img.src = URL.createObjectURL(blob);
          const rm = document.createElement('span');
          rm.className = 'remove-img';
          rm.textContent = 'x';
          rm.onclick = () => {
            const i = State.currentImages.indexOf(b64);
            if (i >= 0) State.currentImages.splice(i, 1);
            div.remove();
            if (!State.currentImages.length) this.imagePreview.style.display = 'none';
          };
          div.appendChild(img);
          div.appendChild(rm);
          this.imagePreview.appendChild(div);
          this.imagePreview.style.display = 'flex';
        }
      }
    });

    this.sendBtn.onclick = () => this.handleSend();
    this.promptEl.addEventListener('keydown', e => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.handleSend();
      }
    });
  },

  needsWebSearch(text) {
    // ONEMLI: bu fonksiyon eskiden index.html'in ALT KISMINDA, ayri bir
    // <script> (ES6 modulu OLMAYAN) icinde tanimliydi. ui.js bir ES6
    // modulu oldugu icin o script'in global scope'una erisemiyordu -
    // "web tetikleme" hic calismiyordu, cunku handleSend zaten
    // web_search'u hep 'false' olarak sabitlemisti. Artik modulun
    // kendi icinde tanimli, dogrudan erisiliyor.
    const p = (text || '').toLowerCase();
    const keywords = ['güncel', 'araştır', 'merkez bankası', 'tcmb', 'fiyat', 'haber', 'site', 'web üzerinden', 'internet', 'enflasyon', 'tüfe', 'tüik', 'istatistik', 'oranlar', 'grafik', 'tablo', 'katalog', 'indir', 'link'];
    return keywords.some(kw => p.includes(kw));
  },

  async handleSend() {
    const text = this.promptEl.value.trim();
    if (!text && !State.currentImages.length && !State.currentFilePackage && !State.activeProjectPackageContent) return;

    const conv = State.conversations[State.currentId];
    if (!conv) return;

    // Web arama onayi SADECE saf metin sorularda tetiklenir - gorsel veya
    // dosya paketi ekliyse (zaten spesifik bir analiz istegi oldugu icin)
    // araya girmiyoruz.
    if (text && this.needsWebSearch(text) && !State.currentImages.length && !State.currentFilePackage) {
      conv.messages = (conv.messages || []).filter(m => !(m.role === 'system' && m.content === 'WELCOME'));
      conv.messages.push({ role: 'user', content: text, created: Date.now() });
      if (conv.messages.filter(m => m.role === 'user').length === 1) {
        conv.title = text.length > 28 ? text.slice(0, 28) + '...' : text;
      }
      this.promptEl.value = '';
      State.saveToStorage();
      this.renderChat();
      this.renderHistory();
      conv.messages.push({
        role: 'assistant',
        content: 'Güncel veri taraması için onay bekleniyor.',
        needsWebApproval: true,
        originalPrompt: text,
        created: Date.now()
      });
      State.saveToStorage();
      this.renderChat();
      return;
    }
    this.executeSend(text, false);
  },

  async executeSend(text, forceWeb) {
    const targetId = State.currentId;
    const conv = State.conversations[targetId];
    if (!conv) return;

    const imgs = State.currentImages.slice();
    // ONEMLI: activeProjectPackageContent (proje bagami) HER mesajda
    // gonderiliyordu - bu, buyuk projelerde her mesajin GPU'yu asiri
    // yormasina, cok yavaslamasina ve zaman asimina yol aciyordu. Sohbet
    // gecmisi zaten backend'e her seferinde gonderiliyor, yani icerik bir
    // kez gorulduyse modelin "hafizasinda" kalmaya devam eder. Simdi
    // sadece bu sohbette DAHA ONCE gonderilmediyse ekleniyor.
    const sendProjectPkg = State.activeProjectPackageContent && !State.projectContextSentFor?.[targetId];
    const pkg = State.currentFilePackage || (sendProjectPkg ? State.activeProjectPackageContent : null) || null;
    const userMsg = text || 'Dosya analizi başlat.';

    if (!conv.messages.some(m => m.content === userMsg && m.role === 'user')) {
      conv.messages = (conv.messages || []).filter(m => !(m.role === 'system' && m.content === 'WELCOME'));
      let badgeInfo = imgs.length ? ` [${imgs.length} görsel]` : '';
      if (State.currentFilePackage) badgeInfo += ` [Manuel Paket eklendi]`;
      if (sendProjectPkg) badgeInfo += ` [Workspace Manifest aktif]`;
      conv.messages.push({ role: 'user', content: userMsg + badgeInfo, created: Date.now() });
      if (conv.messages.filter(m => m.role === 'user').length === 1) {
        conv.title = userMsg.length > 28 ? userMsg.slice(0, 28) + '...' : userMsg;
      }
    }
    if (!conv.created) conv.created = Date.now();

    this.promptEl.value = '';
    State.currentImages = [];
    this.imagePreview.innerHTML = '';
    this.imagePreview.style.display = 'none';
    State.currentFilePackage = null;
    this.packagePreview.innerHTML = '';
    this.packagePreview.style.display = 'none';
    if (sendProjectPkg) {
      if (!State.projectContextSentFor) State.projectContextSentFor = {};
      State.projectContextSentFor[targetId] = true;
    }

    conv.pending = true;
    if (State.currentId === targetId) this.stopBtn.style.display = 'inline-block';
    State.saveToStorage();
    this.renderHistory();
    this.renderChat();

    const history = conv.messages.filter(m => m.role === 'user' || m.role === 'assistant').slice(0, -1).slice(-20).map(m => ({ role: m.role, content: m.content }));
    conv.abortCtrl = new AbortController();
    const assistantMsg = { role: 'assistant', content: '', model: conv.model, created: Date.now() };
    conv.messages.push(assistantMsg);

    let wrap = null, badge = null, msgDiv = null;
    if (State.currentId === targetId) {
      wrap = document.createElement('div');
      wrap.className = 'msg-wrapper assistant';
      badge = document.createElement('div');
      badge.className = 'badge ' + this.badgeCls(this.kind(conv.model)) + ' pulse';
      badge.textContent = conv.model;
      wrap.appendChild(badge);

      msgDiv = document.createElement('div');
      msgDiv.className = 'msg';
      msgDiv.innerHTML = '<span class="hourglass">⏳</span> Model düşünüyor...';
      wrap.appendChild(msgDiv);

      const tsDiv = document.createElement('div');
      tsDiv.className = 'msg-timestamp';
      tsDiv.textContent = this.getFormattedTimestamp(assistantMsg.created);
      wrap.appendChild(tsDiv);
      this.chatBox.appendChild(wrap);
    }

    try {
      const payload = {
        prompt: userMsg,
        model: conv.model,
        history,
        images: imgs.length ? imgs : undefined,
        filePackage: pkg,
        role: this.roleSelect.value || 'default',
        web_search: !!forceWeb,
        is_project: !!State.projectConvMap?.[targetId],
        project_name: State.projectConvMap?.[targetId] || ''
      };

      const res = await API.chat(payload, conv.abortCtrl.signal);
      if (!res.ok || !res.body) throw new Error('Sunucu Yanıt Vermedi');

      const reader = res.body.getReader();
      const dec = new TextDecoder();
      let buf = '', acc = '', used = conv.model, route = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        const lines = buf.split('\n');
        buf = lines.pop();
        for (const line of lines) {
          if (!line.trim()) continue;
          let cleanLine = line.trim();
          if (cleanLine.startsWith('data: ')) cleanLine = cleanLine.substring(6).trim();
          let evt;
          try { evt = JSON.parse(cleanLine); } catch { continue; }

          if (evt.type === 'meta') {
            used = evt.model || used;
            route = evt.route || null;
            assistantMsg.model = used;
            assistantMsg.route = route;
            conv.lastUsedModel = used;
            conv.lastRoute = route;
            if (State.currentId === targetId) {
              if (badge) {
                badge.textContent = this.shortModel(used, route);
                badge.className = 'badge ' + this.badgeCls(this.kind(used)) + ' pulse';
              }
              this.updateTopBadge(conv);
            }
          } else if (evt.type === 'chunk') {
            acc += evt.text;
            assistantMsg.content = acc;
            if (State.currentId === targetId && msgDiv) {
              msgDiv.textContent = acc;
              if (this.chatBox.scrollHeight - this.chatBox.scrollTop - this.chatBox.clientHeight < 80) {
                this.chatBox.scrollTop = this.chatBox.scrollHeight;
              }
            }
          } else if (evt.type === 'error') {
            acc += '\n[Hata] ' + evt.message;
            assistantMsg.content = acc;
            if (State.currentId === targetId && msgDiv) msgDiv.textContent = acc;
          }
        }
      }
      conv.pending = false;
      State.saveToStorage();
      if (State.currentId === targetId) this.renderChat();
      this.renderHistory();
    } catch (e) {
      conv.pending = false;
      if (e.name !== 'AbortError') assistantMsg.content += '\nHata: ' + e.message;
      State.saveToStorage();
      if (State.currentId === targetId) this.renderChat();
      this.renderHistory();
    } finally {
      conv.pending = false;
      if (State.currentId === targetId) this.stopBtn.style.display = 'none';
      conv.abortCtrl = null;
      this.renderHistory();
    }
  }
};


