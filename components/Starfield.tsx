
"use client";

import { useMemo } from "react";
import type { CSSProperties } from "react";

type Star = {
  x: number;
  y: number;
  size: number;
  opacity: number;
  delay: number;
  duration: number;
};

// Pseudo-random cố định: cùng seed luôn ra cùng kết quả
function seededRandom(seed: number): number {
  const x = Math.sin(seed * 127.1 + 78.233) * 43758.5453;
  return x - Math.floor(x);
}

function fixed(value: number): number {
  return Number(value.toFixed(3));
}

export default function Starfield() {
  const stars = useMemo<Star[]>(() => {
    return Array.from({ length: 130 }, (_, i) => ({
      x: fixed(seededRandom(i + 1) * 100),
      y: fixed(seededRandom(i + 200) * 100),
      size: fixed(0.5 + seededRandom(i + 400) * 1.8),
      opacity: fixed(0.2 + seededRandom(i + 600) * 0.6),
      delay: fixed(seededRandom(i + 800) * 8),
      duration: fixed(3 + seededRandom(i + 1000) * 6),
    }));
  }, []);

  return (
    <div className="starfield" aria-hidden="true">
      {stars.map((star, index) => {
        const style: CSSProperties = {
          left: `${star.x}%`,
          top: `${star.y}%`,
          width: `${star.size}px`,
          height: `${star.size}px`,
          opacity: star.opacity,
          animationDelay: `${star.delay}s`,
          animationDuration: `${star.duration}s`,
        };

        return (
          <span
            key={index}
            className="star"
            style={style}
          />
        );
      })}

      <span className="shooting-star shooting-star-1" />
      <span className="shooting-star shooting-star-2" />
    </div>
  );
}
