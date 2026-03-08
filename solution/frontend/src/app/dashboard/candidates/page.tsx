"use client";

import { useEffect, useState } from "react";
import { getEvaluations } from "@/lib/api";
import type { Evaluation } from "@/lib/types";
import { useRouter } from "next/navigation";

const STATUS_TABS = [
  { key: "pending_review", label: "Pendientes" },
  { key: "approved", label: "Aprobados" },
  { key: "rejected", label: "Rechazados" },
  { key: "", label: "Todos" },
];

const REC_MAP: Record<string, { label: string; className: string }> = {
  highly_recommended: { label: "Muy recomendado", className: "bg-green-100 text-green-700" },
  recommended: { label: "Recomendado", className: "bg-blue-100 text-blue-700" },
  needs_review: { label: "Revisar", className: "bg-yellow-100 text-yellow-700" },
  not_recommended: { label: "No recomendado", className: "bg-red-100 text-red-700" },
};

export default function CandidatesPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState("pending_review");
  const [evaluations, setEvaluations] = useState<Evaluation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getEvaluations(activeTab ? { status: activeTab } : {})
      .then(setEvaluations)
      .finally(() => setLoading(false));
  }, [activeTab]);

  return (
    <div className="p-8">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Cola de revisión HITL</h2>
        <p className="text-sm text-gray-500 mt-1">Revisa las evaluaciones del agente y toma la decisión final.</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-gray-100 p-1 rounded-lg w-fit">
        {STATUS_TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition ${
              activeTab === tab.key ? "bg-white shadow text-gray-900" : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-gray-400">Cargando...</div>
      ) : evaluations.length === 0 ? (
        <div className="text-center py-16 text-gray-400">No hay evaluaciones en esta categoría.</div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 uppercase text-xs">
              <tr>
                <th className="text-left px-5 py-3">Candidato</th>
                <th className="text-left px-5 py-3">Campaña</th>
                <th className="text-center px-5 py-3">Score</th>
                <th className="text-left px-5 py-3">Recomendación IA</th>
                <th className="text-center px-5 py-3">Estado</th>
                <th className="text-center px-5 py-3">Acción</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {evaluations.map((ev) => {
                const rec = REC_MAP[ev.ai_recommendation || ""] || { label: "—", className: "bg-gray-100 text-gray-500" };
                const statusLabel = ev.status === "pending_review" ? "Pendiente" : ev.status === "approved" ? "Aprobado" : "Rechazado";
                const statusClass = ev.status === "pending_review" ? "bg-yellow-50 text-yellow-700" : ev.status === "approved" ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700";
                return (
                  <tr key={ev.id} className="hover:bg-gray-50">
                    <td className="px-5 py-3 font-medium">{ev.candidate_name || "Sin nombre"}</td>
                    <td className="px-5 py-3 text-gray-500">{ev.campaign_title || "—"}</td>
                    <td className="px-5 py-3 text-center font-bold">
                      {ev.overall_score !== null ? `${ev.overall_score.toFixed(0)}/100` : "—"}
                    </td>
                    <td className="px-5 py-3">
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${rec.className}`}>{rec.label}</span>
                    </td>
                    <td className="px-5 py-3 text-center">
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${statusClass}`}>{statusLabel}</span>
                    </td>
                    <td className="px-5 py-3 text-center">
                      <button
                        onClick={() => router.push(`/dashboard/candidates/${ev.session_id}`)}
                        className="text-xs bg-brand-600 text-white px-3 py-1 rounded-full hover:bg-brand-700"
                      >
                        {ev.status === "pending_review" ? "Revisar" : "Ver"}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
