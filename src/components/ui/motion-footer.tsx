'use client';

import * as React from 'react';
import { useEffect, useRef } from 'react';
import { motion } from 'motion/react';
import { ArrowRight, ArrowUp, Accessibility, BookOpen, BrainCircuit, Layers3 } from 'lucide-react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

const marqueeItems = [
  'VISUAL-FIRST LEARNING',
  'CONCEPT MAPS',
  'PROCESS VISUALIZATIONS',
  'LEARNER-CONTROLLED PACING',
  'INTERACTIVE PRACTICE',
];

type FooterTarget = 'home' | 'input' | 'lesson' | 'quiz';

type FooterActionProps = {
  onClick: () => void;
  icon: React.ReactNode;
  title: string;
  featured?: boolean;
  reveal?: boolean;
};

function FooterAction({ onClick, icon, title, featured = false, reveal = true }: FooterActionProps) {
  return (
    <motion.button
      type="button"
      onClick={onClick}
      data-footer-reveal={reveal ? true : undefined}
      initial={reveal ? { opacity: 0, y: 28 } : undefined}
      whileInView={reveal ? { opacity: 1, y: 0 } : undefined}
      viewport={reveal ? { once: true, amount: 0.25 } : undefined}
      transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1] }}
      whileHover={{ y: -6 }}
      whileTap={{ scale: 0.985 }}
      className={`group relative flex min-h-[156px] w-full items-end overflow-hidden rounded-[28px] border p-0 text-left shadow-[0_24px_70px_-34px_rgba(0,0,0,.9)] transition-colors duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#ff5278] focus-visible:ring-offset-2 focus-visible:ring-offset-[#100205] ${
        featured
          ? 'border-[#ff5278]/35 bg-[linear-gradient(145deg,rgba(180,0,42,.48),rgba(55,0,16,.8))]'
          : 'border-white/10 bg-[linear-gradient(145deg,rgba(255,255,255,.06),rgba(255,255,255,.025))]'
      }`}
    >
      <span className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_10%_0%,rgba(255,82,120,.2),transparent_42%)] opacity-0 transition-opacity duration-500 group-hover:opacity-100" />
      <span className="pointer-events-none absolute -right-12 -top-12 h-36 w-36 rounded-full bg-[#ff5278]/10 blur-3xl transition-transform duration-700 group-hover:scale-125" />
      <span className="pointer-events-none absolute inset-x-5 bottom-0 h-px bg-gradient-to-r from-transparent via-[#ff5278]/50 to-transparent opacity-0 transition-opacity duration-500 group-hover:opacity-100" />

      <span className="relative flex w-full items-end justify-between gap-4 p-5 sm:p-6">
        <span className="flex min-w-0 items-center gap-4">
          <span
            className={`grid h-11 w-11 shrink-0 place-items-center rounded-2xl border ${
              featured
                ? 'border-[#ff5278]/30 bg-[#ff5278]/15 text-[#ff5278]'
                : 'border-white/10 bg-white/[.04] text-[#ff5278]'
            }`}
          >
            {icon}
          </span>
          <span className="min-w-0">
            <span
              className={`block text-[10px] font-semibold uppercase tracking-[.18em] ${
                featured ? 'text-[#ff5278]' : 'text-white/38'
              }`}
            >
              VisuaLearn action
            </span>
            <span className="mt-1 block text-lg font-medium tracking-[-.025em] text-white sm:text-xl">
              {title}
            </span>
          </span>
        </span>

        <span
          className={`grid h-10 w-10 shrink-0 place-items-center rounded-full border transition-all duration-300 group-hover:translate-x-1 ${
            featured
              ? 'border-white/20 bg-white text-[#7b001c]'
              : 'border-white/10 bg-white/[.04] text-white/65 group-hover:border-[#ff5278]/40 group-hover:text-white'
          }`}
        >
          <ArrowRight size={17} />
        </span>
      </span>
    </motion.button>
  );
}

