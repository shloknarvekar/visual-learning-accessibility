'use client';

import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import {
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  Check,
  CircleHelp,
  ChevronRight,
  FileText,
  Gauge,
  Layers3,
  Lightbulb,
  MousePointer2,
  Network,
  Play,
  RotateCcw,
  Settings2,
  Sparkles,
  Trophy,
  Upload,
  Video,
} from 'lucide-react';
import { photosynthesisExampleLesson, type Lesson, type Section } from '@visual-learning/contracts';
import { apiClient } from '@/lib/api-client';
import { adaptSectionToVisualization, VisualizationRenderer } from '@/components/visuals';
import { Navbar1 } from '@/components/ui/navbar-1';
import { ThreeCardFan } from '@/components/ThreeCardFan';
import { VisualLearningShowcase } from '@/components/VisualLearningShowcase';
import { MotionFooter } from '@/components/ui/motion-footer';
import { CompactFooter, MiniFan, ModeRail, RotatingHeadline, SignalBand } from '@/components/ProductVisualLayer';

const ease = [0.22, 1, 0.36, 1] as const;
const VIDEO_URL = 'https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260826_041744_63efcd78-bf7d-4039-99e2-2461e8a61903.mp4';

type View = 'home' | 'input' | 'processing' | 'lesson' | 'quiz' | 'result' | 'accessibility';

type HomePreview = 'concepts' | 'process' | 'practice';
type LessonMode = 'live' | 'fallback' | 'cached' | 'demo';

function useTypewriter(text: string, speed = 38, startDelay = 600) {
  const [displayed, setDisplayed] = useState('');
  const [done, setDone] = useState(false);

  useEffect(() => {
    let interval: number | undefined;
    const timeout = window.setTimeout(() => {
      let index = 0;
      interval = window.setInterval(() => {
        index += 1;
        setDisplayed(text.slice(0, index));
        if (index >= text.length) {
          setDone(true);
          if (interval) window.clearInterval(interval);
        }
      }, speed);
    }, startDelay);
    return () => {
      window.clearTimeout(timeout);
      if (interval) window.clearInterval(interval);
    };
  }, [speed, startDelay, text]);

  return { displayed, done };
}

function useHeroInteraction(
  videoRef: React.RefObject<HTMLVideoElement | null>,
  heroRef: React.RefObject<HTMLElement | null>,
  active: boolean,
) {
  useEffect(() => {
    const video = videoRef.current;
    const hero = heroRef.current;
    if (!video || !hero || !active) return;

    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
    let raf = 0;
    let targetX = 0.5;
    let targetY = 0.5;
    let smoothX = 0.5;
    let smoothY = 0.5;
    let targetTime: number | null = null;
    let seekBusy = false;
    let queuedSeek = false;
    let lastSeekAt = 0;

    const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

    const setPointer = (clientX: number, clientY: number) => {
      targetX = clamp(clientX / Math.max(window.innerWidth, 1), 0, 1);
      targetY = clamp(clientY / Math.max(window.innerHeight, 1), 0, 1);
      const inside = clientX >= 0 && clientX <= window.innerWidth && clientY >= 0 && clientY <= window.innerHeight;
      hero.style.setProperty('--glow-opacity', inside ? '1' : '0');
      if (Number.isFinite(video.duration) && video.duration > 0 && !reduced.matches) {
        targetTime = video.duration * (0.13 + targetX * 0.74);
        queuedSeek = true;
      }
    };

    const seek = (now: number) => {
      if (reduced.matches || !queuedSeek || targetTime === null || seekBusy) return;
      if (!Number.isFinite(video.duration) || video.duration <= 0) return;
      if (now - lastSeekAt < 80) return;
      const next = clamp(targetTime, 0.06, Math.max(0.06, video.duration - 0.06));
      if (Math.abs(video.currentTime - next) < 0.03) {
        queuedSeek = false;
        return;
      }
      seekBusy = true;
      queuedSeek = false;
      lastSeekAt = now;
      try {
        if (typeof video.fastSeek === 'function') video.fastSeek(next);
        else video.currentTime = next;
      } catch {
        seekBusy = false;
      }
    };

    const frame = (now: number) => {
      smoothX += (targetX - smoothX) * 0.12;
      smoothY += (targetY - smoothY) * 0.12;
      const x = (smoothX - 0.5) * 24;
      const y = (smoothY - 0.5) * 9;
      video.style.transform = `translate3d(${x}px,${y}px,0) scale(1.055)`;
      video.style.objectPosition = `${76 + (smoothX - 0.5) * 7}% ${50 + (smoothY - 0.5) * 2}%`;
      seek(now);
      raf = window.requestAnimationFrame(frame);
    };

    const onPointerMove = (event: PointerEvent) => {
      if (event.pointerType === 'touch') return;
      setPointer(event.clientX, event.clientY);
    };
    const onSeeked = () => {
      seekBusy = false;
      if (queuedSeek) seek(performance.now());
    };
    const onLoaded = () => {
      if (Number.isFinite(video.duration) && video.duration > 0) {
        try { video.currentTime = video.duration * 0.5; } catch { /* noop */ }
      }
    };

    hero.style.setProperty('--glow-opacity', '0');
    window.addEventListener('pointermove', onPointerMove, { passive: true });
    video.addEventListener('seeked', onSeeked);
    video.addEventListener('loadedmetadata', onLoaded);
    if (video.readyState >= 1) onLoaded();
    raf = window.requestAnimationFrame(frame);

    return () => {
      window.removeEventListener('pointermove', onPointerMove);
      video.removeEventListener('seeked', onSeeked);
      video.removeEventListener('loadedmetadata', onLoaded);
      window.cancelAnimationFrame(raf);
      hero.style.setProperty('--glow-opacity', '0');
    };
  }, [active, heroRef, videoRef]);
}

const pageFade = {
  initial: { opacity: 0, y: 14 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.45, ease } },
  exit: { opacity: 0, y: -10, transition: { duration: 0.2, ease: 'easeOut' as const } },
};

