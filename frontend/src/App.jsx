import { useMemo, useRef, useState } from "react";

const API_BASE = "/api";

export default function App() {
  const [session, setSession] = useState(null); // {id, segments, words}
  const [checked, setChecked] = useState({}); // word.index -> bool
  const [audioUrl, setAudioUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(null); // null | 0..1
  const [error, setError] = useState(null);
  const [censoring, setCensoring] = useState(false);
  const audioRef = useRef(null);
  const fileInputRef = useRef(null);

  const flaggedCount = useMemo(
    () => (session ? session.words.filter((w) => w.flagged).length : 0),
    [session]
  );

  async function handleFile(file) {
    if (!file) return;
    setError(null);
    setLoading(true);
    setSession(null);
    setChecked({});

    const url = URL.createObjectURL(file);
    setAudioUrl(url);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API_BASE}/transcribe`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) throw new Error(`Error ${res.status} al transcribir`);
      const { id } = await res.json();
      const data = await pollTranscription(id);
      setSession(data);

      const initialChecked = {};
      for (const w of data.words) {
        if (w.flagged) initialChecked[w.index] = true;
      }
      setChecked(initialChecked);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
      setProgress(null);
    }
  }

  async function pollTranscription(id) {
    for (;;) {
      await new Promise((r) => setTimeout(r, 3000));
      const res = await fetch(`${API_BASE}/transcribe/status/${id}`);
      if (!res.ok) throw new Error(`Error ${res.status} al consultar estado`);
      const status = await res.json();
      if (status.state === "error") {
        throw new Error(status.error || "Error al transcribir");
      }
      if (status.state === "done") {
        const tr = await fetch(`${API_BASE}/transcript/${id}`);
        if (!tr.ok) throw new Error(`Error ${tr.status} al obtener transcripcion`);
        return await tr.json();
      }
      setProgress(status.state === "processing" ? status.progress ?? 0 : 0);
    }
  }

  function onDrop(e) {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    handleFile(file);
  }

  function toggleWord(index) {
    setChecked((prev) => ({ ...prev, [index]: !prev[index] }));
  }

  function jumpTo(time) {
    if (audioRef.current) {
      audioRef.current.currentTime = time;
      audioRef.current.play();
    }
  }

  async function generateCensored() {
    if (!session) return;
    const ranges = session.words
      .filter((w) => checked[w.index])
      .map((w) => ({ start: w.start, end: w.end }));

    if (ranges.length === 0) {
      setError("No hay palabras seleccionadas para censurar");
      return;
    }

    setCensoring(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/censor`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: session.id, ranges, mode: "beep" }),
      });
      if (!res.ok) throw new Error(`Error ${res.status} al censurar`);
      const blob = await res.blob();
      downloadBlob(blob, "audio_censurado.wav");
    } catch (err) {
      setError(err.message);
    } finally {
      setCensoring(false);
    }
  }

  function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  async function downloadTranscript(fmt) {
    if (!session) return;
    const res = await fetch(`${API_BASE}/transcript/export/${session.id}?fmt=${fmt}`);
    if (!res.ok) {
      setError(`Error ${res.status} al descargar transcripcion`);
      return;
    }
    const blob = await res.blob();
    downloadBlob(blob, fmt === "json" ? "transcripcion.json" : "transcripcion.txt");
  }

  return (
    <div className="app">
      <h1>Editor de censura de audio</h1>

      <div
        className="dropzone"
        onDrop={onDrop}
        onDragOver={(e) => e.preventDefault()}
        onClick={() => fileInputRef.current?.click()}
      >
        <p>Arrastra un archivo de audio aqui o hace click para elegirlo</p>
        <input
          ref={fileInputRef}
          type="file"
          accept="audio/*"
          hidden
          onChange={(e) => handleFile(e.target.files?.[0])}
        />
      </div>

      {error && <p className="error">{error}</p>}
      {loading && (
        <p>
          {progress === null
            ? "Subiendo audio..."
            : `Transcribiendo audio... ${Math.round(progress * 100)}%`}
        </p>
      )}

      {audioUrl && (
        <audio ref={audioRef} src={audioUrl} controls className="player" />
      )}

      {session && (
        <div className="results">
          <p className="summary">
            {flaggedCount} palabra(s) detectada(s). Destilda las que no quieras censurar.
          </p>

          <div className="transcript">
            {session.segments.map((seg) => (
              <p key={seg.id} className="segment">
                {session.words
                  .filter((w) => w.segment_id === seg.id)
                  .map((w) => (
                    <span
                      key={w.index}
                      className={w.flagged ? "word flagged" : "word"}
                      onClick={() => jumpTo(w.start)}
                    >
                      {w.flagged && (
                        <input
                          type="checkbox"
                          checked={!!checked[w.index]}
                          onChange={(e) => {
                            e.stopPropagation();
                            toggleWord(w.index);
                          }}
                          onClick={(e) => e.stopPropagation()}
                        />
                      )}
                      {w.word}{" "}
                    </span>
                  ))}
              </p>
            ))}
          </div>

          <div className="actions">
            <button onClick={generateCensored} disabled={censoring}>
              {censoring ? "Generando..." : "Generar audio censurado"}
            </button>
            <button onClick={() => downloadTranscript("txt")}>
              Descargar transcripcion (.txt)
            </button>
            <button onClick={() => downloadTranscript("json")}>
              Descargar transcripcion (.json)
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
