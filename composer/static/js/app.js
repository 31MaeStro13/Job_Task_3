// SVG Illustration Composer Client Application

class ComposerApp {
  constructor() {
    this.state = {
      format: "1200x630",
      size: "l",
      palette: "purple",
      layout: "clustered",
      objects: [],
      selectedId: null,
      zoom: 1.0,
      components: [],
      manualSelection: new Map(), // object_id -> { state: 'main'|'bg' }
    };

    this.dragContext = null;
    this.initElements();
    this.bindEvents();
    this.loadCatalog();
    this.loadInitialPreset("edu");
  }

  initElements() {
    this.formatSelect = document.getElementById("formatSelect");
    this.paletteBtns = document.querySelectorAll(".swatch-btn");
    this.sizeBtns = document.querySelectorAll(".seg-btn");
    this.tabBtns = document.querySelectorAll(".tab-btn");
    this.exportBtn = document.getElementById("exportSvgBtn");

    // Scenario 1
    this.metaphorInput = document.getElementById("metaphorInput");
    this.runMetaphorBtn = document.getElementById("runMetaphorBtn");
    this.useBgCheck = document.getElementById("useBgObjectsCheck");
    this.aiCard = document.getElementById("aiReasoningBox");
    this.aiText = document.getElementById("aiReasoningText");
    this.aiLayoutBadge = document.getElementById("aiLayoutBadge");
    this.aiTags = document.getElementById("aiSelectedTags");

    // Scenario 2
    this.catalogGrid = document.getElementById("componentsCatalog");
    this.runManualBtn = document.getElementById("runManualBtn");
    this.selectedCountBadge = document.getElementById("selectedCountBadge");
    this.layoutRadios = document.querySelectorAll('input[name="layoutOption"]');

    // Canvas
    this.mountPoint = document.getElementById("svgMountPoint");
    this.viewport = document.getElementById("canvasViewport");
    this.container = document.getElementById("canvasContainer");
    this.statusText = document.getElementById("statusInfoText");

    // Inspector
    this.inspector = document.getElementById("inspectorPanel");
    this.scaleRange = document.getElementById("scaleRange");
    this.scaleValue = document.getElementById("scaleValue");
    this.rotateRange = document.getElementById("rotateRange");
    this.rotateValue = document.getElementById("rotateValue");
    this.bringForwardBtn = document.getElementById("bringForwardBtn");
    this.sendBackwardBtn = document.getElementById("sendBackwardBtn");
    this.duplicateBtn = document.getElementById("duplicateBtn");
    this.deleteBtn = document.getElementById("deleteBtn");
    this.closeInspectorBtn = document.getElementById("closeInspectorBtn");

    // Zoom
    this.zoomInBtn = document.getElementById("zoomInBtn");
    this.zoomOutBtn = document.getElementById("zoomOutBtn");
    this.zoomFitBtn = document.getElementById("zoomFitBtn");
    this.zoomText = document.getElementById("zoomLevelText");
  }