export default function VisualLearn() {
  const [lesson, setLesson] = useState<Lesson>(() => photosynthesisExampleLesson);
  const [view, setView] = useState<View>('home');
  const [source, setSource] = useState<'youtube' | 'pdf'>('youtube');
  const [url, setUrl] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState('');
  const [stage, setStage] = useState(0);
  const [activeSection, setActiveSection] = useState(0);
  const [mobileNav, setMobileNav] = useState(false);
  const [answer, setAnswer] = useState<number | null>(null);
  const [question, setQuestion] = useState(0);
  const [score, setScore] = useState(0);
  const [highContrast, setHighContrast] = useState(false);
  const [largeText, setLargeText] = useState(false);
  const [reduceMotion, setReduceMotion] = useState(false);
  const [heroPreview, setHeroPreview] = useState<HomePreview>('concepts');
  const [actionsVisible, setActionsVisible] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [lessonMode, setLessonMode] = useState<LessonMode>('demo');
  const [apiMessage, setApiMessage] = useState('');
  const [apiPending, setApiPending] = useState(false);
  const [lessonId, setLessonId] = useState<string | null>(null);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const heroRef = useRef<HTMLElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const current = lesson.sections[activeSection] ?? lesson.sections[0];
  const progress = lesson.quiz.length ? Math.round(((question + (answer !== null ? 1 : 0)) / lesson.quiz.length) * 100) : 0;

  useHeroInteraction(videoRef, heroRef, view === 'home');

  const { displayed, done } = useTypewriter('Make learning visual. Make it clearer. Make it yours.', 38, 600);

  useEffect(() => {
    const timeout = window.setTimeout(() => setActionsVisible(true), 400);
    return () => window.clearTimeout(timeout);
  }, []);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > window.innerHeight * 0.62);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => {
    if (view !== 'processing') return;
    let index = 0;
    const timer = window.setInterval(() => {
      index += 1;
      setStage(Math.min(4, index));
      if (index >= 4 && !apiPending) {
        window.clearInterval(timer);
        window.setTimeout(() => setView('lesson'), 450);
      }
    }, 700);
    return () => window.clearInterval(timer);
  }, [view, apiPending]);

  const reset = () => {
    setView('home');
    setQuestion(0);
    setAnswer(null);
    setScore(0);
    setActiveSection(0);
    setUrl('');
    setFile(null);
    setError('');
    setStage(0);
    setLesson(photosynthesisExampleLesson);
    setLessonMode('demo');
    setApiMessage('');
    setApiPending(false);
  };

  const goHome = () => {
    reset();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const navigate = (target: View) => {
    setMobileNav(false);
    setView(target);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const begin = async () => {
    setError('');
    setApiMessage('');
    if (source === 'youtube' && !url.trim()) {
      setError('Paste a YouTube URL to continue.');
      return;
    }
    if (source === 'pdf' && !file) {
      setError('Choose a PDF to continue.');
      return;
    }

    setView('processing');
    setStage(0);
    setApiPending(true);

    try {
      if (source === 'pdf' && file) {
        if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
          throw new Error('Please choose a PDF file.');
        }
        const record = await apiClient.createPdfLesson(file);
        setLesson(record.lesson);
        setLessonId(record.lesson_id);
        setLessonMode(record.metadata.generation_status);
        setApiMessage(record.metadata.notice ?? `Lesson generated by ${record.metadata.provider}.`);
      } else {
        // The checked-in API contract currently exposes PDF creation and lesson retrieval.
        // Keep the YouTube UI, but do not invent a frontend endpoint that the repo does not define.
        setLesson(photosynthesisExampleLesson);
        setLessonMode('demo');
        setApiMessage('YouTube input is staged in the UI. The current backend contract exposes PDF lesson creation, so this demo keeps the flow intact without inventing an endpoint.');
      }
    } catch (apiError) {
      setLessonMode('demo');
      setApiMessage(apiError instanceof Error ? apiError.message : 'The lesson service is unavailable. The demo lesson is still available.');
      setLesson(photosynthesisExampleLesson);
      setLessonId(null);
    } finally {
      setApiPending(false);
    }
  };

  const choose = (index: number) => {
    if (answer !== null) return;
    setAnswer(index);
    if (lesson.quiz[question]?.options[index]?.id === lesson.quiz[question]?.correct_option_id) setScore((value) => value + 1);
  };

  const next = () => {
    if (answer === null) return;
    if (question === lesson.quiz.length - 1) {
      setView('result');
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }
    setQuestion((value) => value + 1);
    setAnswer(null);
  };

  const pageTone = highContrast ? 'bg-white text-black' : 'bg-[#faf7f2] text-[#24161b]';
  const accessibilityClass = `${largeText ? 'text-[108%]' : ''} ${reduceMotion ? 'reduce-motion' : ''}`;

  return (
    <div className={`min-h-screen ${pageTone} ${accessibilityClass}`} data-view={view}>
      <Navbar1
        view={view}
        scrolled={scrolled}
        mobileOpen={mobileNav}
        setMobileOpen={setMobileNav}
        onHome={goHome}
        onNavigate={navigate}
        onAccessibility={() => setHighContrast((value) => !value)}
      />

      <main>
        <AnimatePresence mode="wait">
          {view === 'home' && (
            <motion.div key="home" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <section ref={heroRef} className="hero-interactive relative min-h-[100svh] overflow-hidden bg-[#260207] text-white">
                <video ref={videoRef} className="hero-video absolute inset-0 z-0 h-full w-full object-cover object-[78%_center] will-change-transform" src={VIDEO_URL} muted playsInline preload="auto" aria-hidden="true" />
                <div className="pointer-events-none absolute inset-0 z-[1] bg-[radial-gradient(circle_at_80%_40%,rgba(255,74,114,.18),transparent_34%),linear-gradient(90deg,rgba(30,0,8,.72)_0%,rgba(30,0,8,.46)_40%,rgba(30,0,8,.10)_70%,rgba(30,0,8,.16)_100%)]" />
                <div className="pointer-events-none absolute inset-0 z-[1] bg-gradient-to-b from-black/10 via-transparent to-black/45" />
                <div className="pointer-events-none absolute inset-0 z-[2] opacity-[.13] [background-image:linear-gradient(rgba(255,255,255,.16)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,.16)_1px,transparent_1px)] [background-size:36px_36px]" />
                <div className="pointer-events-none absolute inset-0 z-[2] opacity-[var(--glow-opacity)] transition-opacity duration-500 [background:radial-gradient(circle_at_var(--mx,50%)_var(--my,50%),rgba(255,82,120,.22),transparent_18%)]" />
                <div className="relative z-10 flex min-h-[100svh] items-end px-5 pb-14 pt-28 sm:px-8 md:items-center md:px-10 md:pb-0">
                  <div className="w-full max-w-[860px]">
                    <p className="mb-5 max-w-4xl text-[clamp(35px,6.7vw,78px)] font-normal leading-[.98] tracking-[-.055em] text-white sm:mb-6">{displayed}{!done && <span className="ml-1 inline-block h-[.9em] w-[2px] animate-blink bg-white align-middle" />}</p>
                    <motion.p initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: .32, duration: .6, ease }} className="max-w-3xl text-[clamp(17px,2.2vw,24px)] leading-[1.42] text-white/82">Transform lectures, PDFs and notes into structured explanations, concept maps, process visualizations, examples and practice — all in one visual learning workspace.</motion.p>
                    <motion.div initial={{ opacity: 0, y: 10 }} animate={actionsVisible ? { opacity: 1, y: 0 } : { opacity: 0, y: 10 }} transition={{ duration: .4, ease: 'easeOut' }} className="mt-7 flex max-w-4xl flex-wrap gap-y-1">
                      <HeroPill onClick={() => navigate('input')}>Create a visual lesson <ChevronRight size={14}/></HeroPill>
                      <HeroPill onClick={() => navigate('lesson')}>Explore Photosynthesis <Play size={13}/></HeroPill>
                      <HeroPill onClick={() => { setSource('pdf'); navigate('input'); }}>Upload a PDF <Upload size={13}/></HeroPill>
                      <HeroPill onClick={() => navigate('quiz')}>Try a quick practice <CircleHelp size={13}/></HeroPill>
                      <motion.button whileHover={{ y: -4, scale: 1.03 }} whileTap={{ scale: .97 }} onClick={() => setHighContrast((value) => !value)} className="hero-action mx-[0.2em] mb-[0.4em] inline-flex items-center justify-center gap-2 rounded-full border border-white/80 bg-transparent px-4 py-[0.3em] text-[13px] font-medium text-white transition-colors duration-200 hover:bg-[#b4002a] sm:px-5 sm:text-[15px]">Accessibility controls <Settings2 size={12}/></motion.button>
                    </motion.div>
                    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: .55, duration: .55, ease }} className="mt-8 flex flex-wrap gap-2">
                      <FeatureChip text="Concept maps" icon={<Network size={13}/>} /><FeatureChip text="Process visualizations" icon={<Layers3 size={13}/>} /><FeatureChip text="Clear explanations" icon={<Lightbulb size={13}/>} /><FeatureChip text="Learner-controlled pacing" icon={<Gauge size={13}/>} /><FeatureChip text="Interactive quizzes" icon={<CircleHelp size={13}/>} />
                    </motion.div>
                  </div>
                </div>
              </section>

              <ThreeCardFan onOpenLesson={() => navigate('lesson')} onOpenPractice={() => navigate('quiz')} />
              <VisualLearningShowcase onOpenLesson={() => navigate('lesson')} onOpenPractice={() => navigate('quiz')} />
              <MotionFooter onNavigate={(target) => navigate(target === 'home' ? 'home' : target)} />
            </motion.div>
          )}

          {view === 'input' && <CreateView source={source} setSource={setSource} url={url} setUrl={setUrl} file={file} setFile={setFile} error={error} setError={setError} inputRef={inputRef} lessonMode={lessonMode} begin={begin} goHome={goHome} />}
          {view === 'processing' && <ProcessingView stage={stage} lessonMode={lessonMode} apiPending={apiPending} apiMessage={apiMessage} goHome={goHome} />}
          {view === 'lesson' && <LessonView lesson={lesson} current={current} activeSection={activeSection} setActiveSection={setActiveSection} lessonMode={lessonMode} highContrast={highContrast} setHighContrast={setHighContrast} goHome={goHome} onQuiz={() => navigate('quiz')} lessonId={lessonId} />}
          {view === 'quiz' && <QuizView lesson={lesson} question={question} answer={answer} score={score} progress={progress} choose={choose} next={next} goHome={goHome} />}
          {view === 'accessibility' && <AccessibilityView highContrast={highContrast} setHighContrast={setHighContrast} largeText={largeText} setLargeText={setLargeText} reduceMotion={reduceMotion} setReduceMotion={setReduceMotion} goHome={goHome} />}
          {view === 'result' && <ResultView lesson={lesson} score={score} retry={() => { setView('quiz'); setQuestion(0); setAnswer(null); setScore(0); }} goLesson={() => setView('lesson')} goHome={goHome} />}
        </AnimatePresence>
      </main>
    </div>
  );
}

