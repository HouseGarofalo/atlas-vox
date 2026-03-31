import { useEffect, useRef } from "react";

interface AudioLevelMeterProps {
  stream: MediaStream | null;
  className?: string;
}

export function AudioLevelMeter({ stream, className = "" }: AudioLevelMeterProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);

  useEffect(() => {
    if (!stream || !canvasRef.current) return;

    const audioCtx = new AudioContext();
    const source = audioCtx.createMediaStreamSource(stream);
    const analyser = audioCtx.createAnalyser();
    analyser.fftSize = 256;
    source.connect(analyser);

    const dataArray = new Uint8Array(analyser.frequencyBinCount);
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d")!;

    const draw = () => {
      analyser.getByteTimeDomainData(dataArray);

      // Calculate RMS level
      let sum = 0;
      let peak = 0;
      for (let i = 0; i < dataArray.length; i++) {
        const v = (dataArray[i] - 128) / 128;
        sum += v * v;
        peak = Math.max(peak, Math.abs(v));
      }
      const rms = Math.sqrt(sum / dataArray.length);
      const level = Math.min(1, rms * 5); // Scale for visibility
      const isClipping = peak > 0.95;

      // Draw
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const w = canvas.width * level;

      // Background
      ctx.fillStyle = "var(--color-surface-alt, #1a1a2e)";
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Level bar with gradient
      if (isClipping) {
        ctx.fillStyle = "#ef4444";
      } else if (level > 0.7) {
        ctx.fillStyle = "#f59e0b";
      } else {
        ctx.fillStyle = "#22c55e";
      }
      ctx.fillRect(0, 0, w, canvas.height);

      // Threshold markers
      ctx.strokeStyle = "rgba(255,255,255,0.3)";
      ctx.setLineDash([2, 2]);
      // -6dB mark (70%)
      ctx.beginPath();
      ctx.moveTo(canvas.width * 0.7, 0);
      ctx.lineTo(canvas.width * 0.7, canvas.height);
      ctx.stroke();
      // -20dB mark (10%)
      ctx.beginPath();
      ctx.moveTo(canvas.width * 0.1, 0);
      ctx.lineTo(canvas.width * 0.1, canvas.height);
      ctx.stroke();
      ctx.setLineDash([]);

      animRef.current = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      cancelAnimationFrame(animRef.current);
      source.disconnect();
      audioCtx.close();
    };
  }, [stream]);

  return (
    <div className={className}>
      <canvas ref={canvasRef} width={300} height={20} className="w-full h-5 rounded" />
      <div className="flex justify-between text-[10px] text-[var(--color-text-secondary)] mt-0.5">
        <span>Quiet</span>
        <span>Good</span>
        <span>Loud</span>
      </div>
    </div>
  );
}
