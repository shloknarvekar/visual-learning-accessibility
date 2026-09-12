'use client';

import * as React from 'react';
import { motion } from 'motion/react';

export type StreamImage = { src: string; alt?: string };

export function ImageStreamHero({ images, className = '', speed = 16, children }: {
  images: StreamImage[];
  className?: string;
  speed?: number;
  children?: React.ReactNode;
}) {
  return (
    <div className={`relative overflow-hidden ${className}`}>
      <div aria-hidden className="pointer-events-none absolute inset-0 [perspective:900px]">
        {[0, 1].map((rail) =>
          Array.from({ length: 8 }, (_, i) => {
            const img = images[i % images.length];
            const delay = -(i * speed) / 8;
            const side = rail === 0 ? -1 : 1;
            return (
              <motion.div
                key={`${rail}-${i}`}
                className="absolute left-1/2 top-1/2 h-[20vw] max-h-[230px] min-h-[120px] w-[15vw] max-w-[190px] min-w-[100px] overflow-hidden rounded-[18px] border border-white/10 bg-black/30 shadow-2xl"
                animate={{
                  x: [side * 12, side * 22, side * 42],
                  y: ['-50%', '-50%', '-50%'],
                  scale: [0.35, 0.8, 1.8],
                  rotateY: [-side * 8, -side * 18, -side * 28],
                  opacity: [0, 0.65, 0.08],
                }}
                transition={{ duration: speed, delay, repeat: Infinity, ease: 'linear' }}
                style={{ marginLeft: '-7.5vw' }}
              >
                <img src={img.src} alt={img.alt || ''} className="h-full w-full object-cover" draggable={false} />
              </motion.div>
            );
          }),
        )}
      </div>
      {children}
    </div>
  );
}
