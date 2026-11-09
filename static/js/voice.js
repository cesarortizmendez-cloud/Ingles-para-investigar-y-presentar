/* AppVoice: única salida de voz de la aplicación.
 * Todo audio sintetizado (saludo del tutor, palabras, ejemplos, escucha, dictado) pasa por aquí,
 * y el rostro del tutor escucha sus eventos para moverse cada vez que suena una voz.
 *
 * Preferencia por defecto: voz MASCULINA de Estados Unidos (en-US) para inglés y voz masculina
 * en español de EE. UU./Latinoamérica para español. El alumno puede elegir otra (se guarda en
 * el navegador). Las voces disponibles dependen del navegador y del sistema operativo.
 *
 * Eventos: start {seg,index,owner,rate} · boundary {word,charIndex,seg,index,rate,owner}
 *          segment {seg,index,gotBoundary} · end {owner,cancelled} · idle
 */
(function () {
  "use strict";
  var synth = window.speechSynthesis || null;
  var listeners = {};
  var KEY = "ingles-voice-pref";
  var MALE = /\b(male|guy|david|mark|andrew|brian|christopher|eric|roger|steffan|davis|tony|jason|aaron|alex|fred|tom|daniel|ryan|ralph|bruce|jorge|ra[uú]l|alonso|pablo|diego|gerardo|cecilio|enrique|juan|carlos|lorenzo|hombre|masculin)/i;
  var FEMALE = /female|mujer|zira|aria|jenny|michelle|samantha|victoria|karen|moira|tessa|ava|emma|ana\b|paulina|sabina|helena|laura|dalia|paloma|elena|m[oó]nica|catalina|google us english|google español/i;
  var voices = [];

  function emit(ev, data) {
    (listeners[ev] || []).slice().forEach(function (fn) { try { fn(data || {}); } catch (e) { /* un oyente no debe cortar la voz */ } });
  }
  function load() { voices = synth ? synth.getVoices() : []; emit("voices", {}); }
  if (synth) {
    load();
    if (synth.addEventListener) synth.addEventListener("voiceschanged", load);
    else synth.onvoiceschanged = load;
  }
  function norm(l) { return (l || "").replace("_", "-").toLowerCase(); }
  function prefs() { try { return JSON.parse(window.localStorage.getItem(KEY) || "{}"); } catch (e) { return {}; } }
  function setPreferred(base, uri) {
    var p = prefs(); if (uri) p[base] = uri; else delete p[base];
    try { window.localStorage.setItem(KEY, JSON.stringify(p)); } catch (e) { /* sin almacenamiento */ }
  }
  function score(v, lang) {
    var l = norm(v.lang), base = lang.slice(0, 2), s = 0;
    var region = base === "en" ? ["en-us", "en-ca"] : ["es-us", "es-mx", "es-419", "es-cl", "es-co", "es-ar", "es-es"];
    var ri = region.indexOf(l);
    s += ri === -1 ? 0 : (region.length - ri) * 12;
    var isFemale = FEMALE.test(v.name) || /female/i.test(v.name);
    if (MALE.test(v.name) && !isFemale) s += 100;
    if (isFemale) s -= 60;
    if (/natural|neural|online|premium|enhanced/i.test(v.name)) s += 30;
    return s;
  }
  function list(lang) {
    if (!voices.length) load();
    var base = lang.slice(0, 2);
    return voices.filter(function (v) { return norm(v.lang).indexOf(base) === 0; })
      .sort(function (a, b) { return score(b, lang) - score(a, lang); });
  }
  function pick(lang) {
    var base = lang.slice(0, 2), wanted = prefs()[base], L = list(lang);
    if (wanted) { for (var i = 0; i < L.length; i++) if (L[i].voiceURI === wanted) return L[i]; }
    return L[0] || null;
  }

  var token = 0, speaking = false;
  function cancel(silent) {
    token++;
    if (synth) synth.cancel();
    var was = speaking; speaking = false;
    if (!silent && was) { emit("end", { cancelled: true }); emit("idle", {}); }
  }

  /** speak("texto", {lang}) o speak([{text, lang}, …], {owner, rate}) */
  function speak(segs, opts) {
    if (!synth) return false;
    opts = opts || {};
    if (typeof segs === "string") segs = [{ text: segs, lang: opts.lang || "en-US" }];
    cancel(false);
    var my = ++token, i = 0;
    if (synth.resume) synth.resume();
    function next() {
      if (my !== token) return;
      if (i >= segs.length) { speaking = false; emit("end", { owner: opts.owner }); emit("idle", {}); return; }
      var seg = segs[i], idx = i; i++;
      var text = String(seg.text || "").replace(/\|/g, " ").replace(/\s+/g, " ").trim();
      if (!text) { next(); return; }
      var lang = seg.lang || opts.lang || "en-US";
      var u = new SpeechSynthesisUtterance(text);
      var v = pick(lang);
      u.lang = v ? v.lang : lang;
      if (v) u.voice = v;
      var rate = (opts.rate || 1) * (lang.indexOf("en") === 0 ? (opts.enRate || 0.94) : 1);
      u.rate = rate;
      u.pitch = opts.pitch || 1;
      var got = false, info = { seg: { text: text, lang: lang }, index: idx, owner: opts.owner, rate: rate };
      u.onstart = function () { if (my !== token) return; speaking = true; emit("start", info); };
      u.onboundary = function (e) {
        if (my !== token || (e.name && e.name !== "word")) return;
        got = true;
        var m = text.substr(e.charIndex).match(/^[A-Za-zÀ-ÿ0-9'’-]+/);
        emit("boundary", { seg: info.seg, index: idx, owner: opts.owner, rate: rate, charIndex: e.charIndex, word: m ? m[0] : "" });
      };
      u.onend = function () {
        if (my !== token) return;
        emit("segment", { seg: info.seg, index: idx, owner: opts.owner, gotBoundary: got });
        setTimeout(next, opts.gap != null ? opts.gap : 200);
      };
      u.onerror = function () { if (my !== token) return; setTimeout(next, 0); };
      synth.speak(u);
    }
    next();
    return true;
  }

  window.AppVoice = {
    supported: !!synth && typeof window.SpeechSynthesisUtterance === "function",
    speak: speak,
    cancel: function () { cancel(false); },
    pause: function () { if (synth) synth.pause(); },
    resume: function () { if (synth) synth.resume(); },
    isPaused: function () { return !!(synth && synth.paused); },
    isSpeaking: function () { return speaking; },
    on: function (ev, fn) { (listeners[ev] = listeners[ev] || []).push(fn); },
    list: list, pick: pick, prefs: prefs, setPreferred: setPreferred,
  };
  window.addEventListener("pagehide", function () { if (synth) synth.cancel(); });
})();
