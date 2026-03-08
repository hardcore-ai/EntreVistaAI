"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getEvaluation, submitDecision } from "@/lib/api";
import type { Evaluation, Message, CompetencyScore } from "@/lib/types";
import { CheckCircle, XCircle, ChevronLeft, MessageSquare, BarChart2 } from "lucide-react";

const REC_MAP: Record<string, { label: string; className: string }> = {
  highly_recommended: { label: "Muy recomendado", className: "bg-green-100 text-green-700 border-green-200" },
  recommended: { label: "Recomendado", className: "bg-blue-100 text-blue-700 border-blue-200" },
  needs_review: { label: "Necesita revisión", className: "bg-yellow-100 text-yellow-700 border-yellow-200" },
  not_recommended: { label: "No recomendado", className: "bg-red-100 text-red-700 border-red-200" },
};

export default function CandidateDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"evaluation" | "transcript">("evaluation");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getEvaluation(id).then(setEvaluation).finally(() => setLoading(false));
  }, [id]);

  async function handleDecision(decision: "approved" | "rejected") {
    if (!evaluation) return;
    setSubmitting(true);
    setError("");
    try {
      const updated = await submitDecision(evaluation.id, decision, notes || undefined);
      setEvaluation(updated);
    } catch {
      setError("Error al guardar la decisión. Intenta de nuevo.");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) return <div className="p-8 text-gray-400">Cargando evaluación...</div>;
  if (!evaluation) return <div className="p-8 text-red-500">Evaluación no encontrada.</div>;

  const rec = REC_MAP[evaluation.ai_recommendation || ""] || { label: "—", className: "bg-gray-100 text-gray-500" };
  const isPending = evaluation.status === "pending_review" || evaluation.status === "escalated";

  return (
    <div className="p-8 max-w-5xl">
      {/* Header */}
      <button onClick={() => router.back()} className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-6">
        <ChevronLeft className="w-4 h-4" /> Volver
      </button>

      <div className="flex items-start justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">{evaluation.candidate_name || "Candidato"}</h2>
          <p className="text-sm text-gray-500">{evaluation.campaign_title}</p>
        </div>
        <div className="flex items-center gap-3">
          {evaluation.overall_score !== null && (
            <div className="text-center">
              <p className="text-3xl font-bold text-gray-900">{evaluation.overall_score.toFixed(0)}</p>
              <p className="text-xs text-gray-400">Score /100</p>
            </div>
          )}
          <div className={`border px-3 py-1 rounded-full text-sm font-medium ${rec.className}`}>
            {rec.label}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-4 mb-6 border-b border-gray-200">
        {([["evaluation", "Evaluación", BarChart2], ["transcript", "Transcripción", MessageSquare]] as const).map(([key, label, Icon]) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`flex items-center gap-1.5 pb-3 text-sm font-medium border-b-2 transition -mb-px ${
              activeTab === key ? "border-brand-600 text-brand-600" : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            <Icon className="w-4 h-4" />
            {label}
          </button>
        ))}
      </div>

      {activeTab === "evaluation" && (
        <div className="space-y-6">
          {/* Summary */}
          <div className="bg-white border border-gray-200 rounded-xl p-5">
            <h3 className="font-semibold mb-2">Resumen ejecutivo</h3>
            <p className="text-gray-700 text-sm">{evaluation.summary || "Sin resumen."}</p>
          </div>

          {/* Strengths & Concerns */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-green-50 border border-green-100 rounded-xl p-4">
              <h4 className="font-semibold text-green-800 mb-2 text-sm">Fortalezas</h4>
              <ul className="space-y-1">
                {evaluation.strengths.map((s, i) => (
                  <li key={i} className="text-sm text-green-700 flex items-start gap-1.5">
                    <CheckCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" /> {s}
                  </li>
                ))}
              </ul>
            </div>
            <div className="bg-red-50 border border-red-100 rounded-xl p-4">
              <h4 className="font-semibold text-red-800 mb-2 text-sm">Preocupaciones</h4>
              <ul className="space-y-1">
                {evaluation.concerns.map((c, i) => (
                  <li key={i} className="text-sm text-red-700 flex items-start gap-1.5">
                    <XCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" /> {c}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Competency Scores */}
          <div className="bg-white border border-gray-200 rounded-xl p-5">
            <h3 className="font-semibold mb-4">Evaluación por competencias</h3>
            <div className="space-y-5">
              {evaluation.competency_scores.map((cs: CompetencyScore, i) => (
                <div key={i}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium">{cs.competency}</span>
                    <span className="text-sm font-bold">{cs.score}/5</span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-2 mb-2">
                    <div
                      className="bg-brand-600 h-2 rounded-full"
                      style={{ width: `${(cs.score / 5) * 100}%` }}
                    />
                  </div>
                  <p className="text-xs text-gray-600 mb-1">{cs.rationale}</p>
                  {cs.quotes.length > 0 && (
                    <div className="mt-1 space-y-1">
                      {cs.quotes.map((q, qi) => (
                        <blockquote key={qi} className="text-xs text-gray-500 border-l-2 border-gray-300 pl-2 italic">
                          "{q}"
                        </blockquote>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* HITL Decision Panel */}
          {isPending ? (
            <div className="bg-white border border-brand-200 rounded-xl p-5">
              <h3 className="font-semibold mb-3">Decisión del reclutador</h3>
              <p className="text-xs text-gray-500 mb-3">
                La IA recomienda, pero la decisión final es tuya. Esta acción queda registrada en el historial de auditoría.
              </p>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Notas opcionales para justificar tu decisión..."
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm mb-3 focus:outline-none focus:ring-2 focus:ring-brand-500"
                rows={2}
              />
              {error && <p className="text-red-500 text-sm mb-2">{error}</p>}
              <div className="flex gap-3">
                <button
                  onClick={() => handleDecision("approved")}
                  disabled={submitting}
                  className="flex-1 bg-green-600 text-white py-2 rounded-lg font-medium hover:bg-green-700 disabled:opacity-60 flex items-center justify-center gap-2"
                >
                  <CheckCircle className="w-4 h-4" /> Aprobar candidato
                </button>
                <button
                  onClick={() => handleDecision("rejected")}
                  disabled={submitting}
                  className="flex-1 bg-red-600 text-white py-2 rounded-lg font-medium hover:bg-red-700 disabled:opacity-60 flex items-center justify-center gap-2"
                >
                  <XCircle className="w-4 h-4" /> Rechazar candidato
                </button>
              </div>
            </div>
          ) : (
            <div className={`rounded-xl p-4 ${evaluation.status === "approved" ? "bg-green-50 border border-green-200" : "bg-red-50 border border-red-200"}`}>
              <p className="text-sm font-medium">
                {evaluation.status === "approved" ? "✅ Candidato aprobado" : "❌ Candidato rechazado"}
              </p>
              {evaluation.human_notes && <p className="text-xs text-gray-600 mt-1">"{evaluation.human_notes}"</p>}
              {evaluation.human_disagrees && (
                <p className="text-xs text-orange-600 mt-1">⚠️ El reclutador discrepó con la recomendación de la IA.</p>
              )}
            </div>
          )}
        </div>
      )}

      {activeTab === "transcript" && (
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <h3 className="font-semibold mb-4">Transcripción completa</h3>
          <div className="space-y-3 max-h-[600px] overflow-y-auto pr-2">
            {evaluation.conversation_history.map((msg: Message, i) => (
              <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-[75%] rounded-2xl px-4 py-2.5 text-sm ${
                    msg.role === "user"
                      ? "bg-brand-600 text-white rounded-tr-sm"
                      : "bg-gray-100 text-gray-800 rounded-tl-sm"
                  }`}
                >
                  <p className="text-xs opacity-70 mb-0.5">{msg.role === "user" ? "Candidato" : "EntreVista AI"}</p>
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
