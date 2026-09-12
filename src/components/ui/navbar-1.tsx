'use client';

import * as React from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { Menu, Settings2, Sparkles, X } from 'lucide-react';

type View = 'home' | 'input' | 'processing' | 'lesson' | 'quiz' | 'result' | 'accessibility';

export type Navbar1Props = {
  view: View;
  scrolled: boolean;
  mobileOpen: boolean;
  setMobileOpen: React.Dispatch<React.SetStateAction<boolean>>;
  onHome: () => void;
  onNavigate: (view: View) => void;
  onAccessibility: () => void;
};

const navItems: Array<[View, string]> = [
  ['input', 'Create'],
  ['lesson', 'Learn'],
  ['quiz', 'Practice'],
  ['accessibility', 'Accessibility'],
];

export function Navbar1({
  view,
  scrolled,
  mobileOpen,
  setMobileOpen,
  onHome,
  onNavigate,
  onAccessibility,
}: Navbar1Props) {
  const landing = view === 'home' && !scrolled;
  const foreground = landing ? 'text-white' : 'text-[#3c2028]';
  const shell = landing
    ? 'border-white/20 bg-black/18 text-white shadow-[0_12px_40px_rgba(0,0,0,.10)]'
    : 'border-[#7b001c]/12 bg-white/94 text-[#3c2028] shadow-[0_16px_42px_rgba(80,0,20,.11)]';

  return (
    <>
      <header className="fixed inset-x-0 top-0 z-[70] px-4 pt-4 sm:px-6 sm:pt-5">
        <div className="mx-auto flex max-w-7xl justify-center">
          <motion.div
            layout
            transition={{ type: 'spring', stiffness: 280, damping: 28 }}
            className={`flex w-full items-center justify-between rounded-full border px-3 py-2 backdrop-blur-2xl ${shell}`}
          >
            <motion.button
              type="button"
              onClick={onHome}
              className="focus-ring flex items-center gap-3 rounded-full px-2 py-1.5 text-left"
              aria-label="Go to VisuaLearn home"
              whileTap={{ scale: 0.97 }}
            >
              <motion.span
                className={`grid h-10 w-10 shrink-0 place-items-center rounded-full border ${landing ? 'border-white/20 bg-black/25' : 'border-[#7b001c]/12 bg-white'}`}
                whileHover={{ rotate: 10, scale: 1.05 }}
                transition={{ duration: 0.25 }}
              >
                <Sparkles size={18} />
              </motion.span>
              <span className={`font-heading text-[21px] tracking-tight sm:text-[24px] ${foreground}`}>VisuaLearn</span>
              <span className={`select-none text-[24px] leading-none sm:text-[29px] ${foreground}`} aria-hidden="true">✳︎</span>
            </motion.button>

            <nav className={`hidden items-center gap-1 md:flex ${foreground}`} aria-label="Primary navigation">
              {navItems.map(([target, label], index) => (
                <React.Fragment key={target}>
                  {index > 0 && <span aria-hidden="true" className="px-1 opacity-45">,</span>}
                  <motion.button
                    type="button"
                    onClick={() => onNavigate(target)}
                    className={`relative rounded-full px-4 py-2 text-[15px] font-medium transition-colors lg:text-[16px] ${view === target ? (landing ? 'bg-white/12' : 'bg-[#7b001c]/7 text-[#7b001c]') : ''}`}
                    whileHover={{ y: -1, scale: 1.04 }}
                    whileTap={{ scale: 0.97 }}
                  >
                    {label}
                    {view === target && (
                      <motion.span layoutId="nav-active-dot" className={`absolute inset-x-4 -bottom-0.5 h-px ${landing ? 'bg-white/80' : 'bg-[#b4002a]'}`} />
                    )}
                  </motion.button>
                </React.Fragment>
              ))}

            </nav>

            <motion.button
              type="button"
              aria-label="Accessibility controls"
              onClick={onAccessibility}
              className={`focus-ring hidden h-10 w-10 place-items-center rounded-full border md:grid ${landing ? 'border-white/20 bg-black/20' : 'border-[#7b001c]/12 bg-white'}`}
              whileHover={{ scale: 1.06, rotate: 8 }}
              whileTap={{ scale: 0.94 }}
            >
              <Settings2 size={18} />
            </motion.button>

            <motion.button
              type="button"
              aria-label={mobileOpen ? 'Close navigation' : 'Open navigation'}
              onClick={() => setMobileOpen((value) => !value)}
              className={`focus-ring grid h-10 w-10 place-items-center rounded-full border md:hidden ${landing ? 'border-white/20 bg-black/20' : 'border-[#7b001c]/12 bg-white'}`}
              whileTap={{ scale: 0.92 }}
            >
              <AnimatePresence mode="wait" initial={false}>
                <motion.span
                  key={mobileOpen ? 'close' : 'menu'}
                  initial={{ opacity: 0, rotate: -25, scale: .8 }}
                  animate={{ opacity: 1, rotate: 0, scale: 1 }}
                  exit={{ opacity: 0, rotate: 25, scale: .8 }}
                  transition={{ duration: .18 }}
                >
                  {mobileOpen ? <X size={20} /> : <Menu size={20} />}
                </motion.span>
              </AnimatePresence>
            </motion.button>
          </motion.div>
        </div>
      </header>

      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            className="fixed inset-0 z-[60] flex flex-col justify-center bg-[#7b001c]/96 px-8 backdrop-blur-xl md:hidden"
            initial={{ opacity: 0, x: '100%' }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: '100%' }}
            transition={{ type: 'spring', damping: 26, stiffness: 260 }}
          >
            <div className="mb-10 flex items-center gap-3 text-white">
              <span className="grid h-12 w-12 place-items-center rounded-full border border-white/20 bg-white/10"><Sparkles size={20} /></span>
              <span className="font-heading text-2xl">VisuaLearn</span>
            </div>
            <div className="flex flex-col gap-3">
              {navItems.map(([target, label], i) => (
                <motion.button
                  key={target}
                  type="button"
                  initial={{ opacity: 0, x: 24 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.08 + i * 0.06 }}
                  onClick={() => { onNavigate(target); setMobileOpen(false); }}
                  className="rounded-2xl px-4 py-3 text-left text-[30px] font-medium text-white transition-colors hover:bg-white/10"
                >
                  {label}
                </motion.button>
              ))}

            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
