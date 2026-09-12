'use client';

import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { ArrowRight, Check, CircleHelp, Layers3, Network, Sparkles } from 'lucide-react';

const ease = [0.22, 1, 0.36, 1] as const;

export function RotatingHeadline({
  prefix,
  words,
}: {
  prefix: string;
  words: string[];
}) {
  const [index, setIndex] = useState(0);
  useEffect(() => {
    const id = window.setInterval(() => setIndex((value) => (value + 1) % words.length), 2200);
    return () => window.clearInterval(id);
  }, [words.length]);

  return (
    <h1 className="text-balance text-4xl font-semibold tracking-[-.045em] sm:text-5xl md:text-6xl">
      {prefix}{' '}
      <span className="relative inline-flex min-w-[7ch] overflow-hidden align-baseline text-[#b4002a]">
        <AnimatePresence mode="wait">
          <motion.span
            key={words[index]}
            initial={{ y: '100%', opacity: 0, filter: 'blur(8px)' }}
            animate={{ y: 0, opacity: 1, filter: 'blur(0px)' }}
            exit={{ y: '-100%', opacity: 0, filter: 'blur(8px)' }}
            transition={{ duration: 0.45, ease }}
            className="inline-block"
          >
            {words[index]}
          </motion.span>
        </AnimatePresence>
      </span>
    </h1>
  );
}

export function ModeRail({
  active,
  onChange,
}: {
  active: string;
  onChange: (value: string) => void;
}) {
  const modes = [
    ['concepts', 'Concepts', Network],
    ['process', 'Process', Layers3],
    ['practice', 'Practice', CircleHelp],
  ] as const;
  return (
    <div className="flex flex-wrap gap-2">
      {modes.map(([id, label, Icon]) => (
        <motion.button
          key={id}
          type="button"
          onClick={() => onChange(id)}
          whileHover={{ y: -2, scale: 1.02 }}
          whileTap={{ scale: .97 }}
          className={`inline-flex items-center gap-2 rounded-full border px-3.5 py-2 text-xs font-semibold transition ${active === id ? 'border-[#b4002a] bg-[#b4002a] text-white shadow-[0_10px_26px_rgba(180,0,42,.18)]' : 'border-[#7b001c]/12 bg-white text-[#5f6066] hover:border-[#b4002a]/30 hover:text-[#7b001c]'}`}
        >
          <Icon size={14} /> {label}
        </motion.button>
      ))}
    </div>
  );
}

export function MiniFan({
  labels = ['CONCEPT', 'PROCESS', 'PRACTICE'],
  dark = false,
}: {
  labels?: string[];
  dark?: boolean;
}) {
  const fills = dark ? ['bg-[#2d0811]', 'bg-[#4a0b19]', 'bg-[#160509]'] : ['bg-[#fff0f3]', 'bg-white', 'bg-[#f4ebe9]'];
  return (
    <div className="relative mx-auto flex w-full max-w-2xl items-end justify-center px-4 py-8">
      {labels.slice(0, 3).map((label, i) => (
        <motion.div
          key={label}
          initial={{ opacity: 0, y: 22, x: i === 0 ? 30 : i === 2 ? -30 : 0, rotate: i === 0 ? -8 : i === 2 ? 8 : 0 }}
          whileInView={{ opacity: 1, y: i === 1 ? -12 : 10, x: 0, rotate: i === 0 ? -6 : i === 2 ? 6 : 0 }}
          whileHover={{ y: i === 1 ? -22 : -4, rotate: 0, scale: 1.035, zIndex: 30 }}
          viewport={{ once: true, amount: .25 }}
          transition={{ duration: .6, delay: i * .09, ease }}
          className={`relative -ml-8 aspect-[4/5] w-[34%] rounded-[24px] border border-[#7b001c]/12 p-4 shadow-[0_24px_70px_rgba(45,0,16,.13)] first:ml-0 sm:p-5 ${fills[i]}`}
          style={{ zIndex: i === 1 ? 20 : 10 }}
        >
          <div className={`text-[9px] font-semibold tracking-[.2em] ${dark ? 'text-[#ff5278]/80' : 'text-[#7b001c]/55'}`}>0{i + 1}</div>
          <div className={`mt-20 text-xl font-semibold tracking-tight sm:mt-28 sm:text-2xl ${dark ? 'text-white' : 'text-[#24161b]'}`}>{label}</div>
          <div className={`mt-2 text-xs leading-5 ${dark ? 'text-white/45' : 'text-[#5f6066]'}`}>One idea. One useful representation.</div>
          <div className={`absolute inset-x-4 bottom-4 h-px ${dark ? 'bg-white/10' : 'bg-[#7b001c]/10'}`} />
        </motion.div>
      ))}
    </div>
  );
}