type CreateViewProps = {
  source: 'youtube' | 'pdf';
  setSource: React.Dispatch<React.SetStateAction<'youtube' | 'pdf'>>;
  url: string;
  setUrl: React.Dispatch<React.SetStateAction<string>>;
  file: File | null;
  setFile: React.Dispatch<React.SetStateAction<File | null>>;
  error: string;
  setError: React.Dispatch<React.SetStateAction<string>>;
  inputRef: React.RefObject<HTMLInputElement | null>;
  lessonMode: LessonMode;
  begin: () => void;
  goHome: () => void;
};

function CreateView({ source, setSource, url, setUrl, file, setFile, error, setError, inputRef, lessonMode, begin, goHome }: CreateViewProps) {
  const activeMode = source === 'youtube' ? 'concepts' : 'process';

  return (
    <motion.div key="input" {...pageFade} className="min-h-screen bg-[#faf7f2] text-[#24161b]">
      <section className="relative overflow-hidden px-5 pb-14 pt-32 sm:px-8 md:px-10 md:pb-20">
        <div className="pointer-events-none absolute inset-0 [background-image:linear-gradient(rgba(123,0,28,.05)_1px,transparent_1px),linear-gradient(90deg,rgba(123,0,28,.05)_1px,transparent_1px)] [background-size:52px_52px]" />
        <div className="relative mx-auto grid max-w-7xl gap-10 lg:grid-cols-[1fr_.85fr] lg:items-end">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-[#7b001c]/12 bg-white px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[.2em] text-[#7b001c] shadow-sm">01 · Create</div>
            <div className="mt-5"><RotatingHeadline prefix="Build something" words={['visual.', 'clear.', 'clickable.', 'personal.']} /></div>
            <p className="mt-5 max-w-2xl text-base leading-7 text-[#5f6066] sm:text-lg">Drop in the material. VisuaLearn keeps the academic content intact while changing the shape of the explanation around the learner.</p>
            <div className="mt-7 flex flex-wrap gap-2 text-xs text-[#5f6066]">
              {['PDF', 'YouTube', 'Notes', 'Visual-first'].map((label) => <span key={label} className="rounded-full border border-[#7b001c]/12 bg-white px-3 py-2">{label}</span>)}
            </div>
          </div>
          <MiniFan labels={['INPUT', 'STRUCTURE', 'LESSON']} />
        </div>
      </section>

      <section className="px-5 pb-14 sm:px-8 md:px-10 md:pb-20">
        <div className="mx-auto max-w-7xl rounded-[32px] border border-[#7b001c]/12 bg-white p-4 shadow-[0_30px_80px_rgba(70,0,18,.09)] md:p-6">
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[#7b001c]/10 pb-4">
            <ModeRail active={activeMode} onChange={(value) => { setSource(value === 'concepts' ? 'youtube' : 'pdf'); setError(''); }} />
            <div className="rounded-full border border-[#7b001c]/12 bg-[#faf7f2] px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[.18em] text-[#5f6066]">{lessonMode === 'live' ? 'LIVE API' : lessonMode === 'fallback' ? 'FALLBACK' : 'DEMO'}</div>
          </div>

          <div className="grid gap-6 p-2 pt-6 lg:grid-cols-[.9fr_1.1fr] lg:p-4">
            <div className="rounded-[26px] bg-[#130307] p-6 text-white md:p-8">
              <div className="text-[10px] font-semibold uppercase tracking-[.2em] text-[#ff5278]">Choose your source</div>
              <h2 className="mt-3 text-3xl font-semibold tracking-[-.04em] sm:text-4xl">Start with what you already have.</h2>
              <div className="mt-7 grid grid-cols-2 gap-2 rounded-2xl border border-white/10 bg-white/[.03] p-1">
                <button type="button" onClick={() => { setSource('youtube'); setError(''); }} className={`rounded-xl px-4 py-3 text-sm font-semibold transition ${source === 'youtube' ? 'bg-white text-[#160509]' : 'text-white/55 hover:text-white'}`}><Video className="mr-2 inline" size={16} />YouTube</button>
                <button type="button" onClick={() => { setSource('pdf'); setError(''); }} className={`rounded-xl px-4 py-3 text-sm font-semibold transition ${source === 'pdf' ? 'bg-white text-[#160509]' : 'text-white/55 hover:text-white'}`}><FileText className="mr-2 inline" size={16} />PDF</button>
              </div>
              <div className="mt-6 grid gap-2 text-sm text-white/50">
                <div className="flex items-center gap-3"><Check className="text-[#ff5278]" size={15} /> Frontend-only by design</div>
                <div className="flex items-center gap-3"><Check className="text-[#ff5278]" size={15} /> Live / fallback / demo remains visible</div>
                <div className="flex items-center gap-3"><Check className="text-[#ff5278]" size={15} /> Learner pacing stays yours</div>
              </div>
            </div>

            <div className="rounded-[26px] bg-[#faf7f2] p-6 md:p-8">
              <AnimatePresence mode="wait">
                {source === 'youtube' ? (
                  <motion.div key="youtube" initial={{ opacity: 0, x: 18 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -18 }} transition={{ duration: .4, ease }}>
                    <label htmlFor="url" className="text-sm font-semibold">YouTube lecture URL</label>
                    <input id="url" value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://youtube.com/watch?v=..." className="focus-ring mt-3 w-full rounded-2xl border border-[#7b001c]/12 bg-white px-4 py-4 outline-none transition focus:border-[#b4002a]" />
                    <p className="mt-2 text-xs text-[#5f6066]">Demo input only. Extraction belongs to the backend.</p>
                  </motion.div>
                ) : (
                  <motion.div key="pdf" initial={{ opacity: 0, x: 18 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -18 }} transition={{ duration: .4, ease }}>
                    <input ref={inputRef} type="file" accept="application/pdf,.pdf" className="sr-only" onChange={(event) => {
                      const selected = event.target.files?.[0] || null;
                      setError('');
                      if (selected && !selected.name.toLowerCase().endsWith('.pdf')) {
                        setError('Only PDF files are supported.');
                        setFile(null);
                      } else setFile(selected);
                    }} />
                    <button type="button" onClick={() => inputRef.current?.click()} onDragOver={(event) => event.preventDefault()} onDrop={(event) => {
                      event.preventDefault();
                      const dropped = event.dataTransfer.files?.[0];
                      if (dropped?.type === 'application/pdf' || dropped?.name.toLowerCase().endsWith('.pdf')) {
                        setFile(dropped);
                        setError('');
                      } else setError('Please drop a PDF file.');
                    }} className="group focus-ring w-full rounded-[26px] border-2 border-dashed border-[#7b001c]/14 bg-white p-10 text-center transition hover:-translate-y-1 hover:border-[#b4002a]/45 hover:shadow-[0_22px_45px_rgba(120,0,28,.08)]">
                      <div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-[#fff0f3] text-[#b4002a] transition group-hover:scale-105"><Upload /></div>
                      <div className="mt-4 font-semibold">{file ? file.name : 'Drop a PDF or choose a file'}</div>
                      <div className="mt-2 text-sm text-[#5f6066]">PDF · frontend upload state</div>
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>

              {error && <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} role="alert" className="mt-4 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">{error}</motion.div>}
              <div className="mt-7 flex flex-wrap items-center justify-between gap-4">
                <div className="text-sm text-[#5f6066]">Next → processing → lesson workspace</div>
                <motion.button type="button" onClick={begin} whileHover={{ y: -3 }} whileTap={{ scale: .98 }} className="inline-flex items-center gap-2 rounded-full bg-[#7b001c] px-5 py-3 text-sm font-semibold text-white shadow-[0_14px_30px_rgba(123,0,28,.18)]">Build lesson <ArrowRight size={16} /></motion.button>
              </div>
            </div>
          </div>
        </div>
      </section>

      <SignalBand title="Bring the material. Choose the shape." text="The same content can become a map, a sequence, a comparison or a practice loop without asking the learner to start over.">
        <MiniFan labels={['MAP', 'PROCESS', 'PRACTICE']} dark />
      </SignalBand>
      <CompactFooter onBackHome={goHome} />
    </motion.div>
  );
}

type ProcessingViewProps = {
  stage: number;
  lessonMode: LessonMode;
  apiPending: boolean;
  apiMessage: string;
  goHome: () => void;
};

function ProcessingView({ stage, lessonMode, apiPending, apiMessage, goHome }: ProcessingViewProps) {
  const steps = ['Reading your content','Understanding key concepts','Structuring the lesson','Preparing visual explanations','Creating practice questions'];
  return <motion.div key="processing" {...pageFade} className="min-h-screen bg-[#faf7f2] text-[#24161b]"><section className="px-5 pb-12 pt-32 sm:px-8 md:px-10"><div className="mx-auto max-w-7xl"><div className="text-[10px] font-semibold uppercase tracking-[.2em] text-[#7b001c]">02 · Processing</div><div className="mt-4 grid gap-8 lg:grid-cols-[1fr_.72fr] lg:items-end"><div><RotatingHeadline prefix="Turning material into" words={['structure.','relationships.','visuals.','practice.']}/><p className="mt-5 max-w-2xl text-lg leading-7 text-[#5f6066]">No fake percentage. Just visible stages that explain what the interface is doing while the lesson takes shape.</p></div><MiniFan labels={['READ','MAP','BUILD']}/></div></div></section><section className="bg-[#130307] px-5 py-16 text-white sm:px-8 md:px-10 md:py-20"><div className="mx-auto max-w-7xl"><div className="flex flex-wrap items-center justify-between gap-4"><div><div className="text-[10px] font-semibold uppercase tracking-[.2em] text-[#ff5278]">Pipeline status</div><h2 className="mt-2 text-3xl font-semibold tracking-tight">The lesson is assembling.</h2></div><div className="rounded-full border border-white/10 bg-white/[.04] px-3 py-1.5 text-xs uppercase tracking-[.18em] text-white/55">{lessonMode==='live'?'Live API':lessonMode==='fallback'?'Fallback':'Demo mode'}</div></div>{apiMessage&&<div role="status" className="mt-5 rounded-2xl border border-[#ff5278]/25 bg-[#ff5278]/10 p-4 text-sm text-white/75">{apiMessage}</div>}<div className="mt-10 grid gap-3 md:grid-cols-5">{steps.map((label:string,index:number)=><motion.div key={label} initial={{opacity:0,y:18}} animate={{opacity:1,y:0}} transition={{delay:index*.08,duration:.55,ease}} className={`relative overflow-hidden rounded-[22px] border p-5 ${stage>index?'border-[#ff5278]/35 bg-[#ff5278]/10':stage===index?'border-white/15 bg-white/[.07]':'border-white/10 bg-white/[.025]'}`}>{stage===index&&apiPending&&<motion.div className="pointer-events-none absolute inset-y-0 left-[-40%] w-2/3 bg-gradient-to-r from-transparent via-[#ff5278]/20 to-transparent" animate={{x:['0%','220%']}} transition={{duration:1.4,repeat:Infinity,ease:'linear'}}/>}<div className="relative"><div className="text-[10px] font-semibold uppercase tracking-[.18em] text-white/35">0{index+1}</div><div className="mt-4 text-lg font-semibold">{label}</div><div className="mt-2 text-xs text-white/40">{stage>index?'Done':stage===index?'Working':'Queued'}</div></div></motion.div>)}</div><div className="mt-10"><MiniFan labels={['CONTENT','CONCEPTS','QUESTIONS']} dark/></div></div></section><SignalBand title="The output is more than captions." text="The finished lesson can move between explanation, relationships, diagrams and practice without becoming a wall of text."><MiniFan labels={['EXPLAIN','CONNECT','PRACTICE']} dark={false}/></SignalBand><CompactFooter onBackHome={goHome}/></motion.div>;
}

function getSectionSummary(section: Section): string {
  switch (section.type) {
    case 'concept':
      return section.content.definition;
    case 'explanation':
      return section.content.body;
    case 'process':
      return section.content.steps.map((step) => step.title).join(' → ');
    case 'comparison':
      return section.content.items.join(' · ');
    case 'timeline':
      return section.content.events.map((event) => event.title).join(' · ');
    case 'example':
      return section.content.scenario;
    case 'concept_map':
    case 'diagram':
      return section.content.summary;
    case 'chart':
      return section.content.summary;
    default:
      return '';
  }
}

type SectionContentWithKeyPoints = { key_points?: string[] };

type LessonViewProps = {
  lesson: Lesson;
  current: Section;
  activeSection: number;
  setActiveSection: React.Dispatch<React.SetStateAction<number>>;
  lessonMode: LessonMode;
  highContrast: boolean;
  setHighContrast: React.Dispatch<React.SetStateAction<boolean>>;
  goHome: () => void;
  onQuiz: () => void;
  lessonId: string | null;
};

function LessonView({ lesson, current, activeSection, setActiveSection, lessonMode, highContrast, setHighContrast, goHome, onQuiz, lessonId }: LessonViewProps) {
  const visualization = adaptSectionToVisualization(current as Section, 'biology');
  const modeLabel = lessonMode === 'live' ? 'LIVE' : lessonMode === 'fallback' ? 'FALLBACK' : lessonMode === 'cached' ? 'CACHED' : 'DEMO';
  return <motion.div key="lesson" {...pageFade} className="min-h-screen bg-[#faf7f2] text-[#24161b]">
    <section className="px-5 pb-10 pt-32 sm:px-8 md:px-10">
      <div className="mx-auto grid max-w-7xl gap-10 lg:grid-cols-[.82fr_1.18fr] lg:items-end">
        <div>
          <div className="text-[10px] font-semibold uppercase tracking-[.2em] text-[#7b001c]">03 · Learn</div>
          <RotatingHeadline prefix="Learn in a form that feels" words={['natural.','clear.','visual.','yours.']}/>
          <p className="mt-5 max-w-2xl text-base leading-7 text-[#5f6066] sm:text-lg">{lesson.title} stays tied to the shared lesson contract, while the interface lets the learner choose the representation and pace.</p>
          <div className="mt-7 flex flex-wrap gap-2">
            <span className="rounded-full border border-[#7b001c]/12 bg-white px-3 py-2 text-xs">Section {String(activeSection+1).padStart(2,'0')}</span>
            <span className="rounded-full border border-[#7b001c]/12 bg-white px-3 py-2 text-xs">{modeLabel}</span>
            {lessonId && <span className="rounded-full border border-[#7b001c]/12 bg-white px-3 py-2 text-xs">Lesson {lessonId.slice(0,8)}</span>}
          </div>
        </div>
        <MiniFan labels={['MAP','PROCESS','EXAMPLE']}/>
      </div>
    </section>

    <section className="px-5 pb-16 sm:px-8 md:px-10 md:pb-20">
      <div className="mx-auto grid max-w-7xl gap-5 lg:grid-cols-[230px_minmax(0,1fr)_260px]">
        <aside className="rounded-[26px] border border-[#7b001c]/12 bg-white p-4 shadow-[0_18px_50px_rgba(70,0,18,.06)]">
          <div className="mb-3 flex items-center gap-2 font-semibold"><BookOpen size={17}/> Lesson map</div>
          <div className="grid gap-1">
            {lesson.sections.map((section, index) => <motion.button whileHover={{x:3}} key={section.id} onClick={()=>setActiveSection(index)} className={`focus-ring rounded-xl px-3 py-3 text-left text-sm transition ${activeSection===index?'bg-[#fff0f3] font-semibold text-[#7b001c]':'text-[#5f6066] hover:bg-[#faf7f2]'}`}>{String(index+1).padStart(2,'0')} · {section.title}</motion.button>)}
          </div>
        </aside>

        <article className="min-w-0 rounded-[30px] border border-[#7b001c]/12 bg-white p-6 shadow-[0_26px_80px_rgba(70,0,18,.07)] md:p-9">
          <AnimatePresence mode="wait">
            <motion.div key={current.id} initial={{opacity:0,y:16}} animate={{opacity:1,y:0}} exit={{opacity:0,y:-10}} transition={{duration:.42,ease}}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="rounded-full bg-[#fff0f3] px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[.18em] text-[#7b001c]">{current.type}</span>
                <span className="text-xs text-[#5f6066]">Shared contract + visualization engine</span>
              </div>
              <h2 className="mt-5 text-4xl font-semibold tracking-[-.045em] sm:text-5xl">{current.title}</h2>
              <p className="mt-4 max-w-3xl text-lg leading-8 text-[#5f6066]">{getSectionSummary(current as Section)}</p>

              {'key_points' in current.content && Array.isArray((current.content as SectionContentWithKeyPoints).key_points) && <div className="mt-8 grid gap-3 sm:grid-cols-2">{((current.content as SectionContentWithKeyPoints).key_points as string[]).map((bullet:string,i:number)=><motion.div key={bullet} initial={{opacity:0,y:10}} animate={{opacity:1,y:0}} transition={{delay:i*.06}} className="rounded-2xl border border-[#7b001c]/10 bg-[#faf7f2] p-4 text-sm leading-6"><Check className="mb-2 text-[#b4002a]" size={17}/>{bullet}</motion.div>)}</div>}

              {visualization ? <div className="mt-8 overflow-hidden rounded-[26px] border border-[#7b001c]/12 bg-[#f7f1eb] p-2 sm:p-3"><div className="rounded-[20px] bg-white p-3 sm:p-4"><VisualizationRenderer data={visualization} subject="biology" /></div></div> : <div className="mt-8 rounded-[26px] border border-dashed border-[#7b001c]/15 bg-[#faf7f2] p-6 text-sm leading-6 text-[#5f6066]">{current.type === 'explanation' ? current.content.body : current.type === 'example' ? <><strong className="text-[#24161b]">Scenario:</strong> {current.content.scenario}<br/><br/><strong className="text-[#24161b]">Why it matters:</strong> {current.content.explanation}</> : 'This section is presented as structured text so the same content remains accessible even without a visualization.'}</div>}

              <div className="mt-8 flex flex-wrap justify-between gap-3 border-t border-[#7b001c]/10 pt-5">
                <button disabled={activeSection===0} onClick={()=>setActiveSection((value:number)=>Math.max(0,value-1))} className="focus-ring rounded-full border border-[#7b001c]/12 px-5 py-3 text-sm disabled:opacity-40">Previous</button>
                {activeSection<lesson.sections.length-1?<button onClick={()=>setActiveSection((value:number)=>value+1)} className="focus-ring inline-flex items-center gap-2 rounded-full bg-[#7b001c] px-5 py-3 text-sm font-semibold text-white">Next section <ArrowRight size={15}/></button>:<button onClick={onQuiz} className="focus-ring inline-flex items-center gap-2 rounded-full bg-[#b4002a] px-5 py-3 text-sm font-semibold text-white">Start practice <ArrowRight size={15}/></button>}
              </div>
            </motion.div>
          </AnimatePresence>
        </article>

        <aside className="rounded-[26px] border border-[#7b001c]/12 bg-[#130307] p-5 text-white">
          <div className="flex items-center gap-2 font-semibold"><MousePointer2 size={17}/> Learn your way</div>
          <p className="mt-2 text-sm leading-6 text-white/60">Control pacing, change representation and pause when you need another shape.</p>
          <div className="mt-5 rounded-2xl border border-white/10 bg-white/[.04] p-4"><div className="text-[10px] uppercase tracking-[.18em] text-white/35">Generation status</div><div className="mt-2 text-lg font-semibold text-white">{modeLabel}</div><div className="mt-2 text-xs text-white/45">{lessonMode === 'demo' ? (lessonId ? 'Demo lesson.' : 'Showing the checked-in example lesson.') : 'Generated from the connected lesson service.'}</div></div>
          <div className="mt-3 rounded-2xl border border-white/10 bg-white/[.04] p-4"><div className="text-[10px] uppercase tracking-[.18em] text-white/35">Accessibility</div><button type="button" onClick={()=>setHighContrast((value:boolean)=>!value)} className="focus-ring mt-3 w-full rounded-xl border border-white/10 bg-white/[.03] px-3 py-2.5 text-sm text-white transition hover:border-[#ff5278]/40 hover:bg-[#b4002a]/10">{highContrast?'Standard contrast':'High contrast'}</button></div>
        </aside>
      </div>
    </section>
    <SignalBand title="One lesson. Different representations." text="The same contract powers concepts, processes, comparisons, diagrams, charts and practice without changing the learner's place in the lesson."><MiniFan labels={['MAP','PROCESS','EXAMPLE']} dark/></SignalBand>
    <CompactFooter onBackHome={goHome}/>
  </motion.div>;
}

type QuizViewProps = {
  lesson: Lesson;
  question: number;
  answer: number | null;
  score: number;
  progress: number;
  choose: (index: number) => void;
  next: () => void;
  goHome: () => void;
};

function QuizView({ lesson, question, answer, score, progress, choose, next, goHome }: QuizViewProps) {
  const item = lesson.quiz[question];
  return (
    <motion.div key="quiz" {...pageFade} className="min-h-screen bg-[#faf7f2] text-[#24161b]">
      <section className="px-5 pb-12 pt-32 sm:px-8 md:px-10">
        <div className="mx-auto grid max-w-7xl gap-8 lg:grid-cols-[1fr_.72fr] lg:items-end">
          <div>
            <div className="text-[10px] font-semibold uppercase tracking-[.2em] text-[#b4002a]">04 · Practice</div>
            <RotatingHeadline prefix="Make understanding" words={['visible.','actionable.','memorable.','yours.']}/>
            <p className="mt-5 max-w-2xl text-base leading-7 text-[#5f6066] sm:text-lg">Answer, get feedback, and move on. No long forms and no waiting until the end.</p>
          </div>
          <MiniFan labels={['QUESTION','FEEDBACK','RESULT']}/>
        </div>
      </section>

      <section className="relative overflow-hidden bg-[#140208] px-5 py-16 text-white sm:px-8 md:px-10 md:py-20">
        <div className="pointer-events-none absolute inset-0 opacity-60 [background-image:radial-gradient(circle_at_80%_15%,rgba(255,82,120,.18),transparent_28%),linear-gradient(rgba(255,255,255,.045)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,.045)_1px,transparent_1px)] [background-size:auto,44px_44px,44px_44px]" />
        <div className="relative mx-auto max-w-4xl">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-[.2em] text-[#ff5278]">Quick check</div>
              <h2 className="mt-2 text-3xl font-semibold tracking-tight text-white sm:text-4xl">Check your understanding.</h2>
            </div>
            <div className="text-base font-medium text-white/75">{question + 1} / {lesson.quiz.length}</div>
          </div>
          <div className="mt-5 h-2 overflow-hidden rounded-full bg-white/12">
            <motion.div className="h-full rounded-full bg-[#ff5278] shadow-[0_0_18px_rgba(255,82,120,.55)]" animate={{ width: `${Math.max(8, progress)}%` }} transition={{ duration: .45, ease }} />
          </div>

          <div className="mt-8 rounded-[30px] border border-white/14 bg-[#1d0b10] p-6 shadow-[0_28px_90px_rgba(0,0,0,.42)] md:p-9">
            <AnimatePresence mode="wait">
              <motion.div key={question} initial={{ opacity: 0, x: 24, filter: 'blur(5px)' }} animate={{ opacity: 1, x: 0, filter: 'blur(0px)' }} exit={{ opacity: 0, x: -24, filter: 'blur(5px)' }} transition={{ duration: .42, ease }}>
                <div className="text-[11px] font-semibold uppercase tracking-[.18em] text-white/55">Question {String(question + 1).padStart(2, '0')}</div>
                <h3 className="mt-4 max-w-3xl text-2xl font-semibold leading-tight text-white sm:text-3xl">{item.prompt}</h3>

                <div className="mt-7 grid gap-3">
                  {item.options.map((option: { id: string; text: string }, index: number) => {
                    const selected = answer === index;
                    const correct = option.id === item.correct_option_id;
                    const state = answer === null
                      ? 'border-white/15 bg-[#241117] hover:border-[#ff5278]/55 hover:bg-[#2a1219]'
                      : selected && correct
                        ? 'border-[#ff5278]/70 bg-[#7b001c]/35'
                        : selected
                          ? 'border-red-300/45 bg-red-500/15'
                          : correct
                            ? 'border-[#ff5278]/55 bg-[#7b001c]/20'
                            : 'border-white/10 bg-[#1d0b10]';
                    return (
                      <motion.button
                        type="button"
                        key={option.id}
                        onClick={() => choose(index)}
                        whileHover={answer === null ? { x: 5 } : undefined}
                        whileTap={answer === null ? { scale: .995 } : undefined}
                        className={`group flex w-full items-center gap-3 rounded-2xl border p-4 text-left text-white transition-all duration-200 ${state}`}
                      >
                        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-white/25 bg-black/20 text-sm font-semibold text-white">{String.fromCharCode(65 + index)}</span>
                        <span className="flex-1 text-[16px] font-medium text-white sm:text-[17px]">{option.text}</span>
                        {answer !== null && correct && <Check className="text-[#ff5278]" size={18} />}
                        {answer === null && <ArrowRight className="opacity-0 transition group-hover:opacity-100" size={17} />}
                      </motion.button>
                    );
                  })}
                </div>

                {answer !== null && (
                  <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="mt-6 rounded-2xl border border-[#ff5278]/25 bg-[#7b001c]/18 p-5">
                    <div className="text-base font-semibold text-white">{answer !== null && item.options[answer]?.id === item.correct_option_id ? 'Correct.' : 'Here’s the idea.'}</div>
                    <p className="mt-1 text-sm leading-6 text-white/72">{item.explanation}</p>
                  </motion.div>
                )}

                <div className="mt-7 flex flex-wrap items-center justify-between gap-3">
                  <button type="button" onClick={goHome} className="rounded-full border border-white/15 px-4 py-3 text-sm font-medium text-white/80 transition hover:border-white/30 hover:bg-white/6">Exit practice</button>
                  {answer !== null && (
                    <motion.button type="button" onClick={next} whileHover={{ y: -2 }} whileTap={{ scale: .98 }} className="inline-flex items-center gap-2 rounded-full bg-white px-5 py-3 text-sm font-semibold text-[#140208] shadow-[0_12px_30px_rgba(255,255,255,.12)]">
                      {question === lesson.quiz.length - 1 ? 'See result' : 'Next question'} <ArrowRight size={16} />
                    </motion.button>
                  )}
                </div>
              </motion.div>
            </AnimatePresence>
          </div>
        </div>
      </section>

      <SignalBand title="Practice is part of the lesson." text="Immediate feedback keeps the learner in control and makes it easy to revisit the representation when something does not click."><MiniFan labels={['QUESTION','FEEDBACK','RETRY']} dark={false}/></SignalBand>
      <CompactFooter onBackHome={goHome}/>
    </motion.div>
  );
}

type AccessibilityViewProps = {
  highContrast: boolean;
  setHighContrast: React.Dispatch<React.SetStateAction<boolean>>;
  largeText: boolean;
  setLargeText: React.Dispatch<React.SetStateAction<boolean>>;
  reduceMotion: boolean;
  setReduceMotion: React.Dispatch<React.SetStateAction<boolean>>;
  goHome: () => void;
};

function AccessibilityView({ highContrast, setHighContrast, largeText, setLargeText, reduceMotion, setReduceMotion, goHome }: AccessibilityViewProps) {
  return (
    <motion.div key="accessibility" {...pageFade} className="min-h-screen bg-[#faf7f2] text-[#24161b]">
      <section className="px-5 pb-14 pt-32 sm:px-8 md:px-10">
        <div className="mx-auto max-w-7xl">
          <div className="inline-flex items-center gap-2 rounded-full border border-[#7b001c]/12 bg-white px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[.2em] text-[#7b001c]">06 · Accessibility</div>
          <div className="mt-6 max-w-4xl">
            <RotatingHeadline prefix="Make the interface" words={['clear.','comfortable.','controllable.','yours.']}/>
            <p className="mt-5 max-w-2xl text-base leading-7 text-[#5f6066] sm:text-lg">VisuaLearn keeps information visible, interaction predictable, and pacing under your control. These settings change the interface without changing the lesson content.</p>
          </div>

          <div className="mt-10 grid gap-4 lg:grid-cols-3">
            <AccessibilityCard title="Contrast" eyebrow="SEE MORE CLEARLY" icon={<Sparkles size={20}/>} active={highContrast} onClick={() => setHighContrast((value: boolean) => !value)} description="Increase text and control contrast for stronger separation." action={highContrast ? 'Standard contrast' : 'High contrast'} />
            <AccessibilityCard title="Readable type" eyebrow="MAKE TEXT EASIER" icon={<FileText size={20}/>} active={largeText} onClick={() => setLargeText((value: boolean) => !value)} description="Increase interface text size without changing the lesson layout." action={largeText ? 'Normal size' : 'Larger text'} />
            <AccessibilityCard title="Reduced motion" eyebrow="KEEP IT CALM" icon={<Gauge size={20}/>} active={reduceMotion} onClick={() => setReduceMotion((value: boolean) => !value)} description="Tone down non-essential movement and preserve the learning flow." action={reduceMotion ? 'Motion on' : 'Reduce motion'} />
          </div>
        </div>
      </section>

      <section className="bg-[#130307] px-5 py-16 text-white sm:px-8 md:px-10">
        <div className="mx-auto grid max-w-7xl gap-5 lg:grid-cols-[1.1fr_.9fr]">
          <div className="rounded-[30px] border border-white/10 bg-[#1d0b10] p-7 md:p-9">
            <div className="text-[10px] font-semibold uppercase tracking-[.2em] text-[#ff5278]">Design principles</div>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight text-white">Nothing important should depend on hearing, colour, or speed alone.</h2>
            <div className="mt-7 grid gap-3 sm:grid-cols-2">
              {['Visible interaction states','Keyboard-friendly controls','Learner-controlled pacing','Readable hierarchy'].map((item, i) => (
                <motion.div key={item} whileHover={{ y: -3 }} className="rounded-2xl border border-white/10 bg-white/[.035] p-4">
                  <div className="text-[10px] uppercase tracking-[.18em] text-white/40">0{i + 1}</div>
                  <div className="mt-2 font-semibold text-white">{item}</div>
                </motion.div>
              ))}
            </div>
          </div>
          <div className="rounded-[30px] border border-[#ff5278]/20 bg-[linear-gradient(145deg,rgba(180,0,42,.34),rgba(255,255,255,.035))] p-7 md:p-9">
            <div className="flex h-full min-h-[260px] flex-col justify-between">
              <div><div className="text-[10px] uppercase tracking-[.18em] text-[#ff5278]">Your control panel</div><div className="mt-3 text-2xl font-semibold text-white">Change the interface. Keep the learning.</div></div>
              <div className="space-y-3">
                <SettingRow label="High contrast" value={highContrast} onClick={() => setHighContrast((v: boolean) => !v)} />
                <SettingRow label="Larger text" value={largeText} onClick={() => setLargeText((v: boolean) => !v)} />
                <SettingRow label="Reduced motion" value={reduceMotion} onClick={() => setReduceMotion((v: boolean) => !v)} />
              </div>
            </div>
          </div>
        </div>
      </section>
      <CompactFooter onBackHome={goHome}/><div className="sr-only"><button onClick={goHome}>Back home</button></div>
    </motion.div>
  );
}

type AccessibilityCardProps = {
  title: string;
  eyebrow: string;
  icon: ReactNode;
  active: boolean;
  onClick: () => void;
  description: string;
  action: string;
};

function AccessibilityCard({ title, eyebrow, icon, active, onClick, description, action }: AccessibilityCardProps) {
  return <motion.button type="button" whileHover={{ y: -5 }} whileTap={{ scale: .99 }} onClick={onClick} className={`text-left rounded-[28px] border p-6 shadow-[0_18px_55px_rgba(70,0,18,.06)] transition ${active ? 'border-[#b4002a]/30 bg-[#fff0f3]' : 'border-[#7b001c]/12 bg-white hover:border-[#b4002a]/25'}`}><div className="flex items-center justify-between"><span className="grid h-10 w-10 place-items-center rounded-xl bg-[#fff0f3] text-[#b4002a]">{icon}</span><span className={`rounded-full px-3 py-1 text-[10px] font-semibold uppercase tracking-[.16em] ${active ? 'bg-[#b4002a] text-white' : 'bg-[#f4eee8] text-[#5f6066]'}`}>{active ? 'On' : 'Off'}</span></div><div className="mt-6 text-[10px] font-semibold uppercase tracking-[.18em] text-[#7b001c]">{eyebrow}</div><div className="mt-2 text-xl font-semibold">{title}</div><p className="mt-2 text-sm leading-6 text-[#5f6066]">{description}</p><div className="mt-5 inline-flex rounded-full border border-[#7b001c]/12 bg-[#faf7f2] px-4 py-2 text-xs font-semibold">{action}</div></motion.button>;
}

type SettingRowProps = {
  label: string;
  value: boolean;
  onClick: () => void;
};

function SettingRow({ label, value, onClick }: SettingRowProps) {
  return <button type="button" onClick={onClick} className="flex w-full items-center justify-between rounded-2xl border border-white/10 bg-white/[.035] px-4 py-3 text-left hover:border-[#ff5278]/40"><span className="text-sm font-medium text-white">{label}</span><span className={`relative h-6 w-11 rounded-full transition ${value ? 'bg-[#ff5278]' : 'bg-white/15'}`}><span className={`absolute top-1 h-4 w-4 rounded-full bg-white transition ${value ? 'left-6' : 'left-1'}`} /></span></button>;
}

type ResultViewProps = {
  lesson: Lesson;
  score: number;
  retry: () => void;
  goLesson: () => void;
  goHome: () => void;
};

function ResultView({ lesson, score, retry, goLesson, goHome }: ResultViewProps) {
  return <motion.div key="result" {...pageFade} className="min-h-screen bg-[#faf7f2] text-[#24161b]"><section className="px-5 pb-14 pt-32 sm:px-8 md:px-10"><div className="mx-auto max-w-7xl text-center"><div className="mx-auto grid h-16 w-16 place-items-center rounded-2xl bg-[#fff0f3] text-[#b4002a]"><Trophy size={28}/></div><div className="mt-6 text-[10px] font-semibold uppercase tracking-[.2em] text-[#7b001c]">05 · Result</div><RotatingHeadline prefix="You made the idea" words={['click.','stick.','visible.','yours.']}/><p className="mx-auto mt-5 max-w-2xl text-base leading-7 text-[#5f6066] sm:text-lg">A result should tell you what happened and make the next step obvious.</p><MiniFan labels={['SCORE','INSIGHT','NEXT STEP']}/></div></section><section className="bg-[#130307] px-5 py-16 text-white sm:px-8 md:px-10 md:py-20"><div className="mx-auto max-w-5xl"><div className="grid gap-4 md:grid-cols-[1.25fr_.75fr]"><div className="rounded-[30px] border border-white/10 bg-white/[.04] p-7 md:p-9"><div className="text-[10px] font-semibold uppercase tracking-[.2em] text-[#ff5278]">Practice complete</div><div className="mt-4 flex items-end gap-3"><div className="text-7xl font-semibold tracking-[-.07em]">{score}</div><div className="pb-3 text-xl text-white/35">/ {lesson.quiz.length}</div></div><p className="mt-3 max-w-xl text-white/50">Use the score to decide whether to retry, revisit a section, or move on.</p><div className="mt-7 grid gap-3 sm:grid-cols-3"><ResultStat n={`${Math.round(score/lesson.quiz.length*100)}%`} t="Score"/><ResultStat n={`${lesson.quiz.length}`} t="Questions"/><ResultStat n="Visual" t="Mode"/></div></div><div className="rounded-[30px] border border-[#ff5278]/20 bg-[linear-gradient(145deg,rgba(180,0,42,.34),rgba(255,255,255,.035))] p-7"><Sparkles className="text-[#ff5278]"/><div className="mt-4 text-xl font-semibold">Choose what happens next.</div><div className="mt-5 grid gap-2"><button type="button" onClick={retry} className="rounded-2xl border border-white/10 bg-white/[.04] px-4 py-3 text-left text-sm transition hover:-translate-y-0.5 hover:border-[#ff5278]/45">Retry practice</button><button type="button" onClick={goLesson} className="rounded-2xl border border-white/10 bg-white/[.04] px-4 py-3 text-left text-sm transition hover:-translate-y-0.5 hover:border-[#ff5278]/45">Revisit the lesson</button><button type="button" onClick={goHome} className="rounded-2xl bg-white px-4 py-3 text-left text-sm font-semibold text-[#130307] transition hover:-translate-y-0.5">Back to VisuaLearn</button></div></div></div></div></section><SignalBand title="Learning should adapt." text="The end of one practice loop is the beginning of the next representation."><MiniFan labels={['REVIEW','RETRY','MOVE ON']} dark/></SignalBand><CompactFooter onBackHome={goHome}/></motion.div>;
}

function HeroPill({ children, onClick }: { children: ReactNode; onClick: () => void }) {
  return <motion.button type="button" whileHover={{ y: -5, scale: 1.035 }} whileTap={{ scale: .97 }} onClick={onClick} className="hero-action group relative mx-[0.2em] mb-[0.4em] inline-flex items-center justify-center gap-1.5 overflow-hidden whitespace-nowrap rounded-full border border-white/20 bg-white px-4 py-[0.3em] text-[13px] font-medium text-black shadow-[0_14px_34px_rgba(0,0,0,.16)] transition-colors duration-200 hover:bg-[#b4002a] hover:text-white sm:px-5 sm:text-[15px]"><span className="pointer-events-none absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/35 to-transparent transition-transform duration-500 group-hover:translate-x-full" />{children}</motion.button>;
}

function FeatureChip({ text, icon }: { text: string; icon: ReactNode }) {
  return <motion.div whileHover={{ y: -3 }} className="hero-feature inline-flex items-center gap-1.5 rounded-full border border-white/20 bg-black/20 px-3 py-1.5 text-[12px] text-white/82 backdrop-blur-md transition-all duration-300 hover:border-white/40 hover:bg-white/10 sm:text-[13px]">{icon}{text}</motion.div>;
}

function Visualization({ kind, label }: { kind: string; label: string }) {
  const items = kind === 'process' ? ['Light', 'Chlorophyll', 'Energy conversion', 'Glucose + O₂'] : kind === 'map' ? ['Sunlight', 'Water', 'CO₂', 'Glucose', 'O₂'] : kind === 'comparison' ? ['Stores energy', 'Uses light', 'Builds glucose', 'Releases O₂'] : ['Input', 'Transform', 'Output'];
  return <section aria-label={label} className="mt-8 overflow-hidden rounded-[26px] border border-[#7b001c]/12 bg-[#f7f1eb]"><div className="flex items-center justify-between border-b border-[#7b001c]/10 bg-white px-5 py-4"><div><div className="text-[10px] font-semibold uppercase tracking-[.18em] text-[#5f6066]">Visualization placeholder</div><div className="mt-1 font-semibold">{label}</div></div><span className="text-[10px] uppercase tracking-[.16em] text-[#5f6066]">Person 3 boundary</span></div><div className="p-5 md:p-6">{kind==='chart'?<div className="flex h-44 items-end gap-3">{[35,62,48,82,68,92].map((height,index)=><motion.div key={index} initial={{height:0}} animate={{height:`${height}%`}} transition={{delay:index*.06,duration:.5,ease}} className="flex-1 rounded-t-xl bg-[#b4002a]/75"/> )}</div>:<div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{items.map((item,index)=><motion.div key={item} initial={{opacity:0,y:8}} animate={{opacity:1,y:0}} transition={{delay:index*.07}} className="rounded-2xl border border-[#7b001c]/10 bg-white p-4"><div className="text-[10px] uppercase tracking-[.18em] text-[#5f6066]">0{index+1}</div><div className="mt-2 font-semibold">{item}</div>{index<items.length-1&&kind==='process'&&<div className="mt-3 text-xs text-[#b4002a]">↓ next stage</div>}</motion.div>)}</div>}<div className="mt-5 rounded-2xl border border-dashed border-[#7b001c]/12 bg-white p-4 text-sm text-[#5f6066]"><span className="font-semibold text-[#24161b]">Renderer contract:</span> <code className="rounded bg-[#f1ede6] px-1.5 py-0.5">VisualizationRenderer data={'{visualizationData}'}</code></div></div></section>;
}

function ResultStat({ n, t }: { n: string; t: string }) { return <div className="rounded-2xl border border-white/10 bg-white/[.03] p-4"><div className="text-2xl font-semibold">{n}</div><div className="mt-1 text-[10px] uppercase tracking-[.18em] text-white/35">{t}</div></div>; }
