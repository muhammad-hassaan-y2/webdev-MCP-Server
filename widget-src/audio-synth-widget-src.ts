import { App, PostMessageTransport } from "@modelcontextprotocol/ext-apps";

interface SynthConfig {
  title: string;
  waveform: OscillatorType;
  baseFrequency: number;
  filterCutoff: number;
  resonance: number;
  description: string;
  equation: string;
}

let app: App;
let audioCtx: AudioContext | null = null;
let osc: OscillatorNode | null = null;
let filter: BiquadFilterNode | null = null;
let gainNode: GainNode | null = null;
let analyser: AnalyserNode | null = null;

let isSoundActive = false;
let currentWaveform: OscillatorType = "sawtooth";
let currentFreq = 220;
let currentCutoff = 1800;
let currentVolume = 0.5;

const el = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;

function initAudio() {
  if (audioCtx) return;
  const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
  audioCtx = new AudioContextClass();

  analyser = audioCtx.createAnalyser();
  analyser.fftSize = 2048;

  filter = audioCtx.createBiquadFilter();
  filter.type = "lowpass";
  filter.frequency.setValueAtTime(currentCutoff, audioCtx.currentTime);
  filter.Q.setValueAtTime(4.0, audioCtx.currentTime);

  gainNode = audioCtx.createGain();
  gainNode.gain.setValueAtTime(0, audioCtx.currentTime);

  // Signal routing: Filter -> Gain -> Analyser -> Output
  filter.connect(gainNode);
  gainNode.connect(analyser);
  analyser.connect(audioCtx.destination);

  drawOscilloscope();
}

function startTone(freq: number) {
  initAudio();
  if (!audioCtx || !filter || !gainNode) return;

  if (audioCtx.state === "suspended") {
    audioCtx.resume();
  }

  // Stop old oscillator if any
  if (osc) {
    try { osc.stop(); osc.disconnect(); } catch (e) {}
  }

  osc = audioCtx.createOscillator();
  osc.type = currentWaveform;
  osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
  osc.connect(filter);
  osc.start();

  // Attack envelope
  gainNode.gain.cancelScheduledValues(audioCtx.currentTime);
  gainNode.gain.setValueAtTime(gainNode.gain.value, audioCtx.currentTime);
  gainNode.gain.linearRampToValueAtTime(currentVolume, audioCtx.currentTime + 0.05);

  isSoundActive = true;
  el("audio-indicator").textContent = `Playing: ${Math.round(freq)} Hz (${currentWaveform})`;
  el("audio-indicator").style.color = "#38bdf8";
}

function stopTone() {
  if (!audioCtx || !gainNode) return;

  // Release envelope
  gainNode.gain.cancelScheduledValues(audioCtx.currentTime);
  gainNode.gain.setValueAtTime(gainNode.gain.value, audioCtx.currentTime);
  gainNode.gain.linearRampToValueAtTime(0.0001, audioCtx.currentTime + 0.15);

  setTimeout(() => {
    if (!isSoundActive && osc) {
      try { osc.stop(); osc.disconnect(); osc = null; } catch (e) {}
    }
  }, 160);

  isSoundActive = false;
  el("audio-indicator").textContent = "Idle — click keys or drag sliders";
  el("audio-indicator").style.color = "#94a3b8";
}

function drawOscilloscope() {
  const canvas = el<HTMLCanvasElement>("oscilloscope");
  const ctx = canvas.getContext("2d");
  if (!ctx || !analyser) return;

  const width = (canvas.width = canvas.parentElement?.clientWidth || 600);
  const height = (canvas.height = 160);

  const bufferLength = analyser.frequencyBinCount;
  const dataArray = new Uint8Array(bufferLength);

  function render() {
    requestAnimationFrame(render);
    if (!analyser || !ctx) return;

    analyser.getByteTimeDomainData(dataArray);

    ctx.fillStyle = "#040711";
    ctx.fillRect(0, 0, width, height);

    // Draw Grid
    ctx.lineWidth = 1;
    ctx.strokeStyle = "#0f172a";
    ctx.beginPath();
    ctx.moveTo(0, height / 2);
    ctx.lineTo(width, height / 2);
    ctx.stroke();

    // Draw Waveform
    ctx.lineWidth = 2.5;
    ctx.strokeStyle = isSoundActive ? "#38bdf8" : "#334155";
    ctx.shadowBlur = isSoundActive ? 10 : 0;
    ctx.shadowColor = "#38bdf8";

    ctx.beginPath();
    const sliceWidth = (width * 1.0) / bufferLength;
    let x = 0;

    for (let i = 0; i < bufferLength; i++) {
      const v = dataArray[i] / 128.0;
      const y = (v * height) / 2;

      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }

      x += sliceWidth;
    }

    ctx.lineTo(width, height / 2);
    ctx.stroke();
  }

  render();
}