  bindEvents() {
    // Format change
    this.formatSelect.addEventListener("change", (e) => {
      this.state.format = e.target.value;
      this.recomputeOrUpdate();
    });

    // Detail size change
    this.sizeBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        this.sizeBtns.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        this.state.size = btn.dataset.size;
        this.recomputeOrUpdate();
      });
    });

    // Palette change
    this.paletteBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        this.paletteBtns.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        this.changePalette(btn.dataset.palette);
      });
    });

    // Tabs
    this.tabBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        this.tabBtns.forEach((b) => b.classList.remove("active"));
        document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));
        btn.classList.add("active");
        const target = document.getElementById(btn.dataset.tab);
        if (target) target.classList.add("active");
      });
    });

    // Chips
    document.querySelectorAll(".chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        this.metaphorInput.value = chip.dataset.text;
        this.runMetaphor();
      });
    });

    // Metaphor Run
    this.runMetaphorBtn.addEventListener("click", () => this.runMetaphor());

    // Manual Run
    this.runManualBtn.addEventListener("click", () => this.runManual());

    // Layout Radio
    this.layoutRadios.forEach((r) => {
      r.addEventListener("change", () => {
        this.state.layout = r.value;
      });
    });

    // Presets
    document.querySelectorAll(".ref-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        this.loadInitialPreset(btn.dataset.preset);
      });
    });

    // Export SVG
    this.exportBtn.addEventListener("click", () => this.exportSvg());

    // Inspector Events
    this.closeInspectorBtn.addEventListener("click", () => this.deselectObject());

    this.scaleRange.addEventListener("input", (e) => {
      const val = parseFloat(e.target.value);
      this.scaleValue.textContent = `${val.toFixed(2)}x`;
      this.updateSelectedProperty("scale", val);
    });

    this.rotateRange.addEventListener("input", (e) => {
      const val = parseInt(e.target.value, 10);
      this.rotateValue.textContent = `${val}°`;
      this.updateSelectedProperty("rotation", val);
    });

    this.bringForwardBtn.addEventListener("click", () => this.adjustLayer(1));
    this.sendBackwardBtn.addEventListener("click", () => this.adjustLayer(-1));
    this.duplicateBtn.addEventListener("click", () => this.duplicateSelected());
    this.deleteBtn.addEventListener("click", () => this.deleteSelected());

    // Zoom
    this.zoomInBtn.addEventListener("click", () => this.setZoom(this.state.zoom + 0.1));
    this.zoomOutBtn.addEventListener("click", () => this.setZoom(this.state.zoom - 0.1));
    this.zoomFitBtn.addEventListener("click", () => this.fitToScreen());

    // Canvas click (deselect if clicking background)
    this.mountPoint.addEventListener("mousedown", (e) => this.handleCanvasMouseDown(e));
    window.addEventListener("mousemove", (e) => this.handleMouseMove(e));
    window.addEventListener("mouseup", (e) => this.handleMouseUp(e));
  }

  async loadCatalog() {
    try {
      const res = await fetch("/api/components/");
      const data = await res.json();
      if (data.success) {
        this.state.components = data.components;
        this.renderCatalogGrid();
      }
    } catch (err) {
      console.error("Ошибка загрузки каталога:", err);
    }
  }

  renderCatalogGrid() {
    this.catalogGrid.innerHTML = "";
    this.state.components.forEach((comp) => {
      const card = document.createElement("div");
      card.className = "catalog-item";
      card.dataset.id = comp.id;

      card.innerHTML = `
        <div class="catalog-thumb">${comp.preview_svg}</div>
        <div class="catalog-info">
          <span class="catalog-name" title="${comp.name_ru}">${comp.name_ru}</span>
          <button class="role-toggle" title="Переключить: Главный / Фоновый">Главный</button>
        </div>
      `;

      const roleBtn = card.querySelector(".role-toggle");
      roleBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        const cur = this.state.manualSelection.get(comp.id);
        if (cur) {
          cur.state = cur.state === "main" ? "bg" : "main";
          roleBtn.textContent = cur.state === "main" ? "Главный" : "Фоновый";
          roleBtn.classList.toggle("is-bg", cur.state === "bg");
        }
      });

      card.addEventListener("click", () => {
        if (this.state.manualSelection.has(comp.id)) {
          this.state.manualSelection.delete(comp.id);
          card.classList.remove("selected");
        } else {
          this.state.manualSelection.set(comp.id, { state: comp.default_role === "support" ? "bg" : "main" });
          card.classList.add("selected");
          const cur = this.state.manualSelection.get(comp.id);
          roleBtn.textContent = cur.state === "main" ? "Главный" : "Фоновый";
          roleBtn.classList.toggle("is-bg", cur.state === "bg");
        }
        this.updateSelectedCount();
      });

      this.catalogGrid.appendChild(card);
    });
  }

  updateSelectedCount() {
    const count = this.state.manualSelection.size;
    this.selectedCountBadge.textContent = `${count} выбрано`;
  }

  async runMetaphor() {
    const metaphor = this.metaphorInput.value.trim();
    if (!metaphor) {
      alert("Пожалуйста, введите метафору или заголовок.");
      return;
    }

    this.setStatus("ИИ анализирует метафору и подбирает ассеты...");
    this.runMetaphorBtn.disabled = true;

    try {
      const res = await fetch("/api/compose/metaphor/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          metaphor: metaphor,
          format: this.state.format,
          size: this.state.size,
          palette: this.state.palette,
          use_bg_objects: this.useBgCheck.checked,
        }),
      });

      const data = await res.json();
      if (data.success) {
        this.state.objects = data.objects;
        this.renderSvg(data.svg_content);

        // Show AI reasoning
        this.aiCard.classList.remove("hidden");
        this.aiText.textContent = data.reasoning;
        this.aiLayoutBadge.textContent = data.layout;

        this.aiTags.innerHTML = "";
        data.objects.forEach((obj) => {
          const tag = document.createElement("span");
          tag.className = "layout-tag";
          tag.textContent = `${obj.name_ru} (${obj.state === "main" ? "Главный" : "Фон"})`;
          this.aiTags.appendChild(tag);
        });

        this.setStatus(`Композиция собрана по смыслу (${data.objects.length} объектов)`);
      } else {
        alert("Ошибка генерации: " + JSON.stringify(data.errors));
      }
    } catch (err) {
      console.error("Ошибка запроса метафоры:", err);
      this.setStatus("Ошибка соединения с сервером");
    } finally {
      this.runMetaphorBtn.disabled = false;
    }
  }

  async runManual() {
    if (this.state.manualSelection.size === 0) {
      alert("Выберите хотя бы один объект из библиотеки слева.");
      return;
    }

    const components = [];
    this.state.manualSelection.forEach((val, object_id) => {
      components.append ? null : components.push({ object_id, state: val.state });
    });

    this.setStatus("Сборка композиции по выбранным компонентам...");
    this.runManualBtn.disabled = true;

    try {
      const res = await fetch("/api/compose/manual/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          components: components,
          format: this.state.format,
          size: this.state.size,
          palette: this.state.palette,
          layout: this.state.layout,
        }),
      });

      const data = await res.json();
      if (data.success) {
        this.state.objects = data.objects;
        this.renderSvg(data.svg_content);
        this.setStatus(`Собрано вручную (${data.objects.length} объектов)`);
      }
    } catch (err) {
      console.error(err);
      this.setStatus("Ошибка сборки");
    } finally {
      this.runManualBtn.disabled = false;
    }
  }

  async changePalette(newPalette) {
    this.state.palette = newPalette;
    this.setStatus(`Перекраска в палитру: ${newPalette}...`);

    try {
      const res = await fetch("/api/composition/recolor/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          objects: this.state.objects,
          to_palette: newPalette,
          format: this.state.format,
        }),
      });

      const data = await res.json();
      if (data.success) {
        this.renderSvg(data.svg_content);
        this.setStatus(`Палитра изменена: ${newPalette}`);
      }
    } catch (err) {
      console.error(err);
      this.setStatus("Ошибка перекраски");
    }
  }

  async recomputeOrUpdate() {
    if (this.state.objects.length === 0) return;
    this.setStatus("Обновление параметров сцены...");

    try {
      const res = await fetch("/api/composition/update/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          objects: this.state.objects,
          format: this.state.format,
          size: this.state.size,
          palette: this.state.palette,
        }),
      });

      const data = await res.json();
      if (data.success) {
        this.renderSvg(data.svg_content);
        this.fitToScreen();
      }
    } catch (err) {
      console.error(err);
    }
  }

  loadInitialPreset(type) {
    if (type === "edu") {
      this.metaphorInput.value = "Дистанционное образование и онлайн-лекции";
      this.runMetaphor();
    } else if (type === "fin") {
      this.metaphorInput.value = "Управление семейным бюджетом и инвестиции";
      this.runMetaphor();
    } else if (type === "team") {
      this.metaphorInput.value = "Командная интеграция и поиск решения";
      this.runMetaphor();
    }
  }

  renderSvg(svgCode) {
    this.mountPoint.innerHTML = svgCode;
    const svgEl = this.mountPoint.querySelector("svg");
    if (!svgEl) return;

    // Attach click and interaction hooks on rendered scene objects
    svgEl.querySelectorAll(".scene-object").forEach((group) => {
      const id = group.getAttribute("id");
      if (id === this.state.selectedId) {
        group.classList.add("selected");
      }
    });

    this.fitToScreen();
  }

  handleCanvasMouseDown(e) {
    const objectGroup = e.target.closest(".scene-object");
    if (objectGroup) {
      e.preventDefault();
      const id = objectGroup.getAttribute("id");
      this.selectObject(id);

      const objData = this.state.objects.find((o) => o.id === id);
      if (objData) {
        this.dragContext = {
          id: id,
          startX: e.clientX,
          startY: e.clientY,
          initialObjX: objData.x,
          initialObjY: objData.y,
          element: objectGroup,
        };
      }
    } else {
      // Clicked on background rect
      this.deselectObject();
    }
  }

  handleMouseMove(e) {
    if (!this.dragContext) return;
    e.preventDefault();

    const dx = (e.clientX - this.dragContext.startX) / this.state.zoom;
    const dy = (e.clientY - this.dragContext.startY) / this.state.zoom;

    const newX = Math.round(this.dragContext.initialObjX + dx);
    const newY = Math.round(this.dragContext.initialObjY + dy);

    const objData = this.state.objects.find((o) => o.id === this.dragContext.id);
    if (objData) {
      objData.x = newX;
      objData.y = newY;

      // Update DOM transform immediately for ultra-smooth 60fps drag
      const rot = objData.rotation || 0;
      const s = objData.scale || 1.0;
      this.dragContext.element.setAttribute("transform", `translate(${newX}, ${newY}) rotate(${rot}) scale(${s})`);
    }
  }

  handleMouseUp(e) {
    if (this.dragContext) {
      this.dragContext = null;
      this.setStatus("Позиция обновлена");
    }
  }

  selectObject(id) {
    this.state.selectedId = id;
    const obj = this.state.objects.find((o) => o.id === id);

    document.querySelectorAll(".scene-object").forEach((el) => {
      el.classList.toggle("selected", el.getAttribute("id") === id);
    });

    if (obj) {
      this.inspector.classList.remove("hidden");
      document.getElementById("inspectorTitle").textContent = `${obj.name_ru || obj.object_id} (${obj.state})`;
      this.scaleRange.value = obj.scale || 1.0;
      this.scaleValue.textContent = `${(obj.scale || 1.0).toFixed(2)}x`;
      this.rotateRange.value = obj.rotation || 0;
      this.rotateValue.textContent = `${obj.rotation || 0}°`;
    }
  }

  deselectObject() {
    this.state.selectedId = null;
    document.querySelectorAll(".scene-object").forEach((el) => el.classList.remove("selected"));
    this.inspector.classList.add("hidden");
  }

  updateSelectedProperty(prop, value) {
    const obj = this.state.objects.find((o) => o.id === this.state.selectedId);
    if (!obj) return;
    obj[prop] = value;

    // Update DOM
    const el = document.getElementById(obj.id);
    if (el) {
      const rot = obj.rotation || 0;
      const s = obj.scale || 1.0;
      el.setAttribute("transform", `translate(${obj.x}, ${obj.y}) rotate(${rot}) scale(${s})`);
    }
  }

  adjustLayer(delta) {
    const obj = this.state.objects.find((o) => o.id === this.state.selectedId);
    if (!obj) return;
    obj.z_index = (obj.z_index || 0) + delta * 5;
    this.recomputeOrUpdate();
  }

  duplicateSelected() {
    const obj = this.state.objects.find((o) => o.id === this.state.selectedId);
    if (!obj) return;
    const copy = JSON.parse(JSON.stringify(obj));
    copy.id = "c_" + Math.random().toString(36).substring(2, 8);
    copy.x += 35;
    copy.y += 35;
    copy.z_index = (obj.z_index || 0) + 1;
    this.state.objects.push(copy);
    this.recomputeOrUpdate();
    setTimeout(() => this.selectObject(copy.id), 200);
  }

  deleteSelected() {
    if (!this.state.selectedId) return;
    this.state.objects = this.state.objects.filter((o) => o.id !== this.state.selectedId);
    this.deselectObject();
    this.recomputeOrUpdate();
  }

  exportSvg() {
    const svgEl = this.mountPoint.querySelector("svg");
    if (!svgEl) {
      alert("Холст пуст.");
      return;
    }

    const svgXml = svgEl.outerHTML;
    const blob = new Blob([svgXml], { type: "image/svg+xml;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `illustration_${this.state.format}_${this.state.palette}.svg`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    this.setStatus("SVG файл успешно скачан!");
  }

  setZoom(val) {
    this.state.zoom = Math.max(0.3, Math.min(2.0, val));
    this.viewport.style.transform = `scale(${this.state.zoom})`;
    this.zoomText.textContent = `${Math.round(this.state.zoom * 100)}%`;
  }

  fitToScreen() {
    const svgEl = this.mountPoint.querySelector("svg");
    if (!svgEl) return;
    const w = parseFloat(svgEl.getAttribute("width")) || 1200;
    const h = parseFloat(svgEl.getAttribute("height")) || 630;

    const availableW = this.container.clientWidth - 80;
    const availableH = this.container.clientHeight - 80;

    const scaleW = availableW / w;
    const scaleH = availableH / h;
    const bestFit = Math.min(scaleW, scaleH, 1.0);
    this.setZoom(bestFit);
  }

  setStatus(text) {
    this.statusText.textContent = text;
  }
}

// Start app on DOMContentLoaded
document.addEventListener("DOMContentLoaded", () => {
  window.app = new ComposerApp();
});
