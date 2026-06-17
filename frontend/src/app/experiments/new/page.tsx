"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import { api } from "@/lib/api";
import type { Dataset } from "@/lib/types";

const EVALUATOR_TYPES = ["exact_match", "embedding_similarity", "llm_judge", "agent_trace"];
const STEPS = ["Basic Info", "Dataset & Model", "Evaluator Config"];

export default function NewExperimentPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [form, setForm] = useState({
    name: "",
    description: "",
    model_name: "claude-haiku-4-5-20251001",
    prompt_template: "",
    tags: [] as string[],
    dataset_id: "",
    evaluator_type: "exact_match",
    max_attempts: 3,
    run_immediately: false,
  });
  const [tagInput, setTagInput] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const { data: datasets } = useSWR("datasets-list", () => api.datasets.list({ limit: 100 }));

  function update(key: string, value: unknown) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function addTag() {
    if (tagInput.trim() && !form.tags.includes(tagInput.trim())) {
      update("tags", [...form.tags, tagInput.trim()]);
    }
    setTagInput("");
  }

  async function submit() {
    setSubmitting(true);
    try {
      const exp = await api.experiments.create({
        name: form.name,
        description: form.description || undefined,
        dataset_id: form.dataset_id || undefined,
        model_name: form.model_name || undefined,
        prompt_template: form.prompt_template || undefined,
        tags: form.tags,
        config: { evaluator_type: form.evaluator_type, max_attempts: form.max_attempts },
      } as Parameters<typeof api.experiments.create>[0]);

      if (form.run_immediately && exp.id) {
        await api.experiments.run(exp.id);
      }
      router.push(`/experiments/${exp.id}`);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-xl font-semibold mb-6">New Experiment</h1>

      {/* Step indicator */}
      <div className="flex gap-2 mb-8">
        {STEPS.map((label, i) => (
          <div key={i} className="flex items-center gap-2">
            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
              i <= step ? "bg-blue-600 text-white" : "bg-gray-200 text-gray-500"
            }`}>{i + 1}</div>
            <span className={`text-sm ${i === step ? "text-gray-900 font-medium" : "text-gray-400"}`}>{label}</span>
            {i < STEPS.length - 1 && <div className="w-8 h-px bg-gray-300 mx-1" />}
          </div>
        ))}
      </div>

      <div className="bg-white border border-gray-200 rounded-xl p-6 space-y-4">
        {step === 0 && (
          <>
            <Field label="Name *">
              <input className="input" value={form.name} onChange={e => update("name", e.target.value)} placeholder="e.g. GPT-4o accuracy eval" />
            </Field>
            <Field label="Description">
              <textarea className="input h-20 resize-none" value={form.description} onChange={e => update("description", e.target.value)} placeholder="What are you evaluating?" />
            </Field>
            <Field label="Tags">
              <div className="flex gap-2">
                <input className="input flex-1" value={tagInput} onChange={e => setTagInput(e.target.value)}
                  onKeyDown={e => e.key === "Enter" && (e.preventDefault(), addTag())}
                  placeholder="Add tag, press Enter" />
                <button onClick={addTag} className="btn-secondary text-sm px-3">Add</button>
              </div>
              <div className="flex flex-wrap gap-1 mt-2">
                {form.tags.map(t => (
                  <span key={t} className="bg-blue-100 text-blue-700 text-xs px-2 py-0.5 rounded-full flex items-center gap-1">
                    {t}
                    <button onClick={() => update("tags", form.tags.filter(x => x !== t))} className="text-blue-400 hover:text-blue-700">×</button>
                  </span>
                ))}
              </div>
            </Field>
          </>
        )}

        {step === 1 && (
          <>
            <Field label="Dataset">
              <select className="input" value={form.dataset_id} onChange={e => update("dataset_id", e.target.value)}>
                <option value="">— Select dataset —</option>
                {datasets?.items.map((d: Dataset) => (
                  <option key={d.id} value={d.id}>{d.name} ({d.row_count ?? "?"} rows)</option>
                ))}
              </select>
            </Field>
            <Field label="Model">
              <input className="input" value={form.model_name} onChange={e => update("model_name", e.target.value)} placeholder="claude-haiku-4-5-20251001" />
            </Field>
            <Field label="System Prompt Template">
              <textarea className="input h-24 resize-none font-mono text-xs" value={form.prompt_template}
                onChange={e => update("prompt_template", e.target.value)} placeholder="You are a helpful assistant. Evaluate: {question}" />
            </Field>
          </>
        )}

        {step === 2 && (
          <>
            <Field label="Evaluator Type">
              <select className="input" value={form.evaluator_type} onChange={e => update("evaluator_type", e.target.value)}>
                {EVALUATOR_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </Field>
            <Field label="Max Retries per Task">
              <input className="input" type="number" min={1} max={10} value={form.max_attempts} onChange={e => update("max_attempts", Number(e.target.value))} />
            </Field>
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input type="checkbox" checked={form.run_immediately} onChange={e => update("run_immediately", e.target.checked)} />
              Run immediately after creation
            </label>

            <div className="mt-4 p-4 bg-gray-50 rounded-lg text-sm text-gray-600 space-y-1">
              <p><strong>Summary</strong></p>
              <p>Name: {form.name}</p>
              <p>Dataset: {datasets?.items.find((d: Dataset) => d.id === form.dataset_id)?.name ?? "None"}</p>
              <p>Model: {form.model_name}</p>
              <p>Evaluator: {form.evaluator_type}</p>
            </div>
          </>
        )}
      </div>

      <div className="flex justify-between mt-6">
        <button onClick={() => setStep(s => s - 1)} disabled={step === 0} className="btn-secondary disabled:opacity-40">
          Back
        </button>
        {step < STEPS.length - 1 ? (
          <button onClick={() => setStep(s => s + 1)} disabled={step === 0 && !form.name.trim()} className="btn-primary disabled:opacity-40">
            Next
          </button>
        ) : (
          <button onClick={submit} disabled={submitting || !form.name.trim()} className="btn-primary disabled:opacity-40">
            {submitting ? "Creating…" : "Create Experiment"}
          </button>
        )}
      </div>

      <style jsx>{`
        .input { @apply w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500; }
        .btn-primary { @apply bg-blue-600 text-white px-5 py-2 rounded-lg text-sm hover:bg-blue-700 transition-colors; }
        .btn-secondary { @apply border border-gray-300 text-gray-700 px-5 py-2 rounded-lg text-sm hover:bg-gray-50 transition-colors; }
      `}</style>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      {children}
    </div>
  );
}