export function MotionFooter({ onNavigate }: { onNavigate?: (target: FooterTarget) => void }) {
  const footerRef = useRef<HTMLElement | null>(null);
  const contentRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (typeof window === 'undefined' || !footerRef.current) return;

    gsap.registerPlugin(ScrollTrigger);
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduce) return;

    const ctx = gsap.context(() => {
      const reveals = contentRef.current?.querySelectorAll('[data-footer-reveal]');
      if (!reveals?.length) return;

      gsap.fromTo(
        reveals,
        { y: 28, opacity: 0 },
        {
          y: 0,
          opacity: 1,
          stagger: 0.08,
          duration: 0.7,
          ease: 'power3.out',
          scrollTrigger: {
            trigger: footerRef.current,
            start: 'top 74%',
            once: true,
          },
        },
      );
    }, footerRef);

    return () => ctx.revert();
  }, []);

  const go = (target: FooterTarget) => {
    onNavigate?.(target);
    window.setTimeout(() => window.scrollTo({ top: 0, behavior: 'smooth' }), 30);
  };

  return (
    <footer
      ref={footerRef}
      className="relative overflow-hidden bg-[#100205] px-5 pb-8 pt-12 text-white sm:px-8 md:px-10 md:pt-16"
    >
      <div className="pointer-events-none absolute inset-0 opacity-[0.32] [background-image:linear-gradient(rgba(255,255,255,.05)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,.05)_1px,transparent_1px)] [background-size:56px_56px] [mask-image:linear-gradient(to_bottom,transparent,black_16%,black_84%,transparent)]" />
      <div className="pointer-events-none absolute left-1/2 top-[38%] h-[48vh] w-[68vw] -translate-x-1/2 rounded-full bg-[#b4002a]/16 blur-[120px]" />
      <div className="pointer-events-none absolute left-1/2 top-0 h-px w-[min(1100px,86%)] -translate-x-1/2 bg-gradient-to-r from-transparent via-[#ff5278]/50 to-transparent" />

      <div className="relative z-10 overflow-hidden border-y border-white/10 py-3">
        <div className="flex w-max animate-[footer-marquee_32s_linear_infinite] items-center whitespace-nowrap text-[10px] font-semibold tracking-[.28em] text-white/42 sm:text-xs">
          {[...marqueeItems, ...marqueeItems].map((item, index) => (
            <React.Fragment key={`${item}-${index}`}>
              <span className="px-6">{item}</span>
              <span className="text-[#ff5278]">✦</span>
            </React.Fragment>
          ))}
        </div>
      </div>

      <div ref={contentRef} className="relative z-10 mx-auto max-w-6xl py-16 sm:py-20 md:py-24">
        <div>
          <div data-footer-reveal className="text-[10px] font-semibold uppercase tracking-[.22em] text-[#ff5278]">
            Keep the lesson moving
          </div>
          <h2
            data-footer-reveal
            className="mt-5 max-w-5xl text-5xl font-semibold leading-[.9] tracking-[-.06em] sm:text-6xl md:text-8xl"
          >
            Learning should <span className="text-[#ff5278]">adapt.</span>
          </h2>
          <p data-footer-reveal className="mt-6 max-w-xl text-base leading-7 text-white/55 sm:text-lg">
            Bring in the material. Choose the representation. Pause, explore, practice, and come back when the idea needs another shape.
          </p>
        </div>

        <div className="mt-16 grid gap-4 md:grid-cols-3">
          <FooterAction featured onClick={() => go('input')} icon={<BookOpen size={18} />} title="Build a visual lesson" />
          <FooterAction onClick={() => go('lesson')} icon={<BrainCircuit size={18} />} title="Explore Photosynthesis" />
          <FooterAction onClick={() => go('quiz')} icon={<Layers3 size={18} />} title="Try interactive practice" />
        </div>

        <div data-footer-reveal className="mt-8 flex flex-wrap gap-3">
          {(
            [
              ['Create', 'input'],
              ['Learn', 'lesson'],
              ['Practice', 'quiz'],
            ] as const
          ).map(([label, target]) => (
            <button
              key={label}
              type="button"
              onClick={() => go(target)}
              className="rounded-full border border-white/10 bg-white/[.03] px-4 py-2 text-xs font-medium text-white/60 transition hover:-translate-y-0.5 hover:border-[#ff5278]/40 hover:bg-[#b4002a]/10 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#ff5278]"
            >
              {label}
            </button>
          ))}
          <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[.03] px-4 py-2 text-xs text-white/45">
            <Accessibility size={14} /> Accessibility built in
          </span>
        </div>

        <div
          data-footer-reveal
          className="mt-10 flex flex-col gap-5 border-t border-white/10 pt-6 text-xs text-white/40 sm:flex-row sm:items-center sm:justify-between"
        >
          <div>© 2026 VisuaLearn · Visual-first learning</div>
          <div className="flex flex-wrap items-center gap-4">
            <span>Built for learner control</span>
            <span className="text-[#ff5278]">●</span>
            <span>No audio required</span>
            <button
              type="button"
              onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
              className="ml-1 grid h-10 w-10 place-items-center rounded-full border border-white/10 bg-white/[.03] text-white transition hover:-translate-y-1 hover:border-[#ff5278]/40 hover:bg-[#b4002a]/15 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#ff5278]"
              aria-label="Back to top"
            >
              <ArrowUp size={16} />
            </button>
          </div>
        </div>
      </div>

      <style jsx>{`
        @keyframes footer-marquee {
          from { transform: translateX(0); }
          to { transform: translateX(-50%); }
        }

        @media (prefers-reduced-motion: reduce) {
          :global(.animate-[footer-marquee_32s_linear_infinite]) {
            animation-play-state: paused;
          }
        }
      `}</style>
    </footer>
  );
}
