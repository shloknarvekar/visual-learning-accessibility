"use client";

import { motion } from "motion/react";
import { ArrowRight, BrainCircuit, CircleHelp, Layers3 } from "lucide-react";

const cards = [
  {
    eyebrow: "01 · CONCEPTS",
    title: "See the idea.",
    body: "Turn the lecture into a visual map of the concepts that matter.",
    image:
      "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=900&q=80",
    icon: BrainCircuit,
  },
  {
    eyebrow: "02 · PROCESS",
    title: "Follow what happens.",
    body: "Break a complex sequence into readable, connected visual stages.",
    image:
      "https://images.unsplash.com/photo-1531482615713-2afd69097998?auto=format&fit=crop&w=900&q=80",
    icon: Layers3,
  },
  {
    eyebrow: "03 · PRACTICE",
    title: "Make it click.",
    body: "Check understanding with immediate feedback while the idea is fresh.",
    image:
      "https://images.unsplash.com/photo-1497633762265-9d179a990aa6?auto=format&fit=crop&w=900&q=80",
    icon: CircleHelp,
  },
];

export function ThreeCardFan({
  onOpenLesson,
  onOpenPractice,
}: {
  onOpenLesson: () => void;
  onOpenPractice: () => void;
}) {
  return (
    <section className="relative overflow-hidden bg-[#faf7f2] px-5 py-20 text-[#24161b] sm:px-8 md:px-10 md:py-28">
      <div className="pointer-events-none absolute inset-0 [background-image:linear-gradient(rgba(123,0,28,.055)_1px,transparent_1px),linear-gradient(90deg,rgba(123,0,28,.055)_1px,transparent_1px)] [background-size:56px_56px] opacity-50" />
      <div className="relative mx-auto max-w-6xl">
        <div className="grid gap-12 lg:grid-cols-[.72fr_1.28fr] lg:items-center">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.3 }}
            transition={{ duration: 0.55 }}
          >
            <div className="inline-flex items-center gap-2 rounded-full border border-[#7b001c]/12 bg-white px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[.18em] text-[#7b001c] shadow-sm">
              One lesson. Three useful shapes.
            </div>
            <h2 className="mt-5 max-w-xl text-4xl font-semibold leading-[.95] tracking-[-.055em] sm:text-5xl md:text-6xl">
              The same idea can look <span className="text-[#b4002a]">different</span> when it needs
              to.
            </h2>
            <p className="mt-5 max-w-xl text-base leading-7 text-[#5f6066] sm:text-lg">
              VisuaLearn keeps the academic content intact — it changes the representation so the
              learner can choose the form that makes the concept easiest to understand.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={onOpenLesson}
                className="group inline-flex items-center gap-2 rounded-full bg-[#7b001c] px-5 py-3 text-sm font-semibold text-white shadow-[0_16px_34px_rgba(123,0,28,.18)] transition duration-300 hover:-translate-y-1 hover:bg-[#980022]"
              >
                Explore the lesson{" "}
                <ArrowRight size={16} className="transition-transform group-hover:translate-x-1" />
              </button>
              <button
                type="button"
                onClick={onOpenPractice}
                className="inline-flex items-center gap-2 rounded-full border border-[#7b001c]/15 bg-white px-5 py-3 text-sm font-semibold text-[#5a2630] transition duration-300 hover:-translate-y-1 hover:border-[#b4002a]/30 hover:shadow-[0_14px_30px_rgba(90,0,20,.08)]"
              >
                Try practice <CircleHelp size={16} />
              </button>
            </div>
          </motion.div>

          <div className="relative mx-auto flex w-full max-w-3xl items-center justify-center px-3 py-8 sm:px-8">
            <div className="pointer-events-none absolute inset-x-12 bottom-3 h-24 rounded-full bg-[#7b001c]/10 blur-3xl" />
            <div className="relative flex w-full items-center justify-center">
              {cards.map((card, index) => {
                const Icon = card.icon;
                const rotate = index === 0 ? -7 : index === 2 ? 7 : 0;
                const y = index === 1 ? -8 : 14;
                const x = index === 0 ? 38 : index === 2 ? -38 : 0;
                const z = index === 1 ? 30 : 10;
                return (
                  <motion.article
                    key={card.eyebrow}
                    initial={{ opacity: 0, y: y + 22, x, rotate }}
                    whileInView={{ opacity: 1, y, x: 0, rotate }}
                    whileHover={{ y: -12, rotate: 0, scale: 1.035, zIndex: 50 }}
                    viewport={{ once: true, amount: 0.2 }}
                    transition={{ duration: 0.65, delay: index * 0.1, ease: [0.22, 1, 0.36, 1] }}
                    className="relative -ml-10 w-[38%] shrink-0 overflow-hidden rounded-[28px] border border-[#7b001c]/10 bg-white shadow-[0_28px_70px_rgba(70,0,18,.13)] first:ml-0"
                    style={{ zIndex: z }}
                  >
                    <div className="relative aspect-[4/5] overflow-hidden bg-[#eee7df]">
                      <img
                        src={card.image}
                        alt=""
                        className="h-full w-full object-cover transition duration-700 ease-out hover:scale-105"
                        loading="lazy"
                      />
                      <div className="absolute inset-0 bg-gradient-to-t from-[#1c050b]/65 via-transparent to-transparent" />
                      <div className="absolute left-4 top-4 rounded-full border border-white/25 bg-black/25 px-3 py-1.5 text-[9px] font-semibold tracking-[.16em] text-white backdrop-blur-md">
                        {card.eyebrow}
                      </div>
                    </div>
                    <div className="p-5 sm:p-6">
                      <div className="grid h-9 w-9 place-items-center rounded-xl bg-[#fff0f3] text-[#7b001c]">
                        <Icon size={17} />
                      </div>
                      <h3 className="mt-4 text-xl font-semibold tracking-[-.035em] sm:text-2xl">
                        {card.title}
                      </h3>
                      <p className="mt-2 text-sm leading-6 text-[#656069]">{card.body}</p>
                    </div>
                  </motion.article>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
