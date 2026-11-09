/* PWA: registro del service worker, botón de instalación y menú móvil. */
(function () {
  "use strict";

  // ---------------------------------------------------------- menú móvil
  var toggle = document.querySelector("[data-nav-toggle]");
  var nav = document.getElementById("main-nav");
  // altura real de la barra: el menú móvil se abre justo debajo
  var bar = document.querySelector(".topbar");
  function barHeight() { if (bar) document.documentElement.style.setProperty("--topbar-h", bar.getBoundingClientRect().height + "px"); }
  barHeight(); window.addEventListener("resize", barHeight);
  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
      document.body.classList.toggle("nav-open", open);
    });
  }

  // ---------------------------------------------------------- tablas desplazables en móvil
  document.querySelectorAll("table.table").forEach(function (t) {
    if (t.parentElement && t.parentElement.classList.contains("table-wrap")) return;
    var w = document.createElement("div");
    w.className = "table-wrap";
    t.parentNode.insertBefore(w, t);
    w.appendChild(t);
  });

  // ---------------------------------------------------------- service worker
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(function () {});
    });
  }

  // ---------------------------------------------------------- ¿app instalada?
  var standalone = window.matchMedia("(display-mode: standalone)").matches ||
                   window.matchMedia("(display-mode: window-controls-overlay)").matches ||
                   window.navigator.standalone === true;
  if (standalone) document.documentElement.classList.add("is-app");

  // En la app instalada, el ingreso pregunta si mantener la sesión abierta (y lo deja marcado).
  var remember = document.querySelector('input[name="remember"]');
  if (remember && standalone) {
    remember.checked = true;
    var note = document.querySelector("[data-app-note]");
    if (note) note.hidden = false;
  }

  // ---------------------------------------------------------- instalación según el equipo
  var KEY = "ingles-install-dismissed";
  var fab = document.querySelector("[data-install-fab]");
  var sheet = document.querySelector("[data-install-sheet]");
  if (!fab || !sheet) return;

  function store(get, value) {
    try {
      if (get) return window.localStorage.getItem(KEY);
      window.localStorage.setItem(KEY, value);
    } catch (e) { return null; }
    return null;
  }

  // Detecta el equipo para mostrar las instrucciones correctas.
  var ua = navigator.userAgent || "";
  var touchMac = navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1;   // iPad con iPadOS
  var isIOS = /iPad|iPhone|iPod/.test(ua) || touchMac;
  var isAndroid = /Android/i.test(ua);
  var isMac = !isIOS && /Macintosh|Mac OS X/.test(ua);
  var isWindows = /Windows/.test(ua);
  var isFirefox = /Firefox|FxiOS/.test(ua);
  var isEdge = /Edg\//.test(ua);
  var isSafari = /Safari/.test(ua) && !/Chrome|CriOS|Chromium|Edg|EdgiOS|FxiOS|OPR|SamsungBrowser/.test(ua);
  var isIPad = /iPad/.test(ua) || touchMac;
  var platform =
      isIOS ? (isSafari ? "ios" : "ios-other")
    : isAndroid ? "android"
    : isMac ? (isSafari ? "mac-safari" : (isFirefox ? "desktop-firefox" : "desktop"))
    : isFirefox ? "desktop-firefox"
    : "desktop";
  var TITLES = {
    "ios": isIPad ? "Instala la app en tu iPad" : "Instala la app en tu iPhone",
    "ios-other": isIPad ? "Instala la app en tu iPad" : "Instala la app en tu iPhone",
    "android": "Instala la app en tu teléfono Android",
    "mac-safari": "Instala la app en tu Mac",
    "desktop": isWindows ? "Instala la app en tu computador Windows" : (isMac ? "Instala la app en tu Mac" : "Instala la app en tu computador"),
    "desktop-firefox": "Instala la app en tu computador"
  };
  var deferred = null;

  function openSheet() {
    var title = sheet.querySelector("#install-title");
    if (title) title.textContent = TITLES[platform];
    sheet.querySelectorAll("[data-install-platform]").forEach(function (el) {
      el.hidden = el.getAttribute("data-install-platform").split(" ").indexOf(platform) === -1;
    });
    var native = sheet.querySelector("[data-install-native-wrap]");
    if (native) native.hidden = !deferred;
    var manual = sheet.querySelector("[data-install-manual]");
    if (manual) manual.hidden = !!deferred && (platform === "android" || platform === "desktop");
    sheet.querySelectorAll("[data-edge-only]").forEach(function (el) { el.hidden = !isEdge; });
    sheet.querySelectorAll("[data-chrome-only]").forEach(function (el) { el.hidden = isEdge; });
    sheet.hidden = false;
    document.body.classList.add("sheet-open");
  }

  function closeAll(remember) {
    sheet.hidden = true;
    fab.hidden = true;
    document.body.classList.remove("sheet-open");
    if (remember) store(false, String(Date.now()));
  }

  function maybeShowFab() {
    if (standalone) return;
    var dismissed = store(true);
    // Si se cerró, vuelve a ofrecerse a los 14 días.
    if (dismissed && Date.now() - parseInt(dismissed, 10) < 14 * 864e5) return;
    fab.hidden = false;
    fab.classList.add("pop");
  }

  function nativeInstall() {
    if (!deferred) return openSheet();
    deferred.prompt();
    deferred.userChoice.then(function () { deferred = null; closeAll(true); });
  }

  window.addEventListener("beforeinstallprompt", function (e) {
    e.preventDefault();               // Chrome / Edge / Samsung: guardamos el aviso nativo para nuestro botón
    deferred = e;
    maybeShowFab();
  });
  // Safari, Firefox y navegadores sin aviso nativo: el botón abre las instrucciones de ese equipo.
  if (!standalone) setTimeout(function () { if (!deferred) maybeShowFab(); }, 1500);

  document.querySelectorAll("[data-install-open]").forEach(function (b) {
    b.addEventListener("click", function () {
      if (standalone) return;
      if (deferred && (platform === "android" || platform === "desktop")) nativeInstall();
      else openSheet();
    });
  });
  document.querySelectorAll("[data-install-dismiss]").forEach(function (b) {
    b.addEventListener("click", function () { closeAll(true); });
  });
  var nativeBtn = sheet.querySelector("[data-install-native]");
  if (nativeBtn) nativeBtn.addEventListener("click", nativeInstall);
  sheet.addEventListener("click", function (e) { if (e.target === sheet) closeAll(false); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape" && !sheet.hidden) closeAll(false); });
  window.addEventListener("appinstalled", function () { closeAll(true); });
})();
