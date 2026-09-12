'use client';

import { useState, type ReactNode } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  ArrowRight,
  BrainCircuit,
  Check,
  CircleHelp,
  Layers3,
  Lightbulb,
  Network,
  Play,
  Sparkles,
  Timer,
} from 'lucide-react';

const ease = [0.22, 1, 0.36, 1] as const;

const fanCards = [
  {
    kicker: '01 · CONCEPT MAP',
    title: 'See the relationships.',
    body: 'Turn a dense explanation into a map of inputs, dependencies and outcomes.',
    accent: 'from-[#fff4f5] via-white to-[#fff8f9]',
    icon: <Network size={18} />,
    visual: (
      <div className="relative h-full w-full overflow-hidden rounded-[24px] bg-[#fff8f8] p-6">
        <div className="absolute left-1/2 top-1/2 h-20 w-20 -translate-x-1/2 -translate-y-1/2 rounded-full border border-[#b4002a]/20 bg-white shadow-[0_18px_50px_rgba(180,0,42,.13)] grid place-items-center text-[11px] font-semibold text-[#7b001c]">Photosynthesis</div>
        {[
          ['left-2 top-8', 'Sunlight'],
          ['right-3 top-14', 'CO₂'],
          ['left-6 bottom-10', 'Water'],
          ['right-5 bottom-8', 'Glucose'],
        ].map(([pos, label]) => (
          <div key={label} className={`absolute ${pos} rounded-full border border-[#7b001c]/12 bg-white px-3 py-1.5 text-[10px] font-medium text-[#4b2a31] shadow-sm`}>{label}</div>
        ))}
        <svg className="pointer-events-none absolute inset-0 h-full w-full" viewBox="0 0 320 210" fill="none" aria-hidden="true">
          <path d="M84 55 C120 72 125 90 160 105" stroke="#b4002a" strokeOpacity=".18" strokeWidth="2" strokeDasharray="4 5"/>
          <path d="M244 70 C205 80 198 90 160 105" stroke="#b4002a" strokeOpacity=".18" strokeWidth="2" strokeDasharray="4 5"/>
          <path d="M88 165 C123 145 134 130 160 105" stroke="#b4002a" strokeOpacity=".18" strokeWidth="2" strokeDasharray="4 5"/>
          <path d="M238 168 C210 150 190 132 160 105" stroke="#b4002a" strokeOpacity=".18" strokeWidth="2" strokeDasharray="4 5"/>
        </svg>
      </div>
    ),
  },
  {
    kicker: '02 · PROCESS',
    title: 'Follow the sequence.',
    body: 'Make a process readable one decision, transformation or stage at a time.',
    accent: 'from-[#fff7f4] via-white to-[#fffafb]',
    icon: <Layers3 size={18} />,
    visual: (
      <div className="flex h-full flex-col justify-center gap-3 rounded-[24px] bg-white p-6">
        {['Light enters', 'Energy is converted', 'Glucose is formed'].map((item, i) => (
          <motion.div key={item} initial={{ x: 16, opacity: 0 }} whileInView={{ x: 0, opacity: 1 }} viewport={{ once: true }} transition={{ delay: i * .1, duration: .45, ease }} className="flex items-center gap-3 rounded-2xl border border-[#7b001c]/10 bg-[#fff7f8] p-3">
            <span className="grid h-8 w-8 shrink-0 place-items-center rounded-xl bg-[#7b001c] text-xs font-semibold text-white">0{i + 1}</span>
            <div className="flex-1 text-sm font-semibold text-[#26171c]">{item}</div>
            {i < 2 && <ArrowRight size={15} className="text-[#b4002a]" />}
          </motion.div>
        ))}
        <div className="mt-1 flex items-center gap-2 text-[10px] uppercase tracking-[.18em] text-[#7b001c]/45"><span className="h-px flex-1 bg-[#7b001c]/10"/>VISUAL SEQUENCE<span className="h-px flex-1 bg-[#7b001c]/10"/></div>
      </div>
    ),
  },
  {
    kicker: '03 · PRACTICE',
    title: 'Check the click.',
    body: 'Test understanding with quick feedback instead of waiting until the end.',
    accent: 'from-[#fff4f7] via-white to-[#fff8fb]',
    icon: <CircleHelp size={18} />,
    visual: (
      <div className="h-full rounded-[24px] bg-[#17070c] p-5 text-white shadow-inner">
        <div className="flex items-center justify-between text-[10px] uppercase tracking-[.16em] text-white/45"><span>01 / 03</span><span>Practice</span></div>
        <div className="mt-8 text-lg font-semibold tracking-tight">What stores much of the chemical energy?</div>
        <div className="mt-5 space-y-2">
          {['Glucose', 'Oxygen', 'Water'].map((item, i) => (
            <div key={item} className={`flex items-center gap-3 rounded-xl border px-3 py-2.5 text-sm ${i === 0 ? 'border-[#ff5278]/50 bg-[#b4002a]/20' : 'border-white/10 bg-white/[.03]'}`}>
              <span className="grid h-6 w-6 place-items-center rounded-lg border border-white/15 text-[10px]">{String.fromCharCode(65 + i)}</span>
              {item}
              {i === 0 && <Check size={14} className="ml-auto text-[#ff5278]" />}
            </div>
          ))}
        </div>
      </div>
    ),
  },
];