function setupEvents() {
  // Waveform buttons
  const waveBtns = document.querySelectorAll<HTMLButtonElement>("#synth-widget .wave-btn");
  waveBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      waveBtns.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      currentWaveform = (btn.getAttribute("data-wave") || "sawtooth") as OscillatorType;
      if (osc) osc.type = currentWaveform;
    });
  });

  // Pitch slider
  const pitchSlider = el<HTMLInputElement>("param-pitch");
  pitchSlider.addEventListener("input", () => {
    currentFreq = Number(pitchSlider.value);
    el("val-pitch").textContent = `${currentFreq} Hz`;
    if (osc && audioCtx) {
      osc.frequency.setValueAtTime(currentFreq, audioCtx.currentTime);
    }
    startTone(currentFreq);
  });
  pitchSlider.addEventListener("change", () => stopTone());

  // Filter slider
  const filterSlider = el<HTMLInputElement>("param-filter");
  filterSlider.addEventListener("input", () => {
    currentCutoff = Number(filterSlider.value);
    el("val-filter").textContent = `${currentCutoff} Hz`;
    if (filter && audioCtx) {
      filter.frequency.setValueAtTime(currentCutoff, audioCtx.currentTime);
    }
  });

  // Volume slider
  const volSlider = el<HTMLInputElement>("param-vol");
  volSlider.addEventListener("input", () => {
    currentVolume = Number(volSlider.value) / 100;
    el("val-vol").textContent = `${volSlider.value}%`;
    if (gainNode && audioCtx && isSoundActive) {
      gainNode.gain.setValueAtTime(currentVolume, audioCtx.currentTime);
    }
  });

  // Piano keys
  const keys = document.querySelectorAll<HTMLElement>("#synth-widget .piano-key");
  keys.forEach((key) => {
    const freq = Number(key.getAttribute("data-freq"));

    const press = () => {
      key.classList.add("pressed");
      pitchSlider.value = String(Math.round(freq));
      el("val-pitch").textContent = `${Math.round(freq)} Hz`;
      startTone(freq);
    };

    const release = () => {
      key.classList.remove("pressed");
      stopTone();
    };

    key.addEventListener("mousedown", press);
    key.addEventListener("mouseup", release);
    key.addEventListener("mouseleave", release);

    key.addEventListener("touchstart", (e) => { e.preventDefault(); press(); }, { passive: false });
    key.addEventListener("touchend", (e) => { e.preventDefault(); release(); }, { passive: false });
  });
}

async function init() {
  setupEvents();

  app = new App({ name: "audio-synth-widget", version: "1.0.0" }, {});

  app.ontoolresult = (params: any) => {
    const sc = params?.structuredContent;
    if (sc?.synthConfig) {
      const cfg = sc.synthConfig as SynthConfig;
      el("synth-name").textContent = cfg.title || "Audio Synthesizer";
      el("synth-preset-desc").textContent = cfg.description || "";

      if (cfg.waveform) {
        currentWaveform = cfg.waveform;
        document.querySelectorAll<HTMLButtonElement>("#synth-widget .wave-btn").forEach((btn) => {
          if (btn.getAttribute("data-wave") === cfg.waveform) btn.classList.add("active");
          else btn.classList.remove("active");
        });
      }

      if (cfg.baseFrequency) {
        currentFreq = cfg.baseFrequency;
        el<HTMLInputElement>("param-pitch").value = String(currentFreq);
        el("val-pitch").textContent = `${currentFreq} Hz`;
      }

      if (cfg.filterCutoff) {
        currentCutoff = cfg.filterCutoff;
        el<HTMLInputElement>("param-filter").value = String(currentCutoff);
        el("val-filter").textContent = `${currentCutoff} Hz`;
      }
    }
  };

  await app.connect(new PostMessageTransport(window.parent, window.parent));
}

init();
