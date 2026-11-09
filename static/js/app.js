/* Inglés para investigar y presentar — interacción del navegador.
 * Sin dependencias. Módulos:
 *  1. Registro de ayudas y tiempo por actividad (AUD02, §11)
 *  2. Voz sintetizada del navegador con velocidad, pausa y repetición (AUD01, AUD02)
 *  3. Grabadora: prueba de micrófono, grabación, escucha, regrabación, subida,
 *     transcripción editable y manejo de fallas (AUD03, AUD05, AUD08)
 *  4. Contador de palabras
 */
(function () {
  "use strict";

  // ------------------------------------------------------------ 1. ayudas y tiempo
  var pageHelps = new Set();

  function formOf(el) {
    var art = el.closest("article.activity");
    return art ? art.querySelector("form.activity-form") : null;
  }

  function addHelp(form, help) {
    if (!form || !help) return;
    var input = form.querySelector('input[name="helps_csv"]');
    if (!input) return;
    var set = new Set(input.value ? input.value.split(",") : []);
    set.add(help);
    input.value = Array.from(set).join(",");
  }

  document.querySelectorAll("details[data-help]").forEach(function (d) {
    d.addEventListener("toggle", function () { if (d.open) addHelp(formOf(d), d.dataset.help); });
  });
  document.querySelectorAll("details[data-help-page]").forEach(function (d) {
    d.addEventListener("toggle", function () { if (d.open) pageHelps.add(d.dataset.helpPage); });
  });
  document.querySelectorAll("details[data-lexis-hint]").forEach(function (d) {
    d.addEventListener("toggle", function () {
      var f = d.closest("form"); var h = f && f.querySelector("[data-helped]");
      if (d.open && h) h.value = "1";
    });
  });

  document.querySelectorAll("form.activity-form").forEach(function (form) {
    var started = null;
    function start() { if (started === null) started = Date.now(); }
    form.addEventListener("focusin", start);
    form.addEventListener("input", start);
    var art = form.closest("article.activity");
    if (art) art.addEventListener("click", start);
    form.addEventListener("submit", function (ev) {
      var elapsed = form.querySelector('input[name="elapsed_ms"]');
      if (elapsed && started !== null) elapsed.value = String(Date.now() - started);
      pageHelps.forEach(function (h) { addHelp(form, h); });
      if (form.dataset.type === "oral") {
        var rec = form.querySelector("[data-recording-id]");
        var noMic = form.querySelector('input[name="no_mic"]');
        if (rec && !rec.value && !(noMic && noMic.checked)) {
          ev.preventDefault();
          var st = form.querySelector(".rec-status");
          if (st) st.textContent = "Graba tu respuesta antes de enviarla, o marca «No puedo grabar ahora».";
        }
      }
    });
  });

  // ------------------------------------------------------------ 2. voz sintetizada (vía AppVoice)
  document.querySelectorAll("[data-tts]").forEach(function (box) {
    var play = box.querySelector('[data-action="play"]');
    var pause = box.querySelector('[data-action="pause"]');
    var rate = box.querySelector("[data-rate]");
    if (!window.AppVoice || !AppVoice.supported) {
      box.classList.add("tts-unavailable");
      if (play) play.disabled = true;
      if (pause) pause.disabled = true;
      var note = document.createElement("span");
      note.className = "small muted";
      note.textContent = " Este navegador no ofrece voz sintetizada; usa la transcripción cuando esté disponible.";
      box.appendChild(note);
      return;
    }
    play.addEventListener("click", function () {
      var r = parseFloat(rate ? rate.value : "1") || 1;
      var form = formOf(box);
      if (r < 1) addHelp(form, "slow_audio");
      if (box.dataset.ttsHelp) addHelp(form, box.dataset.ttsHelp);
      // Acento según el perfil: en-US (predeterminado), en-GB, o "intl" = el acento que trae cada audio.
      var pref = document.body.dataset.accent || "en-US", own = box.dataset.lang || "en-US";
      var lang = own.indexOf("es") === 0 ? "es-US" : (pref === "intl" ? own : pref);
      AppVoice.speak([{ text: box.dataset.text || "", lang: lang }], { rate: r, owner: box, enRate: 1 });
    });
    pause.addEventListener("click", function () {
      if (AppVoice.isPaused()) AppVoice.resume(); else if (AppVoice.isSpeaking()) AppVoice.pause();
    });
  });

  // ------------------------------------------------------------ 3. grabadora
  function pickMime() {
    if (!window.MediaRecorder || !MediaRecorder.isTypeSupported) return "";
    var options = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus"];
    for (var i = 0; i < options.length; i++) if (MediaRecorder.isTypeSupported(options[i])) return options[i];
    return "";
  }

  function fmt(s) { var m = Math.floor(s / 60); var r = Math.floor(s % 60); return m + ":" + (r < 10 ? "0" : "") + r; }

  function micErrorMessage(err) {
    var name = err && err.name;
    if (name === "NotAllowedError" || name === "SecurityError")
      return "Micrófono bloqueado: autoriza el acceso en el candado de la barra de direcciones y vuelve a intentar. No es un error de idioma.";
    if (name === "NotFoundError" || name === "OverconstrainedError")
      return "No se encontró un micrófono. Conecta uno o marca «No puedo grabar ahora».";
    if (name === "NotReadableError")
      return "El micrófono está en uso por otra aplicación.";
    return "No fue posible usar el micrófono (" + (name || "error desconocido") + ").";
  }

  document.querySelectorAll("[data-recorder]").forEach(function (box) {
    var form = box.closest("form");
    var btnTest = box.querySelector('[data-action="test"]');
    var btnStart = box.querySelector('[data-action="start"]');
    var btnStop = box.querySelector('[data-action="stop"]');
    var timer = box.querySelector(".rec-timer");
    var meter = box.querySelector("[data-level]");
    var status = box.querySelector(".rec-status");
    var playback = box.querySelector("[data-playback]");
    var transcript = box.querySelector("[data-transcript]");
    var recId = box.querySelector("[data-recording-id]");
    var minS = parseFloat(box.dataset.min || "0");
    var maxS = parseFloat(box.dataset.max || "120");
    var csrf = form ? form.querySelector('input[name="csrfmiddlewaretoken"]') : null;

    var stream = null, recorder = null, chunks = [], t0 = 0, tick = null, peak = 0;
    var audioCtx = null, analyser = null, rafId = null, recognition = null;

    function say(msg) { if (status) status.textContent = msg; }

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || !window.MediaRecorder) {
      btnTest.disabled = btnStart.disabled = true;
      say("Este navegador no permite grabar audio. Puedes continuar marcando «No puedo grabar ahora»: la habilidad oral quedará pendiente de evidencia.");
      return;
    }

    function startLevel(s) {
      try {
        var Ctx = window.AudioContext || window.webkitAudioContext;
        audioCtx = new Ctx();
        analyser = audioCtx.createAnalyser();
        analyser.fftSize = 1024;
        audioCtx.createMediaStreamSource(s).connect(analyser);
        var buf = new Uint8Array(analyser.fftSize);
        (function loop() {
          analyser.getByteTimeDomainData(buf);
          var sum = 0;
          for (var i = 0; i < buf.length; i++) { var x = (buf[i] - 128) / 128; sum += x * x; }
          var rms = Math.sqrt(sum / buf.length);
          var level = Math.min(1, rms * 4);
          peak = Math.max(peak, level);
          if (meter) meter.value = level;
          rafId = requestAnimationFrame(loop);
        })();
      } catch (e) { /* el medidor es opcional */ }
    }

    function stopLevel() {
      if (rafId) cancelAnimationFrame(rafId);
      rafId = null;
      if (audioCtx) { audioCtx.close().catch(function () {}); audioCtx = null; }
      if (meter) meter.value = 0;
    }

    function release() {
      stopLevel();
      if (stream) { stream.getTracks().forEach(function (t) { t.stop(); }); stream = null; }
    }

    btnTest.addEventListener("click", function () {
      peak = 0;
      navigator.mediaDevices.getUserMedia({ audio: true }).then(function (s) {
        stream = s;
        startLevel(s);
        say("Habla unos segundos: el medidor debería moverse.");
        setTimeout(function () {
          var ok = peak > 0.08;
          release();
          say(ok ? "Micrófono funcionando." : "No se detectó voz: revisa que el micrófono correcto esté seleccionado y no esté silenciado.");
        }, 3000);
      }).catch(function (err) { say(micErrorMessage(err)); });
    });

    function startRecognition() {
      var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SR || !transcript) return;
      try {
        recognition = new SR();
        recognition.lang = "en-US";
        recognition.continuous = true;
        recognition.interimResults = false;
        recognition.onresult = function (e) {
          for (var i = e.resultIndex; i < e.results.length; i++) {
            if (e.results[i].isFinal) transcript.value = (transcript.value + " " + e.results[i][0].transcript).trim();
          }
        };
        recognition.onerror = function () { /* la transcripción es opcional */ };
        recognition.start();
      } catch (e) { recognition = null; }
    }

    btnStart.addEventListener("click", function () {
      peak = 0; chunks = [];
      if (recId) recId.value = "";
      if (transcript) transcript.value = "";
      navigator.mediaDevices.getUserMedia({ audio: true }).then(function (s) {
        stream = s;
        var mime = pickMime();
        try { recorder = mime ? new MediaRecorder(s, { mimeType: mime }) : new MediaRecorder(s); }
        catch (e) { recorder = new MediaRecorder(s); }
        recorder.ondataavailable = function (e) { if (e.data && e.data.size) chunks.push(e.data); };
        recorder.onstop = onStop;
        recorder.start();
        startLevel(s);
        startRecognition();
        t0 = Date.now();
        btnStart.disabled = true; btnStop.disabled = false; btnTest.disabled = true;
        say("Grabando… (se detiene sola a los " + maxS + " s)");
        tick = setInterval(function () {
          var el = (Date.now() - t0) / 1000;
          timer.textContent = fmt(el);
          if (el >= maxS) btnStop.click();
        }, 250);
      }).catch(function (err) { say(micErrorMessage(err)); });
    });

    btnStop.addEventListener("click", function () {
      if (recorder && recorder.state !== "inactive") recorder.stop();
      if (recognition) { try { recognition.stop(); } catch (e) {} }
      clearInterval(tick);
      btnStop.disabled = true;
    });

    function onStop() {
      var duration = (Date.now() - t0) / 1000;
      var silent = peak < 0.06;
      release();
      btnStart.disabled = false; btnTest.disabled = false;
      btnStart.textContent = "● Regrabar";
      var type = (recorder && recorder.mimeType) || "audio/webm";
      var blob = new Blob(chunks, { type: type });
      playback.src = URL.createObjectURL(blob);
      playback.hidden = false;
      if (!blob.size) { say("No se capturó audio. Vuelve a intentar."); return; }
      if (silent) {
        say("Se detectó silencio o un audio muy bajo. No es un error de idioma: revisa el micrófono y vuelve a grabar.");
        return;
      }
      var warn = duration < minS ? " Duró " + Math.round(duration) + " s: menos que el objetivo de " + minS + " s." : "";
      say("Subiendo la grabación…");
      var fd = new FormData();
      fd.append("audio", blob, "grabacion." + (type.indexOf("mp4") >= 0 ? "m4a" : type.indexOf("ogg") >= 0 ? "ogg" : "webm"));
      fd.append("activity_id", box.dataset.activity);
      fd.append("package_id", box.dataset.package);
      fd.append("duration_s", duration.toFixed(1));
      setTimeout(function () { // dar tiempo al último resultado del reconocimiento
        if (transcript) fd.append("transcript", transcript.value);
        fetch(box.dataset.upload, {
          method: "POST", body: fd, credentials: "same-origin",
          headers: { "X-CSRFToken": csrf ? csrf.value : "" }
        }).then(function (r) {
          return r.json().then(function (j) { return { ok: r.ok, j: j }; });
        }).then(function (res) {
          if (!res.ok) { say(res.j.error || "El servidor rechazó la grabación."); return; }
          recId.value = res.j.id;
          say("Grabación guardada (" + Math.round(duration) + " s). Escúchala, compárala con el modelo, corrige la transcripción y envía." + warn);
        }).catch(function () {
          say("Servicio no disponible: la grabación no se guardó. Revisa tu conexión y vuelve a grabar.");
        });
      }, 600);
    }
  });

  // ------------------------------------------------------------ 4. contador de palabras
  document.querySelectorAll("textarea[data-words]").forEach(function (ta) {
    var out = ta.parentElement.querySelector("[data-word-count]");
    var min = ta.dataset.min, max = ta.dataset.max;
    function update() {
      var n = (ta.value.match(/[A-Za-zÀ-ÿ0-9]+(?:['\-.,][A-Za-zÀ-ÿ0-9]+)*/g) || []).length;
      if (out) out.textContent = n + " palabra" + (n === 1 ? "" : "s") + (min ? " · meta " + min + "–" + max : "");
    }
    ta.addEventListener("input", update);
    update();
  });
})();