export function VisualLearningShowcase({ onOpenLesson, onOpenPractice }: { onOpenLesson: () => void; onOpenPractice: () => void }) {
  const [activeOrbit, setActiveOrbit] = useState(0);
  const [practiceChoice, setPracticeChoice] = useState<number | null>(null);
  const orbitNodes = [
    { label: 'Sunlight', note: 'Energy input', icon: <Sparkles size={14} /> },
    { label: 'Water', note: 'Raw material', icon: <Lightbulb size={14} /> },
    { label: 'CO₂', note: 'Carbon source', icon: <BrainCircuit size={14} /> },
    { label: 'Glucose', note: 'Energy stored', icon: <Check size={14} /> },
    { label: 'O₂', note: 'Released', icon: <Play size={14} /> },
  ];

  return (
    <div className="relative overflow-hidden bg-[#f7f4ef] text-[#24161b]">
      <div className="pointer-events-none absolute inset-0 grid-bg opacity-[.35]" />
      <div className="relative">
        <section className="px-5 py-20 sm:px-8 md:px-10 md:py-28">
          <div className="mx-auto max-w-6xl">
            <div className="grid gap-10 lg:grid-cols-[.72fr_1.28fr] lg:items-end">
              <motion.div initial={{ opacity: 0, y: 22 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: .25 }} transition={{ duration: .55, ease }}>
                <div className="inline-flex items-center gap-2 rounded-full border border-[#7b001c]/10 bg-white px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[.18em] text-[#7b001c] shadow-sm"><Sparkles size={12}/> One source. Multiple representations.</div>
                <h2 className="mt-5 max-w-2xl text-4xl font-semibold leading-[.98] tracking-[-.055em] sm:text-5xl md:text-6xl">A lesson should be able to <span className="text-[#b4002a]">change shape</span> around you.</h2>
                <p className="mt-5 max-w-xl text-base leading-7 text-[#5f6066] sm:text-lg">This is the layer between raw material and understanding: concepts, process, relationships and practice — all connected, all explorable.</p>
                <div className="mt-8 flex flex-wrap gap-3">
                  <button onClick={onOpenLesson} className="group inline-flex items-center gap-2 rounded-full bg-[#7b001c] px-5 py-3 text-sm font-semibold text-white shadow-[0_14px_34px_rgba(123,0,28,.18)] transition hover:-translate-y-1 hover:bg-[#980022]">Explore the lesson <ArrowRight size={16} className="transition-transform group-hover:translate-x-1" /></button>
                  <button onClick={onOpenPractice} className="inline-flex items-center gap-2 rounded-full border border-[#7b001c]/15 bg-white px-5 py-3 text-sm font-semibold text-[#5a2630] transition hover:-translate-y-1 hover:border-[#b4002a]/30 hover:shadow-[0_12px_30px_rgba(123,0,28,.08)]">Try practice <CircleHelp size={16}/></button>
                </div>
              </motion.div>

              <div className="grid gap-4 md:grid-cols-3">
                {fanCards.map((card, index) => (
                  <motion.article key={card.kicker} initial={{ opacity: 0, y: 34, rotate: index === 0 ? -4 : index === 2 ? 4 : 0 }} whileInView={{ opacity: 1, y: 0, rotate: index === 0 ? -4 : index === 2 ? 4 : 0 }} whileHover={{ y: -10, rotate: 0, scale: 1.02 }} viewport={{ once: true, amount: .2 }} transition={{ duration: .6, delay: index * .08, ease }} className={`overflow-hidden rounded-[30px] border border-[#7b001c]/10 bg-gradient-to-br ${card.accent} shadow-[0_24px_70px_rgba(64,0,12,.09)]`}>
                    <div className="aspect-[4/5] p-3">{card.visual}</div>
                    <div className="px-5 pb-6 pt-3">
                      <div className="flex items-center gap-2 text-[10px] font-semibold tracking-[.16em] text-[#7b001c]/65"><span className="grid h-7 w-7 place-items-center rounded-lg bg-[#7b001c] text-white">{card.icon}</span>{card.kicker}</div>
                      <h3 className="mt-4 text-xl font-semibold tracking-[-.03em]">{card.title}</h3>
                      <p className="mt-2 text-sm leading-6 text-[#656069]">{card.body}</p>
                    </div>
                  </motion.article>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="overflow-hidden bg-[#130407] px-5 py-20 text-white sm:px-8 md:px-10 md:py-28">
          <div className="mx-auto grid max-w-6xl gap-10 lg:grid-cols-[.85fr_1.15fr] lg:items-center">
            <motion.div initial={{ opacity: 0, x: -24 }} whileInView={{ opacity: 1, x: 0 }} viewport={{ once: true, amount: .25 }} transition={{ duration: .55, ease }}>
              <div className="text-[10px] font-semibold uppercase tracking-[.2em] text-[#ff5278]">Interactive concept orbit</div>
              <h2 className="mt-4 text-4xl font-semibold tracking-[-.05em] sm:text-5xl">Click the concept. <span className="text-[#ff5278]">See what changes.</span></h2>
              <p className="mt-5 max-w-xl text-base leading-7 text-white/60 sm:text-lg">Instead of opening another wall of text, the lesson lets you move through the relationships around the idea.</p>
              <div className="mt-7 grid gap-2 sm:grid-cols-2">
                {orbitNodes.map((node, index) => (
                  <button key={node.label} onClick={() => setActiveOrbit(index)} className={`flex items-center gap-3 rounded-2xl border px-3 py-3 text-left transition ${activeOrbit === index ? 'border-[#ff5278]/45 bg-[#b4002a]/18' : 'border-white/10 bg-white/[.03] hover:border-white/20 hover:bg-white/[.05]'}`}>
                    <span className="grid h-8 w-8 place-items-center rounded-xl bg-white/10 text-[#ff5278]">{node.icon}</span>
                    <span><span className="block text-sm font-semibold">{node.label}</span><span className="block text-[11px] text-white/45">{node.note}</span></span>
                  </button>
                ))}
              </div>
            </motion.div>

            <motion.div initial={{ opacity: 0, scale: .96 }} whileInView={{ opacity: 1, scale: 1 }} viewport={{ once: true, amount: .2 }} transition={{ duration: .7, ease }} className="relative min-h-[480px] overflow-hidden rounded-[34px] border border-white/10 bg-[radial-gradient(circle_at_center,rgba(255,82,120,.18),transparent_34%),radial-gradient(circle_at_70%_30%,rgba(180,0,42,.24),transparent_28%),#0a0205]">
              <div className="absolute inset-0 opacity-20 [background-image:linear-gradient(rgba(255,255,255,.16)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,.16)_1px,transparent_1px)] [background-size:42px_42px]" />
              <div className="absolute left-1/2 top-1/2 h-52 w-52 -translate-x-1/2 -translate-y-1/2 rounded-full border border-[#ff5278]/25 bg-[radial-gradient(circle_at_35%_30%,rgba(255,130,150,.7),rgba(180,0,42,.28)_40%,transparent_70%)] shadow-[0_0_120px_rgba(180,0,42,.35)]" />
              <motion.div animate={{ rotate: 360 }} transition={{ duration: 24, repeat: Infinity, ease: 'linear' }} className="absolute left-1/2 top-1/2 h-[340px] w-[340px] -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/10" />
              <motion.div animate={{ rotate: -360 }} transition={{ duration: 31, repeat: Infinity, ease: 'linear' }} className="absolute left-1/2 top-1/2 h-[420px] w-[420px] -translate-x-1/2 -translate-y-1/2 rounded-full border border-[#ff5278]/10" />
              <div className="absolute left-1/2 top-1/2 z-10 -translate-x-1/2 -translate-y-1/2 text-center">
                <div className="text-[10px] font-semibold uppercase tracking-[.18em] text-white/45">Active concept</div>
                <AnimatePresence mode="wait">
                  <motion.div key={orbitNodes[activeOrbit].label} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} className="mt-2 text-4xl font-semibold tracking-[-.05em]">{orbitNodes[activeOrbit].label}</motion.div>
                </AnimatePresence>
                <div className="mt-2 text-xs text-white/45">{orbitNodes[activeOrbit].note}</div>
              </div>
              {orbitNodes.map((node, index) => {
                const angles = [0, 72, 144, 216, 288];
                const angle = (angles[index] * Math.PI) / 180;
                const x = Math.cos(angle) * 184;
                const y = Math.sin(angle) * 154;
                return (
                  <motion.button key={node.label} onClick={() => setActiveOrbit(index)} whileHover={{ scale: 1.08 }} className={`absolute left-1/2 top-1/2 grid h-16 w-16 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full border text-[10px] font-semibold transition ${activeOrbit === index ? 'border-[#ff5278]/60 bg-[#b4002a]/30 text-white shadow-[0_0_34px_rgba(255,82,120,.2)]' : 'border-white/10 bg-white/[.03] text-white/55'}`} style={{ marginLeft: x, marginTop: y }}>{node.label}</motion.button>
                );
              })}
              <div className="absolute bottom-5 left-5 right-5 flex items-center justify-between rounded-2xl border border-white/10 bg-black/25 px-4 py-3 text-xs text-white/55 backdrop-blur-xl"><span>Drag or click around the idea</span><span className="text-[#ff5278]">01 · visual relationship layer</span></div>
            </motion.div>
          </div>
        </section>

        <section className="px-5 py-20 sm:px-8 md:px-10 md:py-28">
          <div className="mx-auto max-w-6xl">
            <div className="grid gap-10 lg:grid-cols-[.7fr_1.3fr]">
              <motion.div initial={{ opacity: 0, y: 18 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: .5, ease }} className="lg:sticky lg:top-28 lg:self-start">
                <div className="text-[10px] font-semibold uppercase tracking-[.18em] text-[#7b001c]">The learning loop</div>
                <h2 className="mt-4 text-4xl font-semibold tracking-[-.05em] sm:text-5xl">From <span className="text-[#b4002a]">raw material</span> to “ohhh.”</h2>
                <p className="mt-5 max-w-md text-base leading-7 text-[#5f6066]">Each layer builds on the last, without forcing the learner into one fixed representation.</p>
                <div className="mt-7 rounded-2xl border border-[#7b001c]/10 bg-white p-4 shadow-[0_18px_48px_rgba(90,0,20,.07)]">
                  <div className="flex items-center gap-3"><div className="grid h-9 w-9 place-items-center rounded-xl bg-[#7b001c] text-white"><Timer size={17}/></div><div><div className="text-sm font-semibold">Learner-controlled pacing</div><div className="text-xs text-[#6b6166]">Pause, explore, return.</div></div></div>
                </div>
              </motion.div>

              <div className="space-y-4">
                {[
                  ['01', 'Bring the material in', 'YouTube, PDF or notes become the starting point — not the final format.', <Play size={18}/>],
                  ['02', 'Structure the meaning', 'Key concepts, entities, examples and relationships become navigable pieces.', <Layers3 size={18}/>],
                  ['03', 'See the system', 'Concept maps and process views expose what connects to what.', <Network size={18}/>],
                  ['04', 'Try it yourself', 'Practice questions reveal whether the idea actually clicked.', <CircleHelp size={18}/>],
                ].map(([num, title, text, icon], i) => (
                  <motion.div key={num} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: .22 }} transition={{ delay: i * .07, duration: .5, ease }} whileHover={{ x: 5 }} className="group rounded-[26px] border border-[#7b001c]/10 bg-white p-5 shadow-[0_14px_40px_rgba(90,0,20,.05)] sm:p-7">
                    <div className="flex items-start gap-4"><div className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-[#fff0f3] text-[#7b001c] transition group-hover:scale-105">{icon}</div><div className="min-w-0 flex-1"><div className="flex items-center justify-between gap-4"><span className="text-[10px] font-semibold tracking-[.2em] text-[#7b001c]/45">{num}</span><span className="text-xs text-[#9d8f95]">{i + 1 === 4 ? 'understanding' : 'next layer'}</span></div><h3 className="mt-3 text-xl font-semibold tracking-[-.03em] sm:text-2xl">{title}</h3><p className="mt-2 max-w-2xl text-sm leading-6 text-[#656069] sm:text-base">{text}</p></div></div>
                  </motion.div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="bg-[#fffaf8] px-5 pb-24 pt-4 sm:px-8 md:px-10 md:pb-32">
          <div className="mx-auto max-w-6xl overflow-hidden rounded-[34px] border border-[#7b001c]/10 bg-white shadow-[0_28px_90px_rgba(70,0,18,.08)]">
            <div className="grid gap-0 lg:grid-cols-[1fr_.8fr]">
              <div className="p-7 sm:p-10 md:p-12">
                <div className="text-[10px] font-semibold uppercase tracking-[.2em] text-[#7b001c]">Practice, but make it visual</div>
                <h2 className="mt-4 text-3xl font-semibold tracking-[-.04em] sm:text-4xl">The answer isn't the end. The feedback is part of the lesson.</h2>
                <p className="mt-4 max-w-xl text-sm leading-6 text-[#5f6066] sm:text-base">Learners can choose an option, see why it is right or wrong, and return to the visual representation that explains the idea.</p>
                <div className="mt-8 space-y-3">
                  {['Glucose stores chemical energy.', 'Oxygen is a byproduct.', 'Water is an input.'].map((option, i) => (
                    <button key={option} onClick={() => setPracticeChoice(i)} className={`group flex w-full items-center gap-3 rounded-2xl border px-4 py-4 text-left transition ${practiceChoice === i ? (i === 0 ? 'border-[#7b001c]/30 bg-[#fff0f3]' : 'border-[#b4002a]/30 bg-[#fff7f8]') : 'border-[#7b001c]/10 bg-[#fffdfc] hover:-translate-y-0.5 hover:border-[#b4002a]/20 hover:shadow-[0_12px_28px_rgba(90,0,20,.06)]'}`}><span className={`grid h-8 w-8 place-items-center rounded-xl text-xs font-semibold ${practiceChoice === i ? 'bg-[#7b001c] text-white' : 'bg-[#fff0f3] text-[#7b001c]'}`}>{String.fromCharCode(65 + i)}</span><span className="flex-1 text-sm font-medium">{option}</span>{practiceChoice === i && (i === 0 ? <Check className="text-[#7b001c]" size={18}/> : <CircleHelp className="text-[#b4002a]" size={18}/>)} </button>
                  ))}
                </div>
                {practiceChoice !== null && <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="mt-4 rounded-2xl border border-[#b4002a]/12 bg-[#fff4f6] p-4 text-sm leading-6 text-[#5f6066]"><span className="font-semibold text-[#7b001c]">Why:</span> Glucose is the energy-rich product that stores much of the chemical energy captured during photosynthesis.</motion.div>}
              </div>
              <div className="relative overflow-hidden bg-[#120307] p-7 text-white sm:p-10"><div className="absolute inset-0 opacity-20 [background-image:linear-gradient(rgba(255,255,255,.11)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,.11)_1px,transparent_1px)] [background-size:28px_28px]" /><div className="relative flex h-full min-h-[320px] flex-col justify-between"><div><div className="text-[10px] uppercase tracking-[.2em] text-[#ff5278]">Visual feedback</div><div className="mt-4 text-3xl font-semibold tracking-[-.04em]">The lesson can move with the question.</div></div><div className="relative mt-10 h-40"><motion.div animate={{ x: [0, 20, 0], opacity: [0.5, 1, .5] }} transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }} className="absolute left-[10%] top-1/2 h-20 w-20 -translate-y-1/2 rounded-full bg-[#b4002a]/40 blur-xl"/><motion.div animate={{ rotate: [0, 12, 0] }} transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut' }} className="absolute left-[31%] top-[26%] rounded-2xl border border-[#ff5278]/30 bg-[#b4002a]/10 px-4 py-3 text-xs text-white/80 backdrop-blur">concept map</motion.div><motion.div animate={{ y: [0, -10, 0] }} transition={{ duration: 3.5, repeat: Infinity, ease: 'easeInOut', delay: .3 }} className="absolute right-[8%] bottom-[8%] rounded-2xl border border-white/10 bg-white/[.04] px-4 py-3 text-xs text-white/65 backdrop-blur">process view</motion.div><motion.div animate={{ y: [0, 10, 0] }} transition={{ duration: 3.2, repeat: Infinity, ease: 'easeInOut', delay: .6 }} className="absolute left-[50%] bottom-[22%] rounded-2xl border border-white/10 bg-white/[.04] px-4 py-3 text-xs text-white/65 backdrop-blur">practice</motion.div></div><div className="flex items-center justify-between text-xs text-white/45"><span>learner-controlled</span><span className="text-[#ff5278]">visual-first</span></div></div></div>
            </div>
          </div>
        </section>

        <section className="bg-[#7b001c] px-5 py-20 text-white sm:px-8 md:px-10 md:py-28">
          <motion.div initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: .3 }} transition={{ duration: .6, ease }} className="mx-auto flex max-w-6xl flex-col gap-8 lg:flex-row lg:items-end lg:justify-between">
            <div><div className="text-[10px] font-semibold uppercase tracking-[.2em] text-white/50">Next stop: your material</div><h2 className="mt-4 max-w-3xl text-4xl font-semibold tracking-[-.05em] sm:text-5xl md:text-6xl">Bring the lecture. We'll change the way you can see it.</h2></div>
            <button onClick={onOpenLesson} className="group inline-flex shrink-0 items-center gap-2 rounded-full bg-white px-5 py-3 text-sm font-semibold text-[#7b001c] transition hover:-translate-y-1 hover:bg-[#fff4f6]">Open a visual lesson <ArrowRight size={16} className="transition-transform group-hover:translate-x-1" /></button>
          </motion.div>
        </section>
      </div>
    </div>
  );
}