export function SignalBand({
  dark = true,
  title,
  text,
  children,
}: {
  dark?: boolean;
  title: string;
  text: string;
  children?: ReactNode;
}) {
  return (
    <section className={`${dark ? 'bg-[#130307] text-white' : 'bg-[#faf7f2] text-[#24161b]'} relative overflow-hidden border-y ${dark ? 'border-white/10' : 'border-[#7b001c]/10'}`}>
      <div className="pointer-events-none absolute inset-0 opacity-30 [background-image:linear-gradient(rgba(180,0,42,.12)_1px,transparent_1px),linear-gradient(90deg,rgba(180,0,42,.12)_1px,transparent_1px)] [background-size:52px_52px]" />
      <div className="relative mx-auto grid max-w-7xl gap-8 px-5 py-16 sm:px-8 md:grid-cols-[.72fr_1.28fr] md:items-center md:px-10 md:py-20">
        <div>
          <div className={`text-[10px] font-semibold uppercase tracking-[.2em] ${dark ? 'text-[#ff5278]' : 'text-[#7b001c]'}`}>One lesson. Many ways to click.</div>
          <h2 className="mt-4 max-w-3xl text-4xl font-semibold leading-[.94] tracking-[-.05em] sm:text-5xl md:text-6xl">
            {(() => {
              const parts = title.trim().split(/\s+/);
              const accent = parts.pop() ?? '';
              return <>{parts.join(' ')} {dark ? <span className="text-[#ff5278]">{accent}</span> : <span className="text-[#b4002a]">{accent}</span>}</>;
            })()}
          </h2>
          <p className={`mt-5 max-w-xl text-base leading-7 sm:text-lg ${dark ? 'text-white/55' : 'text-[#5f6066]'}`}>{text}</p>
        </div>
        <div>{children}</div>
      </div>
    </section>
  );
}

export function CompactFooter({ onBackHome }: { onBackHome: () => void }) {
  return (
    <footer className="relative overflow-hidden bg-[#100205] px-5 py-12 text-white sm:px-8 md:px-10">
      <div className="pointer-events-none absolute inset-0 opacity-25 [background-image:linear-gradient(rgba(255,255,255,.05)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,.05)_1px,transparent_1px)] [background-size:52px_52px]" />
      <div className="relative mx-auto max-w-7xl">
        <div className="flex flex-wrap items-center justify-between gap-5 border-b border-white/10 pb-8">
          <div>
            <div className="text-[10px] font-semibold uppercase tracking-[.2em] text-[#ff5278]">VisuaLearn</div>
            <div className="mt-2 text-3xl font-semibold tracking-[-.04em] sm:text-4xl">Keep the lesson moving.</div>
          </div>
          <motion.button type="button" onClick={onBackHome} whileHover={{ y: -3 }} whileTap={{ scale: .97 }} className="inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/[.04] px-5 py-3 text-sm font-semibold text-white transition hover:border-[#ff5278]/50 hover:bg-[#b4002a]/15">Back to home <ArrowRight size={15} /></motion.button>
        </div>
        <div className="mt-8 flex flex-wrap items-center gap-x-7 gap-y-3 text-xs text-white/42">
          <span>Visual-first</span><span className="text-[#ff5278]">✦</span><span>Learner-controlled</span><span className="text-[#ff5278]">✦</span><span>No audio required</span><span className="text-[#ff5278]">✦</span><span>Accessible by design</span>
        </div>
      </div>
    </footer>
  );
}
